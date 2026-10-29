#!/usr/bin/env python3
"""B20_R136 (experiment A of `docs/OMEGA_RECURSIVE_INVENTION.md` §15): does a sense Genesis synthesises, choosing the
engine per graph, beat the best fixed engine and the builder's hand features, with its own computation charged?
(DEV, preregistered)

    taskset -c 0 python3 scripts/b20r136_sense_choice.py evidence/sense_choice_b20r136   run ALONE (resumable; slices exit 3)

**Why.** The adopted architecture's first vertical slice: synthesise a sense, use it to choose the method per
instance, verify the gain, keep it. B20_R165 gives a real reason for a per-instance choice: C0_1, the engine
Genesis's searches found, beats the builder-configured REX by about 1.2% on ±1-weighted planar graphs, ties it on
unweighted planar graphs and loses to it on ±1 tori and random graphs. A sense that sees which kind of graph it faces
could take C0_1's gain without its losses. Nobody tells the search which property matters.

**The choices** (K = 2): REX (mcx3's DEFAULT) and C0_1 (B20_R165's pre-specified engine, read from B20_R151's
evidence with its recorded key), the pinned mcx3 binary at 1 s CPU.

**Graphs (fresh).** Five families of 2,000 vertices, as B20_R165's classes: planar2 and planar2_pm1 (density 0.99),
torus2d_pm1 (100 x 20 and 50 x 40, alternating), erdos and erdos_pm1 (p 0.01). Generated from SEED, disjoint by
canonical identity from Gset and from every graph of B20_R151, B20_R152, B20_R165 and B20_R173. A training set
(TRAIN_PER = 8 per family, 40) and a test set (TEST_PER = 12 per family, 60).

**Scores.** A run's value is its cut; a graph's score for a choice is the mean of T_RUNS = 2 runs, relative to REX's
mean on that graph at 1 s: (cut - REX) / REX. Runs are seeded by (study, engine, graph, run, budget).

**Arms on the test set** (each graph's choice made from the graph alone):
  * SENSE: `senses.synthesis.synthesise` on the training set (SEARCH_BUDGET = 300 candidate senses, 4-fold
    cross-validation, seed 0; nothing about the families given) gives a sense; its stump, refitted on the whole
    training set, chooses. **Its computation is charged**: on each test graph the sense's CPU time is measured, and
    the chosen engine runs for 1 s minus that time (rounded up to 0.01 s, at least 0.5 s);
  * HAND: the builder's features (B20_R105: the degree sequence's coefficient of variation and log(max / mean)),
    whichever of the two cross-validates better on the training set, with the same stump and the same charge;
  * FIXED: the engine with the better mean training score, everywhere, at 1 s;
  * ORACLE (a reference): the better engine on each test graph, by its 1 s runs.

**Primary (Holm over the two, alpha 0.05):**
  * P1: SENSE against FIXED, the per-graph score difference, one-sided Wilcoxon signed-rank over the 60 test graphs;
    passes if p_Holm < 0.05 and the mean difference is at least MATERIAL (0.1%);
  * P2: SENSE against HAND, the same test and rule.
**Verdict:**
  * INVALID if validity fails;
  * SENSE_INVENTION_HELPS if P1 and P2 pass;
  * BEATS_FIXED_ONLY if only P1 passes;
  * otherwise NOT_SHOWN.
**Secondary (reported):**
  * S1: each arm's mean score, and the oracle's (the headroom of choosing);
  * S2: the synthesised sense, its cross-validated training value against the baseline and the oracle, and the
    search's charges;
  * S3: per-family means of every arm and the choices each made;
  * S4: the senses' CPU per graph (SENSE and HAND) and the budgets the chosen engines received;
  * S5: HAND against FIXED, one-sided.
**Validity:**
  * the median CPU of the full 1 s runs is at least 0.9 s;
  * the graph sets are pairwise disjoint and disjoint from everything excluded;
  * C0_1 hashes to its recorded key and B20_R151's summary has its recorded digest;
  * mcx3's pin and the protected judge's source are the ones at preregistration (the judge is not asked here).

**Expectation, stated before running (low confidence).** FIXED is REX (C0_1 loses on three of five families). The
search finds a sense that separates ±1-weighted graphs or planar ones; SENSE beats FIXED by about 0.2% on average (the
gain comes from one family in five) and P1 passes. P2 is uncertain: the degree features already separate planar
graphs from tori and random graphs, and C0_1 ties REX on unweighted planar graphs, so choosing C0_1 on every planar
graph costs little; HAND may come close to SENSE. So BEATS_FIXED_ONLY, low confidence.

**Development looks (disclosed).** None on these graphs or on these engines' choices. The sense language and its
synthesis were tested on random fixtures only (`test_sense_synthesis`). B20_R165's per-family results (read in full
when recorded) motivate the design. A timing check before preregistration (29 Oct 2026; one graph per family, seeds
990000-990004, no study's; no engine run) measured the senses' CPU (0.007-0.057 s per graph) and showed three values
per family: the share of positive weights separates the ±1 families from the unweighted ones, mean clustering
separates the planar families (0.34) from the others, and the degree CV separates planar (1.2), random (0.22) and
tori (0). It is why the expectation for P2 is uncertain. The hand features' second statistic is log1p(max / mean)
rather than log(max / mean): a monotone transform, which a stump cannot tell apart.

**Cost.** Training: 40 graphs x 2 engines x 2 runs x 1 s (about 3 min); test: 60 x (2 x 2 + 2 x 2) x 1 s (8 min);
the search and the senses: minutes. Under 20 min, in slices of 6,600 s. **Status.** DEV; licenses nothing.
"""
import hashlib
import json
import math
from pathlib import Path
import resource
import statistics
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis.common import code_identity, digest  # noqa: E402

STUDY = 'b20r136'
OUTPUT = ROOT / 'evidence' / 'sense_choice_b20r136'
SEED = 20531361
R151_DIR = ROOT / 'evidence' / 'expressiveness_b20r151'
R151_SUMMARY_SHA256 = 'd021b145c395fa410c619c94ba5bfee1a1ab34a715c591148ba11fc5d6dd93df'
CANDIDATE = 'C0_1'
FAMILIES = (('planar2', {'n': 2000, 'density': 0.99}), ('planar2_pm1', {'n': 2000, 'density': 0.99}),
            ('torus2d_pm1', {'rows': 100, 'cols': 20}), ('erdos', {'n': 2000, 'p': 0.01}),
            ('erdos_pm1', {'n': 2000, 'p': 0.01}))
TORUS_ALT = {'rows': 50, 'cols': 40}
TRAIN_PER, TEST_PER = 8, 12
T_RUNS, BUDGET, MIN_BUDGET = 2, 1.0, 0.5
SEARCH_BUDGET = 300
MATERIAL, ALPHA = 0.001, 0.05
PROTECTED_FEEDBACK_SHA256 = '2ff4a5ab1e5b445b9144afbcc43596b8b1701ae541e8916c73e45009c0e3bdd6'
MCX3_SHA256 = '9449f8b669506b159dff56c7d6d1c1276859d0fa83852b04c805086999dcbd24'
HAND = (['cv_n', 'deg'], ['log1p_s', ['div_s', ['max_n', 'deg'], ['mean_n', 'deg']]])
SLICE_S, PAUSED = 6600, 3


class Paused(Exception):
    pass


def file_digest(path):
    p = Path(path)
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def engines(r151_dir=R151_DIR):
    from genesis.candidate_kinds import mcx3 as K3
    s = json.loads((Path(r151_dir) / 'summary.json').read_text())
    progs = json.loads((Path(r151_dir) / 'programs.json').read_text())
    key = s['arms']['planar2000'][CANDIDATE]
    cfg = progs[key]
    return {'REX': dict(K3.DEFAULT), CANDIDATE: cfg}, digest(cfg)[:16] == key


def excluded_identities():
    import b20r173_protected_release as R173
    from genesis.domains import adapter
    A = adapter('maxcut_v1')
    ex = R173.excluded_identities()
    g173 = R173.graphs(ex)
    return ex | {A.exposure_identity(t)['canonical'] for v in g173.values() for t in v}


def graphs(excluded, train_per=TRAIN_PER, test_per=TEST_PER):
    """{'train': [task], 'test': [task]}: fresh and disjoint, families interleaved, from SEED."""
    from genesis.domains import adapter
    A = adapter('maxcut_v1')
    seen, out = set(excluded), {'train': [], 'test': []}
    for s, (name, per) in enumerate((('train', train_per), ('test', test_per))):
        for i in range(per):
            for f, (fam, params) in enumerate(FAMILIES):
                if fam == 'torus2d_pm1' and i % 2:
                    params = TORUS_ALT
                got, seen, _ = A.generate(SEED + 100000 * s + 1000 * f + i, 1, 'DEV', fam, params, excluded=seen)
                t = got[0]
                out[name].append((fam, t))
    return out


def as_graph(task):
    return {'n': task.n, 'edges': [list(e) for e in task.edges]}


def run_seed(engine, task_id, occ, budget):
    return int(digest({'study': STUDY, 'engine': engine, 'task': task_id, 'occ': occ, 'budget': budget})[:12], 16)


def real_runner(cfg, task, seed, budget):
    from genesis.candidate_kinds import mcx3 as K3
    from genesis.models_maxcut import MaxCutCandidateView
    r0 = resource.getrusage(resource.RUSAGE_CHILDREN)
    v = K3.solve(MaxCutCandidateView(n=task.n, edges=task.edges), {'cpu_seconds': budget, 'config': cfg}, budget,
                 seed)['value']
    r1 = resource.getrusage(resource.RUSAGE_CHILDREN)
    return v, (r1.ru_utime + r1.ru_stime) - (r0.ru_utime + r0.ru_stime)


class Lab:
    """Runs and sense timings, cached and appended to runs.jsonl as they are made."""

    def __init__(self, path=None, runner=real_runner, deadline=None):
        self.path, self.runner, self.deadline = path, runner, deadline
        self.cache, self.new = {}, 0
        if path is not None and Path(path).exists():
            for line in Path(path).read_text().splitlines():
                if line.strip():
                    r = json.loads(line)
                    self.cache[r['key']] = r

    def _put(self, k, rec):
        self.cache[k] = dict(rec, key=k)
        self.new += 1
        if self.path is not None:
            with open(self.path, 'a') as f:
                f.write(json.dumps(self.cache[k], sort_keys=True) + '\n')

    def _check(self):
        if self.new and self.deadline is not None and time.monotonic() > self.deadline:
            raise Paused

    def run(self, name, cfg, task, occ, budget=BUDGET):
        k = f'run|{name}|{task.task_id}|{occ}|{budget:g}'
        if k not in self.cache:
            self._check()
            v, cpu = self.runner(cfg, task, run_seed(name, task.task_id, occ, budget), budget)
            self._put(k, {'value': v, 'cpu': round(cpu, 4)})
        return self.cache[k]['value']

    def sense(self, label, expr, task, lib=None):
        """(value, CPU seconds) of a sense on a graph, measured once (on a fresh context) and recorded."""
        from genesis.senses import graph as SG
        from genesis.senses import synthesis as SY
        k = f'sense|{label}|{task.task_id}'
        if k not in self.cache:
            self._check()
            c0 = time.process_time()
            ctx = SG.Context(as_graph(task))
            v = SY.evaluate(expr, ctx, lib or SY.EMPTY)
            self._put(k, {'value': v, 'cpu': round(time.process_time() - c0, 4)})
        return self.cache[k]['value'], self.cache[k]['cpu']


def score_matrix(lab, eng, tasks):
    """(n x K) mean cut relative to REX's mean, the engines in sorted order (REX's column is 0)."""
    names = sorted(eng)
    M = np.zeros((len(tasks), len(names)))
    for i, (_, t) in enumerate(tasks):
        rex = statistics.mean(lab.run('REX', eng['REX'], t, r) for r in range(T_RUNS))
        for j, n in enumerate(names):
            v = statistics.mean(lab.run(n, eng[n], t, r) for r in range(T_RUNS))
            M[i, j] = (v - rex) / rex
    return names, M


def charged_budget(cpu):
    return max(MIN_BUDGET, round(BUDGET - math.ceil(cpu * 100) / 100, 2))


def chosen_score(lab, eng, names, choice, task, cpu, label):
    """The chosen engine's mean cut at the charged budget, relative to REX's mean at 1 s."""
    b = charged_budget(cpu)
    rex = statistics.mean(lab.run('REX', eng['REX'], task, r) for r in range(T_RUNS))
    n = names[choice]
    v = statistics.mean(lab.run(n, eng[n], task, f'{label}{r}', b) for r in range(T_RUNS))
    return (v - rex) / rex, b


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
        run = max(run, min(1.0, (len(order) - i) * ps[k]))
        out[k] = run
    return out


def verdict(valid, p1, p2):
    if not valid:
        return 'INVALID'
    if p1 and p2:
        return 'SENSE_INVENTION_HELPS'
    return 'BEATS_FIXED_ONLY' if p1 else 'NOT_SHOWN'


def main(argv=None, registered=True, runner=real_runner, excluded=None, sizes=(TRAIN_PER, TEST_PER),
         search_budget=SEARCH_BUDGET, output=OUTPUT):
    """Run (or resume) the study; 0 when done, PAUSED at the end of a time slice. A design test may redirect the
    output, shrink the sets and pass a fake runner while keeping registered=True (B20_R141's lesson)."""
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        raise SystemExit(__doc__.splitlines()[4])
    out = Path(argv[0]).resolve()
    if registered and out != Path(output).resolve():
        raise SystemExit(f'the registered output is {output}')
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    from genesis.candidate_kinds import mcx3 as K3
    from genesis.senses import graph as SG
    from genesis.senses import synthesis as SY
    ex = excluded if excluded is not None else excluded_identities()
    G = graphs(ex, *sizes)
    eng, cand_ok = engines()
    lab = Lab(out / 'runs.jsonl', runner, deadline=t0 + SLICE_S)
    try:
        names, Mtr = score_matrix(lab, eng, G['train'])
        spath = out / 'search.json'
        if spath.exists():
            sr = json.loads(spath.read_text())
        else:
            ctx = [SG.Context(as_graph(t)) for _, t in G['train']]
            r = SY.synthesise(ctx, Mtr, search_budget, seed=0)
            fs = SY.folds(len(Mtr), SY.FOLDS, 0)
            hand_cv = [SY.cv_value(SY.values(h, ctx), Mtr, fs) for h in HAND]
            hand = HAND[int(np.argmax(hand_cv))]
            sense_theta, _ = SY.stump(SY.values(r['sense'], ctx), Mtr)
            hand_theta, _ = SY.stump(SY.values(hand, ctx), Mtr)
            fixed = int(np.argmax(Mtr.mean(0)))
            sr = {'sense': r['sense'], 'cv_value': r['value'], 'cv_baseline': r['baseline'], 'cv_oracle': r['oracle'],
                  'evaluated': r['evaluated'], 'charges': r['charges'], 'hand': hand, 'hand_cv': hand_cv,
                  'sense_theta': list(sense_theta), 'hand_theta': list(hand_theta), 'fixed': fixed, 'names': names}
            spath.write_text(json.dumps(sr, indent=1, sort_keys=True, default=float) + '\n')
        rows = []
        for fam, t in G['test']:
            sv, scpu = lab.sense('sense', sr['sense'], t)
            hv, hcpu = lab.sense('hand', sr['hand'], t)
            cs = int(SY.act(tuple(sr['sense_theta']), np.array([sv]))[0])
            ch = int(SY.act(tuple(sr['hand_theta']), np.array([hv]))[0])
            s_sense, b_sense = chosen_score(lab, eng, names, cs, t, scpu, 'sense')
            s_hand, b_hand = chosen_score(lab, eng, names, ch, t, hcpu, 'hand')
            full = score_matrix(lab, eng, [(fam, t)])[1][0]
            rows.append({'family': fam, 'task': t.task_id, 'SENSE': s_sense, 'HAND': s_hand,
                         'FIXED': float(full[sr['fixed']]), 'ORACLE': float(full.max()), 'choice_sense': names[cs],
                         'choice_hand': names[ch], 'budget_sense': b_sense, 'budget_hand': b_hand,
                         'cpu_sense': scpu, 'cpu_hand': hcpu})
    except Paused:
        return PAUSED
    col = lambda a: [r[a] for r in rows]                                   # noqa: E731
    t1 = wilcoxon([a - b for a, b in zip(col('SENSE'), col('FIXED'))], 'greater')
    t2 = wilcoxon([a - b for a, b in zip(col('SENSE'), col('HAND'))], 'greater')
    adj = holm({'P1': t1['p'], 'P2': t2['p']})
    t1['p_holm'], t2['p_holm'] = adj['P1'], adj['P2']
    p1 = t1['p_holm'] < ALPHA and t1['mean'] >= MATERIAL
    p2 = t2['p_holm'] < ALPHA and t2['mean'] >= MATERIAL
    fams = [f for f, _ in FAMILIES]
    s3 = {f: {a: statistics.mean(r[a] for r in rows if r['family'] == f) for a in ('SENSE', 'HAND', 'FIXED', 'ORACLE')}
          for f in fams}
    for f in fams:
        s3[f]['C0_1_by_sense'] = sum(r['choice_sense'] == CANDIDATE for r in rows if r['family'] == f)
        s3[f]['C0_1_by_hand'] = sum(r['choice_hand'] == CANDIDATE for r in rows if r['family'] == f)
    full_cpus = [r['cpu'] for k, r in lab.cache.items() if k.startswith('run|') and k.endswith('|1')]
    cpu_ok = not full_cpus or statistics.median(full_cpus) >= 0.9 * BUDGET
    from genesis.domains import adapter
    A = adapter('maxcut_v1')
    ids = {k: {A.exposure_identity(t)['canonical'] for _, t in v} for k, v in G.items()}
    disjoint = not (ids['train'] & ids['test']) and not any(ids[k] & ex for k in ids)
    pins = {'mcx3': K3.BINARY_SHA256 == MCX3_SHA256 and K3.binary_digest() == MCX3_SHA256,
            'feedback': file_digest(ROOT / 'src/genesis/autonomy/feedback.py') == PROTECTED_FEEDBACK_SHA256,
            'r151_summary': file_digest(R151_DIR / 'summary.json') == R151_SUMMARY_SHA256, 'candidate_key': cand_ok}
    valid = cpu_ok and disjoint and all(pins.values())
    v = verdict(valid, p1, p2)
    summary = {'study': STUDY, 'schema': 'genesis-b20r136-sense-choice-v1', 'verdict': v, 'valid': valid,
               'validity': {'cpu': cpu_ok, 'disjoint': disjoint, **pins},
               'P1': dict(t1, passed=p1), 'P2': dict(t2, passed=p2),
               'S1': {a: statistics.mean(col(a)) for a in ('SENSE', 'HAND', 'FIXED', 'ORACLE')},
               'S2': sr, 'S3': s3,
               'S4': {'cpu_sense_median': statistics.median(col('cpu_sense')),
                      'cpu_hand_median': statistics.median(col('cpu_hand')),
                      'budget_sense_min': min(col('budget_sense')), 'budget_hand_min': min(col('budget_hand'))},
               'S5': wilcoxon([a - b for a, b in zip(col('HAND'), col('FIXED'))], 'greater'),
               'rows': rows, 'graphs': {k: [t.task_id for _, t in v] for k, v in G.items()},
               'code_identity': code_identity(ROOT)['sha256'], 'status': 'DEV; licenses nothing'}
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True, default=float) + '\n')
    print(json.dumps({k: summary[k] for k in ('verdict', 'valid', 'P1', 'P2', 'S1')}, indent=1, default=float))
    return 0


if __name__ == '__main__':
    sys.exit(main())
