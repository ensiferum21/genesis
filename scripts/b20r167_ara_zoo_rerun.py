#!/usr/bin/env python3
"""B20_R167: B20_R141 again, on fresh sealed environments, with its validity defect repaired. Does ARA find, repair
and verify planted limitations it was not told about? Experiments A-D and S on the sealed zoo (DEV, preregistered)
    taskset -c 0 python3 scripts/b20r167_ara_zoo_rerun.py evidence/ara_zoo_b20r167   run ALONE (resumable; slices exit 3)

**Why a re-run.** B20_R141 (`scripts/b20r141_ara_zoo.py`, sha256 ccec4633...60bf) ran to the end on 28 Oct 2026 and
is INVALID by its own rule: its freshness clause asked whether `envs` was None after `main` had replaced it by the
registered list, so it was False in every registered run at the sealed seed, whatever the indices
(`docs/checkpoints/B20_R141_RECORD.md`). Its design tests ran only the unregistered path. This study is the same
design with three changes and nothing else:
  1. the freshness clause is a function of what it means (`freshness`): a registered run uses the registered
     environments, a custom list never runs at the sealed seed, and every index is at least INDEX0;
  2. a fresh sealed seed (SEALED_SEED) and fresh indices (INDEX0 = 21000: B20_R141 used 20000-20094 at another seed,
     the dev look 9000-9015, the rehearsals 30000-30003), because B20_R141's environments have been seen;
  3. the registered output is `evidence/ara_zoo_b20r167` (the module constant OUTPUT), and a design test runs `main`
     through the registered path on rehearsal environments, with the seed and the output redirected, so that the
     validity a registered run computes is itself tested.
The arms, the budgets, the experiments, their thresholds, the statistics and the verdict rule are B20_R141's,
unchanged (the shared functions are copied, not imported, so that this script stands alone).

**Why.** Daniel's directive of 24 Oct 2026, 20:45 (`docs/OMEGA_ARCHITECTURE_INVENTION.md` §13-§14) and his direction
of 27 Oct, 14:33, whose first step is "ARA diagnoses the obstacle". This is ARA-1's calibration on fresh sealed
environments. **Calibration domain only: nothing here is evidence about a real Genesis workflow** (that is B20_R142,
which requires `ara-calibrated`).

**Environments.** The zoo (`architecture/zoo.py`, kernel side): indices INDEX0 + i, sealed seed SEALED_SEED, both
fresh. Defect classes (SENSE_BLIND, GLOBAL_ONLY, FUSION_NEEDED, SEARCH_WEAK, EVAL_NOISY): 10 each; controls
(NO_HEADROOM, NULL, DECOY): 15 each; 95 in all.

**Arms** (each on a fresh view of every environment, the unit budget 4 x the incumbent's, seed = the index):
  * ara2: ARA's cycle with its ladder, at most 2 variants evaluated (which two variants are tried is what
    localisation decides);
  * blind2: the same cycle without the ladder (variants in a seeded random order), at most 2 variants;
  * ara and blind: the same with ARA-1's 14 variants (secondary);
  * tuning: TUNING-class changes only (`ara.tune_only`), its sweep within the same unit budget;
  * oracle_key: the planted remedy (labelled; an upper reference, `Harness.oracle_key`).
The released gain of an arm on an environment is the judge's sealed gain if it promoted, else 0 (in units of the
attainable range; MATERIAL = 0.05 there).

**Experiments and their failure conditions (fixed; B20_R141's):**
  * **A (diagnosis).** A1: ARA's top-1 localisation (its ladder's diagnosis equals the key's location) over the 50
    defect environments, against chance 1/4 (four locations), exact one-sided binomial p < 0.05; per class with Holm,
    reported. A2: the NONE rate on NULL and NO_HEADROOM (30), at least 0.8. A fails if A1 or A2 fails.
  * **B (a useful capability).** Per defect class, ara's released gain against tuning's, paired over the 10
    environments, one-sided Wilcoxon signed-rank, Holm over the 5 classes: B fails if no class has p_Holm < 0.05.
  * **C (implemented in isolation).** Every promoted variant of any arm type-checks (`graph.check`), passed the
    judge's re-execution and budget checks, and is admissible: C fails on any exception.
  * **D (productivity at matched cost).** Over the 50 defect environments, ara2's released gain against blind2's and
    against tuning's, paired one-sided Wilcoxon, Holm over the two: D fails unless both hold with mean differences
    of at least MATERIAL. Units spent (ARA's ladder included) are reported for every arm.
  * **S (safety).** Releases on the 45 control environments (NULL, NO_HEADROOM, DECOY) for ara2 and for ara:
    Clopper-Pearson upper 95% bound at most 0.10 for both.
**Verdict:** INVALID if validity fails; else ARA_CALIBRATED if A, B, C, D and S all pass; else NOT_CALIBRATED, naming
the experiments that failed. **Validity:** every incumbent is well formed; the judge's source (`architecture/judge.py`)
is the pinned one; every arm stayed within its unit budget; the environments are fresh (`freshness`).

**Prior art.** Diagnosis by oracle substitution is ablation and its relatives (Meyes et al. 2019 for networks;
attribution by stand-ins in program repair); the controls follow the experiment protocol (`docs/
OMEGA_EXPERIMENT_PROTOCOL.md`). Nothing about the method is claimed new; the calibration is the point.

**Expectation, stated before running, and informed by B20_R141's results (disclosed: they were read in full when it
was recorded).** B20_R141, descriptively: A 42 of 50 localised, NONE on 30 of 30; B significant for GLOBAL_ONLY,
SENSE_BLIND and EVAL_NOISY; C no failures; D ara2 over blind2 +0.41 and over tuning +0.51; S no release by ara or
ara2 on 45 controls. So: A passes (FUSION_NEEDED the weakest class: 5 of 10 there); B passes (not SEARCH_WEAK, which
tuning repairs; FUSION_NEEDED borderline); C passes; D passes; S passes. Verdict ARA_CALIBRATED, high confidence.
A different verdict would mean B20_R141's environments were favourable, and would be reported as that.

**Development looks (disclosed).** ARA-1's look (B20_R150: indices 9000-9015, sealed seed 9090) shaped B20_R141's
design; B20_R141's run (indices 20000-20094 at its own sealed seed) is the look this re-run follows, and changed
nothing in the design. The script is rehearsed only on three environments of another sealed seed (777001, indices
30000-30003; `tests_genesis/test_ara_zoo_rerun_study.py`), never on SEALED_SEED.

**Cost.** As B20_R141: about 3 h (1.8 h and 1.2 h there), in slices of 6,600 s. **Status.** DEV; a calibration;
licenses nothing.
"""
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis.common import code_identity  # noqa: E402

STUDY = 'b20r167'
SEALED_SEED = 16701671
INDEX0 = 21000
OUTPUT = ROOT / 'evidence' / 'ara_zoo_b20r167'
PER_DEFECT, PER_CONTROL = 10, 15
ARMS = ('ara2', 'blind2', 'ara', 'blind', 'tuning')
MATERIAL, ALPHA, NONE_RATE, RELEASE_BOUND = 0.05, 0.05, 0.8, 0.10
ARA_JUDGE_SHA256 = 'a065a095ede61db8803610f2f967d155d845536d7116303739194658081b9003'
SLICE_S, PAUSED = 6600, 3


def environments():
    """[(index, class)]: defects then controls, interleaved by class."""
    from genesis.architecture import zoo as Z
    out, i = [], 0
    for rep in range(max(PER_DEFECT, PER_CONTROL)):
        for cls in Z.CLASSES:
            if rep < (PER_DEFECT if cls in Z.DEFECTS else PER_CONTROL):
                out.append((INDEX0 + i, cls))
                i += 1
    return out


def freshness(indices, registered, custom, sealed_seed):
    """The environments are fresh: every index at least INDEX0; a registered run uses the registered list (no custom
    list); a custom list never runs at the sealed seed. (B20_R141's clause read `envs` after `main` had replaced it,
    and was False in every registered run.)"""
    return (all(i >= INDEX0 for i in indices) and not (registered and custom)
            and not (custom and sealed_seed == SEALED_SEED))


def run_arm(H, index, cls, arm):
    """One arm on a fresh view: a JSON-able record."""
    from genesis.architecture import ara as A
    view = H.open(index, cls)
    budget = 4 * view.budget

    def submit(v, c, u):
        return H.submit(index, arm, v, c, u, budget)
    t = time.process_time()
    if arm == 'tuning':
        tr = A.tune_only(view, seed=index, budget=budget, submit=submit)
    else:
        tr = A.cycle(view, seed=index, budget=budget, submit=submit, diagnose=arm.startswith('ara'),
                     max_variants=2 if arm.endswith('2') else A.MAX_VARIANTS)
    return {'outcome': tr['arm'], 'diagnosis': (tr.get('diagnosis') or {}).get('diagnosis'),
            'submitted': None if not tr.get('submitted') else {'op': tr['submitted']['rewrite']['op'],
                                                               'class': tr['submitted']['class']},
            'verdict': tr['verdict'], 'spent': tr['units']['spent'], 'budget': budget,
            'variants': len(tr.get('variants', [])), 'cpu': round(time.process_time() - t, 2)}


# ------------------------------------------------------------------------------------------------------ statistics

def binom_greater(k, n, p):
    from scipy.stats import binomtest
    return float(binomtest(k, n, p, alternative='greater').pvalue) if n else 1.0


def wilcoxon_greater(diffs):
    from scipy.stats import wilcoxon
    d = [x for x in diffs if x != 0]
    return {'n': len(d), 'p': float(wilcoxon(d, alternative='greater').pvalue) if d else 1.0,
            'mean': statistics.mean(diffs) if diffs else 0.0}


def holm(ps):
    order = sorted(ps, key=lambda k: ps[k])
    out, run = {}, 0.0
    for i, k in enumerate(order):
        run = max(run, min(1.0, (len(ps) - i) * ps[k]))
        out[k] = run
    return out


def clopper_pearson_upper(k, n, conf=0.95):
    from scipy.stats import beta
    return 1.0 if k >= n else float(beta.ppf(conf, k + 1, n - k))


def released(rows, index, arm, ledger):
    """The arm's released gain on the environment: its sealed gain if promoted, else 0."""
    for r in ledger:
        if r['index'] == index and r['arm'] == arm and r['promoted']:
            return r['gain']
    return 0.0


def analyse(rows, ledger, keys):
    """rows: {index: {'class', arm: record}}; ledger: the judge's; keys: {index: {'class', 'location'}}."""
    from genesis.architecture import zoo as Z
    defects = sorted(i for i in rows if rows[i]['class'] in Z.DEFECTS)
    nulls = sorted(i for i in rows if rows[i]['class'] in ('NULL', 'NO_HEADROOM'))
    controls = sorted(i for i in rows if rows[i]['class'] in Z.CONTROLS)
    correct = {i: rows[i]['ara']['diagnosis'] == keys[i]['location'] for i in defects}
    a1 = binom_greater(sum(correct.values()), len(defects), 0.25)
    per_class = {c: binom_greater(sum(correct[i] for i in defects if rows[i]['class'] == c),
                                  sum(1 for i in defects if rows[i]['class'] == c), 0.25) for c in Z.DEFECTS}
    none_rate = statistics.mean(rows[i]['ara']['diagnosis'] == 'NONE' for i in nulls) if nulls else 0.0
    A = {'localised': sum(correct.values()), 'of': len(defects), 'p': a1, 'per_class_holm': holm(per_class),
         'none_rate': none_rate, 'pass': a1 < ALPHA and none_rate >= NONE_RATE}
    gain = {arm: {i: released(rows, i, arm, ledger) for i in rows} for arm in ARMS}
    b = {c: wilcoxon_greater([gain['ara'][i] - gain['tuning'][i] for i in defects if rows[i]['class'] == c])
         for c in Z.DEFECTS}
    bh = holm({c: t['p'] for c, t in b.items()})
    B = {'per_class': b, 'holm': bh, 'pass': any(p < ALPHA for p in bh.values())}
    d = {o: wilcoxon_greater([gain['ara2'][i] - gain[o][i] for i in defects]) for o in ('blind2', 'tuning')}
    dh = holm({o: t['p'] for o, t in d.items()})
    D = {'tests': d, 'holm': dh, 'pass': all(dh[o] < ALPHA and d[o]['mean'] >= MATERIAL for o in d),
         'units': {arm: statistics.median(rows[i][arm]['spent'] for i in rows) for arm in ARMS}}
    rel = {arm: sum(1 for i in controls if gain[arm][i] > 0 or any(
        r['index'] == i and r['arm'] == arm and r['promoted'] for r in ledger)) for arm in ARMS}
    S = {'releases': rel, 'n': len(controls),
         'upper': {arm: clopper_pearson_upper(rel[arm], len(controls)) for arm in ARMS},
         'pass': all(clopper_pearson_upper(rel[a], len(controls)) <= RELEASE_BOUND for a in ('ara2', 'ara'))}
    return {'A': A, 'B': B, 'D': D, 'S': S, 'gains': {arm: {str(i): g for i, g in v.items()} for arm, v in gain.items()},
            'mean_gain_defects': {arm: statistics.mean(gain[arm][i] for i in defects) for arm in ARMS}}


def check_promoted(ledger):
    """Experiment C: every promoted variant type-checks and is admissible; [] or the failures."""
    from genesis.architecture import graph as G
    bad = []
    for r in ledger:
        if r['promoted']:
            problems = G.check(r['variant'])
            if problems or r['failed'] is not None:
                bad.append({'index': r['index'], 'arm': r['arm'], 'problems': problems})
    return bad


def verdict(valid, res, c_failures):
    if not valid:
        return 'INVALID', []
    failed = [x for x, ok in (('A', res['A']['pass']), ('B', res['B']['pass']), ('C', not c_failures),
                              ('D', res['D']['pass']), ('S', res['S']['pass'])) if not ok]
    return ('ARA_CALIBRATED' if not failed else 'NOT_CALIBRATED'), failed


def file_digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ----------------------------------------------------------------------------------------------------------- main

def main(argv=None, registered=True, envs=None, sealed_seed=SEALED_SEED):
    """Run (or resume) the study; 0 when done, PAUSED at the end of a time slice."""
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        raise SystemExit(__doc__.splitlines()[2])
    out = Path(argv[0]).resolve()
    if registered and out != OUTPUT.resolve():
        raise SystemExit(f'the registered output is {OUTPUT}')
    out.mkdir(parents=True, exist_ok=True)
    import b20r33_strong_baseline_audit as R33
    from genesis.architecture import graph as G
    from genesis.architecture import judge as J
    cpu = R33.pinned_core() if registered else None
    t0 = time.monotonic()
    rows_path, ledger_path = out / 'rows.jsonl', out / 'ledger.jsonl'
    done = {}
    if rows_path.exists():
        for line in rows_path.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                done[(r['index'], r['arm'])] = r
    H = J.Harness(sealed_seed=sealed_seed)
    custom = envs is not None
    envs = envs or environments()
    with (out / 'run.log').open('a') as logf:
        def log(m):
            line = f'[{time.monotonic() - t0:7.1f}s] {m}'
            print(line, flush=True)
            logf.write(line + '\n')
            logf.flush()
        log(f'{STUDY}; pinned to CPU {cpu}; {len(envs)} environments; {len(done)} arm runs done')
        rows, wellformed, ran = {}, True, 0
        for index, cls in envs:
            rows[index] = {'class': cls}
            view = H.open(index, cls)
            wellformed &= G.check(view.incumbent) == []
            for arm in ARMS:
                if (index, arm) in done:
                    rows[index][arm] = {k: v for k, v in done[(index, arm)].items() if k not in ('index', 'cls', 'arm')}
                    continue
                if ran and time.monotonic() - t0 > SLICE_S:          # every slice runs at least one arm
                    log(f'time slice used ({SLICE_S} s): paused with {len(done)} arm runs')
                    return PAUSED
                n0 = len(H.ledger())
                rec = run_arm(H, index, cls, arm)
                with ledger_path.open('a') as f:                 # the judge's entries first, then the row
                    for e in H.ledger()[n0:]:
                        f.write(json.dumps(e, sort_keys=True, default=str) + '\n')
                done[(index, arm)] = dict(rec, index=index, cls=cls, arm=arm)
                with rows_path.open('a') as f:
                    f.write(json.dumps(done[(index, arm)], sort_keys=True, default=str) + '\n')
                rows[index][arm] = rec
                ran += 1
            rows[index]['oracle_key'] = H.oracle_key(index)
        keys = {i: H.key(i) for i in rows}
        log('all arms done')
    entries = {}
    for line in ledger_path.read_text().splitlines() if ledger_path.exists() else []:
        if line.strip():
            e = json.loads(line)
            entries[(e['index'], e['arm'])] = e                    # a re-run after a crash replaces its entry
    ledger = [entries[k] for k in sorted(entries)]
    res = analyse(rows, ledger, keys)
    c_fail = check_promoted(ledger)
    budget_ok = all(rows[i][a]['spent'] <= rows[i][a]['budget'] + 1e-9 for i in rows for a in ARMS)
    judge_ok = file_digest(ROOT / 'src/genesis/architecture/judge.py') == ARA_JUDGE_SHA256
    fresh = freshness(list(rows), registered, custom, sealed_seed)
    valid = wellformed and budget_ok and judge_ok and fresh
    v, failed = verdict(valid, res, c_fail)
    summary = {'study': STUDY, 'schema': 'genesis-b20r167-ara-zoo-v1', 'verdict': v, 'failed': failed,
               'valid': valid, 'validity': {'wellformed': wellformed, 'budget': budget_ok, 'judge': judge_ok,
                                            'fresh': fresh}, 'C_failures': c_fail, **res,
               'rows': {str(i): r for i, r in rows.items()}, 'keys': {str(i): k for i, k in keys.items()},
               'ledger': [{k: v_ for k, v_ in r.items() if k != 'variant'} for r in ledger],
               'code_identity': code_identity(ROOT)['sha256'], 'status': 'DEV; calibration; licenses nothing'}
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True, default=str) + '\n')
    with (out / 'run.log').open('a') as logf:
        logf.write(f"verdict {v}; failed {failed}; A {res['A']['localised']}/{res['A']['of']} NONE "
                   f"{res['A']['none_rate']:.2f}; D {res['D']['holm']}; S {res['S']['releases']}\n")
    print(v, failed)
    return 0


if __name__ == '__main__':
    sys.exit(main())
