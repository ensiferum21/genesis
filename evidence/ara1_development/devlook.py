"""ARA-1 development look (disclosed in its record): every arm on 2 environments per class, zoo indices 9000-9015,
sealed seed 9090. Not a result."""
import json, sys, time
sys.path.insert(0, '/home/claude/gx/src')
from genesis.architecture import judge as J, ara as A, zoo as Z, graph as G
H = J.Harness(sealed_seed=9090)
rows = []
t0 = time.time()
for rep in range(2):
    for ci, cls in enumerate(Z.CLASSES):
        idx = 9000 + rep * len(Z.CLASSES) + ci
        out = {'index': idx, 'class': cls}
        for arm in ('ara', 'blind', 'tuning'):
            view = H.open(idx, cls)
            budget = 4 * view.budget
            sub = lambda v, c, u, arm=arm, idx=idx: H.submit(idx, arm, v, c, u, budget)
            t = time.time()
            if arm == 'tuning':
                tr = A.tune_only(view, seed=1, budget=budget, submit=sub)
            else:
                tr = A.cycle(view, seed=1, budget=budget, submit=sub, diagnose=(arm == 'ara'))
            out[arm] = {'arm': tr['arm'], 'diag': (tr.get('diagnosis') or {}).get('diagnosis'),
                        'submitted': tr.get('submitted') and [tr['submitted']['rewrite']['op'], tr['submitted']['rewrite'].get('args'), tr['submitted']['class']],
                        'verdict': tr['verdict'], 'spent': round(tr['units']['spent']), 'secs': round(time.time() - t, 1)}
        out['oracle_key'] = round(H.oracle_key(idx), 3)
        rows.append(out)
        print(json.dumps(out), flush=True)
led = H.ledger()
json.dump({'rows': rows, 'ledger': [{k: v for k, v in r.items() if k != 'variant'} for r in led]},
          open('/tmp/claude-0/-home-claude/52ea77a0-8bc1-573f-ac60-c5bbc0436e28/scratchpad/ara/devlook.json', 'w'), indent=1, default=str)
print('promoted', {a: sum(1 for r in led if r['arm'] == a and r['promoted']) for a in ('ara', 'blind', 'tuning')}, f'{time.time()-t0:.0f}s')
