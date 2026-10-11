#!/usr/bin/env python3
"""B20 / W20: effort-matched control for the failure-driven curriculum on Wolfram's axiom.

  b20_curriculum_control.py OUT_DIR          (writes OUT_DIR/curriculum_control.json)

Written after `b20_hard_followup.py`. There, a curriculum built from variants of failed
development targets raised the successor on seed 311 from 0 to 12 of 15. That
curriculum had 60 CPU-s of its own, so this control matches the effort. Rules are fixed
here before running. For each hard seed (311–314):
  * plain       the fixed policy over the ordinary conjecture pool, 60 CPU-s;
  * curriculum  the fixed policy over valid variants of the failed development targets
                (specializations and equal sub-equations), 60 CPU-s;
  * both        the two libraries together.
Before evaluation, every library is screened against the evaluation targets (EXACT and
INSTANCE are removed and counted), so that success is not near-duplicate answers.
Successors are evaluated on the seed's 15 evaluation targets with 3 s each and the 8 most
relevant lemmas. The evaluation targets are never used to build anything.
"""
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from genesis.learning import equational as Q  # noqa: E402
from genesis.learning import memory as MEM  # noqa: E402
from genesis.learning import research as RS  # noqa: E402

SYSTEM = 'ba_wolfram'
SEEDS = [311, 312, 313, 314]
RULES = {'budget_s': 60, 'prove_s': 10, 'eval_s': 3, 'premise_k': 8, 'eval_targets': 15, 'dev_targets': 10,
         'target_range': [5, 8], 'pool_size': 5, 'per_bucket': 8, 'false_conjectures': 30}


def main(argv=None):
    out = Path((argv or sys.argv[1:])[0])
    path = out / 'curriculum_control.json'
    if path.exists():
        raise FileExistsError(path)
    t0 = time.monotonic()
    log = lambda m: print(f'[{time.monotonic() - t0:7.1f}s] {m}', flush=True)
    rows = []
    for seed in SEEDS:
        pool = Q.true_equations(SYSTEM, RULES['pool_size'], per_bucket=RULES['per_bucket'], seed=seed) + \
            Q.false_equations(SYSTEM, RULES['pool_size'], RULES['false_conjectures'], seed=seed)
        lo, hi = RULES['target_range']
        dev = Q.sample_targets(SYSTEM, RULES['dev_targets'], min_total=lo, max_total=hi, seed=seed * 7 + 1, exclude=pool)
        ev = Q.sample_targets(SYSTEM, RULES['eval_targets'], min_total=lo, max_total=hi, seed=seed * 7 + 2,
                              exclude=pool + dev)
        evd = RS.evaluate_successor(SYSTEM, [], dev, eval_s=RULES['eval_s'])
        failed = [d for d, r in zip(dev, evd['rows']) if r['status'] != 'PROVED']
        seen, variants = set(), []
        for d in failed:
            for v in MEM.variants(d, Q.SYSTEMS[SYSTEM]['decider']):
                if v['valid'] and v['eq'] not in seen:
                    seen.add(v['eq']); variants.append(v['eq'])
        plain = RS.run(SYSTEM, RS.Fixed(seed), pool, budget_s=RULES['budget_s'], dev_targets=dev,
                       prove_s=RULES['prove_s'], premise_k=RULES['premise_k'])
        cur = RS.run(SYSTEM, RS.Fixed(seed), variants, budget_s=RULES['budget_s'], dev_targets=dev,
                     prove_s=RULES['prove_s'], premise_k=RULES['premise_k'])
        cur_lib = [dict(l, id='C' + l['id'], uses=['C' + u for u in l['uses']],
                        premise_ids=['C' + u for u in l['premise_ids']]) for l in cur['library']]
        arms = {'plain': plain['library'], 'curriculum': cur_lib, 'both': plain['library'] + cur_lib}
        scores, excluded = {}, {}
        for arm, lib in arms.items():
            kept, ex = MEM.screen(lib, ev)
            excluded[arm] = [x['reason'] for x in ex]
            scores[arm] = RS.evaluate_successor(SYSTEM, kept, ev, eval_s=RULES['eval_s'],
                                                premise_k=RULES['premise_k'])['proved']
        empty = RS.evaluate_successor(SYSTEM, [], ev, eval_s=RULES['eval_s'])['proved']
        rows.append({'seed': seed, 'empty': empty, 'scores': scores, 'excluded': excluded,
                     'dev_failed': len(failed), 'variants': len(variants),
                     'plain_library': len(plain['library']), 'plain_cpu_s': plain['cpu_s'],
                     'curriculum_library': len(cur_lib), 'curriculum_cpu_s': cur['cpu_s'], 'targets': len(ev)})
        log(f'seed {seed}: empty {empty}, {scores}, libraries plain {len(plain["library"])} / curriculum '
            f'{len(cur_lib)}, excluded {excluded}')
    path.write_text(json.dumps({'rules': RULES, 'rows': rows}, indent=1, sort_keys=True) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
