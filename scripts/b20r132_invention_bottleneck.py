#!/usr/bin/env python3
"""B20_R132: the bottleneck scientist turned on Genesis's own invention (DEV, preregistered)

    taskset -c 0 python3 scripts/b20r132_invention_bottleneck.py OUT_DIR     run ALONE (resumable; slices exit 3)

**Why.** B20_R127's inventor wrote max-cut engines under the feedback contract version 2 and released nothing in all
nine searches. Nothing could have been released: the best training (A) gains over REX were +0.04% to +0.23%, while
the judge's release threshold tau was 0.75% to 2.45%, 4 to 52 times larger (its record, Ω0). Daniel's directive (24
Oct 2026, 15:35, item 2): distinguish **independently** four explanations, with planted positive controls,
zero-signal controls, fresh confirmation sets and matched total compute, without weakening the protected judge:
  * (H) **genuine lack of headroom**: at 1 s, REX may leave nothing to gain on these graphs;
  * (X) **language expressiveness**: no engine the language can write may do better at 1 s;
  * (S) **search effectiveness**: better engines may exist that the search does not propose;
  * (E) **evaluation sensitivity**: the judge may be unable to see gains of the size the search finds.
Each has its own instrument below. The protected judge (`autonomy/feedback.py`, contract version 2) is used unchanged
for the V2 arms, and its source is checked against its digest at preregistration. The candidate version 3
(`autonomy/contract_v3.py`, research plane, adopted nowhere: it reuses the protected `Judge` class and calibrates it
on one-step mutations of the incumbent instead of random engines) is what the L arms test.

**Graphs** (generated as B20_R127's were: B20_R105's settings without the 3,000-vertex tori; Gset identities
excluded; seeds from SEED). Per class (random, planar, toroidal): two fresh truth sets T1 and T2 of 12 graphs each,
never seen by any search; per replicate (3): split A (the inventor's data) 4 graphs, B and C (the judge's
confirmation splits) 12 graphs each, of which the first 4 are the 4-graph splits.

**Runs.** The pinned `mcx2` binary at 1 s CPU, run directly; every value is the cut of the returned partition,
recomputed in Python (`mcx2.solve`). A run's seed is a hash of (study, engine, graph, occurrence), the occurrence
counting that engine's earlier evaluations on that split in the same search, so every arm making the same evaluation
gets the same run: the arms share their runs and their noise. Reference on each graph: REX (`mcx2` DEFAULT) at 1 s
with one fixed seed; a split evaluation is the mean over its graphs of cut / reference. The REX baseline on T1 and T2
is the mean of two runs; an engine's T-gain is 100 x the mean over the graphs of (cut - baseline) / baseline (%),
from one run per graph; comparisons are one-sided Wilcoxon signed-rank tests on per-graph differences (zeros
dropped).

**The searches** (one per class and replicate, shared by the arms): `selfimprove`'s ORIGINAL process (the contract's
steady-state search), the population started with REX and then random engines, the seed from (class, replicate).
**Arms**, matched in charged evaluations (a unit = one 4-graph split evaluation = 4 graph-seconds; MAX_EVALS = 240):
  * V2@160: the protected contract version 2 (`selfimprove.search`), 4-graph splits, 160 units (B20_R127's budget);
  * V2: the same, 240 units;
  * L: version 3 (`contract_v3.steady_state_search`, `calibration='local'`), 4-graph splits, 240 units;
  * L12: version 3 with 12-graph confirmation splits, each B or C evaluation charged 3 units (fewer proposals).
The version 3 copy of the search is the protected one exactly under version 2's calibration (`test_contract_v3`),
and it keeps version 2's draws, so the four arms make the same search until one stops.

**Instruments of the four explanations (per class).**
  * (H) **Headroom:** REX at 10 s against the baseline on T1 and T2 (24 graphs): HEADROOM if better at p < 0.05 by
    at least MATERIAL (0.05%, the smallest planted gain), else NO_HEADROOM.
  * (X) **Expressiveness:** a pool of engines written in the language: fixed in advance, the human designs written in
    it (B20_R127's TEMPLATES), B20_R127's nine engines and 16 random engines; and every engine the trajectories put
    on T1 (below). Each runs once per graph on T1; the best by T1-gain is confirmed on the fresh T2: EXPRESSIBLE if
    better than the baseline there at p < 0.05 by at least MATERIAL, else NOT_FOUND (a lower bound: the pool is
    finite).
  * (S) **Search effectiveness**, two ways:
      - real: every distinct submission of every arm (what the searches proposed to their judges) runs on T1; the
        class's best submission by T1-gain is confirmed on T2, and its T2-gain compared with the expressiveness
        winner's;
      - planted and reachable: a positive control in which every engine's run is drawn from a pool of real REX runs
        (12 seeds on each graph of the first replicate) and multiplied by (1 + delta) for engines whose program
        contains a pair-descent statement D. REX has none and the random initial engines are drawn without one, so
        the gain is absent at the start and reachable by one insertion or replacement. 10 searches per arm and delta
        (0.25%, 1%) per class: FOUND if a submission carried D; RELEASED if the final engine does.
  * (E) **Evaluation sensitivity**, two ways:
      - planted power curves: for each judge's real tau (from the trajectories) and delta in DELTAS, the probability
        that a submission truly better by delta beats an equal-noise incumbent by more than tau (4,000 simulated pairs
        of split evaluations drawn from the REX pools: REX's run noise only, so an upper bound on power);
      - zero signal: 20 searches per arm per class on the pools with no gain at all; any release is false.
  * **Diagnosis rule (fixed):** HEADROOM if NO_HEADROOM; else EXPRESSIVENESS if NOT_FOUND; else SEARCH if the best
    submission's T2-gain is below half the expressiveness winner's; else EVALUATION if the version 2 judge's delta50
    (the smallest delta in DELTAS with power at least 0.5) exceeds the best submission's T2-gain, or does not exist;
    else NONE_IDENTIFIED.

**Truth for every decision.** Each arm's final engine and the starting incumbent run on T1 and T2; each release is
audited on T1 against the engine it replaced (HARMFUL if worse at p < 0.05, CONFIRMED if better, else UNRESOLVED).
The 16 one-step mutations of each starting incumbent run on T1 (the signal near the incumbent; version 3's
calibration set).

**Primary family (Holm, alpha 0.05):**
  * P1 (the judge): over the 9 trajectories, L's final gain on T1+T2 against V2's, paired one-sided Wilcoxon (L > V2);
  * P2 (evaluator against proposals): L12's against L's, paired two-sided Wilcoxon: EVALUATOR_BETTER,
    PROPOSALS_BETTER or NO_DIFFERENCE.
**Safety:** S1, version 3's zero-signal release rate (arm L, 60 searches): Clopper-Pearson upper 95% bound at most
0.10. S2, the release audit, reported for every arm. **Verdict:** INVALID if validity fails; else V3_UNSAFE if S1
fails; else JUDGE_WAS_THE_BOTTLENECK if P1 holds after Holm; else NOT_SHOWN. The diagnosis is reported per class
beside it. **Validity:** median CPU of the runs at least 0.9 of each budget; every arm's release history,
reconstructed from its own calls, reproduces its judge's count and final engine; the protected judge's source is the
one at preregistration.

**Prior art (no novelty is claimed for version 3).** Comparing a challenger with the incumbent on the same instances
and only beyond the noise is the intensification of algorithm configurators (racing: Maron and Moore 1994; F-race,
Birattari et al. 2002; SMAC, Hutter, Hoos and Leyton-Brown 2011); estimating noise from re-evaluated near solutions is
the uncertainty handling of Hansen et al. (2009, CMA-ES); the fixed-threshold release is the Ladder (Blum and Hardt
2015). Racing (adaptive numbers of confirmation graphs) is a candidate next version, not tested here.

**Development looks (disclosed).** B20_R127's trace (its record). One look on CPU 1 while B20_R130 ran (24 Oct, about
18:36-18:50; seeds 9,400,000+, never used here; per class 8 graphs at 1 s, two 4-graph splits): REX's run-to-run
noise (relative standard deviation) 0.03% / 0.26% / 0.04% (random / planar / toroidal); tau from 8 random engines
5.7% / 2.9% / 4.5% against 0.33% / 0.74% / 0.42% from 8 one-step mutations of REX; REX at 10 s against 1 s on 4
graphs +0.02% / +0.61% / +0.06%; one planar mutation of REX scored +0.26% on B and +0.23% on C. After the look the
materiality threshold MATERIAL (0.05%, the smallest planted gain) was added to the headroom and expressiveness
labels: a gain smaller than that is treated as none.

**Expectation, stated before running.** Version 2's tau about 1-3% (B20_R127: 0.75-2.45%), version 3's 0.3-0.8%.
Headroom: random NO_HEADROOM (about 0.02%), toroidal borderline, planar HEADROOM (about 0.6%). Planar: expressible
gains of about 0.1-0.3%, found by the searches and released by version 3 but not by version 2 (diagnosis
EVALUATION); random and toroidal: HEADROOM. Version 2's delta50 above 1% (none in the grid), version 3's 0.2-0.5%.
The planted 1% gain FOUND in most searches and RELEASED by version 3 only. S1 holds. P1 NOT_SHOWN: only the planar
trajectories (3 of 9) differ, and P1 needs at least 6. Verdict NOT_SHOWN, with the per-class diagnosis as the
result.

**Cost.** Per class: trajectories about 77 min (per replicate: A about 750 s, version 2's calibration 260 s, version
3's 400 s, submissions 120 s); T1 and T2 about 25 min; references, headroom and pools about 12 min: about 1.9 h; 5.7 h
in all, in slices of 6,600 s. **Status.** DEV; licenses nothing. Version 3 is adopted nowhere by this study.
"""
import hashlib
import json
from pathlib import Path
import random
import resource
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis.common import code_identity, digest  # noqa: E402

STUDY = 'b20r132'
SEED = 20521321
CLASSES = ('random', 'planar', 'toroidal')
REPLICATES = 3
SPLITS = {'A': 4, 'B': 12, 'C': 12}
T_GRAPHS = 12
BUDGET, LONG = 1.0, 10.0
MAX_EVALS = 240
ARMS = {'V2@160': ('v2', 4, 160), 'V2': ('v2', 4, MAX_EVALS), 'L': ('v3', 4, MAX_EVALS), 'L12': ('v3', 12, MAX_EVALS)}
ORDER = ('L', 'V2', 'L12', 'V2@160')
NULL_SEARCHES, PLANTED_SEARCHES, POOL = 20, 10, 12
PLANTED = (0.0025, 0.01)
DELTAS = (0.0, 0.0005, 0.001, 0.002, 0.003, 0.005, 0.01)
POWER_PAIRS = 4000
POOL_RANDOM = 16
ALPHA, S1_BOUND = 0.05, 0.10
MATERIAL = 0.0005            # 0.05%: a gain below this is treated as none (headroom, expressiveness)
PROTECTED_FEEDBACK_SHA256 = '2ff4a5ab1e5b445b9144afbcc43596b8b1701ae541e8916c73e45009c0e3bdd6'
SLICE_S, PAUSED = 6600, 3


class Paused(Exception):
    pass


# ----------------------------------------------------------------------------------------------- graphs and runs

def graphs(excluded):
    """{class: {'T1': [task], 'T2': [task], rep: {'A', 'B', 'C': [task]}}} of fresh generated graphs."""
    import b20r127_self_invented_engine as R127
    from genesis.domains import adapter
    A = adapter('maxcut_v1')
    seen, out, k = set(excluded), {}, 0
    st = R127.settings()

    def draw(cls, n):
        nonlocal seen, k
        ts = []
        for i in range(n):
            fam, params = st[cls][(i + k) % len(st[cls])]
            got, seen, _ = A.generate(SEED + 1000 * k + i, 1, 'DEV', fam, params, excluded=seen)
            ts.append(got[0])
        k += 1
        return ts
    for cls in CLASSES:
        out[cls] = {'T1': draw(cls, T_GRAPHS), 'T2': draw(cls, T_GRAPHS)}
        for rep in range(REPLICATES):
            out[cls][rep] = {s: draw(cls, n) for s, n in SPLITS.items()}
    return out


def run_seed(engine_key, task_id, occ, budget):
    return int(digest({'study': STUDY, 'engine': engine_key, 'task': task_id, 'occ': occ, 'budget': budget})[:12], 16)


def real_runner(cfg, task, seed, budget):
    """(value, CPU seconds of the engine process) of one direct run of the pinned binary."""
    from genesis.candidate_kinds import mcx2 as K2
    from genesis.models_maxcut import MaxCutCandidateView
    r0 = resource.getrusage(resource.RUSAGE_CHILDREN)
    v = K2.solve(MaxCutCandidateView(n=task.n, edges=task.edges), {'cpu_seconds': budget, 'config': cfg}, budget,
                 seed)['value']
    r1 = resource.getrusage(resource.RUSAGE_CHILDREN)
    return v, (r1.ru_utime + r1.ru_stime) - (r0.ru_utime + r0.ru_stime)


class Lab:
    """Every run, cached by (engine, graph, occurrence, budget) and appended to runs.jsonl as it is made."""

    def __init__(self, path=None, runner=real_runner, deadline=None):
        self.path, self.runner, self.deadline = path, runner, deadline
        self.cache, self.programs = {}, {}
        if path is not None and Path(path).exists():
            for line in Path(path).read_text().splitlines():
                if line.strip():
                    r = json.loads(line)
                    self.cache[r['key']] = r

    @staticmethod
    def ekey(cfg):
        return digest(cfg)[:16]

    def run(self, cfg, task, occ, budget=BUDGET):
        ek = self.ekey(cfg)
        self.programs.setdefault(ek, cfg)
        k = f'{ek}|{task.task_id}|{occ}|{budget:g}'
        if k not in self.cache:
            if self.deadline is not None and time.monotonic() > self.deadline:
                raise Paused
            seed = run_seed(ek, task.task_id, occ, budget)
            v, cpu = self.runner(cfg, task, seed, budget)
            self.cache[k] = {'key': k, 'value': v, 'cpu': round(cpu, 4)}
            if self.path is not None:
                with open(self.path, 'a') as f:
                    f.write(json.dumps(self.cache[k], sort_keys=True) + '\n')
        return self.cache[k]['value']

    def ref(self, task):
        from genesis.candidate_kinds import mcx2 as K2
        return self.run(K2.DEFAULT, task, 'ref')


def evaluator(lab, splits, size, log=None):
    """evaluate(cfg, split): the mean over the split's first graphs (A: 4; B and C: `size`) of cut / reference; the
    occurrence of a run counts the engine's earlier evaluations on that split here. `log` receives every call."""
    occ = {}

    def ev(cfg, split):
        k = (Lab.ekey(cfg), split)
        n = occ.get(k, 0)
        occ[k] = n + 1
        ts = splits[split][:4 if split == 'A' else size]
        v = statistics.mean(lab.run(cfg, t, n) / lab.ref(t) for t in ts)
        if log is not None:
            log.append({'engine': k[0], 'split': split, 'occ': n, 'value': v})
        return v
    return ev


def has_trait(cfg):
    """The planted trait: the program contains a pair-descent statement (D)."""
    from genesis.candidate_kinds import mcx2 as K2
    return any(op == 'D' for op, _ in K2.statements(cfg['prog']))


def pool_evaluator(pool, splits, size, salt, delta=0.0, log=None, programs=None):
    """Every engine's run on a graph is a draw from that graph's pool of REX runs (cut / reference), keyed by (salt,
    engine, graph, occurrence), times (1 + delta) for engines with the planted trait (delta 0: zero signal)."""
    occ = {}

    def ev(cfg, split):
        k = (Lab.ekey(cfg), split)
        if programs is not None:
            programs.setdefault(k[0], cfg)
        n = occ.get(k, 0)
        occ[k] = n + 1
        ts = splits[split][:4 if split == 'A' else size]
        vals = []
        for t in ts:
            i = int(digest({'salt': salt, 'engine': k[0], 'task': t.task_id, 'occ': n})[:8], 16) % len(pool[t.task_id])
            vals.append(pool[t.task_id][i])
        v = statistics.mean(vals) * (1 + delta if delta and has_trait(cfg) else 1)
        if log is not None:
            log.append({'engine': k[0], 'split': split, 'occ': n, 'value': v})
        return v
    return ev


# --------------------------------------------------------------------------------------------- the searches

def search_ops(no_trait=False):
    """selfimprove's engine operators with REX first; with no_trait, random engines are drawn without the trait."""
    from genesis.autonomy import selfimprove as SI
    from genesis.candidate_kinds import mcx2 as K2
    ops = SI.engine_ops()
    if no_trait:
        base = ops['random']

        def random_without(rng):
            while True:
                e = base(rng)
                if not has_trait(e):
                    return e
        ops = dict(ops, random=random_without)
    return SI.seeded_ops(ops, [dict(K2.DEFAULT)])


def search(ev, arm, seed, no_trait=False):
    """One arm's search: (winner, report). V2 arms: the protected contract version 2 through selfimprove; L arms: the
    candidate version 3."""
    from genesis.autonomy import contract_v3 as V3
    from genesis.autonomy import selfimprove as SI
    judge, size, max_evals = ARMS[arm]
    cost = {'B': size // 4, 'C': size // 4} if size != 4 else None
    ops = search_ops(no_trait)
    if judge == 'v2':
        return SI.search(SI.ORIGINAL, ops, ev, max_evals, seed, contract=True, calibrate='BC', cost=cost)
    return V3.steady_state_search(ops, ev, max_evals, seed, calibration='local', cost=cost)


def history(calls, tau, n_calibration):
    """The judge's decisions reconstructed from the arm's own calls: the first 2 x n_calibration B/C calls calibrate;
    the next B call is the start; every later B call is a fresh submission, released if it beats the incumbent's B
    score by more than tau."""
    bc = [c for c in calls if c['split'] in ('B', 'C')]
    rest = bc[2 * n_calibration:]
    if not all(c['split'] == 'B' for c in rest):
        raise ValueError('C is used only to calibrate')
    start = rest[0]
    best, inc, subs = start['value'], start['engine'], []
    for c in rest[1:]:
        rel = bool(c['value'] > best + tau)
        subs.append({'engine': c['engine'], 'b': c['value'], 'released': rel, 'replaced': inc if rel else None})
        if rel:
            best, inc = c['value'], c['engine']
    return {'start': start['engine'], 'start_b': start['value'], 'submissions': subs, 'final': inc, 'best': best}


def n_calibration(calls):
    return sum(c['split'] == 'C' for c in calls)


def arm_summary(winner, report, calls):
    tau = float(report['judge']['tau'])
    h = history(calls, tau, n_calibration(calls))
    a_first = {}
    for c in calls:
        if c['split'] == 'A' and c['occ'] == 0:
            a_first[c['engine']] = c['value']
    final = Lab.ekey(winner)
    ok = h['final'] == final and sum(s['released'] for s in h['submissions']) == report['judge']['releases']
    return {'tau': tau, 'final': final, 'history': h, 'proposals': len(a_first),
            'best_a_gain': max(a_first.values()) - a_first[h['start']], 'evaluations': report['evaluations'],
            'releases': report['judge']['releases'], 'consistent': bool(ok)}


def run_arms(lab, splits, seed):
    """Every arm's search on one trajectory: {arm: arm_summary}."""
    out = {}
    for arm in ORDER:
        calls = []
        winner, rep = search(evaluator(lab, splits, ARMS[arm][1], calls), arm, seed)
        out[arm] = arm_summary(winner, rep, calls)
    return out


def pool_search(pool, splits, arm, seed, salt, delta=0.0, no_trait=False):
    """One search on the pool evaluator: {releases, tau, found, released, start_trait} (found: a submission carried the
    trait; released: the final engine carries it)."""
    calls, programs = [], {}
    winner, rep = search(pool_evaluator(pool, splits, ARMS[arm][1], salt, delta, calls, programs), arm, seed,
                         no_trait)
    h = history(calls, float(rep['judge']['tau']), n_calibration(calls))
    return {'releases': rep['judge']['releases'], 'tau': float(rep['judge']['tau']),
            'found': any(has_trait(programs[s['engine']]) for s in h['submissions']),
            'released': has_trait(winner), 'start_trait': has_trait(programs[h['start']])}


def power(pool_vals, size, tau, delta, pairs, seed):
    """P(a submission truly better by delta beats an equal-noise incumbent by more than tau): split evaluations are
    means over `size` graphs of draws from the graphs' REX pools."""
    rng = random.Random(seed)
    gs = pool_vals[:size]
    hit = 0
    for _ in range(pairs):
        inc = sum(rng.choice(g) for g in gs) / len(gs)
        sub = sum(rng.choice(g) for g in gs) / len(gs) * (1 + delta)
        hit += sub > inc + tau
    return hit / pairs


# ------------------------------------------------------------------------------------------------- statistics

def wilcoxon(diffs, alternative):
    from scipy.stats import wilcoxon as W
    d = [x for x in diffs if x != 0]
    if not d:
        return {'n': 0, 'p': 1.0, 'median': 0.0}
    return {'n': len(d), 'p': float(W(d, alternative=alternative).pvalue), 'median': statistics.median(diffs)}


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


def t_gain(values, base, engine, tasks):
    """100 x mean over the tasks of (cut - baseline) / baseline, and the per-graph relative differences."""
    rel = [(values[engine][t] - base[t]) / base[t] for t in tasks]
    return 100 * statistics.mean(rel), rel


def compare(values, base, a, b, tasks):
    """a's gain over b (percentage points) and one-sided Wilcoxon p-values on per-graph differences."""
    ga, ra = t_gain(values, base, a, tasks)
    gb, rb = t_gain(values, base, b, tasks)
    d = [x - y for x, y in zip(ra, rb)]
    return {'gain': ga - gb, 'p_better': wilcoxon(d, 'greater')['p'], 'p_worse': wilcoxon(d, 'less')['p']}


def vs_base(values, base, a, tasks):
    g, rel = t_gain(values, base, a, tasks)
    return {'gain': g, 'p_better': wilcoxon(rel, 'greater')['p']}


def best_by_t1(engines, t1, b1):
    tasks = sorted(b1)
    return min(engines, key=lambda e: (-t_gain(t1, b1, e, tasks)[0], e))


def analyse(traj, t1, t2, base, long, pool_names, null, planted, powers, rex):
    """traj: {'cls|rep': {'start', 'mutations', 'arms': {arm: arm_summary}}}; t1, t2: {cls: {engine: {task: value}}};
    base: {cls: {'T1', 'T2': {task: REX baseline}}}; long: {cls: {task: REX at 10 s}} over T1 and T2; pool_names:
    {cls: [engine]} (the fixed expressiveness pool); null: [{class, arm, releases}]; planted: [{class, arm, delta,
    found, released, start_trait}]; powers: {cls: {arm: {delta: power}}}; rex: REX's engine key."""
    out = {'trajectories': {}, 'diagnosis': {}}
    keys = sorted(traj)
    for tk in keys:
        tr, cls = traj[tk], tk.split('|')[0]
        v1, b1 = t1[cls], base[cls]['T1']
        tasks1 = sorted(b1)
        bb = {**b1, **base[cls]['T2']}
        both = {e: {**t1[cls][e], **t2[cls][e]} for e in t2[cls] if e in t1[cls]}
        tasks12 = sorted(bb)
        muts = [compare(v1, b1, m, tr['start'], tasks1) for m in tr['mutations']]
        row = {'signal': {'gains': [m['gain'] for m in muts], 'better': sum(m['p_better'] < ALPHA for m in muts),
                          'worse': sum(m['p_worse'] < ALPHA for m in muts), 'max_gain': max(m['gain'] for m in muts)},
               'start_gain': t_gain(both, bb, tr['start'], tasks12)[0], 'arms': {}}
        for arm, a in tr['arms'].items():
            audit = []
            for s in a['history']['submissions']:
                if s['released']:
                    c = compare(v1, b1, s['engine'], s['replaced'], tasks1)
                    audit.append({'engine': s['engine'], 'gain_over_replaced': c['gain'],
                                  'label': 'HARMFUL' if c['p_worse'] < ALPHA else (
                                      'CONFIRMED' if c['p_better'] < ALPHA else 'UNRESOLVED')})
            subs = [s['engine'] for s in a['history']['submissions']]
            row['arms'][arm] = {
                'tau_pct': 100 * a['tau'], 'final_gain': t_gain(both, bb, a['final'], tasks12)[0],
                'releases': len(audit), 'audit': audit, 'proposals': a['proposals'], 'evaluations': a['evaluations'],
                'best_a_gain_pct': 100 * a['best_a_gain'],
                'best_submission_t1': max([t_gain(v1, b1, e, tasks1)[0] for e in subs], default=None),
                'detectable': sum(g > 100 * a['tau'] for g in row['signal']['gains'])}
        out['trajectories'][tk] = row
    for cls in CLASSES:
        ks = [k for k in keys if k.startswith(cls + '|')]
        if not ks:
            continue
        b1, b2 = base[cls]['T1'], base[cls]['T2']
        tasks1, tasks2 = sorted(b1), sorted(b2)
        allb = {**b1, **b2}
        rel_long = [(long[cls][t] - allb[t]) / allb[t] for t in sorted(allb)]
        h = wilcoxon(rel_long, 'greater')
        headroom = {'gain_pct': 100 * statistics.mean(rel_long), 'improved': sum(x > 0 for x in rel_long),
                    'graphs': len(rel_long), 'p': h['p'],
                    'label': ('HEADROOM' if h['p'] < ALPHA and statistics.mean(rel_long) >= MATERIAL
                              else 'NO_HEADROOM')}
        cands = sorted(e for e in t1[cls] if e != rex)
        xw = best_by_t1(cands, t1[cls], b1)
        xc = vs_base(t2[cls], b2, xw, tasks2)
        expr = {'pool': len(cands), 'fixed_pool': len(pool_names[cls]),
                'positive_on_t1': sum(t_gain(t1[cls], b1, e, tasks1)[0] > 0 for e in cands),
                'winner': xw, 'winner_t1': t_gain(t1[cls], b1, xw, tasks1)[0], 'winner_t2': xc['gain'],
                'p_t2': xc['p_better'],
                'label': 'EXPRESSIBLE' if xc['p_better'] < ALPHA and xc['gain'] >= 100 * MATERIAL else 'NOT_FOUND'}
        subs = sorted({s['engine'] for k in ks for a in traj[k]['arms'].values() for s in a['history']['submissions']})
        if subs:
            sw = best_by_t1(subs, t1[cls], b1)
            sc = vs_base(t2[cls], b2, sw, tasks2)
            srch = {'submissions': len(subs), 'winner': sw, 'winner_t1': t_gain(t1[cls], b1, sw, tasks1)[0],
                    'winner_t2': sc['gain'], 'p_t2': sc['p_better']}
        else:
            srch = {'submissions': 0, 'winner': None, 'winner_t1': None, 'winner_t2': 0.0, 'p_t2': 1.0}
        pl = {}
        for arm in ARMS:
            for d in PLANTED:
                rows = [r for r in planted if r['class'] == cls and r['arm'] == arm and r['delta'] == d]
                pl[f'{arm}@{d:g}'] = {'searches': len(rows), 'found': sum(r['found'] for r in rows),
                                      'released': sum(r['released'] for r in rows),
                                      'start_trait': sum(r['start_trait'] for r in rows)}
        srch['planted'] = pl
        d50 = {arm: min([d for d in DELTAS if powers[cls][arm][f'{d:g}'] >= 0.5], default=None) for arm in ARMS}
        ev = {'power': powers[cls], 'delta50_pct': {a: (None if d is None else 100 * d) for a, d in d50.items()},
              'tau_pct': {arm: statistics.mean(out['trajectories'][k]['arms'][arm]['tau_pct'] for k in ks)
                          for arm in ARMS}}
        if headroom['label'] == 'NO_HEADROOM':
            label = 'HEADROOM'
        elif expr['label'] == 'NOT_FOUND':
            label = 'EXPRESSIVENESS'
        elif srch['winner_t2'] < 0.5 * expr['winner_t2']:
            label = 'SEARCH'
        elif d50['V2'] is None or 100 * d50['V2'] > srch['winner_t2']:
            label = 'EVALUATION'
        else:
            label = 'NONE_IDENTIFIED'
        out['diagnosis'][cls] = {'headroom': headroom, 'expressiveness': expr, 'search': srch, 'evaluation': ev,
                                 'signal_better': sum(out['trajectories'][k]['signal']['better'] for k in ks),
                                 'bottleneck': label}

    def finals(arm):
        return [out['trajectories'][k]['arms'][arm]['final_gain'] for k in keys]
    p1 = wilcoxon([x - y for x, y in zip(finals('L'), finals('V2'))], 'greater')
    p2 = wilcoxon([x - y for x, y in zip(finals('L12'), finals('L'))], 'two-sided')
    adj = holm({'P1': p1['p'], 'P2': p2['p']})
    p1['p_holm'], p2['p_holm'] = adj['P1'], adj['P2']
    p1['label'] = 'L_BETTER' if adj['P1'] < ALPHA else 'NOT_SHOWN'
    up = statistics.mean(finals('L12')) - statistics.mean(finals('L'))
    p2['label'] = 'NO_DIFFERENCE' if adj['P2'] >= ALPHA else ('EVALUATOR_BETTER' if up > 0 else 'PROPOSALS_BETTER')
    out['P1'], out['P2'] = p1, p2
    out['mean_final_gain'] = {arm: statistics.mean(finals(arm)) for arm in ARMS}
    for name, lab_ in (('releases', None), ('harmful', 'HARMFUL'), ('confirmed', 'CONFIRMED')):
        out[name] = {arm: sum(1 for k in keys for x in out['trajectories'][k]['arms'][arm]['audit']
                              if lab_ is None or x['label'] == lab_) for arm in ARMS}
    nul = {}
    for arm in ARMS:
        rows = [r for r in null if r['arm'] == arm]
        k = sum(r['releases'] > 0 for r in rows)
        nul[arm] = {'searches': len(rows), 'with_release': k, 'upper95': clopper_pearson_upper(k, len(rows))}
    out['null'] = nul
    out['S1'] = 'HOLDS' if nul['L']['upper95'] <= S1_BOUND else 'FAILS'
    out['verdict'] = ('V3_UNSAFE' if out['S1'] == 'FAILS' else
                      'JUDGE_WAS_THE_BOTTLENECK' if p1['label'] == 'L_BETTER' else 'NOT_SHOWN')
    return out


# ----------------------------------------------------------------------------------------------------- the study

def trajectory_seed(cls, rep):
    return int(digest({'study': STUDY, 'class': cls, 'rep': rep})[:12], 16)


def fixed_pool(cls, r127=None):
    """The expressiveness pool fixed in advance: the human designs written in the language, B20_R127's engines, and
    16 random engines (seeded by class); REX itself excluded. {engine key: config}."""
    import b20r127_self_invented_engine as R127
    from genesis.autonomy import selfimprove as SI
    from genesis.candidate_kinds import mcx2 as K2
    out = {}
    for prog in R127.TEMPLATES.values():
        cfg = dict(K2.DEFAULT, prog=prog)
        out[Lab.ekey(cfg)] = cfg
    r127 = r127 or ROOT / 'evidence' / 'self_invented_engine_b20r127' / 'search.json'
    s127 = json.loads(Path(r127).read_text())
    for k in sorted(s127['generations']):
        e = s127['generations'][k]['engine']
        out[Lab.ekey(e)] = e
    rng = random.Random(f'{STUDY}|pool|{cls}')
    rand = {}
    while len(rand) < POOL_RANDOM:
        e = SI.random_engine(rng)
        if Lab.ekey(e) not in out:
            rand[Lab.ekey(e)] = e
    out.update(rand)
    out.pop(Lab.ekey(K2.DEFAULT), None)
    return dict(sorted(out.items()))


def protected_digest():
    return hashlib.sha256((ROOT / 'src' / 'genesis' / 'autonomy' / 'feedback.py').read_bytes()).hexdigest()


def controls(lab, G, traj):
    """The REX pools (engine runs), then the zero-signal, planted and power controls (no engine runs)."""
    from genesis.candidate_kinds import mcx2 as K2
    null, planted, powers = [], [], {}
    for cls in CLASSES:
        splits = G[cls][0]
        pool = {t.task_id: [lab.run(K2.DEFAULT, t, f'pool{i}') / lab.ref(t) for i in range(POOL)]
                for s in ('A', 'B', 'C') for t in splits[s]}
        for i in range(NULL_SEARCHES):
            seed = int(digest({'study': STUDY, 'null': cls, 'i': i})[:12], 16)
            for arm in ORDER:
                r = pool_search(pool, splits, arm, seed, f'null|{cls}|{i}')
                null.append({'class': cls, 'i': i, 'arm': arm, 'releases': r['releases'], 'tau': r['tau']})
        for d in PLANTED:
            for i in range(PLANTED_SEARCHES):
                seed = int(digest({'study': STUDY, 'planted': cls, 'delta': d, 'i': i})[:12], 16)
                for arm in ORDER:
                    r = pool_search(pool, splits, arm, seed, f'planted|{cls}|{d:g}|{i}', d, no_trait=True)
                    planted.append(dict(r, **{'class': cls, 'i': i, 'arm': arm, 'delta': d}))
        powers[cls] = {}
        pv = [pool[t.task_id] for t in splits['B']]
        for arm in ARMS:
            taus = [traj[f'{cls}|{rep}']['arms'][arm]['tau'] for rep in range(REPLICATES)]
            powers[cls][arm] = {f'{d:g}': statistics.mean(
                power(pv, ARMS[arm][1], tau, d, POWER_PAIRS,
                      int(digest({'p': cls, 'a': arm, 'd': d, 'r': r})[:12], 16)) for r, tau in enumerate(taus))
                for d in DELTAS}
    return null, planted, powers


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        raise SystemExit(__doc__.splitlines()[2])
    out = Path(argv[0]).resolve()
    if out != (ROOT / 'evidence' / 'invention_bottleneck_b20r132').resolve():
        raise SystemExit('the registered output is evidence/invention_bottleneck_b20r132')
    out.mkdir(parents=True, exist_ok=True)
    import b20r33_strong_baseline_audit as R33
    from genesis import gset as GS
    from genesis.autonomy import contract_v3 as V3
    from genesis.autonomy import selfimprove as SI
    from genesis.candidate_kinds import mcx2 as K2
    from genesis.domains import adapter
    cpu = R33.pinned_core()
    t0 = time.monotonic()
    logf = (out / 'run.log').open('a')

    def log(m):
        line = f'[{time.monotonic() - t0:7.1f}s] {m}'
        print(line, flush=True)
        logf.write(line + '\n')
        logf.flush()
    log(f'{STUDY}; pinned to CPU {cpu}')
    A = adapter('maxcut_v1')
    G = graphs({A.exposure_identity(t)['canonical'] for t in GS.tasks()})
    lab = Lab(out / 'runs.jsonl', deadline=t0 + SLICE_S)
    rexk = Lab.ekey(K2.DEFAULT)
    try:
        base, long = {}, {}
        for cls in CLASSES:
            base[cls] = {}
            for s in ('T1', 'T2'):
                for t in G[cls][s]:
                    lab.ref(t)
                base[cls][s] = {t.task_id: (lab.run(K2.DEFAULT, t, 0) + lab.run(K2.DEFAULT, t, 1)) / 2
                                for t in G[cls][s]}
            long[cls] = {t.task_id: lab.run(K2.DEFAULT, t, 0, LONG) for s in ('T1', 'T2') for t in G[cls][s]}
        log('references, baselines and REX at 10 s done')
        traj, consistent = {}, True
        t1 = {c: {} for c in CLASSES}
        t2 = {c: {} for c in CLASSES}

        def measure(cls, cfg, sets):
            ek = Lab.ekey(cfg)
            for s in sets:
                tab = t1 if s == 'T1' else t2
                tab[cls][ek] = {t.task_id: (base[cls][s][t.task_id] if ek == rexk else lab.run(cfg, t, 0))
                                for t in G[cls][s]}
        for rep in range(REPLICATES):
            for cls in CLASSES:
                tk = f'{cls}|{rep}'
                seed = trajectory_seed(cls, rep)
                arms = run_arms(lab, G[cls][rep], seed)
                consistent &= all(a['consistent'] for a in arms.values())
                start = arms['L']['history']['start']
                muts = V3.local_calibration(SI.engine_ops(), lab.programs[start], seed)
                measure(cls, lab.programs[start], ('T1', 'T2'))
                for m in muts:
                    measure(cls, m, ('T1',))
                for a in arms.values():
                    measure(cls, lab.programs[a['final']], ('T1', 'T2'))
                    for s in a['history']['submissions']:
                        measure(cls, lab.programs[s['engine']], ('T1',))
                traj[tk] = {'start': start, 'mutations': [Lab.ekey(m) for m in muts], 'arms': arms}
                log(f"{tk}: start {start}; " + '; '.join(
                    f"{arm} tau {100 * a['tau']:.3f}% releases {a['releases']} final {a['final']}"
                    for arm, a in arms.items()))
        pool_names = {}
        for cls in CLASSES:
            measure(cls, K2.DEFAULT, ('T1', 'T2'))
            fp = fixed_pool(cls)
            pool_names[cls] = sorted(fp)
            for cfg in fp.values():
                measure(cls, cfg, ('T1',))
            b1 = base[cls]['T1']
            xw = best_by_t1(sorted(e for e in t1[cls] if e != rexk), t1[cls], b1)
            measure(cls, lab.programs[xw], ('T2',))
            subs = sorted({s['engine'] for k in traj if k.startswith(cls + '|')
                           for a in traj[k]['arms'].values() for s in a['history']['submissions']})
            if subs:
                measure(cls, lab.programs[best_by_t1(subs, t1[cls], b1)], ('T2',))
            log(f'{cls}: {len(t1[cls]) - 1} engines on T1; expressiveness winner {xw}')
        null, planted, powers = controls(lab, G, traj)
        log('controls: zero-signal releases ' + ', '.join(
            f"{a} {sum(r['releases'] > 0 for r in null if r['arm'] == a)}/{sum(r['arm'] == a for r in null)}"
            for a in ORDER))
    except Paused:
        log(f'time slice used ({SLICE_S} s): paused with {len(lab.cache)} runs')
        return PAUSED
    res = analyse(traj, t1, t2, base, long, pool_names, null, planted, powers, rexk)
    cpus = {}
    for r in lab.cache.values():
        b = r['key'].rsplit('|', 1)[1]
        cpus.setdefault(b, []).append(r['cpu'] / float(b))
    med = {b: statistics.median(v) for b, v in cpus.items()}
    protected = protected_digest() == PROTECTED_FEEDBACK_SHA256
    valid = all(m >= 0.9 for m in med.values()) and consistent and protected
    (out / 'controls.json').write_text(json.dumps({'null': null, 'planted': planted, 'powers': powers}, indent=1,
                                                  sort_keys=True) + '\n')
    (out / 'programs.json').write_text(json.dumps(lab.programs, indent=1, sort_keys=True) + '\n')
    summary = dict(res, study=STUDY, schema='genesis-b20r132-invention-bottleneck-v1', valid=valid,
                   verdict=res['verdict'] if valid else 'INVALID', cpu_median=med, consistent=consistent,
                   protected_judge_unchanged=protected,
                   inputs={'traj': traj, 't1': t1, 't2': t2, 'base': base, 'long': long, 'pool_names': pool_names},
                   graphs={c: {'T1': [t.task_id for t in G[c]['T1']], 'T2': [t.task_id for t in G[c]['T2']],
                               **{str(r): {s: [t.task_id for t in v] for s, v in G[c][r].items()}
                                  for r in range(REPLICATES)}} for c in CLASSES},
                   code_identity=code_identity(ROOT)['sha256'], status='DEV; licenses nothing')
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n')
    log(f"valid {valid}; verdict {summary['verdict']}; P1 {res['P1']['label']} (p {res['P1']['p']:.4g}); P2 "
        f"{res['P2']['label']}; S1 {res['S1']}; bottlenecks "
        f"{ {c: d['bottleneck'] for c, d in res['diagnosis'].items()} }; mean final gain {res['mean_final_gain']}; "
        f"releases {res['releases']}; harmful {res['harmful']}; confirmed {res['confirmed']}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
