#!/usr/bin/env python3
"""B20_R174: does Genesis's search beat random sampling of the same language? The control that B20_R173's release
lacks, on ±1-weighted planar graphs (DEV, preregistered)

    taskset -c 0 python3 scripts/b20r174_search_vs_random.py evidence/search_vs_random_b20r174   run ALONE (resumable; slices exit 3)

**Why.** B20_R173 recorded the protected judge releasing C0_1, an engine from B20_R151's search, over the builder's
REX on ±1-weighted planar graphs. Its amended record (`docs/checkpoints/B20_R173_RECORD.md`, "Against random
engines") shows that REX is weak there: of the judge's 47 random calibration engines from the same language (L0), 7
cleared the same release bar, and the best came within 0.05% of C0_1 on the judge's split. So the release is
evidence about the builder's language and the judge, not that Genesis's search finds anything random sampling would
not. This study asks that question directly, at matched evaluations, on fresh graphs.

**The search arm (fixed; nothing is re-run).** B20_R151's three Λ0 ceiling winners on planar2000, C0_0, C0_1 and
C0_2, read from its committed evidence with their recorded keys. Each is the winner of `selfimprove.search` with the
ceiling process (population 32, children 16, leaders 4, tournament 3, crossover 0.25), its initial population REX and
then random L0 engines (`expressive.operators.ops('L0', bound=32)`), over 480 evaluations of 8 planar2000 graphs at
1 s (planar2 and planar2_pm1 alternating), its winner the best of 4 finalists re-evaluated 4 times: 496 evaluations
of 8 graphs.

**The random arm (run here).** RANDOM_r, r = 0, 1, 2. REX first, then distinct engines drawn by the same operators'
`random` (the generator of the search's initial population, at the same description bound), each evaluated once on a
fresh split A_r of 8 planar2000 graphs (planar2 and planar2_pm1 alternating, as B20_R151's), until 480 evaluations.
Its 4 best by that score are then re-evaluated 4 times each, and the best mean wins (ties: the shorter program, then
the key), which is the search's own final rule. That is 496 evaluations of 8 graphs, matched. An evaluation is B20_R151's: the mean over the split
of cut / reference, the reference REX at 1 s with a fixed seed, a run's seed a hash of (study, engine, graph,
occurrence).

**Graphs (fresh).** Generated from SEED, disjoint by canonical identity from Gset, from every graph of B20_R151,
B20_R152, B20_R165, B20_R173 and B20_R136, and from each other: A_0, A_1, A_2 (8 each), T (24 planar2_pm1 graphs,
the primary truth set) and T2 (12 planar2 graphs, secondary).

**Truth.** Every winner (three search, three random) and REX run twice per truth graph at 1 s. A winner's T-gain on a
graph is (its mean cut - REX's mean cut) / REX's mean cut, as in B20_R151.

**Primary.** P1, on T: per graph, the mean T-gain of the three search winners minus that of the three random winners;
a one-sided Wilcoxon signed-rank test (search > random); and over the replicates, the exact one-sided permutation
test of the six winners' mean T-gains (the search's three against the random three; p = 1/20 when every search
winner beats every random winner). SEARCH_BEATS_RANDOM if the Wilcoxon p < 0.05, the mean difference is at least
MATERIAL (0.1%), and the permutation p <= 0.05.
**Verdict:** INVALID if validity fails; SEARCH_BEATS_RANDOM if P1 holds; otherwise NOT_SHOWN, read as RANDOM_BETTER
if the two-sided Wilcoxon p < 0.05 with the mean at most -MATERIAL, RANDOM_MATCHES_SEARCH if |mean| < MATERIAL, and
UNRESOLVED otherwise.
**Secondary (reported; they decide nothing):**
  * S1: C0_1 (the released engine) against the best random winner (by T-gain on T), per graph, two-sided;
  * S2: each winner's mean T-gain on T and on T2, and each against REX, one-sided;
  * S3: the random arm's A scores: the share of random engines scoring above REX on A, and the finalists;
  * S4: P1's test on T2 (planar2, where B20_R165 found no gain over REX).
**Validity:**
  * the median CPU of the 1 s runs is at least 0.9 s;
  * the graph sets are pairwise disjoint and disjoint from everything excluded;
  * the three search winners hash to their recorded keys, and B20_R151's summary has its recorded digest;
  * every random arm made exactly 496 evaluations of 8 graphs, on Λ0 programs within the bound;
  * mcx3's pin and the protected judge's source are the ones at preregistration (the judge is not asked).

**Expectation, stated before running (moderate confidence).** NOT_SHOWN, read as RANDOM_MATCHES_SEARCH: on
B20_R173's split the best of 47 random engines came within 0.05% of C0_1, so the best of 480 random engines, chosen
the way the search chooses, should come within the material margin of the search winners on ±1 planar graphs. S1:
C0_1 within ±0.2% of the best random winner. S4: everything near REX on planar2.

**Development looks (disclosed).** None on these graphs. B20_R173's calibration calls (read in full when its record
was amended, 30 Oct 2026) motivate the study. B20_R151, B20_R165 and B20_R173 were read in full when recorded.

**Cost.** The random arm: 3 x 496 x 8 graph-seconds (about 3.3 h); the truth: 7 engines x 36 graphs x 2 runs (about
8.5 min); recomputing the exclusions takes about 2 min at the start of each slice. About 3.5 h, in slices of 6,600 s.
**Status.** DEV; licenses nothing.
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

STUDY = 'b20r174'
OUTPUT = ROOT / 'evidence' / 'search_vs_random_b20r174'
SEED = 20571741
R151_DIR = ROOT / 'evidence' / 'expressiveness_b20r151'
R151_SUMMARY_SHA256 = 'd021b145c395fa410c619c94ba5bfee1a1ab34a715c591148ba11fc5d6dd93df'
SEARCH_WINNERS = ('C0_0', 'C0_1', 'C0_2')
PLANAR = (('planar2', {'n': 2000, 'density': 0.99}), ('planar2_pm1', {'n': 2000, 'density': 0.99}))
REPS, A_SIZE, EVALS, FINALISTS, FINAL_EVALS, BOUND = 3, 8, 480, 4, 4, 32
T_SIZE, T2_SIZE, T_RUNS, BUDGET = 24, 12, 2, 1.0
MATERIAL, ALPHA = 0.001, 0.05
PROTECTED_FEEDBACK_SHA256 = '2ff4a5ab1e5b445b9144afbcc43596b8b1701ae541e8916c73e45009c0e3bdd6'
MCX3_SHA256 = '9449f8b669506b159dff56c7d6d1c1276859d0fa83852b04c805086999dcbd24'
SLICE_S, PAUSED = 6600, 3


class Paused(Exception):
    pass


def file_digest(path):
    p = Path(path)
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


# ------------------------------------------------------------------------------------------- engines and graphs

def search_winners(r151_dir=R151_DIR):
    """{name: config} of B20_R151's three Λ0 ceiling winners, and whether each hashes to its recorded key."""
    s = json.loads((Path(r151_dir) / 'summary.json').read_text())
    progs = json.loads((Path(r151_dir) / 'programs.json').read_text())
    out, ok = {}, True
    for name in SEARCH_WINNERS:
        key = s['arms']['planar2000'][name]
        out[name] = progs[key]
        ok = ok and digest(progs[key])[:16] == key
    return out, ok


def excluded_identities():
    import b20r136_sense_choice as R136
    from genesis.domains import adapter
    A = adapter('maxcut_v1')
    ex = R136.excluded_identities()
    g136 = R136.graphs(ex)
    return ex | {A.exposure_identity(t)['canonical'] for v in g136.values() for _, t in v}


def graphs(excluded, a_size=A_SIZE, t_size=T_SIZE, t2_size=T2_SIZE, reps=REPS):
    """{'A': [[task] per replicate], 'T': [task], 'T2': [task]}: fresh, disjoint, from SEED."""
    from genesis.domains import adapter
    A = adapter('maxcut_v1')
    seen, k = set(excluded), [0]

    def draw(fam, params):
        got, s2, _ = A.generate(SEED + k[0], 1, 'DEV', fam, params, excluded=seen)
        seen.update(s2)
        k[0] += 1
        return got[0]
    out = {'A': [[draw(*PLANAR[i % 2]) for i in range(a_size)] for _ in range(reps)]}
    out['T'] = [draw(*PLANAR[1]) for _ in range(t_size)]
    out['T2'] = [draw(*PLANAR[0]) for _ in range(t2_size)]
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
        self.cache, self.new = {}, 0
        if path is not None and Path(path).exists():
            for line in Path(path).read_text().splitlines():
                if line.strip():
                    r = json.loads(line)
                    self.cache[r['key']] = r

    def run(self, cfg, task, occ, budget=BUDGET):
        ek = digest(cfg)[:16]
        k = f'{ek}|{task.task_id}|{occ}|{budget:g}'
        if k not in self.cache:
            if self.new and self.deadline is not None and time.monotonic() > self.deadline:
                raise Paused                                     # every slice makes at least one new run
            v, cpu = self.runner(cfg, task, run_seed(ek, task.task_id, occ, budget), budget)
            self.new += 1
            self.cache[k] = {'key': k, 'value': v, 'cpu': round(cpu, 4)}
            if self.path is not None:
                with open(self.path, 'a') as f:
                    f.write(json.dumps(self.cache[k], sort_keys=True) + '\n')
        return self.cache[k]['value']

    def ref(self, task):
        from genesis.candidate_kinds import mcx3 as K3
        return self.run(K3.DEFAULT, task, 'ref')


# --------------------------------------------------------------------------------------------- the random arm

def random_arm(lab, tasks, seed, evals=EVALS):
    """REX, then distinct random L0 engines (the search's generator), each evaluated once on `tasks`, until `evals`
    evaluations; then the FINALISTS best re-evaluated FINAL_EVALS times; the best mean wins. Returns (winner config,
    record)."""
    from genesis.candidate_kinds import mcx3 as K3
    from genesis.expressive import lambda1 as L1
    from genesis.expressive import operators as O
    ops = O.ops('L0', bound=BOUND)
    rng = random.Random(seed)
    occ, n_eval = {}, [0]

    def ev(cfg):
        ek = digest(cfg)[:16]
        n = occ.get(ek, 0)
        occ[ek] = n + 1
        n_eval[0] += 1
        return statistics.mean(lab.run(cfg, t, n) / lab.ref(t) for t in tasks)
    entries, seen, first = [], set(), True
    while len(entries) < evals:
        genome = dict(K3.DEFAULT) if first else ops['random'](rng)
        first = False
        cfg = L1.config(genome)
        k = json.dumps(cfg, sort_keys=True)
        if k in seen:
            continue
        seen.add(k)
        if not K3.is_lambda0(K3.parse(cfg['prog'])) or ops['size'](genome) > BOUND:
            raise AssertionError(f'a program outside Λ0 or the bound: {cfg["prog"]}')
        entries.append({'cfg': cfg, 'key': digest(cfg)[:16], 'size': ops['size'](genome), 'scores': [ev(cfg)]})
    ranked = sorted(entries, key=lambda e: (-e['scores'][0], e['size'], e['key']))
    finals = []
    for e in ranked[:FINALISTS]:
        e['final'] = [ev(e['cfg']) for _ in range(FINAL_EVALS)]
        finals.append(e)
    best = max(finals, key=lambda e: (statistics.mean(e['final']), -e['size'], e['key']))
    rex = digest(dict(K3.DEFAULT))[:16]
    rex_score = next(e['scores'][0] for e in entries if e['key'] == rex)
    return best['cfg'], {'evaluations': n_eval[0], 'distinct': len(entries), 'winner': best['key'],
                         'winner_final': statistics.mean(best['final']),
                         'finalists': [{'key': e['key'], 'first': e['scores'][0], 'final': statistics.mean(e['final'])}
                                       for e in finals],
                         'above_rex': sum(e['scores'][0] > rex_score for e in entries if e['key'] != rex),
                         'rex_score': rex_score, 'scores': [round(e['scores'][0], 6) for e in entries]}


# --------------------------------------------------------------------------------------------- the analysis

def t_gains(lab, cfg, tasks):
    from genesis.candidate_kinds import mcx3 as K3
    rex = dict(K3.DEFAULT)
    out = []
    for t in tasks:
        b = statistics.mean(lab.run(rex, t, f'truth{o}') for o in range(T_RUNS))
        c = statistics.mean(lab.run(cfg, t, f'truth{o}') for o in range(T_RUNS))
        out.append((c - b) / b)
    return out


def wilcoxon(diffs, alternative):
    from scipy.stats import wilcoxon as W
    d = [x for x in diffs if x != 0]
    if not d:
        return {'n': 0, 'p': 1.0, 'mean': statistics.mean(diffs) if diffs else 0.0}
    return {'n': len(d), 'p': float(W(d, alternative=alternative).pvalue), 'mean': statistics.mean(diffs)}


def permutation(search_means, random_means):
    """Exact one-sided permutation p of mean(search) - mean(random) over the 20 splits of the six replicates."""
    from itertools import combinations
    allv = list(search_means) + list(random_means)
    obs = statistics.mean(search_means) - statistics.mean(random_means)
    n, hits = 0, 0
    for idx in combinations(range(len(allv)), len(search_means)):
        a = [allv[i] for i in idx]
        b = [allv[i] for i in range(len(allv)) if i not in idx]
        n += 1
        hits += statistics.mean(a) - statistics.mean(b) >= obs - 1e-15
    return hits / n


def analyse(gains, gains2):
    """gains: {winner name: [T-gain per T graph]}; the search's names are SEARCH_WINNERS, the random ones RANDOM_r."""
    rnd = [f'RANDOM_{r}' for r in range(REPS)]

    def diff(g):
        n = len(next(iter(g.values())))
        return [statistics.mean(g[s][i] for s in SEARCH_WINNERS) - statistics.mean(g[r][i] for r in rnd)
                for i in range(n)]
    d = diff(gains)
    one = wilcoxon(d, 'greater')
    two = wilcoxon(d, 'two-sided')
    perm = permutation([statistics.mean(gains[s]) for s in SEARCH_WINNERS], [statistics.mean(gains[r]) for r in rnd])
    p1 = one['p'] < ALPHA and one['mean'] >= MATERIAL and perm <= ALPHA
    if p1:
        reading = 'SEARCH_BEATS_RANDOM'
    elif two['p'] < ALPHA and two['mean'] <= -MATERIAL:
        reading = 'RANDOM_BETTER'
    elif abs(one['mean']) < MATERIAL:
        reading = 'RANDOM_MATCHES_SEARCH'
    else:
        reading = 'UNRESOLVED'
    best_r = max(rnd, key=lambda r: statistics.mean(gains[r]))
    s1 = wilcoxon([a - b for a, b in zip(gains['C0_1'], gains[best_r])], 'two-sided')
    s1['best_random'] = best_r
    s2 = {w: {'T': statistics.mean(gains[w]), 'T2': statistics.mean(gains2[w]),
              'vs_rex_T': wilcoxon(gains[w], 'greater')} for w in list(SEARCH_WINNERS) + rnd}
    d2 = diff(gains2)
    return {'P1': dict(one, permutation_p=perm, passed=p1, two_sided_p=two['p']), 'reading': reading, 'S1': s1,
            'S2': s2, 'S4': wilcoxon(d2, 'greater')}


def verdict(valid, res):
    if not valid:
        return 'INVALID'
    return 'SEARCH_BEATS_RANDOM' if res['P1']['passed'] else 'NOT_SHOWN'


# --------------------------------------------------------------------------------------------- main

def main(argv=None, registered=True, runner=real_runner, excluded=None, sizes=None, evals=EVALS, output=OUTPUT):
    """Run (or resume) the study; 0 when done, PAUSED at the end of a time slice. A design test may redirect the
    output, the runner, the exclusions, the set sizes and the evaluations while keeping registered=True (B20_R141's
    lesson)."""
    from genesis.candidate_kinds import mcx3 as K3
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        raise SystemExit(next(x for x in __doc__.splitlines() if 'taskset' in x).strip())
    out = Path(argv[0]).resolve()
    if registered and out != Path(output).resolve():
        raise SystemExit(f'the registered output is {output}')
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    excluded = excluded_identities() if excluded is None else excluded
    G = graphs(excluded, *(sizes or ()))
    winners, keys_ok = search_winners()
    lab = Lab(out / 'runs.jsonl', runner, t0 + SLICE_S)
    try:
        rand, records = {}, {}
        for r in range(REPS):
            seed = int(digest({'study': STUDY, 'random': r})[:12], 16)
            cfg, rec = random_arm(lab, G['A'][r], seed, evals)
            rand[f'RANDOM_{r}'], records[f'RANDOM_{r}'] = cfg, rec
        engines = dict(winners, **rand)
        gains = {w: t_gains(lab, cfg, G['T']) for w, cfg in engines.items()}
        gains2 = {w: t_gains(lab, cfg, G['T2']) for w, cfg in engines.items()}
    except Paused:
        return PAUSED
    from genesis.domains import adapter
    A = adapter('maxcut_v1')
    ids = [A.exposure_identity(t)['canonical'] for v in (G['A'] + [G['T'], G['T2']]) for t in v]
    disjoint = len(set(ids)) == len(ids) and not (set(ids) & set(excluded))
    one_s = [r['cpu'] for r in lab.cache.values() if r['key'].endswith('|1')]
    cpu_ok = bool(one_s) and statistics.median(one_s) >= 0.9 * BUDGET
    evals_ok = all(rec['evaluations'] == evals + FINALISTS * FINAL_EVALS for rec in records.values())
    validity = {'cpu': cpu_ok, 'disjoint': disjoint, 'winner_keys': keys_ok,
                'r151_summary': file_digest(R151_DIR / 'summary.json') == R151_SUMMARY_SHA256,
                'evaluations': evals_ok, 'mcx3': K3.BINARY_SHA256 == MCX3_SHA256,
                'feedback': file_digest(ROOT / 'src/genesis/autonomy/feedback.py') == PROTECTED_FEEDBACK_SHA256}
    valid = all(validity.values())
    res = analyse(gains, gains2)
    v = verdict(valid, res)
    summary = {'study': STUDY, 'schema': 'genesis-b20r174-search-vs-random-v1', 'verdict': v, 'valid': valid,
               'validity': validity, 'results': res, 'gains': gains, 'gains_T2': gains2,
               'S3': {w: {k: rec[k] for k in ('evaluations', 'distinct', 'winner', 'winner_final', 'finalists',
                                               'above_rex', 'rex_score')} for w, rec in records.items()},
               'random_scores': {w: rec['scores'] for w, rec in records.items()},
               'engines': engines,
               'graphs': {'A': [[t.task_id for t in a] for a in G['A']], 'T': [t.task_id for t in G['T']],
                          'T2': [t.task_id for t in G['T2']]},
               'code_identity': code_identity(ROOT)['sha256'], 'status': 'DEV; licenses nothing'}
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n')
    print(json.dumps({k: summary[k] for k in ('verdict', 'valid', 'validity')}, indent=1))
    print(json.dumps({k: res[k] for k in ('P1', 'reading', 'S1')}, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
