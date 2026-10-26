#!/usr/bin/env python3
"""B20_R148: a portfolio of discovery processes against Genesis's single inventor (Genesis Ω², stage Ω10; DEV, preregistered)

    taskset -c 0 python3 scripts/b20r148_harness_portfolio.py evidence/harness_portfolio_b20r148     run ALONE
                                                            (resumable: rows are saved as they finish; slices exit 3)

**Why.** Daniel's report "Beyond Genesis-Ω" (adopted 26 Oct 2026, `docs/OMEGA_META_ADAPTIVE.md`): the weakest part of
a fixed implementation is a fixed Explorer; no fixed discovery harness is reliably best, so Genesis should keep a
portfolio of discovery processes and learn which deserve compute, judged by verified progress per unit of compute on
tasks it has not seen. Genesis's inventors each run one fixed process (the steady-state evolutionary search of
`autonomy.feedback`). This study is the report's decisive experiment (G0 against G1, G2, G3), translated to an
LLM-free Genesis and bounded: six discovery processes over three of Genesis's own languages, at matched evaluations.

**Questions.**
  * H1: is any one of the six discovery processes best on every task?
  * T1: does an adaptive portfolio (G2, successive halving across processes) beat Genesis's current inventor's search
    (G0, `single:evolution`)?
  * T2: does G2 beat the single process that development tasks would have chosen (H*)?
  * T3: do process parameters meta-tuned on development tasks (G3) add to G2 on fresh tasks?

**Tasks** (`genesis.autonomy.portfolio_tasks`; each split a disjoint fresh sample; T is the study's and is never
charged or shown to an arm). Ten test tasks in three domains:
  * acquisition rules (B20_R129's language; minus experiments needed under the theory model): families base
    (p 10, h 3, density 0.2), shift (14, 4, 0.15), sparse (12, 2, 0.1) and, held out from development, large (16, 5,
    0.15); A 24, V 32, T 64 worlds;
  * planted formulas (rank correlation with a hidden target in the language; optimum 1): small, medium, large and,
    held out, mixed; A 200, V 200, T 400 items;
  * max-cut engine programs (`mcx2`, the pinned binary, at 0.02 s per graph; cut relative to REX at the same budget,
    every cut checked twice): torus (28 x 28, weights +-1) and erdos_pm1 (n 800, p 0.06, weights +-1), a domain held out
    from development entirely; A 3, V 4, T 4 graphs (Gset identities excluded).
Development tasks: the six non-held-out acquisition and formula families on DEVELOPMENT instances (their own seeds,
disjoint from the test instances). Instance seeds: SEED + 100000 x phase + 1000 x task + 100 x split (+ k per world).

**Arms** (`genesis.autonomy.portfolio`; B = 1024 evaluations each, A and V evaluations each costing one; rounds of
B/32; the answer is the arm's best validated program): the six single processes (`single:best_of_n`, `single:hill_climb`,
`single:anneal`, `single:evolution` = G0, `single:map_elites`, `single:racing`), `uniform` (G1), `halving` (G2;
successive halving across processes, 6 -> 2 -> 1, equal shares per stage), `bandit` (UCB1 with 10% exploration;
secondary) and `halving_tuned` (G3: `halving` with each process's parameters chosen by `tune_params` on the development
tasks, 4 settings per process with DEFAULTS first, seeds 200 and 201). Six run seeds (0-5) per test task; within a
seed every arm's processes start from the same random state (common random numbers).

**Measure.** At checkpoints 32, 64, ..., 1024 evaluations the arm's answer is measured on T (the mean of 2 runs for
max-cut, uncharged). Quality q = (T - low) / (high - low) per task: low = the median measured score of 32 reference
random programs; high = the best measured score any arm's answer reached on that task at any checkpoint, or a stated
reference if higher (REX = 1 for max-cut; eig, dec, degree and decfall for acquisition; the target = 1 for formulas).
Primary: AUDC, the trapezoid mean of q over the six checkpoints (each doubling of compute weighs the same).

**Development phase** (before any test task exists in the output): H* = the single process with the best mean AUDC
over the development tasks x seeds 100-102 (normalised as above on the development instances); G3's parameters by
`tune_params`. Both are written to `dev.json` before the test phase starts and never changed.

**Tests.**
  * H1 (descriptive verdict, preregistered rule): a process is BEATEN on a task when another single process's AUDC is
    higher on all six seeds. NO_UNIVERSAL_HARNESS if every one of the six is beaten on at least one test task;
    otherwise UNIVERSAL_HARNESS (naming the unbeaten).
  * Primary family (Holm, alpha 0.05): T1 G2 vs G0, T2 G2 vs H*, T3 G3 vs G2; each a two-sided Wilcoxon signed-rank
    test over the ten test tasks of the per-task mean AUDC difference (zero differences dropped); label BETTER (p_Holm
    < 0.05 and the mean difference > 0), WORSE (p_Holm < 0.05 and < 0) or NOT_DISTINGUISHABLE. If H* is G0's process,
    T2 is the same comparison as T1 and is reported as such (Holm unchanged: conservative).
  * Effect sizes: mean AUDC difference, task wins (of 10), and per domain.
  * Secondary (uncorrected, labelled so): G1 vs G0; bandit vs G2; G2 vs every single process; final quality (q at B)
    for T1-T3; T1 and T3 on the held-out tasks only (acquisition large, formula mixed, both max-cut tasks); CPU per arm.
**Verdict.** G2_BETTER if T1 and T2 are BETTER; G2_BETTER_THAN_G0 if only T1 is; G2_WORSE if T1 or T2 is WORSE and
neither is BETTER; NOT_SHOWN otherwise. Separately G3_ADDS, G3_HURTS or G3_NOT_SHOWN from T3.
**Validity.** Every (task, seed, arm) row present; each run's charged evaluations within [B - 2, B]; every max-cut cut
checked by both checkers (a disagreement stops the study); the protected judge (`autonomy/feedback.py`) unchanged (its
digest is checked; nothing here uses it). Otherwise INVALID.

**Development looks (disclosed; seeds 9999xxxx, never reused).** (1) One instance per domain (acquisition base,
max-cut G(800, 0.06) with weights 1, formula large), every arm, seed 1, B 512 and 1024: the acquisition task saturated
within 16-64 evaluations (many programs reach the best value; the portfolio arms' answers were chosen by a 16-world V
split that preferred programs worse on T, hence the larger V and T here and the harder families); max-cut with weights
1 was flat within noise (every arm within 0.998-1.001 of REX), hence the +-1 families with more spread; on formula
large hill climbing had the best AUDC (0.81 at 512, 0.78 at 1024) and evolution the best final value at 1024 (0.91);
racing was worst; the portfolio arms were in between. (2) Acquisition shift and large (V 32, T 64) and max-cut torus
and erdos_pm1, B 1024, seed 1, six arms: on shift best-of-N had the best AUDC (0.94) and the two portfolio arms the
best final value (-5.83 experiments, against eig -6.69 and decfall -6.20); on large hill climbing had the best AUDC
(0.90); on torus annealing (0.87) and best-of-N (0.83), with every arm within 0.996-1.007 of REX; on erdos_pm1
evolution (0.86) and annealing (0.85), halving lowest (0.68), and the measured values move by about 0.002 between
checkpoints (noise of the same size as the differences). `docs/checkpoints/B20_R148_SETUP.md` has every number.

**Expectation, stated before running.** From the looks: H1 NO_UNIVERSAL_HARNESS is likely (racing and best-of-N are
beaten on formulas; hill climbing on acquisition). T1 and T2: NOT_DISTINGUISHABLE is the builder's expectation, G2
WORSE than H* possible: a portfolio spends early compute on every process, so its early checkpoints follow the
weakest starters, and at this budget the best single process already reaches most of the attainable quality on the
saturating tasks. T3: NOT_DISTINGUISHABLE. A positive T1 or T2 would support the report's central claim in Genesis's
setting; a negative one is recorded as such.

**Cost.** About 5 hours alone on CPU 0 (in slices of at most 6,600 s; the run resumes from its rows): instance
preparation about 20 min (840 causal worlds; the large family about 2.5 s each), development about 55 min (108 runs
for H* and 252 for the tuning, the acquisition ones 12-30 s each), test about 3.7 h (600 runs: acquisition 12-40 s,
max-cut about 65 s, formulas under 1 s each).

**What it decides.** Nothing about packages, rules or comparators; which allocator Genesis's research loop uses next
is a later, separately preregistered decision. **Status.** DEV; licenses nothing.
"""
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

STUDY = 'b20r148'
OUT = 'evidence/harness_portfolio_b20r148'
SEED = 21480000
B, J, ROUNDS, EXPLORE = 1024, 5, 32, 10
RUN_SEEDS = tuple(range(6))
DEV_SEEDS = (100, 101, 102)
TUNE_SEEDS = (200, 201)
CANDIDATES = 4
REFERENCE_N = 32
MCX_SECONDS = 0.02
SLICE_S = 6600
TUNING_RESERVE_S = 3000
PROTECTED_FEEDBACK_SHA256 = '2ff4a5ab1e5b445b9144afbcc43596b8b1701ae541e8916c73e45009c0e3bdd6'   # the protected judge as committed
ALPHA = 0.05

# (domain, family, held_out); the order fixes the task index used in seeds
TASKS = (('acquire', 'base', False), ('acquire', 'shift', False), ('acquire', 'sparse', False),
         ('acquire', 'large', True),
         ('formula', 'small', False), ('formula', 'medium', False), ('formula', 'large', False),
         ('formula', 'mixed', True),
         ('mcx2', 'torus', True), ('mcx2', 'erdos_pm1', True))
SIZES = {'acquire': {'A': 24, 'V': 32, 'T': 64}, 'formula': {'A': 200, 'V': 200, 'T': 400},
         'mcx2': {'A': 3, 'V': 4, 'T': 4}}
ACQ_SETTINGS = {'base': (10, 3, 0.2), 'shift': (14, 4, 0.15), 'sparse': (12, 2, 0.1), 'large': (16, 5, 0.15)}
MCX_SETTINGS = {'torus': ('torus2d_pm1', {'rows': 28, 'cols': 28}), 'erdos_pm1': ('erdos_pm1', {'n': 800, 'p': 0.06})}
PHASES = {'dev': 1, 'test': 2}


def protected_digest():
    return hashlib.sha256((ROOT / 'src/genesis/autonomy/feedback.py').read_bytes()).hexdigest()


def instance_seed(phase, task_index, split):
    return SEED + 100000 * PHASES[phase] + 1000 * task_index + 100 * 'AVT'.index(split)


def dev_tasks_spec():
    return [(i, d, f) for i, (d, f, held) in enumerate(TASKS) if not held and d != 'mcx2']


def test_tasks_spec():
    return [(i, d, f) for i, (d, f, _) in enumerate(TASKS)]


# ----------------------------------------------------------------------------------------------- instances

def load_jsonl(path):
    return [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()] if Path(path).exists() else []


def worlds(out, phase, i, family, split, log):
    """Prepared causal worlds, saved as they are made (resumable)."""
    from genesis.autonomy import portfolio_tasks as PT
    path = out / 'instances' / f'{phase}_{i:02d}_{family}_{split}.jsonl'
    path.parent.mkdir(parents=True, exist_ok=True)
    have = load_jsonl(path)
    n = SIZES['acquire'][split]
    base = instance_seed(phase, i, split)
    if len(have) < n:
        PT.ACQ_FAMILIES[family] = ACQ_SETTINGS[family]
        with path.open('a') as fh:
            for k in range(len(have), n):
                (row,) = PT.acquire_worlds(family, base + k, 1)
                fh.write(json.dumps(row, sort_keys=True) + '\n')
        have = load_jsonl(path)
        log(f'{phase} {family} {split}: {len(have)} worlds')
    if [r['seed'] for r in have] != [base + k for k in range(n)]:
        raise RuntimeError(f'{path}: the worlds are not the preregistered ones')
    return have


def graphs(out, phase, i, family, excluded):
    from genesis.autonomy import portfolio_tasks as PT
    from genesis.common import canonical
    from genesis.models_maxcut import MaxCutTask
    path = out / 'instances' / f'{phase}_{i:02d}_{family}_graphs.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        data = json.loads(path.read_text())
        return {s: [MaxCutTask.model_validate_json(canonical(t)) for t in v] for s, v in data.items()}
    PT.MCX_FAMILIES[family] = MCX_SETTINGS[family]
    from genesis.domains import adapter
    fam, params = MCX_SETTINGS[family]
    n = sum(SIZES['mcx2'].values())
    gs, _, _ = adapter('maxcut_v1').generate(instance_seed(phase, i, 'A'), n, 'DEV', fam, params, excluded=excluded)
    a, v = SIZES['mcx2']['A'], SIZES['mcx2']['V']
    splits = {'A': gs[:a], 'V': gs[a:a + v], 'T': gs[a + v:]}
    path.write_text(json.dumps({s: [t.model_dump(mode='json') for t in v] for s, v in splits.items()}, indent=1,
                               sort_keys=True) + '\n')
    return splits


def build_task(out, phase, i, domain, family, log, excluded=None):
    from genesis.autonomy import portfolio_tasks as PT
    name = f'{domain}:{family}'
    if domain == 'acquire':
        PT.ACQ_FAMILIES[family] = ACQ_SETTINGS[family]
        return PT.acquire_task(family, {s: worlds(out, phase, i, family, s, log) for s in 'AVT'}, name=name)
    if domain == 'formula':
        return PT.formula_task(family, {s: PT.formula_items(instance_seed(phase, i, s), SIZES['formula'][s])
                                        for s in 'AVT'}, name=name)
    PT.MCX_FAMILIES[family] = MCX_SETTINGS[family]
    return PT.mcx_task(family, graphs(out, phase, i, family, excluded or set()), seconds=MCX_SECONDS, name=name)


def references(task):
    """Stated reference scores (measured): REX for max-cut, the established acquisitions, the planted target."""
    from genesis.autonomy import portfolio as P
    return {k: P.measure(task, v) for k, v in task.info.get('references', {}).items()}


# ----------------------------------------------------------------------------------------------- runs

def run_row(task, arm, seed, params):
    from genesis.autonomy import portfolio as P
    c0 = P.cpu_now()
    curve, r = P.curve(task, arm, B, f'{STUDY}:{seed}', params=params, J=J)
    a = r.answer()
    return {'task': task.name, 'arm': arm, 'seed': seed, 'curve': curve, 'used': r.used, 'alloc': r.alloc,
            'cpu_s': round(P.cpu_now() - c0, 3), 'cpu_evaluate_s': round(r.cpu['evaluate'], 3),
            'cpu_logic_s': round(r.cpu['logic'], 3), 'answer': a, 'answer_v': r.v[P.key(a)][0] if a else None,
            'live': getattr(r, 'live', None)}


def lows_for(tasks, path):
    from genesis.autonomy import portfolio as P
    have = json.loads(path.read_text()) if path.exists() else {}
    for t in tasks:
        if t.name not in have:
            have[t.name] = {'low': P.reference_low(t, n=REFERENCE_N, seed=STUDY), 'references': references(t)}
            path.write_text(json.dumps(have, indent=1, sort_keys=True) + '\n')
    return have


def audcs(rows, norms):
    """{(task, arm, seed): AUDC} with high = the best any row (or a reference) reached on the task."""
    from genesis.autonomy import portfolio as P
    high = {}
    for r in rows:
        vals = [v for v in r['curve'] if v is not None]
        high[r['task']] = max([high.get(r['task'], -1e300)] + vals)
    for t, n in norms.items():
        if t in high:
            high[t] = max([high[t]] + list(n['references'].values()))
    return {(r['task'], r['arm'], r['seed']): P.audc_of(r['curve'], norms[r['task']]['low'], high[r['task']])
            for r in rows}, high


def finals(rows, norms, high):
    from genesis.autonomy import portfolio as P
    return {(r['task'], r['arm'], r['seed']): P.normalise(r['curve'][-1] if r['curve'][-1] is not None
                                                          else norms[r['task']]['low'],
                                                          norms[r['task']]['low'], high[r['task']]) for r in rows}


def development(out, log, t0):
    """H* and G3's parameters, from development tasks only; written to dev.json once."""
    from genesis.autonomy import portfolio as P
    path = out / 'dev.json'
    if path.exists():
        return json.loads(path.read_text())
    tasks = [build_task(out, 'dev', i, d, f, log) for i, d, f in dev_tasks_spec()]
    norms = lows_for(tasks, out / 'dev_norms.json')
    rpath = out / 'dev_rows.jsonl'
    rows = load_jsonl(rpath)
    done = {(r['task'], r['arm'], r['seed']) for r in rows}
    for t in tasks:
        for h in P.HARNESSES:
            for s in DEV_SEEDS:
                if (t.name, f'single:{h}', s) in done:
                    continue
                if time.monotonic() - t0 > SLICE_S:
                    return None
                row = run_row(t, f'single:{h}', s, None)
                rows.append(row)
                with rpath.open('a') as fh:
                    fh.write(json.dumps(row, sort_keys=True) + '\n')
    A, _ = audcs(rows, norms)
    mean = {h: statistics.mean(A[(t.name, f'single:{h}', s)] for t in tasks for s in DEV_SEEDS) for h in P.HARNESSES}
    hstar = max(P.HARNESSES, key=lambda h: (mean[h], -P.HARNESSES.index(h)))
    log(f'development: mean AUDC {json.dumps({h: round(v, 4) for h, v in mean.items()})}; H* = {hstar}')
    if time.monotonic() - t0 > SLICE_S - TUNING_RESERVE_S:      # the tuning is one call: start it only with room
        return None
    lows = {t.name: norms[t.name]['low'] for t in tasks}
    tuned, report = P.tune_params(tasks, B, [f'{STUDY}:tune:{s}' for s in TUNE_SEEDS], lows,
                                  candidates_per_harness=CANDIDATES, seed=STUDY, log=log)
    dev = {'hstar': hstar, 'mean_audc': mean, 'tuned': tuned, 'tuning': report,
           'dev_tasks': [t.name for t in tasks]}
    path.write_text(json.dumps(dev, indent=1, sort_keys=True) + '\n')
    return dev


# ----------------------------------------------------------------------------------------------- analysis

def wilcoxon(diffs):
    from scipy.stats import wilcoxon as W
    d = [x for x in diffs if x != 0]
    if not d:
        return 1.0
    return float(W(d, zero_method='wilcox', alternative='two-sided').pvalue)


def holm(ps):
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    adj, run = [0.0] * len(ps), 0.0
    for rank, i in enumerate(order):
        run = max(run, min(1.0, (len(ps) - rank) * ps[i]))
        adj[i] = run
    return adj


def label(p, mean_diff):
    if p < ALPHA and mean_diff > 0:
        return 'BETTER'
    if p < ALPHA and mean_diff < 0:
        return 'WORSE'
    return 'NOT_DISTINGUISHABLE'


def task_means(A, tasks, arm, seeds=RUN_SEEDS):
    return [statistics.mean(A[(t, arm, s)] for s in seeds) for t in tasks]


def compare(A, tasks, a, b):
    da, db = task_means(A, tasks, a), task_means(A, tasks, b)
    diffs = [x - y for x, y in zip(da, db)]
    return {'mean_difference': round(statistics.mean(diffs), 6), 'wins': sum(d > 0 for d in diffs),
            'losses': sum(d < 0 for d in diffs), 'p': wilcoxon(diffs), 'per_task': dict(zip(tasks, [round(d, 6)
                                                                                                   for d in diffs]))}


def analyse(rows, norms, dev):
    from genesis.autonomy import portfolio as P
    A, high = audcs(rows, norms)
    F = finals(rows, norms, high)
    tasks = [f'{d}:{f}' for d, f, _ in TASKS]
    held = [f'{d}:{f}' for d, f, h in TASKS if h]
    # H1
    beaten = {}
    for h in P.HARNESSES:
        beaten[h] = [t for t in tasks if any(all(A[(t, f'single:{o}', s)] > A[(t, f'single:{h}', s)]
                                                 for s in RUN_SEEDS) for o in P.HARNESSES if o != h)]
    unbeaten = [h for h in P.HARNESSES if not beaten[h]]
    h1 = 'NO_UNIVERSAL_HARNESS' if not unbeaten else 'UNIVERSAL_HARNESS'
    winners = {t: max(P.HARNESSES, key=lambda h: (statistics.mean(A[(t, f'single:{h}', s)] for s in RUN_SEEDS),
                                                   -P.HARNESSES.index(h))) for t in tasks}
    hstar = f"single:{dev['hstar']}"
    prim = {'T1': compare(A, tasks, P.G2, P.G0), 'T2': compare(A, tasks, P.G2, hstar),
            'T3': compare(A, tasks, P.G3, P.G2)}
    adj = holm([prim[k]['p'] for k in ('T1', 'T2', 'T3')])
    for k, p in zip(('T1', 'T2', 'T3'), adj):
        prim[k]['p_holm'] = p
        prim[k]['label'] = label(p, prim[k]['mean_difference'])
    l1, l2 = prim['T1']['label'], prim['T2']['label']
    if l1 == 'BETTER' and l2 == 'BETTER':
        verdict = 'G2_BETTER'
    elif l1 == 'BETTER':
        verdict = 'G2_BETTER_THAN_G0'
    elif 'WORSE' in (l1, l2):
        verdict = 'G2_WORSE'
    else:
        verdict = 'NOT_SHOWN'
    g3 = {'BETTER': 'G3_ADDS', 'WORSE': 'G3_HURTS'}.get(prim['T3']['label'], 'G3_NOT_SHOWN')
    sec = {'G1_vs_G0': compare(A, tasks, P.G1, P.G0), 'bandit_vs_G2': compare(A, tasks, 'bandit', P.G2)}
    for h in P.HARNESSES:
        sec[f'G2_vs_{h}'] = compare(A, tasks, P.G2, f'single:{h}')
    sec['final_T1'] = compare(F, tasks, P.G2, P.G0)
    sec['final_T2'] = compare(F, tasks, P.G2, hstar)
    sec['final_T3'] = compare(F, tasks, P.G3, P.G2)
    sec['heldout_T1'] = compare(A, held, P.G2, P.G0)
    sec['heldout_T3'] = compare(A, held, P.G3, P.G2)
    means = {arm: {t: round(statistics.mean(A[(t, arm, s)] for s in RUN_SEEDS), 6) for t in tasks}
             for arm in P.ARMS}
    cpu = {arm: round(statistics.mean(r['cpu_s'] for r in rows if r['arm'] == arm), 3) for arm in P.ARMS}
    return {'H1': {'label': h1, 'unbeaten': unbeaten, 'beaten_on': beaten, 'winner_by_task': winners},
            'primary': prim, 'verdict': verdict, 'g3': g3, 'hstar': hstar, 'secondary': sec,
            'mean_audc': means, 'mean_cpu_s': cpu, 'high': high}


def validity(rows):
    from genesis.autonomy import portfolio as P
    want = {(f'{d}:{f}', arm, s) for d, f, _ in TASKS for arm in P.ARMS for s in RUN_SEEDS}
    have = {(r['task'], r['arm'], r['seed']) for r in rows}
    if have != want or len(rows) != len(want):
        return 'INVALID_MISSING_ROWS'
    if any(not B - 2 <= r['used'] <= B for r in rows):
        return 'INVALID_BUDGET'
    if protected_digest() != PROTECTED_FEEDBACK_SHA256:
        return 'INVALID_PROTECTED_JUDGE_CHANGED'
    return None


# ----------------------------------------------------------------------------------------------- main

def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) != 1 or Path(argv[0]).resolve() != (ROOT / OUT).resolve():
        raise SystemExit(f'usage: {OUT} is the registered output directory')
    from genesis.autonomy import portfolio as P
    from genesis.candidate_kinds import mcx2 as K
    from genesis.common import code_identity
    out = ROOT / OUT
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    with (out / 'run.log').open('a') as logf:
        def log(m):
            line = f'[{time.monotonic() - t0:8.1f}s] {m}'
            print(line, flush=True)
            logf.write(line + '\n')
            logf.flush()
        import os
        cores = os.sched_getaffinity(0)
        if len(cores) != 1:
            raise SystemExit(f'run alone on one core (taskset -c 0), not {sorted(cores)}')
        if K.binary_digest() != K.BINARY_SHA256:
            raise SystemExit('the pinned mcx2 binary is missing')
        if protected_digest() != PROTECTED_FEEDBACK_SHA256:
            raise SystemExit('the protected judge has changed since preregistration')
        log(f'{STUDY}; pinned to CPU {min(cores)}; code identity {code_identity(ROOT)["sha256"][:16]}')
        dev = development(out, log, t0)
        if dev is None:
            log('time slice used: paused in the development phase')
            return 3
        from genesis import gset as GS
        from genesis.domains import adapter
        ex = {adapter('maxcut_v1').exposure_identity(t)['canonical'] for t in GS.tasks()}
        tasks = [build_task(out, 'test', i, d, f, log, excluded=ex) for i, d, f in test_tasks_spec()]
        norms = lows_for(tasks, out / 'norms.json')
        rpath = out / 'rows.jsonl'
        rows = load_jsonl(rpath)
        done = {(r['task'], r['arm'], r['seed']) for r in rows}
        for t in tasks:
            for s in RUN_SEEDS:
                for arm in P.ARMS:
                    if (t.name, arm, s) in done:
                        continue
                    if time.monotonic() - t0 > SLICE_S:
                        log(f'time slice used: paused after {len(rows)} rows')
                        return 3
                    row = run_row(t, arm, s, dev['tuned'] if arm == P.G3 else None)
                    rows.append(row)
                    with rpath.open('a') as fh:
                        fh.write(json.dumps(row, sort_keys=True) + '\n')
                log(f'{t.name} seed {s}: ' + ' '.join(
                    f"{r['arm']} {r['curve'][-1]:.4g}" for r in rows if r['task'] == t.name and r['seed'] == s))
        invalid = validity(rows)
        res = analyse(rows, norms, dev)
        summary = {'schema': 'genesis-b20r148-v1', 'study': STUDY, 'valid': invalid is None, 'invalid': invalid,
                   'verdict': invalid or res['verdict'], 'g3': invalid or res['g3'], 'H1': res['H1'],
                   'primary': res['primary'], 'secondary': res['secondary'], 'hstar': res['hstar'],
                   'mean_audc': res['mean_audc'], 'mean_cpu_s': res['mean_cpu_s'], 'high': res['high'],
                   'norms': norms, 'dev': {k: dev[k] for k in ('hstar', 'mean_audc', 'tuned', 'dev_tasks')},
                   'design': {'B': B, 'J': J, 'rounds': ROUNDS, 'explore': EXPLORE, 'seeds': list(RUN_SEEDS),
                              'tasks': TASKS, 'sizes': SIZES, 'mcx_seconds': MCX_SECONDS},
                   'code_identity': code_identity(ROOT)['sha256'],
                   'status': 'DEV; licenses nothing'}
        (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True, default=str) + '\n')
        log(f"verdict {summary['verdict']}; {summary['g3']}; H1 {res['H1']['label']}; " + '; '.join(
            f"{k} {v['label']} ({v['mean_difference']:+.4f}, {v['wins']}-{v['losses']}, p_holm {v['p_holm']:.3g})"
            for k, v in res['primary'].items()))
    return 0


if __name__ == '__main__':
    sys.exit(main())
