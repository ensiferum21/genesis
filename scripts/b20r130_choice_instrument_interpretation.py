#!/usr/bin/env python3
"""B20_R130: what limits the scientist: the choice of experiments, the instrument, or the interpretation?
(DEV, preregistered; Genesis Ω, Ω1)

    taskset -c 0 python3 scripts/b20r130_choice_instrument_interpretation.py OUT_DIR     run ALONE (resumable)

**Why.** Daniel, 24 Oct 2026 (13:58): measure three capabilities separately, because they are different claims:
better experiment CHOICE (more information from the existing instruments), a better INSTRUMENT (more information
becomes accessible) and better INTERPRETATION (more accurate conclusions from the same observations); and test
whether a distinction is unidentifiable. Development looks after B20_R129's preregistration (disclosed below) found
that the interpretation of B20_R129's framework, not its choice or its instrument, limits it: the established
estimator for linear models with latent confounders (Hyttinen, Eberhardt and Hoyer 2012) reaches a hidden-cause F1
of about 0.7 from all ten experiments where the framework reaches about 0.5.

**Worlds (fresh, from SEED; `causal.sem`, Gaussian noise as B20_R124 and R129).** BASE: p = 10, density 0.2, h = 3,
K = 3 environments, N = 3,000 observational samples, N_INT = 1,000 per experiment. Sets from their own seed ranges:
`calibration` (100: every model and threshold is fitted here and only here), `A`, `B`, `C` (40 each: the instrument
search), `test` (200, used once), `transfer` (50, SHIFT: p = 14, density 0.15, h = 4). Every world's experiments are
drawn once (the generator of B20_R129's lab, seeded by world and variable), so every arm sees the same data.

**The three factors** (all on the same data; every combination that a test needs is run):
  * **CHOICE** of the experiments (a sequence of targets; the first b are run at budget b):
      - `random` (R_RANDOM = 3 orders per world, averaged), `degree` (FCI's degree), `oracle` (reference: the planted
        hidden causes' endpoints first);
      - `genesis`: the scientist Genesis chose in B20_R129 (its `choice.json`), choosing one experiment at a time in
        B20_R129's per-pair framework under this study's calibrated model.
  * **INSTRUMENT** (per-pair framework only): `classify` (B20_R129's) against `invented`, the best instrument of the
    language in `causal.instruments` (15 test sets x 3 levels), chosen by Genesis by its ceiling (hidden-cause F1
    with every experiment, per-pair framework) on A and B, its margin over `classify` confirmed on C (reported).
  * **INTERPRETATION** of whatever was observed:
      - `per_pair`: B20_R129's framework (FCI's questions, the instrument's outcomes, the calibrated model, MAP);
      - `joint`: FCI re-run on the pooled observational data and every done experiment (`causal.joint`), its
        adjacencies as the questions, priors calibrated for its marks, then as `per_pair`;
      - `global`: the multi-regime maximum-likelihood estimator (`causal.global_ml.fit`) on the reference
        environment and every done experiment, its thresholds (tb, to) chosen on the calibration worlds;
      - reference at full budget: `llc`, the established estimator (needs every experiment), the same thresholds.
**Budgets:** 2, 4, 6, 8, and p (every experiment).

**Primary tests** (one family, Holm at alpha 0.05; paired over the 200 test worlds; Wilcoxon signed-rank, zeros
dropped, at least 6 non-zero differences; the measure M = a world's hidden-cause F1 averaged over budgets 2-8):
  * **T_interpretation:** `global` against `per_pair`, both with `genesis`'s experiments: INTERPRETATION_BETTER /
    INTERPRETATION_WORSE / NO_DIFFERENCE;
  * **T_choice:** `genesis` against `random`, both interpreted by `global`: CHOICE_BETTER / CHOICE_WORSE /
    NO_DIFFERENCE;
  * **T_instrument:** `invented` against `classify` in the per-pair framework with every experiment (the ceiling):
    INSTRUMENT_BETTER / INSTRUMENT_WORSE / NO_DIFFERENCE.
**Verdict:** the capabilities whose test is BETTER after Holm (for example CHOICE+INTERPRETATION), NOT_SHOWN if none,
and any WORSE named.

**Secondary (reported, uncorrected):** `joint` against `per_pair` (genesis); `global` against `llc` with every
experiment; the headline Daniel set, genesis + global at 4 against random + per_pair at 8 (non-inferiority, margin
0.05, and two-sided), and the smallest budget at which genesis + global's mean reaches random + per_pair's at 8;
the oracle's regret under `global`; the same tests on directed F1; T_interpretation and T_choice on `transfer`;
**identifiability**: under `global` at 4 and 8 (genesis), the recall of hidden causes by whether both, one or neither
endpoint was intervened on (with every experiment the model is identifiable: Hyttinen et al.'s pair condition; with
neither endpoint intervened it generally is not); CPU per interpretation.
**Validity:** every answer passes `admg.validate`; targets distinct; the share of global fits that converged is
reported.

**Development looks (disclosed; seeds 9,000,000+ and 9,100,000+, B20_R129's dev worlds; none used here).** With
every experiment: per-pair ceiling 0.51 (hidden-cause F1; directed 0.92); joint re-analysis then per-pair 0.59; LLC
0.71-0.77 (thresholds looked at on the evaluation worlds); the multi-regime estimator 0.69 (directed 0.985).
Richer per-pair instruments (gap, pgap): ceiling 0.49-0.53. A third of hidden causes are never asked about by FCI's
questions (near-unfaithful partial correlations, median 0.03, not a defect); re-asking with the experiments' data
reopens most. Under the multi-regime estimator at 4 / 8 experiments (40 worlds): random 0.16 / 0.49, degree 0.28 /
0.59, B20_R129's dev scientist (decfall) 0.33 / 0.65, oracle 0.41 / 0.61. The threshold pair (0.25, 0.15) was looked
at there; this study chooses thresholds on its own calibration worlds.
**Expectation, stated before running.** INTERPRETATION_BETTER and CHOICE_BETTER; T_instrument NO_DIFFERENCE. The
headline is borderline (dev: 0.33 against 0.34). `global` close to `llc` with every experiment. Recall of hidden
causes with neither endpoint intervened near zero.
**Cost.** About 1.5 h on one core. **Status.** DEV; licenses nothing.
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

STUDY = 'b20r130'
SEED = 20481301
BASE = {'p': 10, 'h': 3, 'density': 0.2}
SHIFT = {'p': 14, 'h': 4, 'density': 0.15}
NOISE, K, N_TOTAL, N_INT = 'gauss', 3, 3000, 1000
SETS = {'calibration': (0, 100, BASE), 'A': (1000, 40, BASE), 'B': (2000, 40, BASE), 'C': (3000, 40, BASE),
        'test': (5000, 200, BASE), 'transfer': (6000, 50, SHIFT)}
BUDGETS = (2, 4, 6, 8)
R_RANDOM = 3
TB = (0.15, 0.2, 0.25, 0.3, 0.35)
TO = (0.1, 0.15, 0.2, 0.25, 0.3)
MARGIN, ALPHA, EPS = 0.05, 0.05, 1e-12
R129_CHOICE = ROOT / 'evidence' / 'adaptive_scientist_b20r129' / 'choice.json'


def world(set_name, k):
    off, n, st = SETS[set_name]
    if not 0 <= k < n:
        raise ValueError('no such world')
    return SEED + off + k, st


def load_jsonl(path):
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()] if path.exists() else []


# ------------------------------------------------------------------------------------------------- the data

class Data:
    """One world's observations, regenerated from its seed: the view, the experiments, and the derived tables."""

    def __init__(self, row):
        from genesis.causal import sem as S
        st = row['settings']
        self.row, self.seed, self.p = row, row['seed'], st['p']
        self.truth = row['truth']
        self.view, _ = S.instance(self.seed, st['p'], st['h'], st['density'], NOISE, K, N_TOTAL)
        self.X0 = self.view['environments'][0]
        self.exps = {t: S.sample(self.truth, N_INT, np.random.default_rng([self.seed, 11, t]), env=0, intervene=t)
                     for t in range(self.p)}
        self._joint, self._global = {}, {}

    def regimes_joint(self, done):
        from genesis.causal import methods as PCM
        regs = {'obs': PCM.pooled(self.view)}
        for t in done:
            regs[('do', t)] = self.exps[t]
        return regs

    def joint(self, done):
        """The joint re-analysis for a set of done experiments: (prepared-like dict with marks, adj, lab)."""
        key = tuple(sorted(done))
        if key not in self._joint:
            from genesis.causal import active2 as V2
            from genesis.causal import active3 as A3
            from genesis.causal import joint as J
            base, g = J.fci(self.regimes_joint(key), self.p)
            adj = {i: set(g.adj[i]) for i in range(self.p)}
            marks = {}
            for (i, j), m in V2.decide(base, {}).items():
                marks[A3.key(i, j)] = ('fwd' if m == ('d', (i, j)) else 'bwd' if m == ('d', (j, i)) else
                                       'b' if m[0] == 'b' else 'u')
            lab = {str(t): {str(j): V2.classify(self.exps[t], t, j, adj) for j in sorted(adj[t])}
                   for t in range(self.p)}
            self._joint[key] = {'p': self.p, 'adj': {str(i): sorted(adj[i]) for i in range(self.p)}, 'marks': marks,
                                'flagged': [], 'lab': lab}
        return self._joint[key]

    def global_fit(self, done):
        key = tuple(sorted(done))
        if key not in self._global:
            from genesis.causal import global_ml as GM
            c0 = time.process_time()
            B, Om, ok = GM.fit(GM.covariances(self.X0, {t: self.exps[t] for t in key}), self.p)
            self._global[key] = (B, Om, ok, time.process_time() - c0)
        return self._global[key]


def prepare_set(out, set_name, log):
    from genesis.causal import active3 as A3
    from genesis.causal import instruments as INS
    from genesis.causal import sem as S
    path = out / f'worlds_{set_name}.jsonl'
    have = {r['seed'] for r in load_jsonl(path)}
    for k in range(SETS[set_name][1]):
        seed, st = world(set_name, k)
        if seed in have:
            continue
        c0 = time.process_time()
        view, truth = S.instance(seed, st['p'], st['h'], st['density'], NOISE, K, N_TOTAL)
        prep = A3.prepare(view, truth, N_INT, seed)
        adj = {int(i): v for i, v in prep['adj'].items()}
        X0 = view['environments'][0]
        table = {}
        for t in range(st['p']):
            Xt = S.sample(truth, N_INT, np.random.default_rng([seed, 11, t]), env=0, intervene=t)
            table[str(t)] = {str(j): {x: float(f'{v:.6g}') for x, v in d.items()}
                             for j, d in INS.pvalues(X0, Xt, t, adj).items()}
        row = {'set': set_name, 'seed': seed, 'settings': st, 'truth': truth, 'prep': prep, 'table': table,
               'cpu_s': round(time.process_time() - c0, 3)}
        with path.open('a') as f:
            f.write(json.dumps(row, sort_keys=True) + '\n')
    rows = sorted(load_jsonl(path), key=lambda r: r['seed'])
    log(f'{set_name}: {len(rows)} worlds')
    return rows


# ------------------------------------------------------------------------------------------------- interpretations

def per_pair_decisions(prep, model, done, lab=None, inst_model=None):
    """MAP decisions of the per-pair framework after the experiments `done` (in any order)."""
    from genesis.causal import active3 as A3
    from genesis.causal import instruments as INS
    from genesis.science import design as D
    dom = INS.Domain(prep, inst_model, lab) if lab is not None else A3.CausalDomain(prep, model)
    r = D.Run(dom)
    for t in done:
        r.do(t)
    return r.decisions()


def answer_per_pair(p, decisions):
    from genesis.causal import active3 as A3
    return A3.answer(p, decisions)


def calibrate_joint(cal_data, rng_seed):
    """Priors for the joint re-analysis's marks, from calibration worlds at random done sets of every budget."""
    from genesis.causal import active3 as A3
    rows = []
    for d in cal_data:
        order = [int(x) for x in np.random.default_rng([d.seed, rng_seed]).permutation(d.p)]
        for b in BUDGETS + (d.p,):
            rows.append((d.joint(order[:b]), d.truth))
    return A3.calibrate(rows)


def calibrate_thresholds(cal_data):
    """(tb, to) maximising the mean of hidden-cause and directed F1 over the calibration worlds at random done sets
    of every budget; ties to the earlier pair in TB x TO."""
    from genesis.causal import admg as A
    from genesis.causal import global_ml as GM
    fits = []
    for d in cal_data:
        order = [int(x) for x in np.random.default_rng([d.seed, 17]).permutation(d.p)]
        for b in BUDGETS + (d.p,):
            B, Om, ok, _ = d.global_fit(order[:b])
            fits.append((d.truth, B, Om))
    table = {}
    for tb in TB:
        for to in TO:
            vals = []
            for truth, B, Om in fits:
                sc = A.score(truth, GM.answer(B, Om, tb, to))
                vals.append((sc['bidirected']['f1'] + sc['directed']['f1']) / 2)
            table[f'{tb}|{to}'] = statistics.mean(vals)
    best = max(((tb, to) for tb in TB for to in TO), key=lambda x: (round(table[f'{x[0]}|{x[1]}'], 12),
                                                                    -TB.index(x[0]), -TO.index(x[1])))
    return {'tb': best[0], 'to': best[1], 'table': table}


# ------------------------------------------------------------------------------------------------- statistics

def wilcoxon(a, b, names, alternative='two-sided', shift=0.0):
    from scipy.stats import wilcoxon as W
    diffs = [x - y + shift for x, y in zip(a, b)]
    d = [x for x in diffs if abs(x) > EPS]
    md = statistics.mean(x - y for x, y in zip(a, b)) if diffs else 0.0
    if len(d) < 6:
        return {'label': names[2], 'p': 1.0, 'nonzero': len(d), 'mean_difference': md}
    p = float(W(d, zero_method='wilcox', alternative=alternative).pvalue)
    if alternative == 'greater':
        label = names[0] if p < ALPHA else names[2]
    else:
        label = names[2] if p >= ALPHA else (names[0] if md > 0 else names[1])
    return {'label': label, 'p': p, 'nonzero': len(d), 'mean_difference': md}


def holm(tests, alpha=ALPHA):
    order = sorted(tests, key=lambda k: (tests[k], k))
    out, going = {}, True
    for r, k in enumerate(order):
        going = going and tests[k] <= alpha / (len(order) - r)
        out[k] = going
    return out


def verdict_of(tests, rejected):
    better = [k for k in ('choice', 'instrument', 'interpretation')
              if rejected[k] and tests[k]['label'].endswith('_BETTER')]
    worse = [k for k in ('choice', 'instrument', 'interpretation')
             if rejected[k] and tests[k]['label'].endswith('_WORSE')]
    v = '+'.join(x.upper() for x in better) if better else 'NOT_SHOWN'
    if worse:
        v += ' (WORSE: ' + '+'.join(x.upper() for x in worse) + ')'
    return v


def analyse(rows, set_name='test'):
    """rows: one per (world, choice, order, interpretation, budget) with 'f1' and 'directed_f1'."""
    by = {}
    for r in rows:
        if r['set'] == set_name:
            by.setdefault((r['seed'], r['choice'], r['interp'], r['budget']), []).append(r)
    seeds = sorted({r['seed'] for r in rows if r['set'] == set_name})

    def val(seed, choice, interp, budget, f='f1'):
        rs = by[(seed, choice, interp, budget)]
        return statistics.mean(x[f] for x in rs)

    def M(choice, interp, f='f1'):
        return [statistics.mean(val(s, choice, interp, b, f) for b in BUDGETS) for s in seeds]
    out = {'worlds': len(seeds)}
    means = {}
    for (s, c, i, b) in by:
        means.setdefault(f'{c}|{i}', {})
    for key in sorted(means):
        c, i = key.split('|')
        bs = sorted({b for (s, cc, ii, b) in by if cc == c and ii == i}, key=lambda x: (x == 'full', x))
        means[key] = {str(b): {'hidden_f1': statistics.mean(val(s, c, i, b) for s in seeds),
                               'directed_f1': statistics.mean(val(s, c, i, b, 'directed_f1') for s in seeds)}
                      for b in bs}
    out['means'] = means
    ti = wilcoxon(M('genesis', 'global'), M('genesis', 'per_pair'),
                  ('INTERPRETATION_BETTER', 'INTERPRETATION_WORSE', 'NO_DIFFERENCE'))
    tc = wilcoxon(M('genesis', 'global'), M('random', 'global'), ('CHOICE_BETTER', 'CHOICE_WORSE', 'NO_DIFFERENCE'))
    out['T_interpretation'], out['T_choice'] = ti, tc
    out['directed'] = {
        'interpretation': wilcoxon(M('genesis', 'global', 'directed_f1'), M('genesis', 'per_pair', 'directed_f1'),
                                   ('INTERPRETATION_BETTER', 'INTERPRETATION_WORSE', 'NO_DIFFERENCE')),
        'choice': wilcoxon(M('genesis', 'global', 'directed_f1'), M('random', 'global', 'directed_f1'),
                           ('CHOICE_BETTER', 'CHOICE_WORSE', 'NO_DIFFERENCE'))}
    if set_name != 'test':
        return out
    tn = wilcoxon([val(s, 'all', 'per_pair_invented', 'full') for s in seeds],
                  [val(s, 'all', 'per_pair', 'full') for s in seeds],
                  ('INSTRUMENT_BETTER', 'INSTRUMENT_WORSE', 'NO_DIFFERENCE'))
    out['T_instrument'] = tn
    tests = {'interpretation': ti, 'choice': tc, 'instrument': tn}
    rej = holm({k: v['p'] for k, v in tests.items()})
    out['holm'] = rej
    out['verdict'] = verdict_of(tests, rej)
    g4 = [val(s, 'genesis', 'global', 4) for s in seeds]
    r8 = [val(s, 'random', 'per_pair', 8) for s in seeds]
    sec = {'joint_vs_per_pair': wilcoxon(M('genesis', 'joint'), M('genesis', 'per_pair'),
                                         ('JOINT_BETTER', 'JOINT_WORSE', 'NO_DIFFERENCE')),
           'global_vs_llc_full': wilcoxon([val(s, 'all', 'global', 'full') for s in seeds],
                                          [val(s, 'all', 'llc', 'full') for s in seeds],
                                          ('GLOBAL_BETTER', 'LLC_BETTER', 'NO_DIFFERENCE')),
           'headline_noninferiority': wilcoxon(g4, r8, ('HALF_SUFFICES', 'NOT_SHOWN', 'NOT_SHOWN'), 'greater', MARGIN),
           'headline_two_sided': wilcoxon(g4, r8, ('GENESIS@4_BETTER', 'RANDOM@8_BETTER', 'NO_DIFFERENCE')),
           'oracle_regret_global': {str(b): means['oracle|global'][str(b)]['hidden_f1'] -
                                    means['genesis|global'][str(b)]['hidden_f1'] for b in BUDGETS}}
    target = means['random|per_pair']['8']['hidden_f1']
    sec['smallest_budget_genesis_global_reaches_random_per_pair@8'] = next(
        (b for b in BUDGETS if means['genesis|global'][str(b)]['hidden_f1'] >= target - EPS), None)
    out['secondary'] = sec
    return out


def identifiability(rows, data_truths):
    """Recall of hidden causes under genesis + global at 4 and 8, by how many endpoints were intervened on."""
    out = {}
    for r in rows:
        if r['set'] != 'test' or r['choice'] != 'genesis' or r['interp'] != 'global' or r['budget'] not in (4, 8):
            continue
        truth = data_truths[r['seed']]
        done = set(r['targets'])
        marked = {tuple(sorted(e)) for e in r['answer']['bidirected']}
        for c in truth['confounded']:
            k = sum(v in done for v in c)
            cell = out.setdefault(str(r['budget']), {}).setdefault(str(k), [0, 0])
            cell[0] += tuple(c) in marked
            cell[1] += 1
    return {b: {k: {'marked': v[0], 'hidden_causes': v[1], 'recall': v[0] / v[1] if v[1] else None}
                for k, v in sorted(d.items())} for b, d in sorted(out.items())}


def checks(rows):
    for r in rows:
        if r['problems'] or len(set(r['targets'])) != len(r['targets']):
            return False
    return True


# ------------------------------------------------------------------------------------------------- main

def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        raise SystemExit(__doc__.splitlines()[3])
    out = Path(argv[0]).resolve()
    if out != (ROOT / 'evidence' / 'choice_instrument_interpretation_b20r130').resolve():
        raise SystemExit('the registered output is evidence/choice_instrument_interpretation_b20r130')
    if not R129_CHOICE.exists():
        raise SystemExit('B20_R129 must be recorded first (its choice of scientist is an input)')
    out.mkdir(parents=True, exist_ok=True)
    import b20r33_strong_baseline_audit as R33
    import b20r129_adaptive_scientist as R129
    from genesis.causal import active3 as A3
    from genesis.causal import admg as A
    from genesis.causal import global_ml as GM
    from genesis.causal import instruments as INS
    from genesis.science import design as D
    cpu = R33.pinned_core()
    t0 = time.monotonic()
    logf = (out / 'run.log').open('a')

    def log(m):
        line = f'[{time.monotonic() - t0:7.1f}s] {m}'
        print(line, flush=True)
        logf.write(line + '\n')
        logf.flush()
    log(f'{STUDY}; pinned to CPU {cpu}')
    worlds = {s: prepare_set(out, s, log) for s in SETS}
    choice129 = json.loads(R129_CHOICE.read_text())
    g_arm = choice129['genesis']
    g_acq = R129.acquisition(g_arm, lam=json.loads((R129_CHOICE.parent / 'lambda.json').read_text())['lambda'],
                             invented=choice129['invented'])
    log(f"genesis = B20_R129's choice {g_arm}: {g_acq}")

    # models and thresholds, from the calibration worlds only
    mpath = out / 'models.json'
    if not mpath.exists():
        cal = [Data(r) for r in worlds['calibration']]
        models = {'per_pair': A3.calibrate([(r['prep'], r['truth']) for r in worlds['calibration']]),
                  'joint': calibrate_joint(cal, 19), 'thresholds': calibrate_thresholds(cal)}
        mpath.write_text(json.dumps(models, indent=1, sort_keys=True) + '\n')
        del cal
    models = json.loads(mpath.read_text())
    tb, to = models['thresholds']['tb'], models['thresholds']['to']
    log(f"thresholds tb {tb}, to {to}")

    # the instrument search: every instrument of the language, its ceiling on A and B (choice), C (confirmation)
    ipath = out / 'instruments.json'
    if not ipath.exists():
        def ceiling(prog, rows, imodel):
            vals = []
            for r in rows:
                p = r['settings']['p']
                lab = INS.lab(prog, r['table'], p)
                dec = per_pair_decisions(r['prep'], None, range(p), lab, imodel)
                vals.append(A.score(r['truth'], A3.answer(p, dec))['bidirected']['f1'])
            return statistics.mean(vals)
        table = {}
        for prog in INS.space():
            cal_rows = [(r['prep'], r['truth'], INS.lab(prog, r['table'], r['settings']['p']))
                        for r in worlds['calibration']]
            im = INS.calibrate(cal_rows, prog)
            k = json.dumps(prog, sort_keys=True)
            table[k] = {'AB': ceiling(prog, worlds['A'] + worlds['B'], im), 'C': ceiling(prog, worlds['C'], im)}
        ref = json.dumps(INS.R129, sort_keys=True)
        best = max(table, key=lambda k: (round(table[k]['AB'], 12), k == ref, k))
        classify_ab = statistics.mean(
            A.score(r['truth'], A3.answer(r['settings']['p'], per_pair_decisions(
                r['prep'], models['per_pair'], range(r['settings']['p']))))['bidirected']['f1']
            for r in worlds['A'] + worlds['B'])
        ipath.write_text(json.dumps({'table': table, 'invented': json.loads(best), 'classify_on_AB': classify_ab},
                                    indent=1, sort_keys=True) + '\n')
    inst = json.loads(ipath.read_text())
    inv = inst['invented']
    inv_model = INS.calibrate([(r['prep'], r['truth'], INS.lab(inv, r['table'], r['settings']['p']))
                               for r in worlds['calibration']], inv)
    log(f"invented instrument {inv} (A+B ceiling {inst['table'][json.dumps(inv, sort_keys=True)]['AB']:.3f}, "
        f"classify {inst['classify_on_AB']:.3f})")

    # the test and the transfer
    rpath = out / 'runs.jsonl'
    rows = load_jsonl(rpath)
    done_keys = {r['seed'] for r in rows}
    for set_name in ('test', 'transfer'):
        for row in worlds[set_name]:
            if row['seed'] in done_keys:
                continue
            d = Data(row)
            p = d.p
            prep = row['prep']
            dom = A3.CausalDomain(prep, models['per_pair'])
            seqs = {('genesis', None): D.run(dom, g_acq, p)[0].done,
                    ('degree', None): A3.degree_order(prep),
                    ('oracle', None): A3.oracle_order(prep, d.truth)}
            for o in range(R_RANDOM):
                seqs[('random', o)] = [int(x) for x in R129.rng_for(d.seed, o).permutation(p)]
            new = []

            def add(choice, order, interp, budget, targets, ans, cpu_s):
                problems = A.validate(ans, p)
                sc = A.score(d.truth, ans) if not problems else None
                new.append({'set': set_name, 'seed': d.seed, 'choice': choice, 'order': order, 'interp': interp,
                            'budget': budget, 'targets': list(targets), 'answer': ans, 'problems': problems,
                            'f1': sc['bidirected']['f1'] if sc else 0.0,
                            'directed_f1': sc['directed']['f1'] if sc else 0.0, 'cpu_s': round(cpu_s, 4)})
            for (c, o), seq in seqs.items():
                for b in BUDGETS:
                    done = seq[:b]
                    B, Om, ok, cs = d.global_fit(done)
                    add(c, o, 'global', b, done, GM.answer(B, Om, tb, to), cs)
                    new[-1]['converged'] = ok
                    if set_name == 'test' or c in ('genesis', 'random'):
                        c0 = time.process_time()
                        add(c, o, 'per_pair', b, done, A3.answer(p, per_pair_decisions(prep, models['per_pair'],
                                                                                       done)),
                            time.process_time() - c0)
                    if set_name == 'test' and (c == 'genesis' or (c == 'random' and o == 0)):
                        c0 = time.process_time()
                        jp = d.joint(done)
                        add(c, o, 'joint', b, done, A3.answer(p, per_pair_decisions(jp, models['joint'], done)),
                            time.process_time() - c0)
            full = list(range(p))
            B, Om, ok, cs = d.global_fit(full)
            add('all', None, 'global', 'full', full, GM.answer(B, Om, tb, to), cs)
            new[-1]['converged'] = ok
            c0 = time.process_time()
            Bl, Ol = GM.llc(GM.covariances(d.X0, d.exps), p)
            add('all', None, 'llc', 'full', full, GM.answer(Bl, Ol, tb, to), time.process_time() - c0)
            add('all', None, 'per_pair', 'full', full,
                A3.answer(p, per_pair_decisions(prep, models['per_pair'], full)), 0.0)
            if set_name == 'test':
                lab = INS.lab(inv, row['table'], p)
                add('all', None, 'per_pair_invented', 'full', full,
                    A3.answer(p, per_pair_decisions(prep, None, full, lab, inv_model)), 0.0)
            with rpath.open('a') as f:
                for r in new:
                    f.write(json.dumps(r, sort_keys=True) + '\n')
            rows.extend(new)
            log(f"{set_name} {d.seed}: genesis global@4 {[r['f1'] for r in new if r['choice'] == 'genesis' and r['interp'] == 'global' and r['budget'] == 4][0]:.2f}")
    valid = checks(rows)
    truths = {r['seed']: r['truth'] for s in ('test', 'transfer') for r in worlds[s]}
    res = {'test': analyse(rows, 'test'), 'transfer': analyse(rows, 'transfer'),
           'identifiability': identifiability(rows, truths)}
    gl = [r for r in rows if r['interp'] == 'global']
    res['global_converged_share'] = sum(r.get('converged', False) for r in gl) / len(gl)
    res['cpu_s_mean'] = {i: statistics.mean(r['cpu_s'] for r in rows if r['interp'] == i)
                         for i in sorted({r['interp'] for r in rows})}
    summary = dict(res, study=STUDY, schema='genesis-b20r130-choice-instrument-interpretation-v1', valid=valid,
                   verdict=res['test']['verdict'], runs=len(rows), genesis=g_arm, thresholds=models['thresholds'],
                   instrument=inv, code_identity=code_identity(ROOT)['sha256'], status='DEV; licenses nothing')
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True, default=float) + '\n')
    t = res['test']
    log(f"valid {valid}; verdict {t['verdict']}; interpretation {t['T_interpretation']['label']} "
        f"(p {t['T_interpretation']['p']:.3g}); choice {t['T_choice']['label']} (p {t['T_choice']['p']:.3g}); "
        f"instrument {t['T_instrument']['label']} (p {t['T_instrument']['p']:.3g})")
    return 0 if valid else 1


if __name__ == '__main__':
    sys.exit(main())
