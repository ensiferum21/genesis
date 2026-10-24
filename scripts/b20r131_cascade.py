#!/usr/bin/env python3
"""B20_R131: does a new capability revive old ideas that a fresh search would not find? The cascade, on a real case.
(DEV, preregistered; Genesis Ω contract §7-§8, §16.6, §16.12; stage Ω6)

    taskset -c 0 python3 scripts/b20r131_cascade.py OUT_DIR     run ALONE (resumable by phase)

**Why.** Daniel's master contract (24 Oct 2026, 14:24): store exact discoveries, let a new capability trigger the
reactivation of dormant ones, and measure whether that yields more verified value per total compute than a
no-reactivation control, fresh search, random retrieval and a negative-control trigger. The real case: B20_R129's
four invention searches judged thousands of acquisition rules in the per-pair framework; B20_R130 tests whether a
global interpretation (multi-regime maximum likelihood, `causal.global_ml`) is better. If it is, it is a new
capability, and rules dismissed under the old interpretation may be worth a second look under the new one.

**Inputs (recorded evidence, read at run time):** B20_R129's evidence (its worlds A, B, C, its calibrated model, its
lambda and its searches' seeds) and B20_R130's summary (whether T_interpretation was INTERPRETATION_BETTER after
Holm). If B20_R130 did not show it, the trigger is not a verified capability: the study runs only the null-trigger
arm and the comparators, and records NO_VERIFIED_TRIGGER.

**Phases.**
  1. **Archive.** B20_R129's four searches are replayed exactly (same worlds, model, seeds and code; the replay must
     reproduce every recorded winner and judged score, else the study stops: INVALID). Every distinct program they
     evaluated enters the vault (`genesis.vault`) as a ProgramSpec with its exact source, its lineage (search,
     order of evaluation), its training scores and its cost; then it is set dormant with failure kind
     `context_limited` and an inferred edge `failed_due_to` -> `tag:interpretation` (confidence 0.5: inferred from
     B20_R130's development looks, not proven), scored by its mean training score in B20_R129.
  2. **Trigger.** A CapabilityRecord "global interpretation" unlocking `interpretation`, with an EvidenceRecord naming
     B20_R130 and its record test, set verified. A null trigger (a CapabilityRecord unlocking nothing) is the
     negative control: it must reactivate nothing.
  3. **Arms at matched compute** (FUEL = 24 rule evaluations each on R131's own A worlds; a rule's training score =
     its mean hidden-cause F1 under the global interpretation at budgets 4 and 8, with this study's thresholds):
       - `reactivated`: the vault's opportunities for the trigger (best stored score first), re-tested;
       - `fresh`: a fresh steady-state search in the same language (`autonomy.feedback`, no judge, seeded with eig,
         dec, hybrid, decf and decfall), stopped after FUEL distinct rules (a repeated rule costs nothing: the
         evaluation is deterministic and cached);
       - `random`: FUEL rules drawn uniformly from the whole archive (as archived, before any reactivation);
       - `null`: the null trigger (reactivates nothing): B20_R129's chosen scientist, unchanged.
     Each arm's winner is its best rule by training score (ties to the earlier evaluation).
  4. **Test.** Each arm's winner, and `eig` for reference, on 200 fresh test worlds under the global interpretation:
     a world's score = mean hidden-cause F1 at 4 and 8 experiments.

**Primary test:** `reactivated` against `fresh` on the test worlds, paired Wilcoxon (two-sided, alpha 0.05, at least
6 non-zero differences): REACTIVATION_BETTER / FRESH_BETTER / NO_DIFFERENCE. **Verdict:** CASCADE_ADDS_VALUE if
REACTIVATION_BETTER; NO_VALUE_FROM_CASCADE if NO_DIFFERENCE; CASCADE_WORSE if FRESH_BETTER; NO_VERIFIED_TRIGGER
(above).
**Secondary:** `reactivated` against `random` (does the archive's ranking matter?), against `null` (does
re-evaluating under the new capability help at all?), against `eig`; the null trigger's opportunities (must be none);
an unchanged retry refused; CPU per arm (reactivation and archive costs counted); the vault's integrity
(`Vault.verify`) and exact retrieval of every winner.
**Validity:** the replay reproduces B20_R129's winners and scores; every answer valid (`admg.validate`); every arm
used exactly FUEL evaluations (or all it had).

**Development looks (disclosed).** The vault's tests (`test_vault`: fixtures only). B20_R130's development looks
(in its script). No run of this pipeline on real data.
**Expectation, stated before running.** The null trigger reactivates nothing (by construction, tested).
`reactivated` against `fresh`: NO_DIFFERENCE (both draw from the same language; the archive's ranking was made under
the old interpretation, which may not predict value under the new one). `reactivated` and `fresh` both above
`null`. NO_VALUE_FROM_CASCADE.
**Cost.** About 1 h. **Status.** DEV; licenses nothing.
"""
import json
from pathlib import Path
import statistics
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis.common import code_identity  # noqa: E402

STUDY = 'b20r131'
SEED = 20501311
SETS = {'calibration': (0, 100), 'A': (1000, 40), 'test': (5000, 200)}
BUDGETS = (4, 8)
FUEL = 24
ALPHA = 0.05
R129 = ROOT / 'evidence' / 'adaptive_scientist_b20r129'
R130 = ROOT / 'evidence' / 'choice_instrument_interpretation_b20r130'


def world(set_name, k):
    import b20r129_adaptive_scientist as M129
    off, n = SETS[set_name]
    if not 0 <= k < n:
        raise ValueError('no such world')
    return SEED + off + k, M129.BASE


def wilcoxon(a, b, names):
    import b20r129_adaptive_scientist as M129
    return M129.wilcoxon(a, b, names)


def prepare_set(out, set_name, log):
    """This study's worlds, prepared exactly as B20_R130 prepares its own (FCI, the lab, the instrument table)."""
    import b20r130_choice_instrument_interpretation as M130
    from genesis.causal import active3 as A3
    from genesis.causal import sem as S
    path = out / f'worlds_{set_name}.jsonl'
    have = {r['seed'] for r in M130.load_jsonl(path)}
    for k in range(SETS[set_name][1]):
        seed, st = world(set_name, k)
        if seed in have:
            continue
        c0 = time.process_time()
        view, truth = S.instance(seed, st['p'], st['h'], st['density'], M130.NOISE, M130.K, M130.N_TOTAL)
        prep = A3.prepare(view, truth, M130.N_INT, seed)
        row = {'set': set_name, 'seed': seed, 'settings': st, 'truth': truth, 'prep': prep,
               'cpu_s': round(time.process_time() - c0, 3)}
        with path.open('a') as f:
            f.write(json.dumps(row, sort_keys=True) + '\n')
    rows = sorted(M130.load_jsonl(path), key=lambda r: r['seed'])
    log(f'{set_name}: {len(rows)} worlds')
    return rows


# ------------------------------------------------------------------------------------------------- phase 1

def replay_searches(log):
    """Replay B20_R129's searches with every evaluation recorded: [(search, order, program, split, score)]."""
    import b20r129_adaptive_scientist as M129
    from genesis.autonomy import feedback as FB
    from genesis.science import acquire as Q
    model = json.loads((R129 / 'model.json').read_text())
    lam = json.loads((R129 / 'lambda.json').read_text())['lambda']
    recorded = json.loads((R129 / 'search.json').read_text())
    split = {s: [M129.World(r, model) for r in M129.load_jsonl(R129 / f'worlds_{s}.jsonl')] for s in ('A', 'B', 'C')}
    seeds_prog = [Q.EIG, Q.DEC, Q.hybrid(lam), {'agg': 'sum', 'expr': 'decf'}, {'agg': 'sum', 'expr': 'decfall'}]
    trace = []
    for rec in recorded:
        k = rec['search']

        def evaluate(prog, s, k=k):
            v = -statistics.mean(w.experiments_needed({'kind': 'program', 'program': prog}) for w in split[s])
            trace.append((k, len(trace), prog, s, v))
            return v
        win, rep = FB.steady_state_search(Q.ops(seeds_prog), evaluate, M129.MAX_EVALS, M129.SEED + 100 + k,
                                          contract=True, calibrate='BC')
        rep = json.loads(json.dumps(rep, default=float))
        if win != rec['winner'] or abs(rep['reported'] - rec['report']['reported']) > 1e-12:
            raise RuntimeError(f'replay of search {k} differs from the record')
        log(f'replayed search {k}: {Q.text(win)} (as recorded)')
    return trace, lam


def archive(vault, trace, log):
    from genesis import vault as V
    from genesis.science import acquire as Q
    by = {}
    for k, order, prog, s, v in trace:
        key = json.dumps(prog, sort_keys=True)
        d = by.setdefault(key, {'program': prog, 'first': (k, order), 'scores': {}, 'evaluations': 0})
        d['scores'].setdefault(s, []).append(v)
        d['evaluations'] += 1
    ev129 = vault.put(V.Vault.record('EvidenceRecord', {'study': 'b20r129', 'record_test': 'RecordB20R129',
                                                       'summary': 'evidence/adaptive_scientist_b20r129/summary.json'},
                                     domain='causal', creator={'process': 'b20r131 archive'}))
    recs = []
    for key, d in sorted(by.items(), key=lambda kv: kv[1]['first']):
        recs.append(V.Vault.record(
            'ProgramSpec', {'language': 'science.acquire (B20_R129)', 'source': d['program'],
                            'text': Q.text(d['program'])},
            domain='causal-experiment-choice', creator={'process': 'b20r129 search', 'search': d['first'][0],
                                                        'first_evaluation': d['first'][1]},
            costs={'evaluations': d['evaluations']},
            contracts={'evaluated_under': 'per-pair interpretation (B20_R129)',
                       'scores': {s: statistics.mean(v) for s, v in sorted(d['scores'].items())}}))
    ids = vault.put_many(recs)
    for aid, rec in zip(ids, recs):
        sc = rec['contracts']['scores'].get('A')
        vault.annotate(aid, status='exploratory', evidence=[ev129], reason='evaluated in B20_R129')
        vault.annotate(aid, status='dormant', failure='context_limited',
                       reason='judged only under the per-pair interpretation')
        vault.edge('failed_due_to', aid, 'tag:interpretation', evidence=[ev129], confidence=0.5,
                   scope='causal experiment choice, Gaussian worlds', score=sc,
                   provenance={'hypothesis': 'the per-pair interpretation limits every acquisition rule',
                               'source': 'B20_R130 development looks'})
    log(f'archived {len(ids)} distinct rules from {len(trace)} evaluations')
    return ids, ev129


# ------------------------------------------------------------------------------------------------- scoring

class GWorld:
    """A world under the global interpretation: the scientist's choices come from the per-pair framework (the
    acquisition rule's language), the answer from `global_ml` on the chosen experiments."""

    def __init__(self, row, model, tb, to):
        import b20r130_choice_instrument_interpretation as M130
        from genesis.causal import active3 as A3
        from genesis.science import design as D
        self.row, self.model, self.tb, self.to = row, model, tb, to
        self.data = M130.Data(row)
        self.dom = A3.CausalDomain(row['prep'], model)
        self.beliefs = D.Beliefs(self.dom)
        self._f1 = {}

    def f1(self, done):
        from genesis.causal import admg as A
        from genesis.causal import global_ml as GM
        key = tuple(sorted(done))
        if key not in self._f1:
            B, Om, ok, _ = self.data.global_fit(key)
            self._f1[key] = A.score(self.row['truth'], GM.answer(B, Om, self.tb, self.to))['bidirected']['f1']
        return self._f1[key]

    def score(self, acq):
        from genesis.science import design as D
        r, _ = D.run(self.dom, acq, max(BUDGETS), beliefs=self.beliefs)
        return statistics.mean(self.f1(r.done[:b]) for b in BUDGETS)


def mean_score(worlds, prog):
    acq = prog if 'kind' in prog else {'kind': 'program', 'program': prog}
    return statistics.mean(w.score(acq) for w in worlds)


# ------------------------------------------------------------------------------------------------- main

def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        raise SystemExit(__doc__.splitlines()[3])
    out = Path(argv[0]).resolve()
    if out != (ROOT / 'evidence' / 'cascade_b20r131').resolve():
        raise SystemExit('the registered output is evidence/cascade_b20r131')
    if not (R129 / 'summary.json').exists() or not (R130 / 'summary.json').exists():
        raise SystemExit('B20_R129 and B20_R130 must be recorded first')
    out.mkdir(parents=True, exist_ok=True)
    import b20r33_strong_baseline_audit as R33
    import b20r129_adaptive_scientist as M129
    import b20r130_choice_instrument_interpretation as M130
    from genesis import vault as V
    from genesis.autonomy import feedback as FB
    from genesis.causal import active3 as A3
    from genesis.science import acquire as Q
    cpu = R33.pinned_core()
    t0 = time.monotonic()
    logf = (out / 'run.log').open('a')

    def log(m):
        line = f'[{time.monotonic() - t0:7.1f}s] {m}'
        print(line, flush=True)
        logf.write(line + '\n')
        logf.flush()
    log(f'{STUDY}; pinned to CPU {cpu}')
    s130 = json.loads((R130 / 'summary.json').read_text())
    shown = bool(s130['test']['holm']['interpretation']) and \
        s130['test']['T_interpretation']['label'] == 'INTERPRETATION_BETTER'
    cost = {}

    # worlds (this study's own), the per-pair model and the global thresholds, from its calibration worlds
    worlds = {s: prepare_set(out, s, log) for s in SETS}
    mpath = out / 'models.json'
    if not mpath.exists():
        cal = [M130.Data(r) for r in worlds['calibration']]
        models = {'per_pair': A3.calibrate([(r['prep'], r['truth']) for r in worlds['calibration']]),
                  'thresholds': M130.calibrate_thresholds(cal)}
        mpath.write_text(json.dumps(models, indent=1, sort_keys=True) + '\n')
        del cal
    models = json.loads(mpath.read_text())
    tb, to = models['thresholds']['tb'], models['thresholds']['to']
    A_ = [GWorld(r, models['per_pair'], tb, to) for r in worlds['A']]

    # phase 1-2: the vault, the archive, the trigger and the null trigger
    vroot = out / 'vault'
    state = out / 'phases.json'
    ph = json.loads(state.read_text()) if state.exists() else {}
    with V.Vault(vroot) as vault:
        if 'archive' not in ph:
            c0 = time.process_time()
            trace, lam = replay_searches(log)
            ids, ev129 = archive(vault, trace, log)
            ph['archive'] = {'rules': len(ids), 'ids': ids, 'evaluations': len(trace), 'lambda': lam,
                             'evidence': ev129, 'cpu_s': round(time.process_time() - c0, 3)}
            ev130 = vault.put(V.Vault.record('EvidenceRecord', {
                'study': 'b20r130', 'record_test': 'RecordB20R130',
                'summary': 'evidence/choice_instrument_interpretation_b20r130/summary.json',
                'T_interpretation': s130['test']['T_interpretation'], 'holm': s130['test']['holm']},
                domain='causal', creator={'process': 'b20r131 trigger'}))
            trig = vault.put(V.Vault.record('CapabilityRecord', {
                'name': 'global interpretation of every regime (causal.global_ml.fit)', 'unlocks': ['interpretation'],
                'shown_by': 'b20r130'}, domain='causal', creator={'process': 'b20r131 trigger'}))
            null = vault.put(V.Vault.record('CapabilityRecord', {
                'name': 'null trigger (negative control)', 'unlocks': []}, domain='causal',
                creator={'process': 'b20r131 trigger'}))
            if shown:
                vault.annotate(trig, status='exploratory', reason='a capability')
                vault.annotate(trig, status='reproducible', reason='recorded study')
                vault.annotate(trig, status='verified', evidence=[ev130], reason='B20_R130 T_interpretation')
            ph['trigger'], ph['null'], ph['shown'] = trig, null, shown
            state.write_text(json.dumps(ph, indent=1, sort_keys=True) + '\n')
        trig, null = ph['trigger'], ph['null']
        null_opps = vault.opportunities(null, FUEL)
        ph['null_opportunities'] = len(null_opps)
        choice129 = json.loads((R129 / 'choice.json').read_text())
        g129 = M129.acquisition(choice129['genesis'], lam=ph['archive']['lambda'], invented=choice129['invented'])

        # phase 3: the arms at matched compute
        if 'arms' not in ph:
            arms = {}
            if shown:
                c0 = time.process_time()
                opps = vault.opportunities(trig, FUEL)
                tested = []
                for aid in opps:
                    vault.reactivate(aid, trig, reason='B20_R131 trigger')
                    prog = vault.get(aid)['content']['source']
                    s = mean_score(A_, prog)
                    tested.append({'id': aid, 'program': prog, 'score': s})
                    vault.annotate(aid, status='reproducible', reason=f're-tested under the global interpretation: '
                                                                      f'{s:.6f}')
                retry_refused = False
                try:
                    vault.reactivate(opps[0], trig, reason='retry')
                except V.VaultError:
                    retry_refused = True
                arms['reactivated'] = {'tested': tested, 'cpu_s': round(time.process_time() - c0, 3),
                                       'retry_refused': retry_refused}
            c0 = time.process_time()
            evals, cache = [], {}

            class Spent(Exception):
                pass

            def evaluate(prog, split):
                k = json.dumps(prog, sort_keys=True)
                if k not in cache:
                    if len(evals) >= FUEL:
                        raise Spent()
                    cache[k] = mean_score(A_, prog)
                    evals.append({'program': prog, 'score': cache[k]})
                return cache[k]
            lam = ph['archive']['lambda']
            seeds_prog = [Q.EIG, Q.DEC, Q.hybrid(lam), {'agg': 'sum', 'expr': 'decf'}, {'agg': 'sum', 'expr': 'decfall'}]
            try:
                FB.steady_state_search(Q.ops(seeds_prog), evaluate, 50 * FUEL, SEED + 7, contract=False)
            except Spent:
                pass
            arms['fresh'] = {'tested': evals, 'cpu_s': round(time.process_time() - c0, 3)}
            c0 = time.process_time()
            archived = ph['archive']['ids']
            rng = np.random.default_rng([SEED, 3])
            pick = [archived[int(i)] for i in rng.choice(len(archived), size=min(FUEL, len(archived)), replace=False)]
            arms['random'] = {'tested': [{'id': a, 'program': vault.get(a)['content']['source'],
                                          'score': mean_score(A_, vault.get(a)['content']['source'])} for a in pick],
                              'cpu_s': round(time.process_time() - c0, 3)}
            ph['arms'] = arms
            state.write_text(json.dumps(ph, indent=1, sort_keys=True) + '\n')
        arms = ph['arms']
        winners = {'null': g129['program'] if g129['kind'] == 'program' else g129, 'eig': {'kind': 'eig'}}
        for a, d in arms.items():
            best = max(range(len(d['tested'])), key=lambda i: (round(d['tested'][i]['score'], 12), -i))
            winners[a] = d['tested'][best]['program']
        integrity = vault.verify()

    # phase 4: the test
    rpath = out / 'runs.jsonl'
    rows = M129.load_jsonl(rpath)
    have = {(r['seed'], r['arm']) for r in rows}
    for row in worlds['test']:
        w = GWorld(row, models['per_pair'], tb, to)
        new = []
        for arm, prog in sorted(winners.items()):
            if (row['seed'], arm) in have:
                continue
            acq = prog if 'kind' in prog else {'kind': 'program', 'program': prog}
            from genesis.science import design as D
            r, _ = D.run(w.dom, acq, max(BUDGETS), beliefs=w.beliefs)
            f = {str(b): w.f1(r.done[:b]) for b in BUDGETS}
            new.append({'seed': row['seed'], 'arm': arm, 'targets': r.done, 'f1': f,
                        'score': statistics.mean(f.values())})
        with rpath.open('a') as fh:
            for x in new:
                fh.write(json.dumps(x, sort_keys=True) + '\n')
        rows.extend(new)
    by = {(r['seed'], r['arm']): r['score'] for r in rows}
    seeds = sorted({r['seed'] for r in rows})
    col = lambda a: [by[(s, a)] for s in seeds]                       # noqa: E731
    res = {'means': {a: statistics.mean(col(a)) for a in sorted(winners)}, 'winners': winners,
           'null_opportunities': ph['null_opportunities'], 'vault': integrity,
           'arm_cpu_s': {a: d['cpu_s'] for a, d in arms.items()},
           'archive': {k: v for k, v in ph['archive'].items() if k != 'ids'},
           'arm_training_best': {a: max(x['score'] for x in d['tested']) for a, d in arms.items() if d['tested']}}
    if shown:
        t = wilcoxon(col('reactivated'), col('fresh'), ('REACTIVATION_BETTER', 'FRESH_BETTER', 'NO_DIFFERENCE'))
        res['primary'] = t
        res['verdict'] = {'REACTIVATION_BETTER': 'CASCADE_ADDS_VALUE', 'NO_DIFFERENCE': 'NO_VALUE_FROM_CASCADE',
                          'FRESH_BETTER': 'CASCADE_WORSE'}[t['label']]
        res['secondary'] = {f'reactivated_vs_{o}': wilcoxon(col('reactivated'), col(o), ('REACTIVATED_BETTER',
                                                                                         'OTHER_BETTER',
                                                                                         'NO_DIFFERENCE'))
                            for o in ('random', 'null', 'eig')}
        res['retry_refused'] = arms['reactivated']['retry_refused']
    else:
        res['verdict'] = 'NO_VERIFIED_TRIGGER'
    valid = ph['null_opportunities'] == 0 and integrity.get('integrity') == 'LOCAL_HASH_CHECKED'
    summary = dict(res, study=STUDY, schema='genesis-b20r131-cascade-v1', valid=valid, thresholds=models['thresholds'],
                   code_identity=code_identity(ROOT)['sha256'], status='DEV; licenses nothing')
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True, default=float) + '\n')
    log(f"valid {valid}; verdict {res['verdict']}; means " + ', '.join(f'{a} {v:.3f}' for a, v in res['means'].items()))
    return 0 if valid else 1


if __name__ == '__main__':
    sys.exit(main())
