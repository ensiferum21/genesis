#!/usr/bin/env python3
"""B20_R124: when the noise is Gaussian, do experiments become necessary to mark hidden causes? (DEV, preregistered)

    taskset -c 0 python3 scripts/b20r124_gaussian_hidden_causes.py OUT_DIR     run ALONE (resumable), then analyse

**Why.** B20_R122: on non-Gaussian (Laplace) data Genesis marks hidden causes with F1 0.47 against FCI's 0.21, almost
all of it from the observational flag (residual dependence), while experiments add direction but not detection.
The flag rests on non-Gaussianity: with Gaussian noise an uncorrelated residual is independent, so the flag should
see nothing. This is a prediction the theory makes and the system has not been tested on: there, the observational
route closes, and only experiments can separate a hidden common cause from a direct one. If so, the choice of
experiments, which B20_R120 and R122 found no better than chance, is where the remaining value is.

**Design (fixed before running).**
  * **Instances:** 40 fresh seeds from SEED; B20_R122's settings except the noise: p = 10, edge density 0.2,
    h = 3 hidden confounders, K = 3 environments, **Gaussian** noise (observed and hidden), N = 3,000 observational
    samples; N_INT = 1,000 samples per intervention.
  * **Arms** (`causal.active2`, version 2's rule and signal):
      - `fci` (FCI alone) and `flag` (FCI plus the observational flag);
      - `random@4`, `degree@4`, `suspicion@4` and `oracle@4` (all with the flag);
      - `random@8` (a larger budget).
  * **Measures:** F1 of the hidden-cause marks (primary); directed F1; the spurious rate; SHD.
  * **Test 1 (primary), are experiments needed?** `random@4` against `flag`, the paired Wilcoxon signed-rank test of
    hidden-cause F1 over the 40 seeds (zeros dropped, two-sided, alpha 0.05, at least 6 non-zero differences):
    EXPERIMENTS_ADD / EXPERIMENTS_SUBTRACT / NO_DIFFERENCE. **Verdict:** EXPERIMENTS_NEEDED if EXPERIMENTS_ADD,
    NOT_SHOWN otherwise.
  * **Secondary tests** (same test, reported): `flag` against `fci` (does the flag still help?); `oracle@4` against
    `random@4` (is there value in the choice of experiments?); `suspicion@4` against `random@4`; `random@8` against
    `random@4`.
  * **Validity:** every answer passes `admg.validate`; every arm uses exactly its budget of distinct targets.

**Development looks (disclosed).** None on Gaussian data. B20_R121's development and B20_R122's result were on
Laplace data (fresh seeds here).

**Expectation, stated before running.** The flag marks almost nothing beyond FCI (`flag` against `fci`:
NO_DIFFERENCE). Experiments add hidden-cause marks (EXPERIMENTS_NEEDED), more at budget 8. The oracle's choice is
clearly better than random (the value of choosing experiments well), and Genesis's suspicion, whose signal is blind
here, is no better than random. Hidden-cause F1 lower than on Laplace data for every arm.
**Cost.** 40 seeds x 7 arms: about 3 minutes. **Status.** DEV; licenses nothing.
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
import b20r120_propose_interventions as R120  # noqa: E402
import b20r122_hidden_causes_v2 as R122  # noqa: E402

STUDY = 'b20r124'
SEED = 20341241
N_SEEDS = 40
P, H, K, DENSITY, N_TOTAL, N_INT = R122.P, R122.H, R122.K, R122.DENSITY, R122.N_TOTAL, R122.N_INT
NOISE = 'gauss'
ARMS = ('fci', 'flag', 'random@4', 'degree@4', 'suspicion@4', 'oracle@4', 'random@8')
ALPHA = 0.05


def analyse(rows):
    by = {(r['seed'], r['arm']): r for r in rows}
    seeds = sorted({r['seed'] for r in rows})

    def col(arm):
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
    w = R120.wilcoxon_label
    ex = ('EXPERIMENTS_ADD', 'EXPERIMENTS_SUBTRACT', 'NO_DIFFERENCE')
    test1 = w(col('random@4'), col('flag'), ex)
    secondary = {
        'flag_vs_fci': w(col('flag'), col('fci'), ('FLAG_HELPS', 'FLAG_HURTS', 'NO_DIFFERENCE')),
        'oracle_vs_random@4': w(col('oracle@4'), col('random@4'), ('ORACLE_BETTER', 'ORACLE_WORSE', 'NO_DIFFERENCE')),
        'suspicion_vs_random@4': w(col('suspicion@4'), col('random@4'),
                                   ('SUSPICION_BETTER', 'SUSPICION_WORSE', 'NO_DIFFERENCE')),
        'random@8_vs_random@4': w(col('random@8'), col('random@4'), ('MORE_HELPS', 'MORE_HURTS', 'NO_DIFFERENCE'))}
    verdict = 'EXPERIMENTS_NEEDED' if test1['label'] == 'EXPERIMENTS_ADD' else 'NOT_SHOWN'
    return {'means': means, 'test1': test1, 'secondary': secondary, 'verdict': verdict}


def checks(rows):
    for r in rows:
        if r['valid_problems']:
            return False
        m = R122.arm_spec(r['arm'])[1]
        if len(r['targets']) != m or len(set(r['targets'])) != m:
            return False
    return True


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        raise SystemExit(__doc__.splitlines()[2])
    out = Path(argv[0]).resolve()
    if out != (ROOT / 'evidence' / 'gaussian_hidden_causes_b20r124').resolve():
        raise SystemExit('the registered output is evidence/gaussian_hidden_causes_b20r124')
    out.mkdir(parents=True, exist_ok=True)
    import b20r33_strong_baseline_audit as R33
    from genesis.causal import active2 as V2
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
    log(f'{STUDY}; pinned to CPU {cpu}; {N_SEEDS} instances x {len(ARMS)} arms; Gaussian noise')
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
            strat, m, flag = R122.arm_spec(arm)
            c0 = time.process_time()
            ans, rec = V2.resolve(view, truth, strat, m, N_INT, seed, flag=flag)
            cpu_s = time.process_time() - c0
            problems = A.validate(ans, P)
            sc = A.score(truth, ans) if not problems else None
            row = {'seed': seed, 'arm': arm, 'answer': ans, 'scores': sc, 'targets': rec['targets'],
                   'tests': rec['tests'], 'suspicion': rec['suspicion'], 'valid_problems': problems,
                   'cpu_s': round(cpu_s, 3),
                   'truth': {'confounded': truth['confounded'], 'directed': sorted(A.truth_marks(truth)[0])}}
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
    summary = dict(res, study=STUDY, schema='genesis-b20r124-gaussian-hidden-causes-v1', valid=valid,
                   instances=N_SEEDS, runs=len(rows), code_identity=code_identity(ROOT)['sha256'],
                   status='DEV; licenses nothing')
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n')
    log(f"valid {valid}; test 1 {res['test1']['label']} (p {res['test1']['p']:.3g}); verdict {res['verdict']}; "
        'bidirected F1 ' + ', '.join(f"{a} {v['bidirected_f1']:.2f}" for a, v in res['means'].items()))
    return 0


if __name__ == '__main__':
    sys.exit(main())
