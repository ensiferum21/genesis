#!/usr/bin/env python3
"""B20_R54 design pilot (DEV): does research beyond the pool reach Wolfram's ceiling?

    b20r54_wolfram_ceiling.py OUT_DIR            (resumable: a seed whose file exists is skipped)
    b20r54_wolfram_ceiling.py OUT_DIR --summary  (recomputes summary.json from the seed files)

A design diagnostic, not a study. It licenses no claim and adopts nothing.

**Why.** B20_R53 found no selection headroom on Wolfram's axiom at B20's hard settings: once the pool (true equations
of up to 5 operation nodes) is exhausted, which lemmas are kept moves at most 1 of 15 targets. What limits the
successor is the ceiling: 3-8 of 15 targets that no library built from that pool proves. A research procedure can
then help only by reaching *beyond* the pool. This pilot measures whether a larger conjecture space (up to 6 nodes)
moves the ceiling at all, and how the GV6 draft's transferred keep rule behaves there. It decides whether a GV4
study or a GV6 transfer study on the equational target has anything to find (B20R9-OPEN-1; `handoff/gv6/README.md`,
target 2).

**Settings.** B20_R53's rules (B20's hard rules): 10 s per research attempt, 3 s per evaluation target, the 8 most
relevant lemmas, 10 development and 15 evaluation targets of 5-8 nodes. Fresh seeds 5401-5404. Two pools per seed:
  * POOL5: true equations up to 5 nodes (8 per bucket) plus 30 false ones, exactly as in B20_R53;
  * POOL6: true equations up to 6 nodes (8 per bucket) plus 30 false ones of up to 6 nodes.
The evaluation targets avoid both pools and the development targets, and any target with a declared relation
(EXACT, ALPHA, INSTANCE, GENERALIZES; `partitions.EquationalAdapter`) to an item of either pool or to a development
target is dropped (25 are drawn; the first 15 kept), so no pool lemma can answer a target in one step. Every
statement is written to OUT_DIR, so later studies count it as exposed.

**Libraries per seed**, each evaluated on the 15 targets under the same rule (research cap 1800 CPU-s, which did not
bind in B20_R53):
  * EMPTY;
  * EXHAUST5 and EXHAUST6: the fixed policy (smallest first, every proved lemma kept) over POOL5 and POOL6;
  * ORACLE5 and ORACLE6: the lemmas that eligible EXHAUST target proofs used, closed under lemma dependencies (B20_R3's
    optimistic reference, built from the evaluation targets, not an arm);
  * GAP5 and GAP6: B20_R53's ``run_gap`` (the transferred keep rule) over POOL5 and POOL6;
  * EXHAUST5 evaluated a second time (REPEAT), for noise.

**Verdict (fixed here before running).** Per seed, the ceiling headroom is c = ORACLE6 - ORACLE5: what the larger
conjecture space adds to the best library built from the smaller one.
  * CEILING_HEADROOM if mean c >= 2 (of 15) and c >= 2 on at least 3 of the 4 seeds;
  * NO_CEILING_HEADROOM if c <= 1 on every seed;
  * WEAK_CEILING_HEADROOM otherwise.
Reported descriptively: EXHAUST6 - EXHAUST5 (conventional research over the larger pool), GAP6 - EXHAUST5 and
GAP6 - EXHAUST6 (the keep rule), GAP6 - ORACLE6, library sizes, research CPU and the noise |EXHAUST5 - REPEAT|.

**Development looks (disclosed).** Written after B20_R53's full result. A first B20_R54 design (8 seeds; GAP vs the
full library, B20_R9's curator, a random size control and a complement placebo) was drafted and set aside unrun:
B20_R53 bounds any library choice from the pool at about 1 of 15, so it could not reach its own threshold. Before
writing this file the builder counted the true equations for seed 5401 at sizes 5, 6 and 7 (88, 233 and 296; no
prover calls; size 7 took 103 s to enumerate and is not used). No prover call on seeds 5401-5404 preceded the run.

Run pinned to one core (``taskset -c 0``).
"""
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis.learning import equational as Q  # noqa: E402
from genesis.learning import research as RS  # noqa: E402
from genesis.learning.budget import Account  # noqa: E402
from genesis.learning.partitions import EquationalAdapter  # noqa: E402

import b20r53_wolfram_headroom as R53  # noqa: E402

SYSTEM = R53.SYSTEM
RULES = R53.RULES
SEEDS = [5401, 5402, 5403, 5404]
POOLS = {'5': 5, '6': 6}
CAP = 1800
DRAW = 25
VERDICT = {'min_mean': 2, 'min_seed': 2, 'min_seeds': 3, 'none_max': 1}
PRIOR_SEEDS = R53.PRIOR_SEEDS + tuple(R53.SEEDS)


def pool_of(seed, size):
    return Q.true_equations(SYSTEM, size, per_bucket=RULES['per_bucket'], seed=seed) + \
        Q.false_equations(SYSTEM, size, RULES['false_conjectures'], seed=seed)


def material(seed):
    """(pools {'5': [...], '6': [...]}, development targets, evaluation targets, dropped related targets)."""
    pools = {k: pool_of(seed, v) for k, v in POOLS.items()}
    every = pools['5'] + pools['6']
    lo, hi = RULES['target_range']
    dev = Q.sample_targets(SYSTEM, RULES['dev_targets'], min_total=lo, max_total=hi, seed=seed * 7 + 1, exclude=every)
    drawn = Q.sample_targets(SYSTEM, DRAW, min_total=lo, max_total=hi, seed=seed * 7 + 2, exclude=every + dev)
    ad = EquationalAdapter()
    keep, dropped = [], []
    for t in drawn:
        rel = next((r for r in (ad.relation(t, v) for v in every + dev) if r), None)
        (dropped if rel else keep).append((t, rel))
    return pools, dev, [t for t, _ in keep[:RULES['eval_targets']]], [(Q.text(t), r) for t, r in dropped]


def one_seed(seed, out, log):
    path = out / f'seed_{seed}.json'
    if path.exists():
        log(f'seed {seed}: already done')
        return json.loads(path.read_text())
    pools, dev, ev, dropped = material(seed)
    if len(ev) < RULES['eval_targets']:
        raise SystemExit(f'seed {seed}: only {len(ev)} unrelated targets')
    t0 = time.monotonic()

    def evaluate(lib, label):
        e = RS.evaluate_successor(SYSTEM, lib, ev, eval_s=RULES['eval_s'], premise_k=RULES['premise_k'],
                                  label=f'r54-{label}:{seed}')
        return {'proved': e['proved'], 'statuses': [r['status'] for r in e['rows']], 'lemma_use': e['lemma_use'],
                'lemmas': len(lib), 'library': [l['text'] for l in lib]}
    row = {'seed': seed, 'pools': {k: [Q.text(e) for e in p] for k, p in pools.items()},
           'dev': [Q.text(e) for e in dev], 'targets': [Q.text(e) for e in ev], 'dropped_related': dropped,
           'research': {}, 'libraries': {}}
    row['libraries']['empty'] = evaluate([], 'empty')
    for k, pool in pools.items():
        ex = RS.run(SYSTEM, RS.Fixed(), pool, account=Account(R53.budget(CAP), label=f'r54-exhaust{k}:{seed}'),
                    prove_s=RULES['prove_s'], premise_k=RULES['premise_k'])
        gp = R53.run_gap(pool, Account(R53.budget(CAP), label=f'r54-gap{k}:{seed}'))
        row['research'][f'exhaust{k}'] = {'cpu_s': ex['cpu_s'], 'stop_reason': ex['account'].get('stop_reason'),
                                          'lemmas': len(ex['library']),
                                          'untried': len(pool) - len(ex['trajectory']),
                                          'outcomes': [[s['eq'], s['outcome'], s.get('cpu_s')] for s in ex['trajectory']]}
        row['research'][f'gap{k}'] = {'cpu_s': gp['cpu_s'], 'stop_reason': gp['account'].get('stop_reason'),
                                      'kept': [l['text'] for l in gp['library']],
                                      'cheaply_derivable': sum(s['outcome'] == 'CHEAP_DERIVABLE' for s in gp['trajectory']),
                                      'trajectory': gp['trajectory']}
        e = evaluate(ex['library'], f'exhaust{k}')
        row['libraries'][f'exhaust{k}'] = e
        orc = R53.closure(ex['library'], list(e['lemma_use']))
        row['libraries'][f'oracle{k}'] = evaluate(orc, f'oracle{k}')
        row['libraries'][f'gap{k}'] = evaluate(gp['library'], f'gap{k}')
        if k == '5':
            row['libraries']['repeat5'] = evaluate(ex['library'], 'repeat5')
        L = row['libraries']
        log(f'seed {seed} pool{k}: {len(pool)} items; exhaust {L[f"exhaust{k}"]["proved"]} ({len(ex["library"])} lemmas, '
            f'{ex["cpu_s"]} s), oracle {L[f"oracle{k}"]["proved"]} ({len(orc)}), gap {L[f"gap{k}"]["proved"]} '
            f'({len(gp["library"])} kept, {row["research"][f"gap{k}"]["cheaply_derivable"]} cheaply derivable, '
            f'{gp["cpu_s"]} s)')
    row['wall_s'] = round(time.monotonic() - t0, 1)
    row['status'] = 'DESIGN_PILOT_DEV'
    R53.dump(path, row)
    log(f'seed {seed}: empty {row["libraries"]["empty"]["proved"]}, repeat5 {row["libraries"]["repeat5"]["proved"]} '
        f'[{row["wall_s"]} s]')
    return row


def verdict(rows, rule=VERDICT):
    P = lambda r, k: r['libraries'][k]['proved']
    c = [P(r, 'oracle6') - P(r, 'oracle5') for r in rows]
    if statistics.mean(c) >= rule['min_mean'] and sum(x >= rule['min_seed'] for x in c) >= rule['min_seeds']:
        v = 'CEILING_HEADROOM'
    elif max(c) <= rule['none_max']:
        v = 'NO_CEILING_HEADROOM'
    else:
        v = 'WEAK_CEILING_HEADROOM'
    pairs = {'exhaust6-exhaust5': ('exhaust6', 'exhaust5'), 'gap6-exhaust5': ('gap6', 'exhaust5'),
             'gap6-exhaust6': ('gap6', 'exhaust6'), 'gap6-oracle6': ('gap6', 'oracle6'), 'gap5-exhaust5': ('gap5', 'exhaust5')}
    return {'verdict': v, 'ceiling_headroom': c, 'mean': round(statistics.mean(c), 3),
            'descriptive': {k: [P(r, a) - P(r, b) for r in rows] for k, (a, b) in pairs.items()},
            'noise': [abs(P(r, 'exhaust5') - P(r, 'repeat5')) for r in rows], 'rule': rule,
            'seeds': [r['seed'] for r in rows]}


def summarize(out, log):
    rows = [json.loads((out / f'seed_{s}.json').read_text()) for s in SEEDS if (out / f'seed_{s}.json').exists()]
    if len(rows) != len(SEEDS):
        raise SystemExit(f'only {len(rows)} of {len(SEEDS)} seeds present')
    s = verdict(rows)
    table = [{'seed': r['seed'], **{k: v['proved'] for k, v in r['libraries'].items()},
              **{f'{k}_cpu_s': v['cpu_s'] for k, v in r['research'].items()},
              'gap6_kept': len(r['research']['gap6']['kept']), 'gap5_kept': len(r['research']['gap5']['kept']),
              'exhaust6_lemmas': r['research']['exhaust6']['lemmas']} for r in rows]
    summary = dict(s, table=table, system=SYSTEM, rules=RULES, pools=POOLS, cap=CAP, cheap_s=R53.CHEAP_S,
                   status='DESIGN_PILOT_DEV', claim='none; a design diagnostic for GV4 and the GV6 equational target')
    R53.dump(out / 'summary.json', summary)
    log(f'verdict {s["verdict"]}; ceiling headroom {c_fmt(s)}; descriptive {json.dumps(s["descriptive"])}; '
        f'noise {s["noise"]}')
    return summary


def c_fmt(s):
    return f'{s["ceiling_headroom"]} (mean {s["mean"]})'


def main(argv=None):
    a = argv or sys.argv[1:]
    out = Path(a[0])
    t0 = time.monotonic()
    log = lambda m: print(f'[{time.monotonic() - t0:7.1f}s] {m}', flush=True)
    if '--summary' not in a:
        for seed in SEEDS:
            one_seed(seed, out, log)
    summarize(out, log)
    return 0


if __name__ == '__main__':
    sys.exit(main())
