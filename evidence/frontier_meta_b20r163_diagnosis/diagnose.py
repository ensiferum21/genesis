"""A diagnosis of B20_R163's meta-search, made after the study was recorded (30 Oct 2026).

    PYTHONPYCACHEPREFIX=... taskset -c 1 python3 diagnose.py /home/claude/f6-wt diagnosis.json

It repeats the meta-search exactly as the study ran it, from a worktree of the preregistration commit `77d725d`, and
writes what the study's meta.json did not keep: every inner run's configuration and inner spend, and every outer
branch's outer spend. Nothing here was used by the study.
"""
import json
import sys
from pathlib import Path

wt = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(wt / 'scripts'))
sys.path.insert(0, str(wt / 'src'))
import b20r163_frontier_meta as S  # noqa: E402
from genesis.frontier import meta as MT  # noqa: E402
from genesis.frontier.engine import Frontier  # noqa: E402
from genesis.frontier.manifest import Manifest  # noqa: E402

key, fam, seed, null = S.meta_world()
records, sizes = {}, {}


def factory(run_key):
    w = S.make_world(fam, seed, null, S.B_IN)
    rec = records.setdefault(run_key, {})
    sizes['n'] = len(w.problems())

    def verify(p, a):
        v = w.verify(p, a)
        rec[p] = max(rec.get(p, 0.0), v)
        return v
    return Manifest(w, verify, S.B_IN, quantum=S.QUANTUM, description={'study': S.STUDY, 'meta_task': key})


def meta_verify(task, art):
    rec = records.get(art.get('run'))
    return sum(rec.values()) / sizes['n'] if rec else 0.0


dom = MT.MetaDomain({'T0': factory}, policies=('frontier',))
e = Frontier(Manifest(dom, meta_verify, S.META_BUDGET, quantum=S.META_QUANTUM,
                      description={'study': S.STUDY, 'level': 'meta'}), 'frontier', seed=0)
e.run()
art = e.best_artifact['T0']
runs = {k: {'inner_spent': eng.spent, 'value': eng.total() / n} for k, (eng, n) in dom._runs.items()}
branches = []
for bid, b in sorted(e.branches.items()):
    d = b['direction']
    rk = MT.run_key('T0', d, b['seed'])
    branches.append({'branch': bid, 'params': d['params'], 'outer_t': b['t'], 'paused': b['paused'],
                     'run': rk, **runs.get(rk, {})})
out = {'promoted': art['config']['params'], 'promoted_run': art['run'], 'promoted_score': art['score'],
       'promoted_inner_spent_at_artifact': art['inner_spent'], 'c_meta': dom.inner_compute(), 'outer_spent': e.spent,
       'defaults_opened': any(b['params'] == MT.DEFAULT for b in branches), 'branches': branches,
       'matches_study': None}
study = json.loads((wt / 'evidence' / 'frontier_meta_b20r163' / 'meta.json').read_text())
out['matches_study'] = (study['promoted'] == out['promoted'] and study['c_meta'] == out['c_meta']
                        and study['outer_spent'] == out['outer_spent'])
Path(sys.argv[2]).write_text(json.dumps(out, indent=1, sort_keys=True) + '\n')
print(json.dumps({k: v for k, v in out.items() if k != 'branches'}, indent=1))
