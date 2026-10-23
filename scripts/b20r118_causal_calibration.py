#!/usr/bin/env python3
"""B20_R118: where do established causal-discovery methods stand when hidden variables confound? (DEV, preregistered)

    taskset -c 0 python3 scripts/b20r118_causal_calibration.py OUT_DIR     run ALONE (resumable), then analyse

**Why.** Daniel's research alert of 22 Oct 2026, item 2: can a system tell when its measurements cannot explain what
it sees, and propose the measurement that would? Before Genesis builds anything for it, the benchmark needs a
calibration, as Gset had (B20_R102): how often do the established methods, which assume no hidden variables, draw a
causal edge where there is only a hidden common cause, and do several environments, pooled naively, help them? That
is the headroom any hidden-cause-aware method has to aim at.

**Design (fixed before running).**
  * **Instances:** 40 seeds from SEED. Each seed fixes one planted graph (p = 10 observed variables, edge density
    0.2, weights and noise as in `causal.sem`, Laplace noise, N = 3,000 samples in all) and gives four instances, a
    2 x 2 factorial within the seed: h = 0 or 3 hidden variables (each confounding one pair; for a given K the graph,
    the environments and the observed noise are the same in both) x K = 1 or 3 environments (the samples split
    evenly; in each extra environment a third of the observed variables have their noise scaled by U(1.5, 3)).
    160 instances.
  * **Methods** (`causal.methods`, written from their papers): `empty`; `pc` (PC-stable, Fisher's z, alpha 0.01);
    `pc_oracle` (PC told the true conditional independences: its errors are the hidden variables' alone); `lingam`
    (DirectLiNGAM, pairwise measure, alpha 0.01). Multi-environment data are centred per environment and pooled.
  * **Primary measure:** directed-edge F1 against the planted direct causes (orientation included), so h = 0 and
    h = 3 are scored against the same edges. Also reported: causal-adjacency F1, SHD, the bidirected marks (none of
    these methods can make one), and the spurious rate.
  * **Test 1, hidden variables (per data method, pc and lingam):** at K = 1, the paired Wilcoxon signed-rank test of
    directed F1 (h = 3 against h = 0) over the 40 seeds (zeros dropped, two-sided, alpha 0.05, at least 6 non-zero
    differences): HIDDEN_HURTS / HIDDEN_HELPS / NO_EFFECT.
  * **Test 2, naive pooling of environments (per data method and h):** the same test of directed F1, K = 3 against
    K = 1: POOLING_HURTS / POOLING_HELPS / NO_EFFECT.
  * **Headroom:** over the h = 3 instances (both K), the confounded pairs with no direct edge, and the share a method
    connects (pooled over pairs, with a 95% Clopper-Pearson interval). For the better data method at h = 3 (higher
    mean directed F1): CONFOUNDING_MISLEADS if the interval's lower end exceeds 0.5, MOSTLY_SAFE if its upper end is
    below 0.2, PARTIAL otherwise. Hidden causes flagged: the share of h = 3 instances with any bidirected mark.
  * **Validity:** every answer passes `admg.validate`; `pc_oracle` connects every confounded non-adjacent pair (it
    must, by d-separation) and, at h = 0, recovers the true adjacencies exactly.

**Development looks (disclosed).** The domain's tests: on graphs with no hidden variable, the oracle PC's adjacencies
are exact, PC's mean adjacency F1 exceeds 0.85 at 5,000 Gaussian samples and DirectLiNGAM's directed F1 exceeds 0.8
on at least 3 of 4 Laplace graphs; one hand-built chain with a hidden cause fools the oracle PC; answers on one h = 2
instance are valid (not scored). No look at any setting of this study.

**Expectation, stated before running.** The oracle PC connects every confounded pair (theory). PC connects most of
them (about 70%), DirectLiNGAM fewer (about 50%): CONFOUNDING_MISLEADS or PARTIAL. HIDDEN_HURTS for both. Naive
pooling: NO_EFFECT for PC, POOLING_HURTS for DirectLiNGAM (pooled noise is no longer independent).
**Cost.** About 160 x 3 short runs, a few minutes. **Status.** DEV; licenses nothing.
"""
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis.common import code_identity, digest  # noqa: E402

STUDY = 'b20r118'
SEED = 20311181
N_SEEDS = 40
P, DENSITY, NOISE, N_TOTAL = 10, 0.2, 'laplace', 3000
HS, KS = (0, 3), (1, 3)
METHODS = ('empty', 'pc', 'pc_oracle', 'lingam')
DATA_METHODS = ('pc', 'lingam')
ALPHA = 0.05


def cells():
    return [(SEED + i, h, k) for i in range(N_SEEDS) for h in HS for k in KS]


def wilcoxon_label(a, b, names):
    """Paired Wilcoxon of a - b (higher is better): names[0] if a is better, names[1] if worse, else names[2]."""
    from scipy.stats import wilcoxon
    d = [x - y for x, y in zip(a, b) if x != y]
    if len(d) < 6:
        return {'label': names[2], 'p': 1.0, 'nonzero': len(d), 'mean_difference': statistics.mean(
            [x - y for x, y in zip(a, b)]) if a else 0.0}
    p = float(wilcoxon(d, zero_method='wilcox', alternative='two-sided').pvalue)
    md = statistics.mean([x - y for x, y in zip(a, b)])
    return {'label': names[2] if p >= ALPHA else (names[0] if md > 0 else names[1]), 'p': p, 'nonzero': len(d),
            'mean_difference': md}


def clopper_pearson(k, n, level=0.95):
    from scipy.stats import beta
    a = (1 - level) / 2
    lo = 0.0 if k == 0 else float(beta.ppf(a, k, n - k + 1))
    hi = 1.0 if k == n else float(beta.ppf(1 - a, k + 1, n - k))
    return lo, hi


def analyse(rows):
    """rows: one per (seed, h, k, method) with the scores -> the tests and the headroom."""
    by = {(r['seed'], r['h'], r['k'], r['method']): r for r in rows}
    seeds = sorted({r['seed'] for r in rows})

    def f1(h, k, m):
        return [by[(s, h, k, m)]['scores']['directed']['f1'] for s in seeds]
    means = {m: {f'h{h}_k{k}': {key: statistics.mean(
        (by[(s, h, k, m)]['scores'][key]['f1'] if key in ('directed', 'adjacency', 'bidirected')
         else by[(s, h, k, m)]['scores'][key]) for s in seeds) for key in ('directed', 'adjacency', 'shd')}
        for h in HS for k in KS} for m in METHODS}
    test1 = {m: wilcoxon_label(f1(3, 1, m), f1(0, 1, m), ('HIDDEN_HELPS', 'HIDDEN_HURTS', 'NO_EFFECT'))
             for m in DATA_METHODS}
    test2 = {m: {f'h{h}': wilcoxon_label(f1(h, 3, m), f1(h, 1, m), ('POOLING_HELPS', 'POOLING_HURTS', 'NO_EFFECT'))
                 for h in HS} for m in DATA_METHODS}
    spur = {}
    for m in METHODS:
        k_tot = n_tot = 0
        for s in seeds:
            for k in KS:
                sc = by[(s, 3, k, m)]['scores']
                n_pairs = sc['confounded_nonadjacent']
                k_tot += sc['confounded_connected']
                n_tot += n_pairs
        lo, hi = clopper_pearson(k_tot, n_tot) if n_tot else (None, None)
        spur[m] = {'connected': k_tot, 'pairs': n_tot, 'rate': k_tot / n_tot if n_tot else None, 'ci95': [lo, hi]}
    better = max(DATA_METHODS, key=lambda m: (statistics.mean(f1(3, 1, m) + f1(3, 3, m)), -DATA_METHODS.index(m)))
    lo, hi = spur[better]['ci95']
    headroom = 'CONFOUNDING_MISLEADS' if lo is not None and lo > 0.5 else (
        'MOSTLY_SAFE' if hi is not None and hi < 0.2 else 'PARTIAL')
    flagged = {m: statistics.mean(by[(s, 3, k, m)]['scores']['latent_flagged'] for s in seeds for k in KS)
               for m in METHODS}
    return {'means': means, 'test1': test1, 'test2': test2, 'spurious': spur, 'better_at_h3': better,
            'headroom': headroom, 'hidden_flagged': flagged}


def checks(rows):
    """The validity conditions on the oracle."""
    ok = True
    for r in rows:
        if r['method'] != 'pc_oracle':
            continue
        sc = r['scores']
        if sc['confounded_connected'] != sc['confounded_nonadjacent']:
            ok = False
        if r['h'] == 0 and sc['adjacency']['f1'] != 1.0:
            ok = False
    return ok


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        raise SystemExit(__doc__.splitlines()[2])
    out = Path(argv[0]).resolve()
    if out != (ROOT / 'evidence' / 'causal_calibration_b20r118').resolve():
        raise SystemExit('the registered output is evidence/causal_calibration_b20r118')
    out.mkdir(parents=True, exist_ok=True)
    import b20r33_strong_baseline_audit as R33
    from genesis.causal import admg as A
    from genesis.causal import methods as CM
    from genesis.causal import sem as S
    cpu = R33.pinned_core()
    t0 = time.monotonic()
    logf = (out / 'run.log').open('a')

    def log(m):
        line = f'[{time.monotonic() - t0:7.1f}s] {m}'
        print(line, flush=True)
        logf.write(line + '\n')
        logf.flush()
    log(f'{STUDY}; pinned to CPU {cpu}; {len(cells())} instances x {len(METHODS)} methods')
    path = out / 'runs.jsonl'
    done = {}
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                done[(r['seed'], r['h'], r['k'], r['method'])] = r
    invalid = 0
    for seed, h, k in cells():
        if all((seed, h, k, m) in done for m in METHODS):
            continue
        view, truth = S.instance(seed, P, h, DENSITY, NOISE, k, N_TOTAL)
        directed, bidirected = A.truth_marks(truth)
        adj = {tuple(sorted(e)) for e in directed}
        conf_nonadj = sorted(bidirected - adj)
        for m in METHODS:
            if (seed, h, k, m) in done:
                continue
            c0 = time.process_time()
            ans = CM.METHODS[m](view, truth=truth)
            cpu_s = time.process_time() - c0
            problems = A.validate(ans, P)
            if problems:
                invalid += 1
                raise SystemExit(f'{m} gave an invalid answer on seed {seed}: {problems}')
            sc = A.score(truth, ans)
            connected = {tuple(sorted(e)) for e in ans['directed']} | {tuple(sorted(e)) for e in ans['undirected']}
            sc['confounded_nonadjacent'] = len(conf_nonadj)
            sc['confounded_connected'] = sum(pr in connected for pr in conf_nonadj)
            row = {'seed': seed, 'h': h, 'k': k, 'method': m, 'answer': ans, 'scores': sc, 'cpu_s': round(cpu_s, 4),
                   'truth': {'directed': sorted(directed), 'confounded': truth['confounded'],
                             'scales': truth['scales']}}
            done[(seed, h, k, m)] = row
            with path.open('a') as f:
                f.write(json.dumps(row, sort_keys=True) + '\n')
        log(f'seed {seed} h {h} k {k}: ' + ', '.join(
            f"{m} F1 {done[(seed, h, k, m)]['scores']['directed']['f1']:.2f}" for m in METHODS))
    rows = list(done.values())
    res = analyse(rows)
    valid = checks(rows) and invalid == 0
    summary = dict(res, study=STUDY, schema='genesis-b20r118-causal-calibration-v1', valid=valid,
                   instances=len(cells()), runs=len(rows), code_identity=code_identity(ROOT)['sha256'],
                   status='DEV; licenses nothing')
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n')
    t1 = ', '.join(f"{m} {v['label']}" for m, v in res['test1'].items())
    better = res['better_at_h3']
    log(f"valid {valid}; test 1: {t1}; headroom {res['headroom']} ({better} connects "
        f"{res['spurious'][better]['rate']:.2f} of confounded pairs)")
    return 0


if __name__ == '__main__':
    sys.exit(main())
