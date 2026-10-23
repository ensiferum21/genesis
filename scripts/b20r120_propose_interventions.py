#!/usr/bin/env python3
"""B20_R120: can Genesis propose the experiments that resolve hidden causes? (DEV, preregistered)

    taskset -c 0 python3 scripts/b20r120_propose_interventions.py OUT_DIR     run ALONE (resumable), then analyse

**Why.** Daniel's research alert, item 2: the test of "knowing what it does not know" is whether the system proposes
the measurement or intervention that resolves a hidden cause. B20_R118: established methods without hidden variables
turn hidden common causes into causal edges (DirectLiNGAM 99% of confounded pairs, PC 68%). FCI allows hidden
variables but often cannot decide. B20_R119 built the step that can: a budget of hard interventions, with Genesis's
choice of targets (`causal.active`, strategy `suspicion`: where FCI's marks and the environments' non-invariance
point to a hidden cause). This study asks whether that choice beats chance and a standard heuristic at equal budgets.

**Design (fixed before running).**
  * **Instances:** 40 seeds from SEED: p = 10 observed variables, edge density 0.2, h = 3 hidden confounders, K = 3
    environments, Laplace noise, N = 3,000 observational samples (`causal.sem`). Each intervention draws N_INT =
    1,000 samples of do(X_t) in the reference environment.
  * **Arms:** `fci` (no intervention; the established method with hidden variables); for budgets m = 2 and 4, the
    strategies `random`, `degree` and `suspicion` (Genesis's), and the reference `oracle` (told the truth; the
    ceiling of target choice). Every arm shares FCI and the decision rule; only the choice of targets differs.
  * **Primary measure:** F1 of the hidden-cause marks (bidirected edges) against the planted confounded pairs.
    Also reported: directed F1, the spurious rate (confounded pairs without a direct edge that keep a causal mark),
    SHD.
  * **Test 1 (primary), at m = 2:** `suspicion` against `random`, the paired Wilcoxon signed-rank test of
    bidirected F1 over the 40 seeds (zeros dropped, two-sided, alpha 0.05, at least 6 non-zero differences):
    SUSPICION_BETTER / SUSPICION_WORSE / NO_DIFFERENCE. **Verdict:** GENESIS_PROPOSES_BETTER if SUSPICION_BETTER,
    GENESIS_PROPOSES_WORSE if SUSPICION_WORSE, NOT_SHOWN otherwise.
  * **Secondary tests** (same test, reported, not part of the verdict): `suspicion` against `random` at m = 4;
    `suspicion` against `degree` at m = 2 and 4; `suspicion` at m = 4 against `fci` (INTERVENTIONS_HELP /
    INTERVENTIONS_HURT / NO_DIFFERENCE).
  * **Validity:** every answer passes `admg.validate`; every arm uses exactly its budget of distinct targets.

**Development looks (disclosed).** B20_R119's tests: FCI with the oracle on hand-built and random models (sound on
all of them; in a builder check on 300 more random models with 3 hidden variables, no unsound mark among 222
bidirected and 1,099 directed ones); the procedure on one hand-built model and on two generated instances (answers
valid, budgets respected; not scored). No look at any instance of this study.

**Expectation, stated before running.** FCI marks some hidden causes (bidirected recall about 0.3). At m = 2,
`random` rarely intervenes on both ends of a confounded pair, `suspicion` often: GENESIS_PROPOSES_BETTER. At m = 4,
`suspicion` is better than `random` and close to `degree`; INTERVENTIONS_HELP. The oracle is well above all.
**Cost.** 40 seeds x 9 arms, each an FCI run and up to 4 interventions: a few minutes. **Status.** DEV; licenses
nothing.
"""
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis.common import code_identity  # noqa: E402

STUDY = 'b20r120'
SEED = 20321201
N_SEEDS = 40
P, H, K, DENSITY, NOISE, N_TOTAL, N_INT = 10, 3, 3, 0.2, 'laplace', 3000, 1000
BUDGETS = (2, 4)
STRATS = ('random', 'degree', 'suspicion', 'oracle')
ARMS = ('fci',) + tuple(f'{s}@{m}' for m in BUDGETS for s in STRATS)
ALPHA = 0.05


def wilcoxon_label(a, b, names):
    """Paired Wilcoxon of a - b (higher is better): names = (better, worse, none)."""
    from scipy.stats import wilcoxon
    diffs = [x - y for x, y in zip(a, b)]
    d = [x for x in diffs if x != 0]
    md = statistics.mean(diffs) if diffs else 0.0
    if len(d) < 6:
        return {'label': names[2], 'p': 1.0, 'nonzero': len(d), 'mean_difference': md}
    p = float(wilcoxon(d, zero_method='wilcox', alternative='two-sided').pvalue)
    return {'label': names[2] if p >= ALPHA else (names[0] if md > 0 else names[1]), 'p': p, 'nonzero': len(d),
            'mean_difference': md}


def analyse(rows):
    by = {(r['seed'], r['arm']): r for r in rows}
    seeds = sorted({r['seed'] for r in rows})

    def bf1(arm):
        return [by[(s, arm)]['scores']['bidirected']['f1'] for s in seeds]
    means = {}
    for arm in ARMS:
        sc = [by[(s, arm)]['scores'] for s in seeds]
        spur = [x['spurious_rate'] for x in sc if x['spurious_rate'] is not None]
        means[arm] = {'bidirected_f1': statistics.mean(x['bidirected']['f1'] for x in sc),
                      'bidirected_precision': statistics.mean(x['bidirected']['precision'] for x in sc),
                      'bidirected_recall': statistics.mean(x['bidirected']['recall'] for x in sc),
                      'directed_f1': statistics.mean(x['directed']['f1'] for x in sc),
                      'shd': statistics.mean(x['shd'] for x in sc),
                      'spurious_rate': statistics.mean(spur) if spur else None}
    sb = ('SUSPICION_BETTER', 'SUSPICION_WORSE', 'NO_DIFFERENCE')
    test1 = wilcoxon_label(bf1('suspicion@2'), bf1('random@2'), sb)
    secondary = {'suspicion_vs_random@4': wilcoxon_label(bf1('suspicion@4'), bf1('random@4'), sb),
                 'suspicion_vs_degree@2': wilcoxon_label(bf1('suspicion@2'), bf1('degree@2'), sb),
                 'suspicion_vs_degree@4': wilcoxon_label(bf1('suspicion@4'), bf1('degree@4'), sb),
                 'suspicion@4_vs_fci': wilcoxon_label(bf1('suspicion@4'), bf1('fci'),
                                                      ('INTERVENTIONS_HELP', 'INTERVENTIONS_HURT', 'NO_DIFFERENCE'))}
    verdict = {'SUSPICION_BETTER': 'GENESIS_PROPOSES_BETTER', 'SUSPICION_WORSE': 'GENESIS_PROPOSES_WORSE'}.get(
        test1['label'], 'NOT_SHOWN')
    return {'means': means, 'test1': test1, 'secondary': secondary, 'verdict': verdict}


def checks(rows):
    for r in rows:
        if r['valid_problems']:
            return False
        m = 0 if r['arm'] == 'fci' else int(r['arm'].split('@')[1])
        if len(r['targets']) != m or len(set(r['targets'])) != m:
            return False
    return True


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        raise SystemExit(__doc__.splitlines()[2])
    out = Path(argv[0]).resolve()
    if out != (ROOT / 'evidence' / 'propose_interventions_b20r120').resolve():
        raise SystemExit('the registered output is evidence/propose_interventions_b20r120')
    out.mkdir(parents=True, exist_ok=True)
    import b20r33_strong_baseline_audit as R33
    from genesis.causal import active as AC
    from genesis.causal import admg as A
    from genesis.causal import sem as S
    cpu = R33.pinned_core()
    t0 = time.monotonic()
    logf = (out / 'run.log').open('a')

    def log(m):
        line = f'[{time.monotonic() - t0:7.1f}s] {m}'
        print(line, flush=True)
        logf.write(line + '\n')
        logf.flush()
    log(f'{STUDY}; pinned to CPU {cpu}; {N_SEEDS} instances x {len(ARMS)} arms')
    path = out / 'runs.jsonl'
    done = {}
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                done[(r['seed'], r['arm'])] = r
    for i in range(N_SEEDS):
        seed = SEED + i
        if all((seed, a) in done for a in ARMS):
            continue
        view, truth = S.instance(seed, P, H, DENSITY, NOISE, K, N_TOTAL)
        for arm in ARMS:
            if (seed, arm) in done:
                continue
            strat, m = ('suspicion', 0) if arm == 'fci' else (arm.split('@')[0], int(arm.split('@')[1]))
            c0 = time.process_time()
            ans, rec = AC.resolve(view, truth, strat, m, N_INT, seed)
            cpu_s = time.process_time() - c0
            problems = A.validate(ans, P)
            sc = A.score(truth, ans) if not problems else None
            row = {'seed': seed, 'arm': arm, 'answer': ans, 'scores': sc, 'targets': rec['targets'],
                   'suspicion': rec['suspicion'], 'valid_problems': problems, 'cpu_s': round(cpu_s, 3),
                   'truth': {'confounded': truth['confounded'],
                             'directed': sorted(A.truth_marks(truth)[0])}}
            done[(seed, arm)] = row
            with path.open('a') as f:
                f.write(json.dumps(row, sort_keys=True) + '\n')
        log(f'seed {seed}: bidirected F1 ' + ', '.join(
            f"{a} {done[(seed, a)]['scores']['bidirected']['f1']:.2f}" for a in ARMS if done[(seed, a)]['scores']))
    rows = list(done.values())
    valid = checks(rows)
    if not valid:
        summary = {'study': STUDY, 'valid': False, 'code_identity': code_identity(ROOT)['sha256']}
        (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n')
        log('INVALID: an answer failed validation or a budget was not used exactly')
        return 1
    res = analyse(rows)
    summary = dict(res, study=STUDY, schema='genesis-b20r120-propose-interventions-v1', valid=valid,
                   instances=N_SEEDS, runs=len(rows), code_identity=code_identity(ROOT)['sha256'],
                   status='DEV; licenses nothing')
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n')
    log(f"valid {valid}; test 1 {res['test1']['label']} (p {res['test1']['p']:.3g}); verdict {res['verdict']}; "
        'bidirected F1 ' + ', '.join(f"{a} {v['bidirected_f1']:.2f}" for a, v in res['means'].items()))
    return 0


if __name__ == '__main__':
    sys.exit(main())
