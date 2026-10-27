#!/usr/bin/env python3
"""B20_R165: do Genesis's searched max-cut engines beat REX on fresh planar graphs? A confirmatory replication of
B20_R151's S5 (DEV, preregistered)

    taskset -c 0 python3 scripts/b20r165_planar_replication.py evidence/planar_replication_b20r165     run ALONE (resumable; slices exit 3)

**Why.** In B20_R151 (recorded 28 Oct 2026; `docs/checkpoints/B20_R151_RECORD.md`), a SECONDARY, uncorrected test
(S5) found that every one of the 18 engines its searches produced beat REX at 1 s on 24 fresh planar graphs of
2,000 vertices. The gains were 0.45% to 0.78%, p <= 0.02 each. That is more than REX's own gain from ten times the
time (+0.572% on its headroom set). It contrasts with B20_R127, where Genesis's engines tied REX, and with
B20_R132, where nothing beat REX by a confirmed amount. A secondary finding licenses nothing. This study asks the
same question again, of the SAME 18 engines, frozen, on graphs no part of Genesis has seen.

**Engines (frozen; nothing is searched here).** The 18 final engines of B20_R151's arms on planar2000 (I0_r, I1_r,
C0_r, C1_r, C0h_r, C1h_r; r = 0, 1, 2), read from B20_R151's committed evidence: `summary.json`, which must have
SHA-256 R151_SUMMARY_SHA256, and `programs.json`. Each configuration must hash to the key the summary records.
REX is mcx3's DEFAULT. **The pre-specified single engine** for P2 is the one with the highest TRAINING score its
search reported (`reports[...]['reported']`). That is C0_1 (`R B1296 B703 C b1 R B703 B703 C C`, reported
1.008414), chosen without reference to B20_R151's truth graphs.

**Graphs (fresh).** Generated from the seed SEED with the adapter's generator. Every graph is disjoint by canonical
identity from Gset, from all of B20_R151's graphs (H, A and T, every class) and from all of B20_R152's (dev,
confirm and truth).
  * primary class planar2000: 48 graphs (planar2 and planar2_pm1 alternating; n 2,000, density 0.99), twice
    B20_R151's 24;
  * secondary classes: toroidal2000 (torus2d_pm1 100 x 20 and 50 x 40) and random2000 (erdos and erdos_pm1, p 0.01),
    24 graphs each. They failed B20_R151's headroom gate, so they ask whether the engines generalise.

**Runs.** The pinned mcx3 binary at 1 s CPU, run directly. Every engine and REX make T_RUNS = 2 runs per graph,
seeded by (study, engine, graph, run). REX also makes one run at 10 s on each planar graph, as a reference for the
headroom on the new graphs. An engine's gain on a graph is (its mean cut - REX's mean cut) / REX's mean cut.

**Primary (Holm over P1 and P2, alpha 0.05), on planar2000.**
  * P1: the mean gain of the 18 engines per graph; one-sided Wilcoxon signed-rank (greater). It passes if p_Holm <
    0.05 and the mean is at least MATERIAL (0.1%).
  * P2: the pre-specified single engine's gain per graph, by the same test and the same rule.
**Verdict:**
  * INVALID if validity fails;
  * REPLICATED if P1 passes, with P2's label reported beside it (REPLICATED_WITH_SINGLE_ENGINE if P2 passes too);
  * otherwise NOT_REPLICATED.
**Secondary (reported, not in the family):**
  * S1: each of the 18 engines against REX on planar2000, one-sided, Holm over the 18;
  * S2: P1's test on toroidal2000 and on random2000 (generalisation);
  * S3: on planar2000, REX at 10 s against REX at 1 s (the headroom), and the 18 engines' mean against REX at 10 s;
  * S4: P1 per family (planar2 and planar2_pm1);
  * S5: the Λ1 engines' mean against the Λ0 engines' mean (B20_R151's P1 direction, here on 48 new graphs),
    two-sided.
**Validity:**
  * the median CPU of the runs at each budget is at least 0.9 of it;
  * the graph sets are pairwise disjoint and disjoint from everything excluded;
  * the 18 configurations hash to their recorded keys;
  * B20_R151's summary has its recorded digest;
  * mcx3's pin and the protected judge's source are the ones at preregistration.

**What this is not.** It is not a release: the protected judge (`autonomy/feedback.py`) is not asked. Its power to
see a gain of this size is low (B20_R132), and a release is a separate step with its own rules. A REPLICATED result
says that engines Genesis's searches found at 1 s beat the builder-configured REX at 1 s on fresh planar graphs of
2,000 vertices. It says nothing about other sizes, other budgets, or other solvers.

**Expectation, stated before running (moderate confidence).**
  * P1 REPLICATED: the mean gain is about 0.5% to 0.7%, and B20_R151's 24 graphs gave p < 0.02 for every engine.
  * P2 passes (C0_1 gave +0.72% there).
  * S2: smaller or no gains on toroidal2000 and random2000, where REX has little headroom.
  * S3: REX at 10 s about +0.5% over REX at 1 s.
  * S5: no difference between the languages.

**Cost.** Planar: 48 x (19 engines x 2 runs) x 1 s plus 48 x 10 s, about 40 min. The two secondary classes: 2 x 24 x
38 x 1 s, about 30 min. In all, about 1.2 h, in slices of 6,600 s. **Status.** DEV; a replication; licenses nothing;
releases nothing. It runs after B20_R152, alone on CPU 0.
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

STUDY = 'b20r165'
SEED = 20521651
R151_DIR = ROOT / 'evidence' / 'expressiveness_b20r151'
R151_SUMMARY_SHA256 = 'd021b145c395fa410c619c94ba5bfee1a1ab34a715c591148ba11fc5d6dd93df'
PRESPECIFIED = 'C0_1'
CLASSES = {
    'planar2000': ((('planar2', {'n': 2000, 'density': 0.99}), ('planar2_pm1', {'n': 2000, 'density': 0.99})), 48),
    'toroidal2000': ((('torus2d_pm1', {'rows': 100, 'cols': 20}), ('torus2d_pm1', {'rows': 50, 'cols': 40})), 24),
    'random2000': ((('erdos', {'n': 2000, 'p': 0.01}), ('erdos_pm1', {'n': 2000, 'p': 0.01})), 24),
}
PRIMARY = 'planar2000'
T_RUNS, BUDGET, LONG = 2, 1.0, 10.0
MATERIAL, ALPHA = 0.001, 0.05
PROTECTED_FEEDBACK_SHA256 = '2ff4a5ab1e5b445b9144afbcc43596b8b1701ae541e8916c73e45009c0e3bdd6'
MCX3_SHA256 = '9449f8b669506b159dff56c7d6d1c1276859d0fa83852b04c805086999dcbd24'
SLICE_S, PAUSED = 6600, 3


class Paused(Exception):
    pass


def file_digest(path):
    p = Path(path)
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


# --------------------------------------------------------------------------------------------- engines and graphs

def engines(r151_dir=R151_DIR):
    """{arm name: config} of B20_R151's 18 planar2000 engines, and whether every config hashes to its key."""
    s = json.loads((Path(r151_dir) / 'summary.json').read_text())
    progs = json.loads((Path(r151_dir) / 'programs.json').read_text())
    arms = s['arms'][PRIMARY]
    out = {name: progs[key] for name, key in sorted(arms.items())}
    keys_ok = all(digest(out[name])[:16] == key for name, key in arms.items())
    return out, keys_ok


def prespecified(r151_dir=R151_DIR):
    """The engine whose search reported the highest training score (no truth graph involved)."""
    s = json.loads((Path(r151_dir) / 'summary.json').read_text())
    reps = {k.split('|')[1]: v['reported'] for k, v in s['reports'].items() if k.split('|')[0] == PRIMARY}
    return max(sorted(reps), key=lambda n: reps[n])


def excluded_identities():
    """Gset, B20_R151's graphs (every class) and B20_R152's graphs, by canonical identity."""
    import b20r151_expressiveness as R151
    import b20r152_self_extension as R152
    from genesis import gset as GS
    from genesis.domains import adapter
    A = adapter('maxcut_v1')
    gset = {A.exposure_identity(t)['canonical'] for t in GS.tasks()}
    G151 = R151.graphs(set())
    r151 = {A.exposure_identity(t)['canonical'] for c in G151 for t in G151[c]['H'] + G151[c]['T']
            + sum(G151[c]['A'], [])}
    _, seen152 = R152.study_graphs(gset | r151)
    return gset | r151 | set(seen152)


def graphs(excluded, classes=None, limit=None):
    """{class: [task]}: fresh, disjoint, from SEED (the first `limit` per class, for tests)."""
    from genesis.domains import adapter
    A = adapter('maxcut_v1')
    seen, out = set(excluded), {}
    for k, cls in enumerate(sorted(classes or CLASSES)):
        fams, n = CLASSES[cls]
        n = n if limit is None else min(n, limit)
        out[cls] = []
        for i in range(n):
            fam, params = fams[i % len(fams)]
            got, seen, _ = A.generate(SEED + 1000 * k + i, 1, 'DEV', fam, params, excluded=seen)
            out[cls].append(got[0])
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
    """Every run, cached by (engine, graph, run, budget) and appended to runs.jsonl as it is made."""

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


# --------------------------------------------------------------------------------------------------- statistics

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


def gains(values, base, tasks):
    """{engine name: [relative gain per graph in `tasks` order]}."""
    return {e: [(values[e][t] - base[t]) / base[t] for t in tasks] for e in values}


def mean_of(rows):
    return [statistics.mean(x) for x in zip(*rows)]


def analyse(finals, families, pre=PRESPECIFIED):
    """finals: {class: {'base': {task: v}, 'values': {name: {task: v}}, 'long': {task: v} (primary only)}}."""
    res = {}
    for cls, f in finals.items():
        tasks = sorted(f['base'])
        g = gains(f['values'], f['base'], tasks)
        res[cls] = {'mean_of_18': wilcoxon(mean_of(list(g.values())), 'greater'),
                    'per_engine': {n: wilcoxon(v, 'greater') for n, v in sorted(g.items())}}
        if cls == PRIMARY:
            ph = holm({n: w['p'] for n, w in res[cls]['per_engine'].items()})
            for n, w in res[cls]['per_engine'].items():
                w['p_holm'] = ph[n]
            res[cls]['single'] = wilcoxon(g[pre], 'greater')
            long_gain = [(f['long'][t] - f['base'][t]) / f['base'][t] for t in tasks]
            m18 = mean_of(list(g.values()))
            res[cls]['S3'] = {'rex10_vs_rex1': wilcoxon(long_gain, 'greater'),
                              'engines_vs_rex10': wilcoxon([a - b for a, b in zip(m18, long_gain)], 'two-sided')}
            res[cls]['S4'] = {}
            for fam in sorted(set(families.values())):
                idx = [i for i, t in enumerate(tasks) if families[t] == fam]
                res[cls]['S4'][fam] = wilcoxon([m18[i] for i in idx], 'greater')
            l1 = mean_of([g[n] for n in g if n[1] == '1'])
            l0 = mean_of([g[n] for n in g if n[1] == '0'])
            res[cls]['S5'] = wilcoxon([a - b for a, b in zip(l1, l0)], 'two-sided')
    p = res[PRIMARY]
    ph = holm({'P1': p['mean_of_18']['p'], 'P2': p['single']['p']})
    lab = lambda w, k: 'PASS' if ph[k] < ALPHA and w['mean'] >= MATERIAL else 'FAIL'
    primary = {'P1': dict(p['mean_of_18'], p_holm=ph['P1'], label=lab(p['mean_of_18'], 'P1')),
               'P2': dict(p['single'], p_holm=ph['P2'], label=lab(p['single'], 'P2'), engine=pre)}
    return primary, res


def verdict(valid, primary):
    if not valid:
        return 'INVALID'
    if primary['P1']['label'] != 'PASS':
        return 'NOT_REPLICATED'
    return 'REPLICATED_WITH_SINGLE_ENGINE' if primary['P2']['label'] == 'PASS' else 'REPLICATED'


# --------------------------------------------------------------------------------------------------------- main

def main(argv=None, runner=real_runner, registered=True, r151_dir=R151_DIR, graph_set=None, excluded=None):
    """Run (or resume) the study; 0 when done, PAUSED at the end of a time slice."""
    argv = sys.argv[1:] if argv is None else argv
    out = Path(argv[0]).resolve()
    if registered and out != (ROOT / 'evidence' / 'planar_replication_b20r165').resolve():
        raise SystemExit('the registered output is evidence/planar_replication_b20r165')
    out.mkdir(parents=True, exist_ok=True)
    cpu = None
    if registered:
        import b20r33_strong_baseline_audit as R33
        cpu = R33.pinned_core()
    t0 = time.monotonic()
    with (out / 'run.log').open('a') as logf:
        def log(m):
            line = f'[{time.monotonic() - t0:7.1f}s] {m}'
            print(line, flush=True)
            logf.write(line + '\n')
            logf.flush()
        log(f'{STUDY}; pinned to CPU {cpu}')
        from genesis.candidate_kinds import mcx3 as K3
        from genesis.domains import adapter
        A = adapter('maxcut_v1')
        eng, keys_ok = engines(r151_dir)
        pre = prespecified(r151_dir)
        excl = excluded_identities() if excluded is None else set(excluded)
        G = graph_set if graph_set is not None else graphs(excl)
        ids = [A.exposure_identity(t)['canonical'] for c in G for t in G[c]]
        disjoint = len(ids) == len(set(ids)) and not set(ids) & excl
        families = {}
        for cls, ts in G.items():
            fams, _ = CLASSES[cls]
            for i, t in enumerate(ts):
                families[t.task_id] = f'{fams[i % len(fams)][0]}#{i % len(fams)}'
        lab = Lab(out / 'runs.jsonl', runner=runner, deadline=t0 + SLICE_S)
        rex = dict(K3.DEFAULT)
        finals = {}
        try:
            for cls in [PRIMARY] + sorted(c for c in G if c != PRIMARY):
                ts = G[cls]
                base = {t.task_id: statistics.mean(lab.run(rex, t, o) for o in range(T_RUNS)) for t in ts}
                values = {n: {t.task_id: statistics.mean(lab.run(cfg, t, o) for o in range(T_RUNS)) for t in ts}
                          for n, cfg in eng.items()}
                f = {'base': base, 'values': values}
                if cls == PRIMARY:
                    f['long'] = {t.task_id: lab.run(rex, t, 0, LONG) for t in ts}
                finals[cls] = f
                log(f'{cls}: {len(ts)} graphs done')
        except Paused:
            log(f'time slice used ({SLICE_S} s): paused with {len(lab.cache)} runs')
            return PAUSED
    cpus = {}
    for r in lab.cache.values():
        b = r['key'].rsplit('|', 1)[1]
        cpus.setdefault(b, []).append(r['cpu'] / float(b))
    med = {b: statistics.median(v) for b, v in cpus.items()}
    pins = {'protected_judge': file_digest(ROOT / 'src' / 'genesis' / 'autonomy' / 'feedback.py') ==
            PROTECTED_FEEDBACK_SHA256,
            'mcx3': K3.BINARY_SHA256 == MCX3_SHA256 and (not registered or K3.binary_digest() == MCX3_SHA256),
            'r151_summary': (not registered) or file_digest(Path(r151_dir) / 'summary.json') == R151_SUMMARY_SHA256,
            'engine_keys': keys_ok, 'prespecified': (not registered) or pre == PRESPECIFIED}
    valid = all(m >= 0.9 for m in med.values()) and disjoint and all(pins.values())
    primary, res = analyse(finals, families, pre)
    v = verdict(valid, primary)
    summary = {'study': STUDY, 'schema': 'genesis-b20r165-planar-replication-v1', 'verdict': v, 'valid': valid,
               'primary': primary, 'results': res, 'cpu_median': med, 'disjoint': disjoint, 'pins': pins,
               'engines': {n: c['prog'] for n, c in eng.items()}, 'prespecified': pre,
               'graphs': {c: [t.task_id for t in G[c]] for c in G}, 'families': families, 'finals': finals,
               'code_identity': code_identity(ROOT)['sha256'], 'status': 'DEV; a replication; licenses nothing'}
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n')
    with (out / 'run.log').open('a') as logf:
        logf.write(f"verdict {v}; P1 {primary['P1']['label']} ({100 * primary['P1']['mean']:+.3f}%, "
                   f"p_holm {primary['P1']['p_holm']:.3g}); P2 {primary['P2']['label']}\n")
    print(json.dumps({k: summary[k] for k in ('verdict', 'valid', 'primary', 'pins', 'cpu_median')}, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
