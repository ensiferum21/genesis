#!/usr/bin/env python3
"""B20_R9 design pilot (DEV): is there headroom in *curating* a lemma library? (B20R3-OPEN-1/2)

    b20r9_curation_pilot.py OUT_DIR VARIANT [VARIANT ...]
    b20r9_curation_pilot.py OUT_DIR --summary

A design diagnostic, not a study; it licenses no claim. B20_R3 and B20_R6 found no room for
choosing *which lemmas to prove* on eight systems, and found that true lemmas interfere: a
bigger library can prove fewer fresh targets (Huntington@614 7/8 -> 0/8; Boolean rings 8-10
nodes: 34 lemmas 11/12, 132 lemmas 8/12). The question here is whether choosing *which proved
lemmas to keep* has headroom over fixed rules, and whether a deployable curator (using
development targets only) captures it.

Per variant (system, pool and target ranges as in the B20_R3/R6 pilots; pool seed 700):
  * EXHAUST library: the fixed policy proves the whole pool (1 s per attempt);
    FIXED@CAP: the fixed policy under cap = 0.25 x exhaust CPU (the B20 rule).
  * per range, 12 DEVELOPMENT targets (seed 900 + range index) and 12 EVALUATION targets
    (seed 910 + range index), disjoint from the pool and from each other.
  * libraries, all built from EXHAUST's lemmas (closed under lemma dependencies), evaluated on the
    evaluation targets at 1 s per target with 8 premises:
      EMPTY, FIXED@CAP, ALL (= EXHAUST),
      DEV-CURATED   deployable: rank lemmas by how many development-target proofs (ALL library)
                    used them; for k in (1, 2, 4, 8, 16) keep the top-k with their dependency
                    closure; choose the k that proves most development targets (ties: smaller k);
      EVAL-CURATED  the same procedure run on the evaluation targets themselves (optimistic: a
                    reference that searches library subsets with the answers in view, NOT an arm).
  * per-target BEST-OF (any of the libraries above proves it): a diagnostic ceiling (s14.3), not a
    deployable baseline.

Verdicts per variant (fixed here before running; 12 evaluation targets per range):
  DEPLOYABLE_GAIN       some range has DEV-CURATED - max(FIXED@CAP, ALL) >= 2
  CURATION_HEADROOM     otherwise, some range has EVAL-CURATED - max(EMPTY, FIXED@CAP, ALL) >= 2
  NO_CURATION_HEADROOM  otherwise
Every pool statement and target is written to OUT_DIR, so later studies count it as exposed.
"""
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis.common import digest  # noqa: E402
from genesis.learning import equational as Q  # noqa: E402
from genesis.learning import research as RS  # noqa: E402
from genesis.learning.budget import Account  # noqa: E402

import b20r3_headroom_pilot as H  # noqa: E402

VARIANTS = {
    'ba_huntington:t6': {'pool_max': 5, 'max_term': 6, 'grid': [(9, 12), (10, 12)]},
    'ba_huntington': {'pool_max': 5, 'max_term': 5, 'grid': [(7, 10), (8, 10)]},
    'bool_ring:t5': {'pool_max': 4, 'max_term': 5, 'grid': [(7, 10), (8, 10)]},
    'ba_sheffer:t6': {'pool_max': 5, 'max_term': 6, 'grid': [(9, 12), (10, 12)]},
}
SEED, TARGETS, SHARE, KS = 700, 12, 0.25, (1, 2, 4, 8, 16)


def closure(library, ids):
    return H.closure(library, ids)


def evaluate(system, library, targets, label):
    return RS.evaluate_successor(system, library, targets, eval_s=1, label=label)


def curate(system, library, targets, label):
    """Rank by use in proofs of `targets` with the full library; keep top-k (+closure); pick the k
    proving most of `targets` (ties: smaller k). Returns (chosen library, k, per-k proved, full proved)."""
    full = evaluate(system, library, targets, f'{label}:all')
    uses = {}
    for r in full['rows']:
        if r['status'] == 'PROVED':
            for u in closure(library, r['lemmas_used']):
                uses[u['id']] = uses.get(u['id'], 0) + 1
    ranked = sorted(uses, key=lambda i: (-uses[i], i))
    per_k, best = {}, None
    for k in KS:
        lib = closure(library, ranked[:k])
        proved = evaluate(system, lib, targets, f'{label}:k{k}')['proved']
        per_k[k] = {'lemmas': len(lib), 'proved': proved}
        if best is None or proved > best[1]:
            best = (lib, proved, k)
        if k >= len(ranked):
            break
    return best[0], best[2], per_k, full['proved']


def pilot(variant, out, log):
    cfg = VARIANTS[variant]
    system = variant.split(':')[0]
    pool = Q.true_equations(system, cfg['pool_max'], per_bucket=8, seed=SEED) + \
        Q.false_equations(system, cfg['pool_max'], 30, seed=SEED)
    ex = RS.run(system, RS.Fixed(), pool, account=Account(H.budget(10 ** 4), label=f'r9-exhaust:{system}'),
                prove_s=1, premise_k=8)
    cap = round(SHARE * ex['account']['cpu_ns_total'] / 1e9, 3)
    fc = RS.run(system, RS.Fixed(), pool, account=Account(H.budget(cap), label=f'r9-fixedcap:{system}'),
                prove_s=1, premise_k=8)
    log(f'{variant}: pool {len(pool)}, exhaust {len(ex["library"])} lemmas in {ex["cpu_s"]} s, cap {cap} s, '
        f'fixed@cap {len(fc["library"])}')
    ranges = []
    for i, (lo, hi) in enumerate(cfg['grid']):
        dev = Q.sample_targets(system, TARGETS, min_total=lo, max_total=hi, max_term=cfg['max_term'],
                               seed=900 + i, exclude=pool)
        ev = Q.sample_targets(system, TARGETS, min_total=lo, max_total=hi, max_term=cfg['max_term'],
                              seed=910 + i, exclude=list(pool) + list(dev))
        lab = f'r9:{system}:{lo}-{hi}'
        res = {name: evaluate(system, lib, ev, f'{lab}:{name}') for name, lib in
               (('empty', []), ('fixed_cap', fc['library']), ('all', ex['library']))}
        dev_lib, dev_k, dev_per_k, dev_all = curate(system, ex['library'], dev, f'{lab}:devcur')
        res['dev_curated'] = evaluate(system, dev_lib, ev, f'{lab}:dev_curated')
        eval_lib, eval_k, eval_per_k, _ = curate(system, ex['library'], ev, f'{lab}:evalcur')
        res['eval_curated'] = evaluate(system, eval_lib, ev, f'{lab}:eval_curated')
        best_of = sum(any(res[n]['rows'][j]['status'] == 'PROVED' for n in res) for j in range(len(ev)))
        row = {'range': [lo, hi], 'dev_targets': [Q.text(t) for t in dev], 'targets': [Q.text(t) for t in ev],
               **{n: res[n]['proved'] for n in res}, 'best_of': best_of,
               'dev_curated_k': dev_k, 'dev_curated_lemmas': [l['text'] for l in dev_lib], 'dev_per_k': dev_per_k,
               'dev_all_proved': dev_all, 'eval_curated_k': eval_k, 'eval_per_k': eval_per_k,
               'per_target': [{'target': Q.text(t), **{n: res[n]['rows'][j]['status'] for n in res}}
                              for j, t in enumerate(ev)]}
        ranges.append(row)
        log(f'{variant} {lo}-{hi}: empty {row["empty"]}, fixed@cap {row["fixed_cap"]}, all {row["all"]}, '
            f'dev-curated {row["dev_curated"]} (k={dev_k}, {len(dev_lib)} lemmas), eval-curated {row["eval_curated"]} '
            f'(k={eval_k}), best-of {best_of} /12')
    H.dump(out / f'{variant.replace(":", "_")}.json', {
        'variant': variant, 'system': system, 'config': {**cfg, 'seed': SEED, 'targets': TARGETS, 'share': SHARE,
                                                         'ks': list(KS)},
        'pool': [Q.text(e) for e in pool], 'pool_sha256': digest([Q.text(e) for e in pool]),
        'exhaust': {'library': [l['text'] for l in ex['library']], 'cpu_s': ex['cpu_s']},
        'fixed_cap': {'library': [l['text'] for l in fc['library']], 'cpu_s': fc['cpu_s']}, 'cap_s': cap,
        'ranges': ranges, 'status': 'DESIGN_PILOT_DEV', 'claim': 'none; a design diagnostic'})


def verdict(d):
    out = 'NO_CURATION_HEADROOM'
    for r in d['ranges']:
        if r['dev_curated'] - max(r['fixed_cap'], r['all']) >= 2:
            return 'DEPLOYABLE_GAIN'
        if r['eval_curated'] - max(r['empty'], r['fixed_cap'], r['all']) >= 2:
            out = 'CURATION_HEADROOM'
    return out


def summarize(out, log):
    rows = {}
    for f in sorted(out.glob('*.json')):
        if f.name == 'summary.json':
            continue
        d = json.loads(f.read_text())
        rows[d['variant']] = {'verdict': verdict(d), 'ranges': [
            {k: r[k] for k in ('range', 'empty', 'fixed_cap', 'all', 'dev_curated', 'eval_curated', 'best_of',
                               'dev_curated_k', 'eval_curated_k')} for r in d['ranges']]}
    H.dump(out / 'summary.json', {'variants': rows, 'status': 'DESIGN_PILOT_DEV',
                                  'rule': 'see the script docstring (fixed before running)'})
    for v, r in rows.items():
        log(f'{v}: {r["verdict"]}  ' + '; '.join(
            f'{x["range"]}: E{x["empty"]} F{x["fixed_cap"]} A{x["all"]} D{x["dev_curated"]} V{x["eval_curated"]} '
            f'B{x["best_of"]}' for x in r['ranges']))


def main(argv=None):
    a = argv or sys.argv[1:]
    out = Path(a[0])
    t0 = time.monotonic()
    log = lambda m: print(f'[{time.monotonic() - t0:7.1f}s] {m}', flush=True)
    if '--summary' in a:
        summarize(out, log)
        return 0
    for v in a[1:]:
        if v not in VARIANTS:
            raise SystemExit(f'unknown variant {v}; fixed set: {sorted(VARIANTS)}')
        pilot(v, out, log)
    return 0


if __name__ == '__main__':
    sys.exit(main())
