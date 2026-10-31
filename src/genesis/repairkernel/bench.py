"""The testbed's world (kernel side): jobs over one component, in a sandbox directory.

A **job** runs a long workload against the component whose source is the sandbox file `<target>.py`, checks every
observation against the kernel's reference model, and checkpoints every `every` operations (`state.json`: the
operation index and the component's attributes). It stops at the first failure: a crash inside the component, or a
`Divergence` when an observation differs from the reference (the job's own validation). `resume()` continues from
the last checkpoint with whatever the sandbox file now holds.

What the research plane receives is the job's handle (`Handle` in one process, for tests; `foundry` serves the same
interface across the isolation boundary): run and resume; the repairable file and its source; the visible tests; and
`trial(seed, n)`, a runner for a fresh workload of its own choosing (or the failing segment from the last checkpoint),
returning pass, crash or divergence, the line events it took and, if asked, what the probe saw (`Observer`: the lines
executed and the component's state at every method return). The reference models, the hidden tests and the kernel's
own seeds stay here."""
import copy
import json
import random
from pathlib import Path
import shutil
import sys
import types

from . import guard as GD
from . import targets as TG
from .. import wire as W

# What a job's checkpoint may hold besides plain data (B20R184-PICKLE: tagged JSON, not pickle): the reference
# models, and the function the memo component is built with.
WIRE_ALLOWED = tuple(sorted(set(TG.REFERENCE.values()), key=lambda c: c.__name__)) + (TG._f,)
STATE = 'state.data.json'


class Divergence(AssertionError):
    """An observation differs from the reference: the job's validation failed."""


def _op_of(message):
    try:
        return int(message.split(':')[0].split()[1])
    except (IndexError, ValueError):
        return None


class StepLimit(RuntimeError):
    """A run exceeded its step budget (an infinite loop in a candidate)."""


def load_source(src, name, filename):
    mod = types.ModuleType(name)
    mod.__file__ = filename
    code = compile(src, filename, 'exec')
    exec(code, mod.__dict__)
    return mod


def _limited(fn, steps, filename, hook=None, count=None):
    """Run fn() counting the lines executed in `filename` (in `count[0]`, if given); StepLimit past `steps`.
    `hook(frame, event)`, if given, sees every line and return event in `filename` (it sees only the component's own
    frames)."""
    count = [0] if count is None else count

    def tracer(frame, event, arg):
        if frame.f_code.co_filename != filename:
            return None

        def local(frame, event, arg):
            if event == 'line':
                count[0] += 1
                if count[0] > steps:
                    raise StepLimit(f'more than {steps} steps')
            if hook is not None and event in ('line', 'return'):
                hook(frame, event)
            return local
        return local
    old = sys.gettrace()
    sys.settrace(tracer)
    try:
        return fn()
    finally:
        sys.settrace(old)


def _ref_call(obj, method, args):
    try:
        return ('ok', getattr(obj, method)(*copy.deepcopy(args)))
    except (KeyError, IndexError, ValueError) as e:
        return ('raise', type(e).__name__)


def _comp_call(obj, method, args, want):
    """The component's call. Where the reference raises, the component must raise the same; elsewhere its
    exceptions propagate (a crash inside the component, with its traceback)."""
    if want[0] == 'raise':
        try:
            return ('ok', getattr(obj, method)(*copy.deepcopy(args)))
        except (KeyError, IndexError, ValueError) as e:
            return ('raise', type(e).__name__)
    return ('ok', getattr(obj, method)(*copy.deepcopy(args)))


def _snapshot(obj):
    return copy.deepcopy(obj.__dict__)


def _restore(cls, d):
    obj = cls.__new__(cls)
    obj.__dict__.update(copy.deepcopy(d))
    return obj


class KernelFault(RuntimeError):
    """A planted fault in the kernel's own code (the benchmark's protected-fault control): not Genesis's to repair."""


def _kernel_check(i, fault_at):
    if fault_at is not None and i == fault_at:
        raise KernelFault(f'op {i}: the reference model failed (planted kernel fault)')


def execute(target, mod, cargs, ckw, op_list, start=0, state=None, check=True, progress=None, fault_at=None):
    """Run op_list[start:] on the component (from `state`, the component's attributes and the reference's, or fresh);
    returns (component attributes, reference, index reached). Raises the component's exception, or Divergence; or,
    at operation `fault_at`, a KernelFault (a control)."""
    cls = getattr(mod, TG.CLASS[target])
    ref_cls = TG.REFERENCE[target]
    if state is None:
        comp, ref = cls(*cargs, **ckw), ref_cls(*cargs, **ckw)
        snap = None
    else:
        comp, ref, snap = _restore(cls, state['comp']), copy.deepcopy(state['ref']), state.get('snap')
    for i in range(start, len(op_list)):
        if progress is not None:
            progress[0] = i
        method, args = op_list[i]
        _kernel_check(i, fault_at)
        if method == 'observe':
            name = TG.OBSERVE[target]
            got = getattr(comp, name)()
            if TG.COMPARE_OBSERVE[target] and check:
                want = getattr(ref, name)()
                if got != want:
                    raise Divergence(f'op {i}: {name}() gave {got!r}, the job expected {want!r}')
            continue
        if target == 'window' and method in ('save', 'restore'):
            if method == 'save':
                snap = comp.state()
                ref.save()
            elif snap is not None:
                comp = cls.load(snap)
                ref.restore()
            continue
        want = _ref_call(ref, method, args)
        got = _comp_call(comp, method, args, want)
        if check and not (target == 'registry' and method == 'add') and got != want:
            raise Divergence(f'op {i}: {method}{tuple(args)!r} gave {got!r}, the job expected {want!r}')
    return {'comp': _snapshot(comp), 'ref': copy.deepcopy(ref), 'snap': copy.deepcopy(snap)}, len(op_list)


CONTAINERS = (list, dict, set, tuple)
SCALARS = (int, float, str, bool, type(None))


def _copy_state(d):
    """The component's attributes as plain builtins (containers copied; anything else by its repr)."""
    out = {}
    for k, v in d.items():
        if isinstance(v, dict):
            out[k] = {kk: (vv if isinstance(vv, SCALARS + (tuple,)) else repr(vv)) for kk, vv in v.items()}
        elif isinstance(v, set):
            out[k] = set(v)
        elif isinstance(v, CONTAINERS):
            out[k] = [x if isinstance(x, SCALARS + (tuple,)) else repr(x) for x in v]
        elif isinstance(v, SCALARS):
            out[k] = v
        else:
            out[k] = repr(v)
    return out


class Observer:
    """The probe: the lines of the component executed, and its state at every method return but `__init__`."""

    def __init__(self):
        self.lines, self.returns = set(), []

    def hook(self, frame, event):
        if event == 'line':
            self.lines.add(frame.f_lineno)
        elif event == 'return':
            slf = frame.f_locals.get('self')
            if slf is not None and frame.f_code.co_name != '__init__':
                try:
                    self.returns.append((frame.f_code.co_name, _copy_state(dict(vars(slf)))))
                except TypeError:
                    pass


def make_runner(target, filename, cargs, ckw, op_list, start, state, original=None):
    """A runner for op_list[start:] from `state` (see `Handle.trial`). With `original`, a candidate the guard refuses
    is not executed."""
    progress = [start]

    def runner(src, steps=200000, observe=None):
        count = [0]
        if original is not None and src != original:
            why = GD.check(original, src)
            if why:
                return {'status': 'crash', 'exception': 'Refused', 'message': why, 'op': 0, 'of': len(op_list) - start,
                        'steps': 0}
        ob = Observer() if observe == 'full' else None
        try:
            mod = load_source(src, f'trial_{target}', filename)
            _limited(lambda: execute(target, mod, cargs, ckw, op_list, start, state, progress=progress), steps,
                     filename, ob.hook if ob else None, count)
        except Divergence as e:
            out = {'status': 'diverge', 'exception': 'Divergence', 'message': str(e),
                   'op': (_op_of(str(e)) or start) - start, 'of': len(op_list) - start}
        except Exception as e:                                      # noqa: BLE001 - a candidate may raise anything
            out = {'status': 'crash', 'exception': type(e).__name__, 'message': str(e)[:200],
                   'op': progress[0] - start, 'of': len(op_list) - start}
        else:
            out = {'status': 'pass', 'op': len(op_list) - start, 'of': len(op_list) - start}
        out['steps'] = count[0]
        if ob:
            out['obs'] = {'lines': ob.lines, 'returns': ob.returns}
        return out
    runner.cost = len(op_list) - start
    return runner


class Job:
    """A job over a component in `workdir` (kernel side)."""

    def __init__(self, workdir, target, seed, n_ops=2400, every=200, source=None, fault_at=None, version=None):
        """`version` 1 (B20_R178): resume continues from the last checkpoint. Version 2 (B20_R180): every checkpoint
        is kept, and a resume that fails steps back to the latest checkpoint from which the job then finishes (a
        defect can corrupt saved state long before it is noticed: a stale cache, a wrong index). The version is kept
        in the job's directory (`job.json`), so that the verifier and the kernel rebuild the same job."""
        self.fault_at = fault_at
        self.dir = Path(workdir)
        self.dir.mkdir(parents=True, exist_ok=True)
        meta = self.dir / 'job.json'
        if version is None:
            version = json.loads(meta.read_text())['version'] if meta.exists() else 1
        else:
            meta.write_text(json.dumps({'version': version}))
        self.version = version
        self.target, self.seed, self.n_ops, self.every = target, seed, n_ops, every
        self.file = self.dir / f'{target}.py'
        if source is not None:
            self.file.write_text(source)
        rng = random.Random(f'job|{target}|{seed}')
        self.cargs, self.ckw = TG.make_args(target, rng)
        self.ops = TG.ops(target, rng, n_ops)
        self.ckpt = self.dir / 'state.json'
        self.log = self.dir / 'job.log'

    def module(self, src=None, tag='live'):
        return load_source(self.file.read_text() if src is None else src, f'job_{self.target}_{tag}', str(self.file))

    def _save(self, i, state):
        data = W.dumps(state, WIRE_ALLOWED)
        (self.dir / STATE).write_text(data)
        if self.version >= 2:
            (self.dir / 'checkpoints').mkdir(exist_ok=True)
            (self.dir / 'checkpoints' / f'{i:07d}.json').write_text(data)
        self.ckpt.write_text(json.dumps({'next': i, 'source_sha256': self._source_sha()}))

    def _source_sha(self):
        import hashlib
        return hashlib.sha256(self.file.read_bytes()).hexdigest()

    def _load_meta(self):
        return json.loads(self.ckpt.read_text()) if self.ckpt.exists() else {}

    def checkpoints(self):
        """The kept checkpoints (version 2), latest first, with 0 (the fresh start) last."""
        d = self.dir / 'checkpoints'
        ks = sorted((int(p.stem) for p in d.glob('*.json')), reverse=True) if d.exists() else []
        return ks + [0]

    def _load(self):
        if not self.ckpt.exists():
            return 0, None
        return json.loads(self.ckpt.read_text())['next'], W.loads((self.dir / STATE).read_text(), WIRE_ALLOWED)

    def run(self, resume=False, steps=10 ** 7):
        """Run (or resume) to the end; {'status': 'done'|'failed', 'traceback', 'op', 'started'}. In version 2 a
        failed resume steps back through the kept checkpoints ('rolled_back_from' says where it was interrupted)."""
        produced_by = self._load_meta().get('source_sha256')
        first = self._run(resume, steps)
        if first['status'] == 'done' or not resume or self.version < 2:
            return first
        if produced_by == self._source_sha():              # the same source made the checkpoint: nothing to undo
            return first
        interrupted = first['started']
        for k in self.checkpoints():
            if k >= interrupted:
                continue
            if k == 0:
                for f in ('state.json', STATE):
                    (self.dir / f).unlink(missing_ok=True)
            else:
                (self.dir / STATE).write_text((self.dir / 'checkpoints' / f'{k:07d}.json').read_text())
                self.ckpt.write_text(json.dumps({'next': k, 'source_sha256': produced_by}))
            r = self._run(True, steps)
            if r['status'] == 'done':
                r['rolled_back_from'] = interrupted
                return r
        first['rolled_back_from'] = interrupted
        return first

    def _run(self, resume=False, steps=10 ** 7):
        import traceback
        mod = self.module()
        start, state = self._load() if resume else (0, None)
        if not resume:
            for f in ('state.json', STATE):
                (self.dir / f).unlink(missing_ok=True)
            if (self.dir / 'checkpoints').exists():
                shutil.rmtree(self.dir / 'checkpoints')
        i = start
        started = start
        try:
            while i < len(self.ops):
                end = min(len(self.ops), i + self.every)
                seg = self.ops[:end]
                state, _ = _limited(lambda: execute(self.target, mod, self.cargs, self.ckw, seg, i, state,
                                                    fault_at=self.fault_at), steps, str(self.file))
                i = end
                self._save(i, state)
        except Exception:
            tb = traceback.format_exc()
            with self.log.open('a') as f:
                f.write(tb)
            return {'status': 'failed', 'traceback': tb, 'op': i, 'started': started}
        return {'status': 'done', 'op': i, 'started': started}

    def trial_spec(self, seed=None, n=None, whole=False):
        """What a runner needs (for the trial executor): the failing segment from the last checkpoint (seed None), the
        job's whole workload from its start (seed None, whole: no saved state, which a defect may have corrupted), or
        a fresh workload of n operations from the caller's seed."""
        if seed is None and whole:
            return {'target': self.target, 'filename': str(self.file), 'cargs': self.cargs, 'ckw': self.ckw,
                    'ops': self.ops, 'start': 0, 'state': None}
        if seed is None:
            i, state = self._load()
            return {'target': self.target, 'filename': str(self.file), 'cargs': self.cargs, 'ckw': self.ckw,
                    'ops': self.ops, 'start': i, 'state': state}
        rng = random.Random(f'trial|{self.target}|{seed}')
        cargs, ckw = TG.make_args(self.target, rng)
        return {'target': self.target, 'filename': str(self.file), 'cargs': cargs, 'ckw': ckw,
                'ops': TG.ops(self.target, rng, n or 200), 'start': 0, 'state': None}


class Handle:
    """What the research plane receives: the job's public face."""

    def __init__(self, job):
        self._job = job
        self.repairable = [str(job.file)]
        self.validation = ('Divergence',)

    def run(self, resume=False):
        return self._job.run(resume=resume)

    def source(self):
        return self._job.file.read_text()

    def visible_tests(self):
        return list(TG.VISIBLE_TESTS[self._job.target])

    def trial(self, seed=None, n=None, whole=False):
        """A runner for a workload: the failing segment (seed None: from the last checkpoint to the job's end), or a
        fresh workload of n operations from `seed` (the caller's own seeds). `runner(src, steps, observe)` returns
        {'status': 'pass'|'crash'|'diverge', 'exception', 'message', 'op', 'of', 'steps'}, and 'obs' (the probe's
        lines and returns) when observe == 'full'; `runner.cost` is its length in operations."""
        sp = self._job.trial_spec(seed, n, whole)
        return make_runner(sp['target'], sp['filename'], sp['cargs'], sp['ckw'], sp['ops'], sp['start'], sp['state'])


def make(defect_id, seed, workdir, n_ops=2400, every=200, version=None):
    """A job over the defect's component, its sandbox holding the defective source; and its Handle."""
    from . import defects as DF                     # the catalogues: the kernel driver's, never the trial executor's
    from . import defects2 as DF2
    from . import defects3 as DF3
    from . import defects4 as DF4
    from . import defects5 as DF5
    from . import defects6 as DF6
    cat = next(c for c in (DF, DF2, DF3, DF4, DF5, DF6) if defect_id in c.BY_ID)
    d = cat.BY_ID[defect_id]
    src = cat.source(defect_id, TG.KERNEL_SOURCES)
    job = Job(workdir, d['target'], seed, n_ops, every, source=src, version=version)
    return job, Handle(job)


def make_clean(target, seed, workdir, n_ops=2400, every=200, fault_at=None, version=None):
    """A job over the correct component (a control: no obstacle; or, with `fault_at`, a fault in the kernel)."""
    job = Job(workdir, target, seed, n_ops, every, source=TG.KERNEL_SOURCES[target], fault_at=fault_at, version=version)
    return job, Handle(job)
