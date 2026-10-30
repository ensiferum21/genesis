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
import sys
import types

from . import guard as GD
from . import targets as TG


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

    def __init__(self, workdir, target, seed, n_ops=2400, every=200, source=None, fault_at=None):
        self.fault_at = fault_at
        self.dir = Path(workdir)
        self.dir.mkdir(parents=True, exist_ok=True)
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
        import pickle
        (self.dir / 'state.pkl').write_bytes(pickle.dumps(state))
        self.ckpt.write_text(json.dumps({'next': i}))

    def _load(self):
        import pickle
        if not self.ckpt.exists():
            return 0, None
        return json.loads(self.ckpt.read_text())['next'], pickle.loads((self.dir / 'state.pkl').read_bytes())

    def run(self, resume=False, steps=10 ** 7):
        """Run (or resume) to the end; {'status': 'done'|'failed', 'traceback', 'op'}."""
        import traceback
        mod = self.module()
        start, state = self._load() if resume else (0, None)
        if not resume:
            for f in ('state.json', 'state.pkl'):
                (self.dir / f).unlink(missing_ok=True)
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

    def trial_spec(self, seed=None, n=None):
        """What a runner needs (for the trial executor): the failing segment from the last checkpoint (seed None), or
        a fresh workload of n operations from the caller's seed."""
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

    def trial(self, seed=None, n=None):
        """A runner for a workload: the failing segment (seed None: from the last checkpoint to the job's end), or a
        fresh workload of n operations from `seed` (the caller's own seeds). `runner(src, steps, observe)` returns
        {'status': 'pass'|'crash'|'diverge', 'exception', 'message', 'op', 'of', 'steps'}, and 'obs' (the probe's
        lines and returns) when observe == 'full'; `runner.cost` is its length in operations."""
        sp = self._job.trial_spec(seed, n)
        return make_runner(sp['target'], sp['filename'], sp['cargs'], sp['ckw'], sp['ops'], sp['start'], sp['state'])


def make(defect_id, seed, workdir, n_ops=2400, every=200):
    """A job over the defect's component, its sandbox holding the defective source; and its Handle."""
    from . import defects as DF                     # the catalogue: the kernel driver's, never the trial executor's
    d = DF.BY_ID[defect_id]
    src = DF.source(defect_id, TG.SOURCES)
    job = Job(workdir, d['target'], seed, n_ops, every, source=src)
    return job, Handle(job)


def make_clean(target, seed, workdir, n_ops=2400, every=200, fault_at=None):
    """A job over the correct component (a control: no obstacle; or, with `fault_at`, a fault in the kernel)."""
    job = Job(workdir, target, seed, n_ops, every, source=TG.SOURCES[target], fault_at=fault_at)
    return job, Handle(job)
