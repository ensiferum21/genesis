#!/usr/bin/env python3
"""B20_R152: does Genesis's engine language grow itself into a better one? (DEV, preregistered)

    taskset -c 0 python3 scripts/b20r152_self_extension.py evidence/self_extension_b20r152     run ALONE (resumable; slices exit 3)

**Why.** Daniel, 27 Oct 2026, 14:33: "ARA diagnoses the obstacle -> Genesis invents a structural repair -> the
independent Judge verifies it -> the Consolidator preserves it -> Genesis resumes research with the improved workflow
... They should improve on themselves as in expressiveness wise and richness" (`docs/OMEGA_EXPRESSIVE_LANGUAGE.md`
§5). X2 (B20_R154) built the pipeline and showed it compounding in a planted world. This study runs it on real
engines: Genesis grows the language from its own engines, generation after generation, every statement decided by
the sealed language judge, and the grown language is then tested on graphs nothing has seen.

**Domain.** Max-cut on planar2000 (planar2 and planar2_pm1, n 2,000, density 0.99), the only class with headroom at
1 s in B20_R151's gate (REX at 10 s +0.572% on 12 fresh graphs, p 0.00024); the pinned mcx3 binary at 1 s; Λ1 (the
builder's construct algebra, mcx3) with named statements; the bound 32 items. Fresh graphs from SEED, Gset excluded,
every set disjoint from the others and from B20_R151's.

**Generations** k = 1, 2, 3 of `expressive.pipeline.generation` (the language judge's claim 'search'):
  1. Genesis's dev searches: DEV_SEARCHES = 4 inventor searches (`feedback.steady_state_search`, contract off, 240
     evaluations of 4 dev graphs, `expressive.operators.ops('L1', library_k-1)`), seeded with REX and the previous
     generation's engines (rewritten in its language); the corpus is the 5 best distinct engines of each search by
     their mean dev score (up to 20), best first;
  2. `expressive.library.learn` proposes one statement at a time; each goes to the language judge (`expressive.judge`,
     kernel side, pinned): parent Λ1 + library_k-1, candidate + the statement, control + a random statement of the
     same size; 3 replicates of the inventor search at half the inventor's budget (120 evaluations of 4 training
     graphs) from the corpus; 24 sealed truth graphs; admitted only if the candidate beats the parent and the control
     over the graphs and over the replicates (exact permutation, p = 1/20 only if every candidate search beats every
     other one). Up to 2 proposals per generation; refused ones are excluded and the next is proposed;
  3. the admitted statements make library_k; the corpus rewritten in it seeds generation k + 1.
A generation that admits nothing ends the line (the queue's stagnation rule). The decisions are consolidated into a
fresh vault at the end (`expressive.consolidate`), so that replays after a pause write nothing twice.

**Confirmation (primary).** If anything was admitted, the grown language L* = Λ1 + library_K is tested against Λ1
(no library) and against Λ1 + a RANDOM library of as many statements of the same lengths (drawn from SEED), by the
inventor at its full budget (240 evaluations of 4 graphs), from REX alone (so the seeds Genesis accumulated play no
part), 5 replicates per language on fresh confirmation graphs (4 per replicate), every winner on the study's own 24
fresh truth graphs, two runs each. **P1:** per truth graph, L*'s mean gain over its replicates minus Λ1's, and minus
the random library's: SELF_EXTENSION_HELPS if both one-sided Wilcoxon signed-rank tests give p < 0.05 with means of
at least MATERIAL (0.05%), and both exact permutation tests of the replicates' means (5 against 5, 252 relabellings)
give p <= 0.05. (Five replicates, not the judge's three: with three, the permutation test passes only if every one
of nine pairings goes the same way, and a stub-engine rehearsal of this script failed a large effect, 4.7% against
2.1%, on one overlap; five keep a lucky search from passing and let a real effect through.)

**Secondary.**
  * S1: per generation, what was proposed, admitted and refused (the judge's verdicts and, from its ledger, its
    lanes), and whether a statement of a later generation calls an earlier one (compounding);
  * S2: reuse, the share of each generation's corpus engines that call library statements;
  * S3: the trend of Genesis's own output, each generation's best dev engine (k = 0 is REX) on the truth graphs, by
    Page's test (graphs as blocks; generations ordered); this reading includes the accumulated seeds, not the
    language alone;
  * S4: P1's two comparisons apart, and each lane against REX.
**Validity:** the median CPU of the runs at least 0.9 of the budget; every search spent its budget; the pins (mcx3,
the language judge, the protected judge) and the code digests in the judge's ledger are the ones at
preregistration; the graph sets are disjoint. **Verdict:** INVALID; else NOTHING_ADMITTED if generation 1 admits
nothing; else SELF_EXTENSION_HELPS if P1 holds; else NOT_SHOWN.

**What this is not.** An admission is a search claim (the statement helps the inventor find better engines at the
bound); it does not say the language can express more. An expressiveness test of Genesis's statements needs the
ceiling search (about 11 h per submission, B20_R154) and is a later study. The builder's construct algebra is in
every arm; any gain here is from the statements Genesis abstracted, which the judge admitted, and is Genesis's.

**Prior art (none claimed).** Library learning by compression: DreamCoder (Ellis et al. 2021), Stitch (Bowers et
al. 2023); module acquisition in genetic programming (Angeline and Pollack 1993); automatically defined functions
(Koza 1994).

**Expectation, stated before running (low confidence).** The learner finds a few recurring fragments (operator runs
with their arguments); the judge admits at most one, in generation 1, and nothing in generation 2: NOTHING_ADMITTED
or NOT_SHOWN. A gain, if any, of about 0.05-0.15%.

**Development looks (disclosed).** None on study data: the design was rehearsed end to end with stub engines only
(`tests_genesis/test_self_extension_study.py`). While it was being written, one line of B20_R151's progress log was
seen (its first Λ0 inventor search's winner and that search's own training score); nothing here uses it. The domain
choice uses B20_R151's gate, which was complete.

**Cost.** Per generation: dev searches about 1.1 h; the first submission about 1.4 h, a second about 0.95 h (the
parent's searches are shared): at most about 3.5 h, three generations at most 10.5 h; confirmation about 4.3 h; at
most about 15 h, in slices of 6,600 s. **Status.** DEV; licenses nothing; adopts nothing.
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

STUDY = 'b20r152'
SEED = 20521521
FAMILIES = (('planar2', {'n': 2000, 'density': 0.99}), ('planar2_pm1', {'n': 2000, 'density': 0.99}))
DEV_GRAPHS, CONFIRM_GRAPHS, T_GRAPHS, T_RUNS = 8, 20, 24, 2
GENERATIONS, DEV_SEARCHES, TOP_PER_SEARCH = 3, 4, 5
MAX_NEW, MAX_TRIES = 2, 2
INV_EVALS, INV_SIZE, BUDGET = 240, 4, 1.0
JUDGE_SCALE, JUDGE_REPLICATES, JUDGE_TRAIN, JUDGE_TRUTH = 0.5, 3, 8, 24
CONFIRM_REPS = 5
BOUND = 32
MATERIAL, ALPHA = 0.0005, 0.05
PROTECTED_FEEDBACK_SHA256 = '2ff4a5ab1e5b445b9144afbcc43596b8b1701ae541e8916c73e45009c0e3bdd6'
MCX3_SHA256 = '9449f8b669506b159dff56c7d6d1c1276859d0fa83852b04c805086999dcbd24'
LANGUAGE_JUDGE_SHA256 = '8390b1998e4dcb91ff282b955d1940cda3508d9be99cd384ad150d21188d5d05'
SLICE_S, PAUSED = 6600, 3


class Paused(Exception):
    pass


def h(*parts):
    return int(hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()[:12], 16)


# ----------------------------------------------------------------------------------------------- graphs and runs

def r151_identities():
    """The canonical identities of B20_R151's graphs, to keep this study's apart."""
    import b20r151_expressiveness as R151
    from genesis.domains import adapter
    A = adapter('maxcut_v1')
    G = R151.graphs(set())
    return {A.exposure_identity(t)['canonical'] for c in G for t in G[c]['H'] + G[c]['T'] + sum(G[c]['A'], [])}


def study_graphs(excluded):
    """{'dev': [task], 'confirm': [task], 'truth': [task]}: fresh, disjoint, from SEED."""
    from genesis.domains import adapter
    A = adapter('maxcut_v1')
    seen, out = set(excluded), {}
    for k, (split, n) in enumerate((('dev', DEV_GRAPHS), ('confirm', CONFIRM_GRAPHS), ('truth', T_GRAPHS))):
        out[split] = []
        for i in range(n):
            fam, params = FAMILIES[i % len(FAMILIES)]
            got, seen, _ = A.generate(SEED + 1000 * k + i, 1, 'DEV', fam, params, excluded=seen)
            out[split].append(got[0])
    return out, seen


def real_runner(cfg, task, seed, budget):
    from genesis.candidate_kinds import mcx3 as K3
    from genesis.models_maxcut import MaxCutCandidateView
    r0 = resource.getrusage(resource.RUSAGE_CHILDREN)
    v = K3.solve(MaxCutCandidateView(n=task.n, edges=task.edges), {'cpu_seconds': budget, 'config': cfg}, budget,
                 seed)['value']
    r1 = resource.getrusage(resource.RUSAGE_CHILDREN)
    return v, (r1.ru_utime + r1.ru_stime) - (r0.ru_utime + r0.ru_stime)


class Lab:
    """The study's runs (dev searches, confirmation, truth), cached by (engine, graph, occurrence) in runs.jsonl."""

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

    def run(self, cfg, task, occ):
        ek = self.ekey(cfg)
        self.programs.setdefault(ek, cfg)
        k = f'{ek}|{task.task_id}|{occ}|{BUDGET:g}'
        if k not in self.cache:
            if self.deadline is not None and time.monotonic() > self.deadline:
                raise Paused
            seed = h(STUDY, ek, task.task_id, occ) % (1 << 62)
            v, cpu = self.runner(cfg, task, seed, BUDGET)
            self.cache[k] = {'key': k, 'value': v, 'cpu': round(cpu, 4)}
            if self.path is not None:
                with open(self.path, 'a') as f:
                    f.write(json.dumps(self.cache[k], sort_keys=True) + '\n')
        return self.cache[k]['value']

    def ref(self, task):
        from genesis.candidate_kinds import mcx3 as K3
        return self.run(K3.DEFAULT, task, 'ref')


def search(lab, library, tasks, seed, starts, log=None):
    """One inventor search in Λ1 + library from `starts`: (winner genome, report, {engine: (genome, mean score)})."""
    from genesis.autonomy import feedback as FB
    from genesis.autonomy import selfimprove as SI
    from genesis.expressive import lambda1 as L1
    from genesis.expressive import operators as O
    occ, scores, genomes = {}, {}, {}

    def ev(genome, split):
        cfg = L1.config(genome, library)
        ek = Lab.ekey(cfg)
        n = occ.get(ek, 0)
        occ[ek] = n + 1
        v = statistics.mean(lab.run(cfg, t, n) / lab.ref(t) for t in tasks)
        scores.setdefault(ek, []).append(v)
        genomes.setdefault(ek, dict(genome))
        if log is not None:
            log.append({'engine': ek, 'value': v})
        return v
    ops = SI.seeded_ops(O.ops('L1', library, bound=BOUND), [dict(s) for s in starts])
    winner, report = FB.steady_state_search(ops, ev, INV_EVALS, seed, contract=False)
    return winner, report, {e: (genomes[e], statistics.mean(v)) for e, v in scores.items()}


def dev_searcher(lab, graphs, reports):
    """The research plane's corpus maker for `pipeline.generation`: DEV_SEARCHES searches, the TOP_PER_SEARCH best
    distinct engines of each, best first."""
    from genesis.candidate_kinds import mcx3 as K3
    state = {'k': 0, 'seeds': []}

    def make(library):
        state['k'] += 1
        starts = [dict(K3.DEFAULT)] + list(state['seeds'])
        pool = {}
        for i in range(DEV_SEARCHES):
            tasks = graphs['dev'][(4 * i) % DEV_GRAPHS:(4 * i) % DEV_GRAPHS + 4]
            w, rep, sc = search(lab, library, tasks, h(STUDY, 'dev', state['k'], i), starts)
            reports.append(dict(rep, generation=state['k'], search=i))
            for e, (g, v) in sorted(sc.items(), key=lambda kv: (-kv[1][1], kv[0]))[:TOP_PER_SEARCH]:
                if e not in pool or v > pool[e][1]:
                    pool[e] = (g, v)
        return [g for e, (g, v) in sorted(pool.items(), key=lambda kv: (-kv[1][1], kv[0]))]
    return make, state


def random_library(grown, seed):
    """As many random statements as `grown` has, each with as many items as its counterpart (no parameters)."""
    import random
    from genesis.candidate_kinds import mcx3 as K3
    from genesis.expressive import lambda1 as L1
    from genesis.expressive import operators as O
    rng = random.Random(seed)
    lib = L1.EMPTY
    for i, d in enumerate(grown.defs):
        size = L1.length(K3.parse(d['body'], calls=True, params=True))
        for _ in range(1000):
            items = [O.random_stmt(rng, 'L1', guards=(j < size - 1)) for j in range(size)]
            try:
                body = K3.render(K3.canonical(tuple(O._freeze(x) for x in items)))
                if L1.length(K3.parse(body)) != size:
                    continue
                lib = lib.extend(f'rnd{i}', body, provenance={'control': True})
                break
            except ValueError:
                continue
    return lib


# ------------------------------------------------------------------------------------------------------ statistics

def wilcoxon(diffs, alternative='greater'):
    from scipy.stats import wilcoxon as W
    d = [x for x in diffs if x != 0]
    if not d:
        return {'n': 0, 'p': 1.0, 'mean': statistics.mean(diffs) if diffs else 0.0}
    return {'n': len(d), 'p': float(W(d, alternative=alternative).pvalue), 'mean': statistics.mean(diffs)}


def replicate_test(a, b):
    from itertools import combinations
    pool, k = list(a) + list(b), len(a)
    obs = statistics.mean(a) - statistics.mean(b)
    hits = total = 0
    for idx in combinations(range(len(pool)), k):
        x = [pool[i] for i in idx]
        y = [pool[i] for i in range(len(pool)) if i not in idx]
        total += 1
        hits += statistics.mean(x) - statistics.mean(y) >= obs - 1e-15
    return hits / total


def page_test(rows):
    """Page's L test for an increasing trend across the columns (rows: blocks), normal approximation (one-sided)."""
    from scipy.stats import norm
    k, n = len(rows[0]), len(rows)
    if k < 3 or n < 2:
        return {'L': None, 'p': 1.0, 'k': k, 'n': n}
    ranks = []
    for r in rows:
        order = sorted(range(k), key=lambda j: r[j])
        rk = [0.0] * k
        i = 0
        while i < k:
            j = i
            while j + 1 < k and r[order[j + 1]] == r[order[i]]:
                j += 1
            for m in range(i, j + 1):
                rk[order[m]] = (i + j) / 2 + 1
            i = j + 1
        ranks.append(rk)
    L = sum((j + 1) * sum(r[j] for r in ranks) for j in range(k))
    mu = n * k * (k + 1) ** 2 / 4
    var = n * k ** 2 * (k + 1) * (k ** 2 - 1) / 144
    z = (L - mu) / var ** 0.5
    return {'L': L, 'z': z, 'p': float(1 - norm.cdf(z)), 'k': k, 'n': n}


def compare(a_lane, b_lane, a_reps, b_reps):
    w = wilcoxon([x - y for x, y in zip(a_lane, b_lane)])
    return dict(w, replicates=replicate_test(a_reps, b_reps))


def p1(confirm):
    """confirm: {lang: {'lane': per-graph mean gains, 'reps': replicate means}} for 'grown', 'none', 'random'."""
    g = confirm['grown']
    out = {o: compare(g['lane'], confirm[o]['lane'], g['reps'], confirm[o]['reps']) for o in ('none', 'random')}
    out['holds'] = all(t['p'] < ALPHA and t['mean'] >= MATERIAL and t['replicates'] <= ALPHA
                       for t in (out['none'], out['random']))
    return out


def verdict(valid, admitted_gen1, p1_result):
    if not valid:
        return 'INVALID'
    if not admitted_gen1:
        return 'NOTHING_ADMITTED'
    return 'SELF_EXTENSION_HELPS' if p1_result and p1_result['holds'] else 'NOT_SHOWN'


def file_digest(path):
    p = Path(path)
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


# ----------------------------------------------------------------------------------------------------------- main

def main(argv=None, runner=real_runner, registered=True, exclude_r151=True):
    """Run (or resume) the study; 0 when done, PAUSED at the end of a time slice."""
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        raise SystemExit(__doc__.splitlines()[2])
    out = Path(argv[0]).resolve()
    if registered and out != (ROOT / 'evidence' / 'self_extension_b20r152').resolve():
        raise SystemExit('the registered output is evidence/self_extension_b20r152')
    out.mkdir(parents=True, exist_ok=True)
    import b20r33_strong_baseline_audit as R33
    cpu = R33.pinned_core() if registered else None
    t0 = time.monotonic()
    with (out / 'run.log').open('a') as logf:
        return _study(out, logf, t0, cpu, runner, registered, exclude_r151)


def _study(out, logf, t0, cpu, runner, registered, exclude_r151):
    from genesis import gset as GS
    from genesis import vault as V
    from genesis.candidate_kinds import mcx3 as K3
    from genesis.domains import adapter
    from genesis.expressive import consolidate as C
    from genesis.expressive import judge as J
    from genesis.expressive import lambda1 as L1
    from genesis.expressive import maxcut_domain as MD
    from genesis.expressive import pipeline as P

    def log(m):
        line = f'[{time.monotonic() - t0:7.1f}s] {m}'
        print(line, flush=True)
        logf.write(line + '\n')
        logf.flush()
    log(f'{STUDY}; pinned to CPU {cpu}')
    A = adapter('maxcut_v1')
    excluded = {A.exposure_identity(t)['canonical'] for t in GS.tasks()}
    if exclude_r151:
        excluded |= r151_identities()
    G, seen = study_graphs(excluded)
    deadline = t0 + SLICE_S
    lab = Lab(out / 'runs.jsonl', runner=runner, deadline=deadline)
    domain = MD.MaxCutDomain(FAMILIES, exclude=seen, budget=BUDGET, cache=out / 'judge_runs.jsonl',
                             deadline=deadline, search_scale=JUDGE_SCALE, bound=BOUND,
                             runner=None if runner is real_runner else runner)
    judge = J.LanguageJudge(domain, sealed_seed=h(STUDY, 'judge'), replicates=JUDGE_REPLICATES, train=JUDGE_TRAIN,
                            truth=JUDGE_TRUTH)
    ids = [A.exposure_identity(t)['canonical'] for s in G for t in G[s]] + \
        [A.exposure_identity(t)['canonical'] for t in domain.drawn()]
    disjoint = len(ids) == len(set(ids)) and not set(ids) & excluded
    reports, gens = [], []
    library = L1.EMPTY
    make, state = dev_searcher(lab, G, reports)
    try:
        for k in range(1, GENERATIONS + 1):
            g = P.generation(k, library, make, judge.submit, claim='search', max_new=MAX_NEW, max_tries=MAX_TRIES)
            gens.append(g)
            log(f"generation {k}: proposed {[(d['name'], d['body']) for d in g['decisions']]}; admitted {g['admitted']}")
            if not g['admitted']:
                break
            library = g['library']
            state['seeds'] = [s for s in g['seeds']]
        # each generation's best dev engine (its corpus's first), and REX, on the truth graphs
        tg = {t.task_id: t for t in G['truth']}
        base = {t: statistics.mean(lab.run(K3.DEFAULT, tg[t], o) for o in range(T_RUNS)) for t in tg}

        def truth_gains(cfg):
            return [(statistics.mean(lab.run(cfg, tg[t], o) for o in range(T_RUNS)) - base[t]) / base[t]
                    for t in sorted(tg)]
        best = [dict(K3.DEFAULT)] + [L1.config(x['seeds'][0], x['library']) for x in gens if x['seeds']]
        trend_rows = list(zip(*[truth_gains(c) for c in best]))
        log('the generations\' best engines on the truth graphs done')
        confirm = None
        grown = gens[-1]['library'] if gens else L1.EMPTY            # the language at the end of the line
        if len(grown):
            rnd = random_library(grown, h(STUDY, 'random library'))
            confirm = {}
            for name, lib in (('none', L1.EMPTY), ('grown', grown), ('random', rnd)):
                lanes = []
                for r in range(CONFIRM_REPS):
                    tasks = G['confirm'][4 * r:4 * r + 4]
                    w, rep, _ = search(lab, lib, tasks, h(STUDY, 'confirm', r), [dict(K3.DEFAULT)])
                    reports.append(dict(rep, confirm=name, replicate=r))
                    lanes.append(truth_gains(L1.config(w, lib)))
                    log(f"confirmation {name} {r}: {L1.config(w, lib)['prog']!r}")
                confirm[name] = {'lane': [statistics.mean(x) for x in zip(*lanes)],
                                 'reps': [statistics.mean(x) for x in lanes], 'library': lib.to_json()}
    except (Paused, MD.Paused):
        log(f'time slice used ({SLICE_S} s): paused with {len(lab.cache)} study runs, {domain.runs()} judge runs')
        return PAUSED
    p1_result = p1(confirm) if confirm else None
    # the vault, built once from the decisions
    vdir = out / 'vault'
    if not (vdir / '.complete').exists():
        import shutil
        shutil.rmtree(vdir, ignore_errors=True)
        with V.Vault(vdir) as vault:
            lib = L1.EMPTY
            led = judge.ledger()
            n = 0
            for x in gens:
                for d in x['decisions']:
                    n += 1
                    cand = lib.extend(d['name'], d['body'], provenance=d['step'])
                    C.consolidate(vault, lib, cand, [d['name']], {'admitted': d['admitted'], 'failed': d['failed'],
                                                                  'claim': 'search'}, ledger_entry=n,
                                  budget=BUDGET)
                    if d['admitted']:
                        lib = cand
        (vdir / '.complete').write_text('ok\n')
    led = judge.ledger()
    cpus = [r['cpu'] for r in lab.cache.values()] + domain.cpu_values()
    med = statistics.median(cpus) / BUDGET if cpus else 1.0
    spent = all(r['evaluations'] >= INV_EVALS for r in reports)
    pins = {'protected_judge': file_digest(ROOT / 'src/genesis/autonomy/feedback.py') == PROTECTED_FEEDBACK_SHA256,
            'language_judge': file_digest(ROOT / 'src/genesis/expressive/judge.py') == LANGUAGE_JUDGE_SHA256,
            'mcx3': K3.BINARY_SHA256 == MCX3_SHA256 and (not registered or K3.binary_digest() == MCX3_SHA256),
            'judge_code': all(r['code'] == J.code_digests() for r in led)}
    valid = med >= 0.9 and spent and disjoint and all(pins.values())
    admitted1 = bool(gens and gens[0]['admitted'])
    v = verdict(valid, admitted1, p1_result)
    compounding = [n for x in gens[1:] for n in x['admitted']
                   if any(y[0] == 'call' for y in K3.walk(K3.parse(x['library'].get(n)['body'], calls=True)))]
    reuse = [sum(1 for s in x['seeds'] if any(y[0] == 'call' for y in K3.walk(K3.parse(s['prog'], calls=True))))
             / max(1, len(x['seeds'])) for x in gens]
    summary = {
        'study': STUDY, 'schema': 'genesis-b20r152-self-extension-v1', 'verdict': v, 'valid': valid,
        'generations': [{'k': x['generation'], 'parent': x['parent'], 'decisions': x['decisions'],
                         'admitted': x['admitted'], 'library': x['library'].to_json()} for x in gens],
        'judge_ledger': led, 'P1': p1_result, 'confirm': confirm, 'compounding': compounding, 'reuse': reuse,
        'trend': {'best': [c['prog'] for c in best], 'page': page_test(trend_rows) if trend_rows else None,
                  'means': [statistics.mean(c) for c in zip(*trend_rows)] if trend_rows else []},
        'cpu_median': med, 'spent': spent, 'disjoint': disjoint, 'pins': pins,
        'graphs': {s: [t.task_id for t in G[s]] for s in G}, 'reports': reports,
        'code_identity': code_identity(ROOT)['sha256'], 'status': 'DEV; licenses nothing'}
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True, default=str) + '\n')
    log(f'valid {valid}; verdict {v}; admitted {[x["admitted"] for x in gens]}; P1 {p1_result}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
