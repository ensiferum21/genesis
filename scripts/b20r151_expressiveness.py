#!/usr/bin/env python3
"""B20_R151: richer expressiveness, measured apart from search (DEV, preregistered)

    taskset -c 0 python3 scripts/b20r151_expressiveness.py evidence/expressiveness_b20r151     run ALONE (resumable; slices exit 3)

**Why.** Daniel, 27 Oct 2026, 14:33: "prioritize richer algorithm expressiveness, experimentally separated from
improvements in search" (`docs/OMEGA_EXPRESSIVE_LANGUAGE.md`). B20_R132 diagnosed EXPRESSIVENESS in every class: of
112-117 engines written in mcx2's language per class, none beat REX on fresh graphs by a confirmed, material amount.
X1 (B20_R153) built a richer language. This study asks whether it can express better engines, and keeps that apart
from whether it makes them easier or harder to find.

**The languages.** Λ0 is mcx2's (a flat loop of physics operators with the S and P guards); Λ1 is mcx3's, the
builder's construct algebra (targets, ?-guards over run-time observables, repeats, blocks). **The algebra is the
builder's: any gain here is a human LANGUAGE change (Λ0 -> Λ1), never Genesis's invention.** Both languages run on
the pinned mcx3 binary (B20_R153: every mcx2 program makes the same moves in it), so the language factor is the
program space only. Description-length bound N = 32 items (`lambda1.length`; mcx2's limit). The operators are
`expressive.operators.ops(lang)`, one implementation with the language as a parameter, the population started with
REX (`mcx3` DEFAULT, "B100 X I S2000 C") then random engines.

**The searches** (the same for both languages; matched compute within each level, in graph-seconds of engine runs):
  * inventor: the protected steady-state search (`autonomy.feedback.steady_state_search`, its constants, contract
    off: the winner is the best of its 4 finalists by 4 re-evaluations on its own data), 240 evaluations of 4 graphs
    at 1 s (B20_R132's inventor budget, 960 graph-seconds, plus the finalists');
  * ceiling: the same algorithm through `selfimprove.search` with a larger process (population 32, children 16,
    leaders 4, tournament 3, crossover 0.25), 480 evaluations of 8 graphs at 1 s (3,840 graph-seconds, four times the
    inventor's, each evaluation on twice the graphs). Its half-budget checkpoint (the same search stopped at 240
    evaluations: the same trajectory, from the same runs) measures whether the ceiling has saturated.
No judge decides anything here: the evaluation factor (B20_R132's) is held out, so that the search's own choice is
what is measured.

**Graphs.** Fresh, generated (seed SEED), Gset identities excluded, all disjoint by canonical identity. Three
candidate classes of 2,000 vertices, where REX at 1 s should be furthest from its longer runs (`docs/
OMEGA_EXPRESSIVE_LANGUAGE.md` §5): planar2000 (planar2 and planar2_pm1, density 0.99, as Gset's G35-G42), toroidal2000
(torus2d_pm1, 100 x 20 and 50 x 40) and random2000 (erdos and erdos_pm1, p 0.01, as Gset's G22-G31). Per class: the
headroom set H (12 graphs), per replicate r a search split A_r (8 graphs; the inventor uses the first 4), and the
truth set T (24 graphs) that no search sees.

**Runs.** The pinned mcx3 binary at 1 s CPU (10 s for headroom), run directly; every value is the cut of the returned
partition, recomputed in Python (`mcx3.solve`). A run's seed is a hash of (study, engine, graph, occurrence), the
occurrence counting that engine's earlier evaluations on that split in the same search, so arms making the same
evaluation share the run (common random numbers). A split evaluation is the mean over its graphs of cut / reference,
the reference REX at 1 s with a fixed seed. T-gain of an engine on a graph: (its mean cut over T_RUNS = 2 runs -
baseline) / baseline, the baseline REX's mean over the same two runs (so REX's own T-gain is 0).

**The headroom gate (first).** Per candidate class, REX at 10 s against the baseline on H: a class PASSES if the mean
relative gain is at least GATE (0.2%) and a one-sided Wilcoxon signed-rank test gives p < 0.05. The (at most)
MAX_CLASSES = 2 passing classes with the largest headroom are studied; if none passes, the verdict is NO_HEADROOM and
nothing else runs.

**Arms per studied class.** Inventor searches I0_r, I1_r (r = 0, 1, 2; seed from (class, r), shared by the languages)
and ceiling searches C0_r, C1_r (r = 0, 1), each with its half-budget checkpoint. Each arm's final engine runs on T;
so does REX. For each Λ1 ceiling winner, four ablations run on T (descriptive): its targets dropped, its ?-guards
dropped (the governed item then always runs), its repeats dropped (the body once), its blocks spliced into their
lists (a block that is a repeat's body stays: a repeat governs one item).

**Primary (Holm over the studied classes, alpha 0.05).** P1, the expressiveness gain: per T graph, the mean T-gain of
the two Λ1 ceiling winners minus that of the two Λ0 ceiling winners; one-sided Wilcoxon signed-rank (Λ1 > Λ0):
EXPRESSIVE if p_Holm < 0.05 and the mean difference is at least MATERIAL (0.05%).
**Secondary (reported per class, not in the primary family):**
  * S1, the language under the inventor: mean T-gain of I1_r minus I0_r, two-sided: LANGUAGE_HELPS_THE_INVENTOR,
    LANGUAGE_HURTS_THE_INVENTOR or NO_DIFFERENCE (p < 0.05 and |mean| >= MATERIAL);
  * S2, the search gain in each language: ceiling minus inventor, one-sided;
  * S3, the interaction: (I1 - I0) - (C1 - C0) per graph, two-sided;
  * S4, saturation: per language, full minus half-budget ceiling winners, two-sided; SATURATED if not
    distinguishable (p >= 0.05) or the mean is below MATERIAL;
  * S5, each arm against REX, one-sided;
  * the reading per class: EXPRESSIVE if P1 holds; else SEARCH_EFFECT if S1 says the language helps the inventor;
    else LANGUAGE_HARDER_TO_SEARCH if S1 says it hurts; else NO_LANGUAGE_EFFECT;
  * the constructs the Λ1 programs use (all evaluated, and the winners), the ablations, program lengths.
**Validity:** the median CPU of the runs at each budget is at least 0.9 of it; every Λ0 arm evaluated only Λ0
programs (checked on every evaluation); every search spent its budget; the protected judge's source, mcx3's pin and
mcx2's pin are the ones at preregistration; H, A and T are pairwise disjoint. **Verdict:** INVALID if validity fails;
else NO_HEADROOM if no class passes the gate; else EXPRESSIVENESS_GAIN if P1 holds in a studied class; else
NOT_SHOWN. Whatever it is, it is a statement about the builder's language at N = 32 on the studied classes.

**Prior art (none claimed).** Extending a program-search language with subroutines and control is old: automatically
defined functions (Koza 1994), module acquisition (Angeline and Pollack 1993); the separation of a search space from
the algorithm that searches it is the usual decomposition of program synthesis (Gulwani, Polozov and Singh 2017).
The operators of both languages are mcx2's, each from its literature (`native/mcx2.c`).

**Expectation, stated before running (low confidence).** The gate passes planar2000 and toroidal2000 (about 0.4-1%
and 0.2-0.4%) and fails random2000 (below 0.1%). P1 NOT_SHOWN: a Λ1 ceiling gain of 0-0.1%, not distinguishable on
24 graphs. S1 NO_DIFFERENCE or LANGUAGE_HURTS_THE_INVENTOR (more kinds of mutation dilute the classic ones at the
same budget). S2: the ceiling beats the inventor by about 0.05-0.2% in Λ0. S4: the Λ0 ceiling roughly SATURATED.
Verdict NOT_SHOWN.

**Cost.** The gate about 7 min. Per studied class: the inventor searches about 1.7 h, the ceiling searches about
4.5 h, T about 20 min: about 6.6 h; at most 13.3 h for two classes, in slices of 6,600 s. **Status.** DEV; licenses
nothing; adopts nothing.
"""
import hashlib
import json
from pathlib import Path
import resource
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis.common import code_identity, digest  # noqa: E402

STUDY = 'b20r151'
SEED = 20521511
CANDIDATES = {
    'planar2000': (('planar2', {'n': 2000, 'density': 0.99}), ('planar2_pm1', {'n': 2000, 'density': 0.99})),
    'toroidal2000': (('torus2d_pm1', {'rows': 100, 'cols': 20}), ('torus2d_pm1', {'rows': 50, 'cols': 40})),
    'random2000': (('erdos', {'n': 2000, 'p': 0.01}), ('erdos_pm1', {'n': 2000, 'p': 0.01})),
}
H_GRAPHS, A_GRAPHS, T_GRAPHS, T_RUNS = 12, 8, 24, 2
INV_REPS, CEIL_REPS = 3, 2
BUDGET, LONG = 1.0, 10.0
INV_EVALS, INV_SIZE = 240, 4
CEIL_EVALS, CEIL_SIZE, CEIL_HALF = 480, 8, 240
BOUND = 32
LANGS = ('L0', 'L1')
GATE, MAX_CLASSES = 0.002, 2
MATERIAL, ALPHA = 0.0005, 0.05
ABLATIONS = ('targets', 'guards', 'repeats', 'blocks')
PROTECTED_FEEDBACK_SHA256 = '2ff4a5ab1e5b445b9144afbcc43596b8b1701ae541e8916c73e45009c0e3bdd6'
MCX3_SHA256 = '9449f8b669506b159dff56c7d6d1c1276859d0fa83852b04c805086999dcbd24'
MCX2_SHA256 = 'c6a797c8aac0674f593da71b0c9210c8e13943249b661e38dd5196693edbec3b'
SLICE_S, PAUSED = 6600, 3


class Paused(Exception):
    pass


def ceiling_process():
    from genesis.autonomy import selfimprove as SI
    return dict(SI.ORIGINAL, pop=32, children=16, leaders=4, tournament=3, p_cross=0.25)


# ----------------------------------------------------------------------------------------------- graphs and runs

def graphs(excluded):
    """{class: {'H': [task], 'T': [task], 'A': [[task] per replicate]}} of fresh generated graphs, pairwise disjoint
    and disjoint from `excluded` (canonical identities)."""
    from genesis.domains import adapter
    A = adapter('maxcut_v1')
    seen, out, k = set(excluded), {}, 0

    def draw(cls, n):
        nonlocal seen, k
        ts = []
        for i in range(n):
            fam, params = CANDIDATES[cls][i % len(CANDIDATES[cls])]
            got, seen, _ = A.generate(SEED + 1000 * k + i, 1, 'DEV', fam, params, excluded=seen)
            ts.append(got[0])
        k += 1
        return ts
    for cls in CANDIDATES:
        out[cls] = {'H': draw(cls, H_GRAPHS), 'T': draw(cls, T_GRAPHS),
                    'A': [draw(cls, A_GRAPHS) for _ in range(max(INV_REPS, CEIL_REPS))]}
    return out


def run_seed(engine_key, task_id, occ, budget):
    return int(digest({'study': STUDY, 'engine': engine_key, 'task': task_id, 'occ': occ, 'budget': budget})[:12], 16)


def real_runner(cfg, task, seed, budget):
    """(value, CPU seconds of the engine process) of one direct run of the pinned mcx3 binary."""
    from genesis.candidate_kinds import mcx3 as K3
    from genesis.models_maxcut import MaxCutCandidateView
    r0 = resource.getrusage(resource.RUSAGE_CHILDREN)
    v = K3.solve(MaxCutCandidateView(n=task.n, edges=task.edges), {'cpu_seconds': budget, 'config': cfg}, budget,
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
            v, cpu = self.runner(cfg, task, run_seed(ek, task.task_id, occ, budget), budget)
            self.cache[k] = {'key': k, 'value': v, 'cpu': round(cpu, 4)}
            if self.path is not None:
                with open(self.path, 'a') as f:
                    f.write(json.dumps(self.cache[k], sort_keys=True) + '\n')
        return self.cache[k]['value']

    def ref(self, task):
        from genesis.candidate_kinds import mcx3 as K3
        return self.run(K3.DEFAULT, task, 'ref')


def evaluator(lab, tasks, lang, log=None):
    """evaluate(genome, split): the mean over `tasks` of cut / reference ('A' only); the occurrence of a run counts
    the engine's earlier evaluations in this search. A Λ0 search may evaluate Λ0 programs only (validity)."""
    from genesis.candidate_kinds import mcx3 as K3
    from genesis.expressive import lambda1 as L1
    occ = {}

    def ev(genome, split):
        if split != 'A':
            raise ValueError(f'no split {split} in this study')
        cfg = L1.config(genome)
        if lang == 'L0' and not K3.is_lambda0(K3.parse(cfg['prog'])):
            raise AssertionError(f'a Λ0 search evaluated a Λ1 program: {cfg["prog"]}')
        ek = Lab.ekey(cfg)
        n = occ.get(ek, 0)
        occ[ek] = n + 1
        v = statistics.mean(lab.run(cfg, t, n) / lab.ref(t) for t in tasks)
        if log is not None:
            log.append({'engine': ek, 'occ': n, 'value': v, 'length': L1.length(K3.parse(cfg['prog']))})
        return v
    return ev


def search(lab, lang, arm, tasks, seed, max_evals=None):
    """One search: (winner config, report, calls). arm 'inventor' or 'ceiling'."""
    from genesis.autonomy import feedback as FB
    from genesis.autonomy import selfimprove as SI
    from genesis.candidate_kinds import mcx3 as K3
    from genesis.expressive import lambda1 as L1
    from genesis.expressive import operators as O
    calls = []
    ops = SI.seeded_ops(O.ops(lang, bound=BOUND), [dict(K3.DEFAULT)])
    if arm == 'inventor':
        ev = evaluator(lab, tasks[:INV_SIZE], lang, calls)
        winner, report = FB.steady_state_search(ops, ev, max_evals or INV_EVALS, seed, contract=False)
    else:
        ev = evaluator(lab, tasks[:CEIL_SIZE], lang, calls)
        winner, report = SI.search(ceiling_process(), ops, ev, max_evals or CEIL_EVALS, seed, contract=False,
                                   calibrate='AB')
    return L1.config(winner), report, calls


def search_seed(cls, arm, rep):
    return int(digest({'study': STUDY, 'class': cls, 'arm': arm, 'rep': rep})[:12], 16)


# ----------------------------------------------------------------------------------------------------- ablations

def ablate(prog, what):
    """The program with one kind of construct removed (see the module docstring), canonical; None if that leaves no
    valid program."""
    from genesis.candidate_kinds import mcx3 as K3

    def item(x):
        k = x[0]
        if k == 'op':
            return [('op', x[1], x[2], None if what == 'targets' else x[3])]
        if k == '?' and what == 'guards':
            return []
        if k == '*':
            body = item(x[2])
            if what == 'repeats':
                return body
            return [('*', x[1], body[0] if len(body) == 1 else ('[', tuple(body)))] if body else []
        if k == '[':
            body = lst(x[1])
            if what == 'blocks':
                return list(body)
            return [('[', body)] if body else []
        return [x]

    def lst(xs):
        return tuple(y for x in xs for y in item(x))
    try:
        out = K3.canonical(lst(prog))
        if not out or K3.check(out):
            return None
        return K3.canonical(K3.parse(K3.render(out)))
    except ValueError:
        return None


def constructs(prog):
    """Which of Λ1's constructs a program uses."""
    from genesis.candidate_kinds import mcx3 as K3
    xs = list(K3.walk(prog))
    return {'targets': any(x[0] == 'op' and x[3] is not None for x in xs),
            'guards': sorted({x[1] for x in xs if x[0] == '?'}), 'repeats': any(x[0] == '*' for x in xs),
            'blocks': any(x[0] == '[' for x in xs)}


# ------------------------------------------------------------------------------------------------------ statistics

def wilcoxon(diffs, alternative):
    from scipy.stats import wilcoxon as W
    d = [x for x in diffs if x != 0]
    if not d:
        return {'n': 0, 'p': 1.0, 'mean': statistics.mean(diffs) if diffs else 0.0}
    return {'n': len(d), 'p': float(W(d, alternative=alternative).pvalue), 'mean': statistics.mean(diffs)}


def holm(ps):
    order = sorted(ps, key=lambda k: ps[k])
    out, run = {}, 0.0
    for i, k in enumerate(order):
        run = max(run, min(1.0, (len(ps) - i) * ps[k]))
        out[k] = run
    return out


def gate(base_h, long_h):
    """{'mean', 'p', 'pass'}: REX at 10 s against the baseline on the headroom set."""
    rel = [(long_h[t] - base_h[t]) / base_h[t] for t in sorted(base_h)]
    w = wilcoxon(rel, 'greater')
    return {'mean': statistics.mean(rel), 'p': w['p'], 'pass': statistics.mean(rel) >= GATE and w['p'] < ALPHA}


def select(gates):
    passing = sorted((c for c, g in gates.items() if g['pass']), key=lambda c: (-gates[c]['mean'], c))
    return passing[:MAX_CLASSES]


def gains(values, base):
    """Per-graph relative gains of each engine: {engine: [(v - b) / b over the sorted graphs]}."""
    tasks = sorted(base)
    return {e: [(vals[t] - base[t]) / base[t] for t in tasks] for e, vals in values.items()}


def mean_of(rows):
    return [statistics.mean(x) for x in zip(*rows)]


def analyse_class(arms, g):
    """arms: {arm name: engine key}; g: per-graph gains by engine key. Arm names I0_r, I1_r, C0_r, C1_r, C0h_r, C1h_r."""
    def lane(prefix, reps):
        return mean_of([g[arms[f'{prefix}_{r}']] for r in range(reps)])
    I0, I1 = lane('I0', INV_REPS), lane('I1', INV_REPS)
    C0, C1 = lane('C0', CEIL_REPS), lane('C1', CEIL_REPS)
    C0h, C1h = lane('C0h', CEIL_REPS), lane('C1h', CEIL_REPS)
    diff = lambda a, b: [x - y for x, y in zip(a, b)]
    p1 = wilcoxon(diff(C1, C0), 'greater')
    s1 = wilcoxon(diff(I1, I0), 'two-sided')
    s1_label = ('NO_DIFFERENCE' if s1['p'] >= ALPHA or abs(s1['mean']) < MATERIAL else
                'LANGUAGE_HELPS_THE_INVENTOR' if s1['mean'] > 0 else 'LANGUAGE_HURTS_THE_INVENTOR')
    s4 = {}
    for lang, full, half in (('L0', C0, C0h), ('L1', C1, C1h)):
        w = wilcoxon(diff(full, half), 'two-sided')
        s4[lang] = dict(w, label='SATURATED' if w['p'] >= ALPHA or w['mean'] < MATERIAL else 'STILL_IMPROVING')
    return {
        'P1': p1,
        'S1': dict(s1, label=s1_label),
        'S2': {'L0': wilcoxon(diff(C0, I0), 'greater'), 'L1': wilcoxon(diff(C1, I1), 'greater')},
        'S3': wilcoxon(diff(diff(I1, I0), diff(C1, C0)), 'two-sided'),
        'S4': s4,
        'S5': {name: wilcoxon(g[e], 'greater') for name, e in sorted(arms.items())},
        'lanes': {k: statistics.mean(v) for k, v in
                  (('I0', I0), ('I1', I1), ('C0', C0), ('C1', C1), ('C0h', C0h), ('C1h', C1h))},
    }


def verdict(studied, per_class, valid):
    """The verdict and the Holm-adjusted P1 p-values; labels and readings are added to per_class."""
    ph = holm({c: per_class[c]['P1']['p'] for c in studied}) if studied else {}
    for c in studied:
        r = per_class[c]
        r['P1']['p_holm'] = ph[c]
        r['P1']['label'] = 'EXPRESSIVE' if ph[c] < ALPHA and r['P1']['mean'] >= MATERIAL else 'NOT_SHOWN'
        r['reading'] = ('EXPRESSIVE' if r['P1']['label'] == 'EXPRESSIVE' else
                        'SEARCH_EFFECT' if r['S1']['label'] == 'LANGUAGE_HELPS_THE_INVENTOR' else
                        'LANGUAGE_HARDER_TO_SEARCH' if r['S1']['label'] == 'LANGUAGE_HURTS_THE_INVENTOR' else
                        'NO_LANGUAGE_EFFECT')
    if not valid:
        return 'INVALID', ph
    if not studied:
        return 'NO_HEADROOM', ph
    v = 'EXPRESSIVENESS_GAIN' if any(per_class[c]['P1']['label'] == 'EXPRESSIVE' for c in studied) else 'NOT_SHOWN'
    return v, ph


def file_digest(path):
    p = Path(path)
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


# ----------------------------------------------------------------------------------------------------------- main

def main(argv=None, runner=real_runner, registered=True):
    """Run (or resume) the study; 0 when done, PAUSED at the end of a time slice."""
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        raise SystemExit(__doc__.splitlines()[2])
    out = Path(argv[0]).resolve()
    if registered and out != (ROOT / 'evidence' / 'expressiveness_b20r151').resolve():
        raise SystemExit('the registered output is evidence/expressiveness_b20r151')
    out.mkdir(parents=True, exist_ok=True)
    import b20r33_strong_baseline_audit as R33
    cpu = R33.pinned_core() if registered else None
    t0 = time.monotonic()
    with (out / 'run.log').open('a') as logf:
        return _study(out, logf, t0, cpu, runner, registered)


def _study(out, logf, t0, cpu, runner, registered):
    from genesis import gset as GS
    from genesis.candidate_kinds import mcx2 as K2
    from genesis.candidate_kinds import mcx3 as K3
    from genesis.domains import adapter

    def log(m):
        line = f'[{time.monotonic() - t0:7.1f}s] {m}'
        print(line, flush=True)
        logf.write(line + '\n')
        logf.flush()
    log(f'{STUDY}; pinned to CPU {cpu}')
    A = adapter('maxcut_v1')
    G = graphs({A.exposure_identity(t)['canonical'] for t in GS.tasks()})
    ids = [A.exposure_identity(t)['canonical'] for c in G for t in G[c]['H'] + G[c]['T'] + sum(G[c]['A'], [])]
    disjoint = len(ids) == len(set(ids))
    lab = Lab(out / 'runs.jsonl', runner=runner, deadline=t0 + SLICE_S)
    rex = dict(K3.DEFAULT)
    arms, finals, reports, usage = {}, {}, {}, {}
    try:
        gates = {}
        for cls in CANDIDATES:
            base_h = {t.task_id: (lab.run(rex, t, 0) + lab.run(rex, t, 1)) / 2 for t in G[cls]['H']}
            long_h = {t.task_id: lab.run(rex, t, 0, LONG) for t in G[cls]['H']}
            gates[cls] = gate(base_h, long_h)
            log(f"gate {cls}: headroom {100 * gates[cls]['mean']:.3f}% p {gates[cls]['p']:.3g} "
                f"{'PASS' if gates[cls]['pass'] else 'fail'}")
        studied = select(gates)
        log(f'studied classes: {studied}')
        for cls in studied:
            arms[cls] = {}
            for r in range(INV_REPS):
                seed = search_seed(cls, 'inventor', r)
                for lang in LANGS:
                    name = f'I{lang[1]}_{r}'
                    cfg, rep, calls = search(lab, lang, 'inventor', G[cls]['A'][r], seed)
                    arms[cls][name] = Lab.ekey(cfg)
                    reports[f'{cls}|{name}'] = dict(rep, max_evals=INV_EVALS)
                    usage[f'{cls}|{name}'] = calls
                    log(f"{cls} {name}: {rep['evaluations']} evaluations, {rep['distinct_programs']} programs; "
                        f"winner {cfg['prog']!r} (reported {rep['reported']:.5f})")
            for r in range(CEIL_REPS):
                seed = search_seed(cls, 'ceiling', r)
                for lang in LANGS:
                    for name, evals in ((f'C{lang[1]}h_{r}', CEIL_HALF), (f'C{lang[1]}_{r}', CEIL_EVALS)):
                        cfg, rep, calls = search(lab, lang, 'ceiling', G[cls]['A'][r], seed, evals)
                        arms[cls][name] = Lab.ekey(cfg)
                        reports[f'{cls}|{name}'] = dict(rep, max_evals=evals)
                        if evals == CEIL_EVALS:
                            usage[f'{cls}|{name}'] = calls
                        log(f"{cls} {name}: {rep['evaluations']} evaluations, {rep['distinct_programs']} programs; "
                            f"winner {cfg['prog']!r} (reported {rep['reported']:.5f})")
            # the truth set: REX's baseline, every arm's final engine, the ablations of the Λ1 ceiling winners
            base = {t.task_id: statistics.mean(lab.run(rex, t, o) for o in range(T_RUNS)) for t in G[cls]['T']}
            engines = dict.fromkeys(sorted(set(arms[cls].values()) | {Lab.ekey(rex)}))
            abl = {}
            for r in range(CEIL_REPS):
                prog = K3.parse(lab.programs[arms[cls][f'C1_{r}']]['prog'])
                for what in ABLATIONS:
                    p = ablate(prog, what)
                    if p is not None and p != prog:
                        cfg = dict(lab.programs[arms[cls][f'C1_{r}']], prog=K3.render(p))
                        abl[f'C1_{r}|{what}'] = Lab.ekey(cfg)
                        lab.programs.setdefault(Lab.ekey(cfg), cfg)
                        engines[Lab.ekey(cfg)] = None
            values = {e: {t.task_id: statistics.mean(lab.run(lab.programs[e], t, o) for o in range(T_RUNS))
                          for t in G[cls]['T']} for e in engines}
            finals[cls] = {'base': base, 'values': values, 'ablations': abl}
            log(f'{cls}: T done ({len(engines)} engines)')
    except Paused:
        log(f'time slice used ({SLICE_S} s): paused with {len(lab.cache)} runs')
        return PAUSED
    per_class = {}
    for cls in arms:
        g = gains(finals[cls]['values'], finals[cls]['base'])
        per_class[cls] = analyse_class(arms[cls], g)
        per_class[cls]['ablations'] = {k: statistics.mean(g[e]) - statistics.mean(g[arms[cls][k.split('|')[0]]])
                                       for k, e in finals[cls]['ablations'].items()}
        per_class[cls]['winners'] = {n: {'prog': lab.programs[e]['prog'], 'mean_gain': statistics.mean(g[e]),
                                         'constructs': constructs(K3.parse(lab.programs[e]['prog']))}
                                     for n, e in sorted(arms[cls].items())}
        l1 = [c for k, cs in usage.items() for c in cs
              if k.split('|')[0] == cls and k.split('|')[1][1] == '1']          # the Λ1 arms: I1_r, C1_r
        progs = {c['engine']: lab.programs[c['engine']]['prog'] for c in l1}
        use = [constructs(K3.parse(p)) for p in progs.values()]
        per_class[cls]['usage_L1'] = {'programs': len(use), **{k: sum(bool(u[k]) for u in use) for k in ABLATIONS}}
    cpus = {}
    for r in lab.cache.values():
        b = r['key'].rsplit('|', 1)[1]
        cpus.setdefault(b, []).append(r['cpu'] / float(b))
    med = {b: statistics.median(v) for b, v in cpus.items()}
    spent = all(rep['evaluations'] >= rep['max_evals'] for rep in reports.values())
    pins = {'protected_judge': file_digest(ROOT / 'src' / 'genesis' / 'autonomy' / 'feedback.py') ==
            PROTECTED_FEEDBACK_SHA256, 'mcx3': K3.BINARY_SHA256 == MCX3_SHA256 and (
                not registered or K3.binary_digest() == MCX3_SHA256),
            'mcx2': K2.BINARY_SHA256 == MCX2_SHA256}
    valid = all(m >= 0.9 for m in med.values()) and spent and disjoint and all(pins.values())
    v, ph = verdict(sorted(arms), per_class, valid)
    (out / 'programs.json').write_text(json.dumps(lab.programs, indent=1, sort_keys=True) + '\n')
    (out / 'calls.json').write_text(json.dumps(usage, indent=1, sort_keys=True) + '\n')
    summary = {'study': STUDY, 'schema': 'genesis-b20r151-expressiveness-v1', 'verdict': v, 'valid': valid,
               'gates': gates, 'studied': sorted(arms), 'per_class': per_class, 'p_holm': ph, 'arms': arms,
               'reports': reports, 'finals': finals, 'cpu_median': med, 'spent': spent, 'disjoint': disjoint,
               'pins': pins,
               'graphs': {c: {'H': [t.task_id for t in G[c]['H']], 'T': [t.task_id for t in G[c]['T']],
                              'A': [[t.task_id for t in a] for a in G[c]['A']]} for c in G},
               'code_identity': code_identity(ROOT)['sha256'], 'status': 'DEV; licenses nothing'}
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n')
    log(f'valid {valid}; verdict {v}; ' + '; '.join(
        f"{c}: P1 {r['P1']['label']} ({100 * r['P1']['mean']:+.3f}%, p_holm {r['P1']['p_holm']:.3g}), S1 "
        f"{r['S1']['label']} ({100 * r['S1']['mean']:+.3f}%), reading {r['reading']}" for c, r in per_class.items()))
    return 0


if __name__ == '__main__':
    sys.exit(main())
