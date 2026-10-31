"""The independent repair verifier (kernel side; `docs/OMEGA_SELF_REPAIR.md` §2.5). The repairer proposes a new source
for one repairable file; this module decides, with checks the repairer never sees:

  1. the boundary: only the job's repairable file changes, by at most MAX_LINES lines, and the static guard
     (`guard`) admits it: it re-arranges what the component already does, nothing more;
  2. it compiles, and the visible tests pass;
  3. the **hidden tests** pass: the kernel's own scenarios for the component, written by the testbed's author and
     never handed to the research plane;
  4. **fresh workloads**: the component matches the kernel's reference on FRESH workloads from the kernel's own
     seeds (never the repairer's), longer than the job;
  5. **the interrupted job resumes**: on a copy of the job's directory, it continues from its last checkpoint with the
     new source and finishes without a failure (for a version-2 job, from the latest kept checkpoint from which it
     finishes: a defect may have corrupted the state saved after it);
  6. for a version-2 job, **resources**: on each fresh workload, the candidate's storage (the total length of the
     component's containers at the end) is at most 2 x + 8, and its work (line events) at most 3 x + 100, of the last
     known-good version of the component (the testbed's correct source): a "repair" may not leak or recompute what
     the component keeps.
A repair is accepted only if all of them hold. `main` runs it in a separate process so that nothing the repairer did in
its own process can reach the verdict."""
import difflib
import json
from pathlib import Path
import random
import shutil
import sys
import tempfile

from . import bench as BN
from . import guard as GD
from . import targets as TG

MAX_LINES = 8
FRESH_SEEDS = ('kernel-fresh-1', 'kernel-fresh-2', 'kernel-fresh-3')

HIDDEN = {
    'memo': '''
s = mod.Scorer(lambda k: k[0] * 10 + k[1], limit=3)
for i in range(20):
    for j in range(3):
        assert s.score([i, j]) == i * 10 + j
assert s.size() <= 3
assert s.score([1, 1]) == 11 and s.score([1, 1]) == 11
calls = []
m = mod.Scorer(lambda k: calls.append(k) or k[0], limit=8)
for _ in range(3):
    for i in range(5):
        assert m.score([i]) == i
assert len(calls) == 5          # a memo memoises: each key computed once while under its limit
''',
    'lru': '''
c = mod.LRU(2)
c.put('a', 1); c.put('b', 2)
assert c.get('a') == 1          # refreshes a
c.put('c', 3)                   # evicts b, the least recent
assert c.get('b') is None and c.get('a') == 1 and c.get('c') == 3
c.put('a', 9)                   # an update refreshes a
c.put('d', 4)                   # evicts c
assert c.keys() == ['a', 'd'] and c.get('a') == 9
c3 = mod.LRU(3)
for k in range(5):
    c3.put(k, k)
assert c3.keys() == [2, 3, 4]
''',
    'registry': '''
r = mod.Registry()
for i, n in enumerate('abcde'):
    r.add(n, i)
r.remove('b')
assert [r.get(n) for n in 'acde'] == [0, 2, 3, 4]
r.remove('a')
r.add('f', 5)
assert [r.get(n) for n in 'cdef'] == [2, 3, 4, 5]
assert r.names() == ['c', 'd', 'e', 'f']
''',
    'stats': '''
calls = []
import builtins
mod.sum = lambda xs: (calls.append(1), builtins.sum(xs))[1]
c = mod.Stats()
c.add(1); c.add(2)
assert c.total() == 3 and c.total() == 3 and c.total() == 3
assert len(calls) == 1          # the total is cached until the values change
del mod.sum
s = mod.Stats()
for v in (3, 9, 4):
    s.add(v)
assert s.total() == 16 and s.top() == 9
s.add(1)
assert s.total() == 17 and s.top() == 9
s.drop_last(); s.drop_last()
assert s.total() == 12 and s.top() == 9
s.drop_last()
assert s.total() == 3 and s.top() == 3
''',
    'window': '''
w = mod.Window(3)
for x in (1, 2, 3, 4):
    w.push(x)
assert w.mean() == 3
snap = w.state()
w.push(10)
w2 = mod.Window.load(snap)
assert w2.mean() == 3 and w.mean() == (3 + 4 + 10) / 3
w2.push(0)
assert mod.Window.load(snap).mean() == 3
''',
    'ttl': '''
c = mod.TTLCache(2, ttl=4)
c.put('a', 1); c.put('b', 2)
assert c.get('a') == 1                  # refreshes a
c.put('c', 3)                           # evicts b
assert c.keys() == ['a', 'c'] and c.get('b') is None
c.put('a', 7)                           # an update refreshes a
assert c.keys() == ['c', 'a']
c.tick(3)
assert c.get('c') == 3
c.tick(1)                               # c and a were put at 0: their deadline 4 has come
assert c.keys() == [] and c.get('a') is None
c.put('x', 1); c.tick(3); c.put('y', 2); c.tick(1)
assert c.keys() == ['y']
assert c.counts() == (2, 2)
''',
    'pq': '''
h = mod.IndexedHeap()
for k in range(12):
    h.push(k, (k * 7) % 12)
h.update(11, -1)
assert h.peek() == 11
h.update(0, 20)
h.remove(5)
h.remove(3)
out = []
while h.size():
    out.append(h.pop())
want = sorted([k for k in range(12) if k not in (5, 3)], key=lambda k: ({11: -1, 0: 20}.get(k, (k * 7) % 12), k))
assert out == want, out
g = mod.IndexedHeap()
for k in range(20):
    g.push(k, 20 - k)
for k in range(0, 20, 3):
    g.remove(k)
assert [g.pop() for _ in range(3)] == [19, 17, 16]
''',
    'ledger': '''
calls = []
import builtins
mod.sum = lambda xs: (calls.append(1), builtins.sum(xs))[1]
g = mod.Ledger()
g.open('a'); g.open('b')
g.deposit('a', 10); g.deposit('b', 5)
assert g.total() == 15 and g.total() == 15
assert len(calls) == 1                  # the total is cached until a balance changes
g.withdraw('a', 10)
assert g.balance('a') == 0 and g.total() == 5
del mod.sum
g.deposit('b', 1)
assert g.history('a') == [0, 2] and g.history('b') == [1, 3]
assert g.undo() == 'b' and g.history('b') == [1] and g.total() == 5
assert g.undo() == 'a' and g.balance('a') == 10 and g.history('a') == [0]
try:
    g.withdraw('b', 6)
    raise AssertionError('overdrawn')
except ValueError:
    pass
''',
    'lease': '''
s = mod.Leases(term=3)
assert s.acquire('a', 'x') and s.acquire('b', 'y')
s.advance(2)
assert s.renew('a', 'x')                 # a now lasts until 5
s.advance(1)                             # b, granted at 0, ends at 3
assert s.owner('b') is None and s.owner('a') == 'x'
assert s.acquire('b', 'z')
assert s.release('a', 'x') and s.owner('a') is None
assert s.acquire('a', 'y')               # free again
s.advance(3)
assert s.owner('a') is None and s.owner('b') is None
assert s.snapshot() == ([], [], 4)
''',
    'graph': '''
g = mod.Graph()
for u, v in ((1, 2), (2, 3), (3, 1), (1, 2)):
    g.link(u, v)
assert g.degree(1) == 2 and g.degree(2) == 2 and g.neighbours(3) == [1, 2]
g.unlink(2, 1)
assert g.degree(1) == 1 and g.degree(2) == 1 and g.neighbours(2) == [3]
g.unlink(2, 1)
assert g.snapshot()[1] == 2
''',
    'bimap': '''
m = mod.BiMap()
m.link('a', 1); m.link('b', 2)
assert m.left(2) == 'b' and m.right('a') == 1
m.link('a', 2)                           # a moves to 2; b loses its partner, 1 is free
assert m.right('a') == 2 and m.left(2) == 'a' and m.right('b') is None and m.left(1) is None
assert m.unlink('a') == 2 and m.left(2) is None
m.link('c', 3)
assert m.snapshot() == ([('c', 3)], [(3, 'c')])
''',
    'log': '''
g = mod.Log()
for e in range(12):
    g.record(e)
g.prune(3)
assert g.count() == 8
assert g.record(3) and not g.record(4)
g.prune(2)
assert all(e % 2 for e in g.events)
''',
}


def changed_lines(old, new):
    return sum(1 for x in difflib.unified_diff(old.splitlines(), new.splitlines(), lineterm='', n=0)
               if x[:1] in '+-' and not x.startswith(('+++', '---')))


def _exec_test(code, mod):
    try:
        exec(code, {'mod': mod})
        return None
    except Exception as e:                                          # noqa: BLE001
        return f'{type(e).__name__}: {str(e)[:120]}'


def verify(jobdir, target, seed, n_ops, every, new_source):
    jobdir = Path(jobdir)
    job = BN.Job(jobdir, target, seed, n_ops, every)
    old = job.file.read_text()
    out = {'checks': {}}
    n = changed_lines(old, new_source)
    refused = GD.check(old, new_source)
    out['checks']['boundary'] = {'ok': 0 < n <= MAX_LINES and refused is None, 'changed_lines': n, 'guard': refused}
    if refused:
        out['checks']['visible'] = {'ok': False, 'failures': [('guard', refused)]}
        out['checks']['hidden'] = {'ok': False, 'failure': 'not run'}
        out['checks']['fresh'] = {'ok': False, 'failures': ['not run']}
        out['checks']['resume'] = {'ok': False, 'at': None}
        out['accepted'] = False
        return out
    try:
        mod = BN.load_source(new_source, 'verify_mod', str(job.file))
        vis = [(name, _exec_test(code, mod)) for name, code in TG.VISIBLE_TESTS[target]]
        out['checks']['visible'] = {'ok': all(e is None for _, e in vis), 'failures': [x for x in vis if x[1]]}
        hidden = BN._limited(lambda: _exec_test(HIDDEN[target], mod), 10 ** 6, str(job.file))
        out['checks']['hidden'] = {'ok': hidden is None, 'failure': hidden}
    except Exception as e:                                          # noqa: BLE001
        out['checks']['visible'] = {'ok': False, 'failures': [('compile', f'{type(e).__name__}: {e}')]}
        out['checks']['hidden'] = {'ok': False, 'failure': 'not run'}
    fresh, resource = [], []
    for s in FRESH_SEEDS:
        rng = random.Random(f'verify|{target}|{s}')
        cargs, ckw = TG.make_args(target, rng)
        op_list = TG.ops(target, rng, 3000)
        try:
            mod = BN.load_source(new_source, 'verify_fresh', str(job.file))
            count = [0]
            st, _ = BN._limited(lambda: BN.execute(target, mod, cargs, ckw, op_list), 10 ** 7, str(job.file),
                                count=count)
            fresh.append(None)
            if job.version >= 2:
                good = BN.load_source(TG.SOURCES_ANY[target], 'verify_good', str(job.file))
                gcount = [0]
                gst, _ = BN._limited(lambda: BN.execute(target, good, cargs, ckw, op_list), 10 ** 7, str(job.file),
                                     count=gcount)
                resource.append({'storage': _storage(st['comp']), 'good_storage': _storage(gst['comp']),
                                 'work': count[0], 'good_work': gcount[0]})
        except Exception as e:                                      # noqa: BLE001
            fresh.append(f'{type(e).__name__}: {str(e)[:120]}')
    out['checks']['fresh'] = {'ok': all(x is None for x in fresh), 'failures': [x for x in fresh if x]}
    if job.version >= 2:
        out['checks']['resource'] = {
            'ok': bool(resource) and len(resource) == len(FRESH_SEEDS) and all(
                r['storage'] <= 2 * r['good_storage'] + 8 and r['work'] <= 3 * r['good_work'] + 100 for r in resource),
            'runs': resource}
    with tempfile.TemporaryDirectory() as d:
        copy = Path(d) / 'job'
        shutil.copytree(jobdir, copy)
        (copy / f'{target}.py').write_text(new_source)
        r = BN.Job(copy, target, seed, n_ops, every).run(resume=True)
    out['checks']['resume'] = {'ok': r['status'] == 'done', 'at': r['op'], 'from': r.get('started'),
                               'rolled_back_from': r.get('rolled_back_from')}
    out['version'] = job.version
    out['accepted'] = all(c['ok'] for c in out['checks'].values())
    return out


def _storage(attrs):
    """The total length of the containers among a component's attributes."""
    return sum(len(v) for v in attrs.values() if isinstance(v, (list, dict, set, tuple)))


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    jobdir, target, seed, n_ops, every, src_path, out_path = argv
    res = verify(jobdir, target, int(seed), int(n_ops), int(every), Path(src_path).read_text())
    Path(out_path).write_text(json.dumps(res, indent=1, default=str))
    return 0


def run_separately(jobdir, target, seed, n_ops, every, new_source):
    """The verdict from a separate process (the research plane's process cannot reach it)."""
    import subprocess
    root = Path(__file__).resolve().parents[3]
    with tempfile.TemporaryDirectory() as d:
        src, out = Path(d) / 'candidate.py', Path(d) / 'verdict.json'
        src.write_text(new_source)
        p = subprocess.run([sys.executable, '-m', 'genesis.repairkernel.verify', str(jobdir), target, str(seed),
                            str(n_ops), str(every), str(src), str(out)], cwd=root,
                           env={'PYTHONPATH': str(root / 'src'), 'PATH': '/usr/bin:/bin'},
                           capture_output=True, text=True, timeout=600)
        if p.returncode != 0:
            return {'accepted': False, 'checks': {}, 'error': p.stderr[-800:]}
        return json.loads(out.read_text())


if __name__ == '__main__':
    sys.exit(main())
