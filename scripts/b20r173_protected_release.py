#!/usr/bin/env python3
"""B20_R173: can the protected judge release Genesis's first confirmed engine gain? A release attempt on ±1-weighted
planar graphs (DEV, preregistered)

    taskset -c 0 python3 scripts/b20r173_protected_release.py evidence/protected_release_b20r173   run ALONE (resumable; slices exit 3)

**Why.** B20_R165 (`docs/checkpoints/B20_R165_RECORD.md`) replicated the first gain of Genesis's own engine searches
over the builder-configured REX on fresh graphs: on ±1-weighted planar graphs of 2,000 vertices at 1 s, the engines
of B20_R151's searches beat REX by 1.16% on every graph, and the pre-specified engine C0_1 by more. Its record names
the next step: "a release attempt through the protected judge on planar2_pm1, whose power at +1.2% should be far
better than at B20_R132's sizes". Nothing Genesis invented has ever been released by the protected judge
(`autonomy/feedback.py`, contract version 2, its source pinned and untouched): in B20_R127 and B20_R132 it released
nothing, and B20_R132 measured why (its threshold, calibrated on random engines, was 6-20 times what local noise
gives). This study asks the judge, by its own unchanged rules, about the one gain that has been confirmed twice.

**Graphs (fresh).** planar2_pm1 (n 2,000, density 0.99), generated from SEED, disjoint by canonical identity from
Gset and from every graph of B20_R151, B20_R152 and B20_R165: the judge's two confirmation splits B and C (SIZE = 12
graphs each) and a truth set T (24 graphs) that the judge never sees.

**Programs.** The incumbent is REX (mcx3's DEFAULT, "B100 X I S2000 C"). The candidate is C0_1, the engine
B20_R165 pre-specified (the highest training score of B20_R151's planar2000 searches), read from B20_R151's committed
evidence with its recorded key. **The judge's calibration programs follow the contract as a search applies it**
(`feedback.steady_state_search(contract=True)`): the initial population of the search that produced C0_1 (the
ceiling search of B20_R151's Λ0 lane: population 32, REX then random engines of `expressive.operators`'s 'L0'
language, seeded) and CALIBRATION_EXTRA (16) more random engines; that is REX and 47 random engines, drawn from SEED.

**Runs.** The pinned mcx3 binary at 1 s CPU, run directly. A graph's reference is one run of REX at 10 s. A
program's score on a split is the mean over the split's graphs of cut / reference, one run per (program, graph,
occurrence), seeded by (study, program, graph, occurrence), as B20_R132's evaluator.

**Primary.** R1: the protected `feedback.Judge` (calibrate='BC', Z = 3, patience as in the contract), built on the
calibration programs with REX as its incumbent, is given one submission, C0_1.
**Verdict:**
  * INVALID if validity fails;
  * RELEASED if the judge releases C0_1 (its B score exceeds REX's by more than the judge's tau);
  * otherwise NOT_RELEASED.
**Secondary (reported; they decide nothing):**
  * S1: the candidate judge version 3 (`contract_v3.local_calibration`, research plane, adopted nowhere): the same
    Judge class calibrated on 16 one-step mutations of REX in the 'L0' language; would it release C0_1?
  * S2: the truth: C0_1 against REX on T, two runs each per graph, the per-graph gain (cut - REX's cut) / REX's cut,
    one-sided Wilcoxon (a third replication of B20_R165's P2 on fresh graphs);
  * S3: where tau comes from: the standard deviation of B - C over REX and the random engines, over the random engines
    alone, and over v3's mutants; tau of each calibration;
  * S4: the observed B gain of C0_1 over REX (as a ratio of scores), and, from the calibration's per-graph scores,
    the split size at which version 2's tau would fall below it (descriptive, assuming per-graph independence).
**Validity:**
  * the median CPU of the 1 s runs is at least 0.9 s, of the 10 s runs at least 9 s;
  * the graph sets are pairwise disjoint and disjoint from everything excluded;
  * C0_1 hashes to its recorded key and B20_R151's summary has its recorded digest;
  * mcx3's pin and the protected judge's source are the ones at preregistration.

**Expectation, stated before running.** NOT_RELEASED, moderate confidence: random engines vary far more from graph to
graph than good ones, so version 2's tau will be several times C0_1's gain (B20_R132's measurement, here with 12-graph
splits). S1: version 3 releases (local tau of a few tenths of a percent). S2: C0_1 beats REX on T by about 1%. If
NOT_RELEASED, this is the case for the human-gated decision on the judge's calibration that the plan reserves for
the supervisor; nothing here changes the judge.

**Development looks (disclosed).** None on this study's graphs. B20_R132's development look measured version 2's
and version 3's thresholds on other classes; B20_R151 and B20_R165 gave the gain (both read in full when recorded).

**Cost.** Calibration: 48 programs x 2 splits x 12 graphs x 1 s (about 19 min); version 3's: 16 x 24 x 1 s (6 min);
references 48 x 10 s (8 min); the truth: 24 x 2 x 2 x 1 s (2 min). About 35 min, in slices of 6,600 s.
**Status.** DEV; releases only what the protected judge releases; licenses nothing else.
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

STUDY = 'b20r173'
OUTPUT = ROOT / 'evidence' / 'protected_release_b20r173'
SEED = 20561731
R151_DIR = ROOT / 'evidence' / 'expressiveness_b20r151'
R151_SUMMARY_SHA256 = 'd021b145c395fa410c619c94ba5bfee1a1ab34a715c591148ba11fc5d6dd93df'
CANDIDATE = 'C0_1'
FAMILY = ('planar2_pm1', {'n': 2000, 'density': 0.99})
SIZE, N_TRUTH = 12, 24
BUDGET, LONG, T_RUNS = 1.0, 10.0, 2
POPULATION, CALIBRATION_EXTRA, V3_MUTANTS = 32, 16, 16
ALPHA = 0.05
PROTECTED_FEEDBACK_SHA256 = '2ff4a5ab1e5b445b9144afbcc43596b8b1701ae541e8916c73e45009c0e3bdd6'
MCX3_SHA256 = '9449f8b669506b159dff56c7d6d1c1276859d0fa83852b04c805086999dcbd24'
SLICE_S, PAUSED = 6600, 3


class Paused(Exception):
    pass


def file_digest(path):
    p = Path(path)
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


# --------------------------------------------------------------------------------------------- programs and graphs

def candidate(r151_dir=R151_DIR):
    """C0_1's configuration, and whether it hashes to the key B20_R151's summary records for it."""
    s = json.loads((Path(r151_dir) / 'summary.json').read_text())
    progs = json.loads((Path(r151_dir) / 'programs.json').read_text())
    key = s['arms']['planar2000'][CANDIDATE]
    cfg = progs[key]
    return cfg, digest(cfg)[:16] == key


def calibration_programs(seed=SEED):
    """REX, then POPULATION - 1 + CALIBRATION_EXTRA random engines of the 'L0' language (configs), seeded."""
    from genesis.candidate_kinds import mcx3 as K3
    from genesis.expressive import lambda1 as L1
    from genesis.expressive import operators as O
    rng = random.Random(f'{STUDY}|{seed}|calibration')
    out = [dict(K3.DEFAULT)]
    keys = {json.dumps(out[0], sort_keys=True)}
    while len(out) < POPULATION + CALIBRATION_EXTRA:
        cfg = L1.config(O.random_engine(rng, 'L0'))
        k = json.dumps(cfg, sort_keys=True)
        if k not in keys:
            keys.add(k)
            out.append(cfg)
    return out


def v3_programs(seed=SEED):
    """Version 3's calibration: V3_MUTANTS one-step mutations of REX in the 'L0' language (configs)."""
    from genesis.autonomy import contract_v3 as V3
    from genesis.candidate_kinds import mcx3 as K3
    from genesis.expressive import lambda1 as L1
    from genesis.expressive import operators as O
    ops = O.ops('L0')
    genome = {k: v for k, v in K3.DEFAULT.items()}
    return [L1.config(g) for g in V3.local_calibration(ops, genome, f'{STUDY}|{seed}', n=V3_MUTANTS)]


def excluded_identities():
    import b20r165_planar_replication as R165
    from genesis.domains import adapter
    A = adapter('maxcut_v1')
    ex = R165.excluded_identities()
    g165 = R165.graphs(ex)
    return ex | {A.exposure_identity(t)['canonical'] for c in g165 for t in g165[c]}


def graphs(excluded, limit=None):
    """{'B', 'C', 'T': [task]}: fresh, disjoint, from SEED (the first `limit` of each, for tests)."""
    from genesis.domains import adapter
    A = adapter('maxcut_v1')
    seen, out = set(excluded), {}
    for k, (name, n) in enumerate((('B', SIZE), ('C', SIZE), ('T', N_TRUTH))):
        n = n if limit is None else min(n, limit)
        out[name] = []
        for i in range(n):
            got, seen, _ = A.generate(SEED + 1000 * k + i, 1, 'DEV', FAMILY[0], FAMILY[1], excluded=seen)
            out[name].append(got[0])
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
        return self.run(K3.DEFAULT, task, 'ref', LONG)


def evaluator(lab, splits, log=None):
    """evaluate(cfg, split): the mean over the split's graphs of cut / reference; the occurrence counts the program's
    earlier evaluations on that split (B20_R132's evaluator)."""
    occ = {}

    def ev(cfg, split):
        k = (digest(cfg)[:16], split)
        n = occ.get(k, 0)
        occ[k] = n + 1
        v = statistics.mean(lab.run(cfg, t, n) / lab.ref(t) for t in splits[split])
        if log is not None:
            log.append({'engine': k[0], 'split': split, 'occ': n, 'value': v})
        return v
    return ev


# --------------------------------------------------------------------------------------------- the judges

def judge(evaluate, calibration, incumbent, cand):
    """The protected Judge (unchanged), one submission: its tau, the start, the decision and the released score."""
    from genesis.autonomy import feedback as FB
    J = FB.Judge(evaluate, calibration, incumbent, calibrate='BC')
    released = J.submit(cand)
    b_cand = J._b(cand)
    return {'tau': J.tau, 'start': J.start, 'b_candidate': b_cand, 'released': released is not None,
            'released_score': released, 'diffs': J.private[0][1]}


def wilcoxon(diffs, alternative):
    from scipy.stats import wilcoxon as W
    d = [x for x in diffs if x != 0]
    if not d:
        return {'n': 0, 'p': 1.0, 'mean': statistics.mean(diffs) if diffs else 0.0}
    return {'n': len(d), 'p': float(W(d, alternative=alternative).pvalue), 'mean': statistics.mean(diffs)}


def split_size_needed(v2, gain, size=SIZE):
    """The split size at which version 2's tau would fall below `gain`, if tau shrank as 1/sqrt(size)."""
    if gain <= 0:
        return None
    return int((v2['tau'] / gain) ** 2 * size) + 1


def verdict(valid, v2):
    if not valid:
        return 'INVALID'
    return 'RELEASED' if v2['released'] else 'NOT_RELEASED'


def main(argv=None, registered=True, limit=None, runner=real_runner, excluded=None, output=OUTPUT, r151_dir=R151_DIR):
    """Run (or resume) the study; 0 when done, PAUSED at the end of a time slice. A design test may redirect the
    output, shrink the sets (`limit`) and pass a fake runner while keeping registered=True, so that the validity a
    registered run computes is itself tested (B20_R141's lesson)."""
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        raise SystemExit(__doc__.splitlines()[3])
    out = Path(argv[0]).resolve()
    if registered and out != Path(output).resolve():
        raise SystemExit(f'the registered output is {output}')
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    from genesis.candidate_kinds import mcx3 as K3
    ex = excluded if excluded is not None else excluded_identities()
    G = graphs(ex, limit)
    lab = Lab(out / 'runs.jsonl', runner, deadline=t0 + SLICE_S)
    cand, cand_ok = candidate(r151_dir)
    cal, v3cal = calibration_programs(), v3_programs()
    if limit is not None:
        cal, v3cal = cal[:max(4, limit)], v3cal[:max(4, limit)]
    try:
        log2, log3 = [], []
        v2 = judge(evaluator(lab, G, log2), cal, dict(K3.DEFAULT), cand)
        v3 = judge(evaluator(lab, G, log3), v3cal, dict(K3.DEFAULT), cand)
        truth = []
        for t in G['T']:
            c = statistics.mean(lab.run(cand, t, f'truth{r}') for r in range(T_RUNS))
            x = statistics.mean(lab.run(dict(K3.DEFAULT), t, f'truth{r}') for r in range(T_RUNS))
            truth.append((c - x) / x)
    except Paused:
        return PAUSED
    rand_diffs = v2['diffs'][1:]
    s3 = {'sd_all_v2': statistics.stdev(v2['diffs']), 'sd_random': statistics.stdev(rand_diffs) if len(rand_diffs) > 1
          else None, 'sd_v3': statistics.stdev(v3['diffs']), 'tau_v2': v2['tau'], 'tau_v3': v3['tau']}
    gain_b = v2['b_candidate'] - v2['start']
    s4 = {'b_gain': gain_b, 'split_size_needed_v2': split_size_needed(v2, gain_b, len(G['B']))}
    s2 = wilcoxon(truth, 'greater')
    cpus = [r['cpu'] for r in lab.cache.values() if r['key'].endswith('|1')]
    cpus10 = [r['cpu'] for r in lab.cache.values() if r['key'].endswith('|10')]
    cpu_ok = (not cpus or statistics.median(cpus) >= 0.9 * BUDGET) and \
        (not cpus10 or statistics.median(cpus10) >= 0.9 * LONG)
    from genesis.domains import adapter
    A = adapter('maxcut_v1')
    ids = {k: {A.exposure_identity(t)['canonical'] for t in v} for k, v in G.items()}
    disjoint = (not (ids['B'] & ids['C']) and not (ids['B'] & ids['T']) and not (ids['C'] & ids['T'])
                and not any(ids[k] & ex for k in ids))
    pins = {'mcx3': K3.BINARY_SHA256 == MCX3_SHA256 and K3.binary_digest() == MCX3_SHA256,
            'feedback': file_digest(ROOT / 'src/genesis/autonomy/feedback.py') == PROTECTED_FEEDBACK_SHA256,
            'r151_summary': file_digest(Path(r151_dir) / 'summary.json') == R151_SUMMARY_SHA256 or not registered,
            'candidate_key': cand_ok}
    valid = cpu_ok and disjoint and all(pins.values())
    v = verdict(valid, v2)
    summary = {'study': STUDY, 'schema': 'genesis-b20r173-protected-release-v1', 'verdict': v, 'valid': valid,
               'validity': {'cpu': cpu_ok, 'disjoint': disjoint, **pins},
               'R1': {k: v2[k] for k in ('tau', 'start', 'b_candidate', 'released', 'released_score')},
               'S1': {k: v3[k] for k in ('tau', 'start', 'b_candidate', 'released', 'released_score')},
               'S2': dict(s2, gains=truth), 'S3': s3, 'S4': s4, 'candidate': cand,
               'calibration_programs': len(cal), 'v3_programs': len(v3cal),
               'graphs': {k: [t.task_id for t in v] for k, v in G.items()}, 'runs': len(lab.cache),
               'code_identity': code_identity(ROOT)['sha256'],
               'status': 'DEV; releases only what the protected judge releases'}
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True, default=str) + '\n')
    (out / 'calls.json').write_text(json.dumps({'v2': log2, 'v3': log3}, sort_keys=True) + '\n')
    print(json.dumps({k: summary[k] for k in ('verdict', 'valid', 'R1', 'S1', 'S3', 'S4')}, indent=1, default=str))
    return 0


if __name__ == '__main__':
    sys.exit(main())
