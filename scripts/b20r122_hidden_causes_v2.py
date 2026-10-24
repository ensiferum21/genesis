#!/usr/bin/env python3
"""B20_R122: does the repaired procedure mark hidden causes, and do Genesis's experiments add anything? (DEV,
preregistered)

    taskset -c 0 python3 scripts/b20r122_hidden_causes_v2.py OUT_DIR     run ALONE (resumable), then analyse

**Why.** B20_R120 (NOT_SHOWN): Genesis's choice of interventions was no better than random, and the diagnosis named
two faults, a weak suspicion signal and a rule that read ancestry as direct causation. B20_R121 repaired both
(`causal.active2`) and added the observational use of the new signal (flagging). It was developed on B20_R120's 40
instances, which were already looked at, so every number from that development is optimistic. This study measures
the repaired procedure once, on fresh instances.

**Design (fixed before running).**
  * **Instances:** 40 fresh seeds from SEED, B20_R120's settings: p = 10, edge density 0.2, h = 3 hidden confounders,
    K = 3 environments, Laplace noise, N = 3,000 observational samples; each intervention draws N_INT = 1,000 samples
    of do(X_t).
  * **Arms** (version 2's rule and signal throughout):
      - `fci`: FCI alone (the established method that allows hidden variables);
      - `flag`: FCI plus the observational flag (no experiment);
      - for budgets m = 2 and 4: `random@m`, `degree@m`, `suspicion@m` (Genesis's choice) and `oracle@m` (told the
        truth; a ceiling), all with the flag, so experiments can only refute flags or decide other pairs.
  * **Measures:** F1 of the hidden-cause marks (bidirected edges) against the planted confounded pairs (primary);
    directed F1; the spurious rate; SHD.
  * **Test 1 (primary), capability:** `suspicion@4` against `fci`, paired Wilcoxon signed-rank test of bidirected
    F1 over the 40 seeds (zeros dropped, two-sided, alpha 0.05, at least 6 non-zero differences):
    GENESIS_BEATS_FCI / GENESIS_BEHIND_FCI / NO_DIFFERENCE.
    **Verdict:** HIDDEN_CAUSES_MARKED if GENESIS_BEATS_FCI, NOT_SHOWN otherwise.
  * **Test 2, do experiments add to the observational flag?** `suspicion@4` against `flag` on bidirected F1:
    EXPERIMENTS_ADD / EXPERIMENTS_SUBTRACT / NO_DIFFERENCE; and the same on directed F1.
  * **Test 3, is Genesis's choice of experiments better than chance?** `suspicion@m` against `random@m` on
    bidirected F1, at m = 2 and 4: SUSPICION_BETTER / SUSPICION_WORSE / NO_DIFFERENCE.
  * Tests 2 and 3 are reported at alpha 0.05 each; only Test 1 decides the verdict.
  * **Validity:** every answer passes `admg.validate`; every arm uses exactly its budget of distinct targets.

**Development looks (disclosed).** All on B20_R120's 40 instances (mean bidirected F1):
  * the pairwise residual signal tried first did not separate confounded pairs (AUC 0.54); the LiNGAM-residual signal
    adopted does (AUC 0.83);
  * with that signal and the new rule, without flags: suspicion 0.28 and 0.49 at m = 2 and 4, random 0.20 and 0.26,
    oracle 0.29 and 0.49;
  * flagging alone 0.46 (FCI 0.19), and letting experiments overwrite flags lowered every arm, so the rule was changed
    to let experiments refute flags but not erase them;
  * the arms of this study as specified: fci 0.19, flag 0.46; at m = 2: random 0.46, degree 0.45, suspicion 0.43,
    oracle 0.45; at m = 4: random 0.49, degree 0.46, suspicion 0.50, oracle 0.52. Directed F1: flag 0.27, the
    budget-4 arms 0.59 to 0.69.

**Expectation, stated before running** (from those looks, discounted for development on the same instances):
HIDDEN_CAUSES_MARKED (suspicion@4 about 0.45 against FCI about 0.2). Test 2: NO_DIFFERENCE on bidirected F1 (the
flag does most of the work), EXPERIMENTS_ADD on directed F1. Test 3: NO_DIFFERENCE at both budgets: Genesis's choice
of experiments is not expected to beat chance. The capability would come from a prior-art principle (residual
independence in linear non-Gaussian models) put to use, not from Genesis's experiment design.
**Cost.** 40 seeds x 10 arms: about 5 minutes. **Status.** DEV; licenses nothing.
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

STUDY = 'b20r122'
SEED = 20331221
N_SEEDS = 40
P, H, K, DENSITY, NOISE, N_TOTAL, N_INT = R120.P, R120.H, R120.K, R120.DENSITY, R120.NOISE, R120.N_TOTAL, R120.N_INT
BUDGETS = (2, 4)
STRATS = ('random', 'degree', 'suspicion', 'oracle')
ARMS = ('fci', 'flag') + tuple(f'{s}@{m}' for m in BUDGETS for s in STRATS)
ALPHA = 0.05


def arm_spec(arm):
    """(strategy, budget, flag)."""
    if arm == 'fci':
        return 'suspicion', 0, False
    if arm == 'flag':
        return 'suspicion', 0, True
    s, m = arm.split('@')
    return s, int(m), True


def analyse(rows):
    by = {(r['seed'], r['arm']): r for r in rows}
    seeds = sorted({r['seed'] for r in rows})

    def col(arm, key):
        return [by[(s, arm)]['scores'][key]['f1'] for s in seeds]
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
    test1 = w(col('suspicion@4', 'bidirected'), col('fci', 'bidirected'),
              ('GENESIS_BEATS_FCI', 'GENESIS_BEHIND_FCI', 'NO_DIFFERENCE'))
    ex = ('EXPERIMENTS_ADD', 'EXPERIMENTS_SUBTRACT', 'NO_DIFFERENCE')
    test2 = {'bidirected': w(col('suspicion@4', 'bidirected'), col('flag', 'bidirected'), ex),
             'directed': w(col('suspicion@4', 'directed'), col('flag', 'directed'), ex)}
    sb = ('SUSPICION_BETTER', 'SUSPICION_WORSE', 'NO_DIFFERENCE')
    test3 = {f'm{m}': w(col(f'suspicion@{m}', 'bidirected'), col(f'random@{m}', 'bidirected'), sb) for m in BUDGETS}
    verdict = 'HIDDEN_CAUSES_MARKED' if test1['label'] == 'GENESIS_BEATS_FCI' else 'NOT_SHOWN'
    return {'means': means, 'test1': test1, 'test2': test2, 'test3': test3, 'verdict': verdict}


def checks(rows):
    for r in rows:
        if r['valid_problems']:
            return False
        m = arm_spec(r['arm'])[1]
        if len(r['targets']) != m or len(set(r['targets'])) != m:
            return False
    return True


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        raise SystemExit(__doc__.splitlines()[3])
    out = Path(argv[0]).resolve()
    if out != (ROOT / 'evidence' / 'hidden_causes_v2_b20r122').resolve():
        raise SystemExit('the registered output is evidence/hidden_causes_v2_b20r122')
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
            strat, m, flag = arm_spec(arm)
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
    summary = dict(res, study=STUDY, schema='genesis-b20r122-hidden-causes-v2-v1', valid=valid, instances=N_SEEDS,
                   runs=len(rows), code_identity=code_identity(ROOT)['sha256'], status='DEV; licenses nothing')
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n')
    log(f"valid {valid}; test 1 {res['test1']['label']} (p {res['test1']['p']:.3g}); verdict {res['verdict']}; "
        'bidirected F1 ' + ', '.join(f"{a} {v['bidirected_f1']:.2f}" for a, v in res['means'].items()))
    return 0


if __name__ == '__main__':
    sys.exit(main())
