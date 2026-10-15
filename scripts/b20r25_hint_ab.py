#!/usr/bin/env python3
"""B20_R25: ground-hint generator v1 vs v2 on identical E proof objects (Lean replay), DEV only.

    b20r25_hint_ab.py OUT_DIR             (writes OUT_DIR/ab.json and OUT_DIR/rows.json)

The fof_lean ground-hint generator v2 was built on the B21 side branch. There, after its
repair, the Lean replay of Wolfram-axiom lemma chains went from 0/11 to 11/11, but on regenerated
libraries, so the comparison was not paired. This step pairs it on the canonical line. Rules
fixed here before running:
  * material, as in B21: Wolfram's single axiom for Boolean algebra (ba_wolfram) at seeds
    2026251 and 2026252, and Sheffer's basis (ba_sheffer) at seed 2026253 as a regression check
    on a system where v1 already replays. Each seed has a pool (size 5, 8 per bucket,
    30 false conjectures), 10 development targets and 15 evaluation targets of 5–8 nodes,
    disjoint from pool and development;
  * one research run per seed: the fixed policy, research.run under a strict account of
    60 CPU s (Wolfram) or 10 CPU s (Sheffer), 10 s per attempt, 8 premises. The successor
    is evaluated with 3 s per target;
  * every evaluation proof that used library lemmas is replayed in Lean with its whole
    lemma chain (research.lean_chain), once with HINTS = 'v1' and once with HINTS = 'v2',
    on the same proof objects;
  * reported: THEOREM_CHECKED counts per version and system, paired outcomes (both,
    v2 only, v1 only, neither), and hinted steps. A v1-only success counts as a v2
    regression and is listed.
A DEV engineering comparison. It licenses no claim.
"""
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from genesis.common import code_identity, digest  # noqa: E402
from genesis.formal_research import fof_lean as F  # noqa: E402
from genesis.learning import equational as Q  # noqa: E402
from genesis.learning import research as RS  # noqa: E402

SEEDS = [('ba_wolfram', 2026251, 60), ('ba_wolfram', 2026252, 60), ('ba_sheffer', 2026253, 10)]
RULES = {'pool_size': 5, 'per_bucket': 8, 'false_conjectures': 30, 'dev_targets': 10, 'eval_targets': 15,
         'target_range': [5, 8], 'prove_s': 10, 'eval_s': 3, 'premise_k': 8}


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False, default=str) + '\n')


def material(system, seed):
    pool = Q.true_equations(system, RULES['pool_size'], per_bucket=RULES['per_bucket'], seed=seed) + \
        Q.false_equations(system, RULES['pool_size'], RULES['false_conjectures'], seed=seed)
    lo, hi = RULES['target_range']
    dev = Q.sample_targets(system, RULES['dev_targets'], min_total=lo, max_total=hi, seed=seed * 7 + 1, exclude=pool)
    ev = Q.sample_targets(system, RULES['eval_targets'], min_total=lo, max_total=hi, seed=seed * 7 + 2,
                          exclude=pool + dev)
    return pool, dev, ev


def main(argv=None):
    out = Path((argv or sys.argv[1:])[0])
    if (out / 'ab.json').exists():
        raise FileExistsError(out / 'ab.json')
    t0 = time.monotonic()
    log = lambda m: print(f'[{time.monotonic() - t0:7.1f}s] {m}', flush=True)
    rows, runs = [], []
    for system, seed, budget in SEEDS:
        pool, dev, ev = material(system, seed)
        res = RS.run(system, RS.Fixed(seed), pool, budget_s=budget, dev_targets=dev, prove_s=RULES['prove_s'],
                     premise_k=RULES['premise_k'])
        e = RS.evaluate_successor(system, res['library'], ev, eval_s=RULES['eval_s'], premise_k=RULES['premise_k'])
        runs.append({'system': system, 'seed': seed, 'budget_s': budget, 'library': len(res['library']),
                     'library_sha256': res['library_sha256'], 'successor': e['proved'], 'targets': len(ev),
                     'panel_sha256': digest([Q.text(t) for t in ev])})
        log(f'{system}@{seed}: library {len(res["library"])}, successor {e["proved"]}/{len(ev)}')
        for r in e['rows']:
            if r['status'] != 'PROVED' or not r['lemmas_used']:
                continue
            entries, gd, gp = RS.lean_chain(res['library'], r['proof'], r['premise_ids'], len(Q.axioms(system)))
            row = {'system': system, 'seed': seed, 'target': r['target'], 'proof_sha256': r['proof_sha256'],
                   'chain_lemmas': len(entries)}
            for version in F.HINT_VERSIONS:
                F.HINTS = version
                t = time.monotonic()
                rec = F.replay(f'b20r25-{version}-{digest({"s": seed, "t": r["target"]})[:10]}', Q.axioms(system),
                               Q.closed(r['eq']), r['proof'], lemmas=entries, goal_deps=gd, goal_positions=gp)
                row[version] = {'status': rec['status'], 'reason': rec.get('reason'), 'steps': rec.get('steps'),
                                'hinted_steps': rec.get('hinted_steps'), 'hints': rec.get('hints'),
                                'errors': (rec.get('errors') or [])[:3], 'seconds': round(time.monotonic() - t, 1)}
            F.HINTS = 'v2'
            rows.append(row)
            log(f'  {r["target"][:50]}: v1 {row["v1"]["status"]}, v2 {row["v2"]["status"]} '
                f'({len(entries)} chained lemmas)')
    ok = lambda r, v: r[v]['status'] == 'THEOREM_CHECKED'
    by_system = {}
    for system in sorted({r['system'] for r in rows}):
        rs = [r for r in rows if r['system'] == system]
        by_system[system] = {'attempted': len(rs), 'v1_checked': sum(ok(r, 'v1') for r in rs),
                             'v2_checked': sum(ok(r, 'v2') for r in rs),
                             'paired': {'both': sum(ok(r, 'v1') and ok(r, 'v2') for r in rs),
                                        'v2_only': sum(ok(r, 'v2') and not ok(r, 'v1') for r in rs),
                                        'v1_only': sum(ok(r, 'v1') and not ok(r, 'v2') for r in rs),
                                        'neither': sum(not ok(r, 'v1') and not ok(r, 'v2') for r in rs)}}
    regressions = [r['target'] for r in rows if ok(r, 'v1') and not ok(r, 'v2')]
    dump(out / 'rows.json', rows)
    dump(out / 'ab.json', {'schema': 'genesis-b20r25-hint-ab-v1', 'rules': RULES, 'seeds': SEEDS, 'runs': runs,
                           'by_system': by_system, 'v2_regressions': regressions,
                           'code_identity': code_identity(ROOT)['sha256'], 'status': 'DEV; licenses no claim',
                           'wall_seconds': round(time.monotonic() - t0, 1)})
    log(f'by system {by_system}; v2 regressions {regressions}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
