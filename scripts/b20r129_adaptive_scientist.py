#!/usr/bin/env python3
"""B20_R129: the adaptive experimental scientist. Can Genesis choose experiments well enough to need fewer of them?
(DEV, preregistered; Genesis Ω, P1 / Ω1)

    taskset -c 0 python3 scripts/b20r129_adaptive_scientist.py OUT_DIR     run ALONE (resumable by phase)

**Why.** Genesis's choice of experiments has tied random choice four times (B20_R120, R122 twice, R124): it chose
every target from an observational score fixed in advance. B20_R124 found where the choice matters most: with
Gaussian noise no observational signal sees hidden causes, and an oracle's 4 interventions did what 8 random ones
did. This study tests the experimental scientist of `science.design` with its first adapter, `causal.active3`:
beliefs over four explanations of every adjacent pair, updated by Bayes' rule from what each experiment predicts
under each explanation, and the next experiment chosen after every result. Daniel's design notes of 24 Oct 2026
(13:15) are built in: decision-aware and hybrid acquisitions, a non-adaptive baseline, the primary outcome as
experiments needed, adaptive at 4 against random at 8, calibration, regret against the oracle, CPU accounting, and a
decision layer that knows no domain.

**Worlds (fresh seeds from SEED; planted linear SEMs with hidden confounders, `causal.sem`).** BASE: p = 10, edge
density 0.2, h = 3 hidden confounders, K = 3 environments, **Gaussian** noise, N = 3,000 observational samples
(B20_R124's settings); N_INT = 1,000 samples per intervention. Sets, each from its own seed range:
  * `calibration` (100): the instrument's model is estimated here (`active3.calibrate`), nothing else;
  * `A`, `B`, `C` (100 each): the invention's splits (A the inventor's, B and C the judge's);
  * `validation` (100): Genesis chooses its scientist here;
  * `test` (200): the preregistered test, used once;
  * `transfer` (100): a SHIFTED family, p = 14, density 0.15, h = 4 (otherwise BASE), for transfer, with the model
    calibrated on BASE (no recalibration).
For every world the observational analysis (FCI, flags) and the lab (the outcome of intervening on each variable)
are computed once (`active3.prepare`), so every strategy that runs an experiment sees the same result.

**The scientist's model.** The `calibrated` model (from `calibration`) is the scientist's; the `theory` model is
reported beside it. **Decision:** the most probable explanation of every pair (`science.design`), the same for every
strategy.

**Acquisitions** (all equal-cost; every choice recomputed after each result unless stated):
  * established: `random` (expected over R_RANDOM = 10 random orders per world), `degree` (FCI degree, fixed order),
    `static_eig` (information gain from the prior, fixed order: the non-adaptive baseline), `eig` (expected
    information gain), `dec` (expected decision improvement), `hybrid` (eig + lam x dec; lam from LAMBDAS chosen on A);
  * builder-designed: `decf` (expected improvement of the hidden-cause decision) and `decfall` (the same, looking
    past one step: the value of observing the pair from both ends);
  * **invented by Genesis:** N_SEARCH independent searches in its acquisition language (`science.acquire`), each
    `autonomy.feedback.steady_state_search` under the feedback contract version 2 (`calibrate='BC'`: the judge holds B
    and C; MAX_EVALS evaluations), seeded with eig, dec, hybrid, decf and decfall so that invention starts from the
    state of the art; score on a split = minus the mean experiments needed (below). The distinct winners are `inv1`...
  * reference: `oracle` (the endpoints of the planted hidden causes first, then degree; reads the truth).

**Genesis's scientist** (`genesis`) is chosen by Genesis on `validation`, before the test, from eig, dec, hybrid,
decf, decfall and the invented winners: the fewest mean experiments needed; ties to the higher mean hidden-cause F1
at 4, then the order listed.

**Primary outcome: experiments needed.** For a world and a strategy, the fewest experiments after which its
hidden-cause F1 reaches the F1 that all p experiments give (the most the experiments can tell under the model; every
strategy reaches it at p). For `random`, the mean over its orders.

**Primary tests** (one family, Holm at alpha 0.05; paired over the 200 test worlds; Wilcoxon signed-rank, zeros
dropped, at least 6 non-zero differences):
  * **T1, fewer experiments:** `genesis` against `random` on experiments needed, two-sided: FEWER_EXPERIMENTS /
    MORE_EXPERIMENTS / NO_DIFFERENCE;
  * **T2, half the experiments:** `genesis` at 4 against `random` at 8 on hidden-cause F1, non-inferiority with
    margin 0.05 (one-sided test that genesis@4 - random@8 + 0.05 > 0): HALF_SUFFICES / NOT_SHOWN.
**Verdict:** ADAPTIVE_SCIENTIST if T1 is FEWER_EXPERIMENTS after Holm; ADAPTIVE_SCIENTIST_HALF_THE_EXPERIMENTS if T2
also holds; WORSE_THAN_RANDOM if T1 is MORE_EXPERIMENTS; NOT_SHOWN otherwise.

**Secondary (reported, uncorrected, the same test on experiments needed unless stated):** eig, dec, hybrid and degree
against random; eig against static_eig (the value of adapting); the best invented (by validation) against eig, and
against the best non-invented (by validation); genesis against oracle (regret); genesis@4 against random@8, two-sided;
T1 and T2 on `transfer`; the theory model against the calibrated one for genesis's acquisition (hidden-cause F1 at 4
and 8); calibration at 4 experiments (Brier score and log score of the true explanation, expected calibration error
of P(hidden cause), 10 bins) for both models; information gained (entropy reduction) at 4, and its rank correlation
with the F1 gained; the instrument's confusion (true relation x outcome) on test; the ceiling (F1 with all
experiments); the smallest budget at which genesis's mean F1 reaches random@8's; the CPU spent choosing.
**Validity:** every answer at every budget passes `admg.validate`; every run's targets are distinct and every full
run uses all p.

**Development looks (disclosed).** On 200 Gaussian dev worlds (seeds 9,000,000-9,000,099 to calibrate, 9,100,000-
9,100,099 to evaluate; none used here), mean experiments needed: random 7.5, degree 5.4, static_eig 5.2, eig 4.5,
dec 4.3, hybrid 4.4, decf 4.4, decfall 4.0, oracle 3.0; hidden-cause F1 at 4: random 0.09, eig 0.23, decfall 0.31,
oracle 0.44; random at 8 0.34; the ceiling 0.51. One dev search (1,500 evaluations, splits of 33 dev worlds) found
`sum (pf * max(seen, inv1((decall - 10.0))))` (follow up the pairs already seen in proportion to the probability of
a hidden cause): 3.96 on the dev evaluation worlds. The features `eigall`, `decall`, `decfall` (the lookahead) were
added after the first dev look, which showed that a hidden cause is answered only from both ends.
**Expectation, stated before running.** T1 FEWER_EXPERIMENTS. T2 NOT_SHOWN (dev: about 0.30 at 4 against 0.34 at
8). Adapting beats not adapting. The invented winner about as good as decfall (NO_DIFFERENCE against the best
non-invented). The oracle still clearly better (regret about one experiment). On transfer, still fewer than random.
**Cost.** About 30 minutes on one core. **Status.** DEV; licenses nothing.
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

STUDY = 'b20r129'
SEED = 20471291
BASE = {'p': 10, 'h': 3, 'density': 0.2}
SHIFT = {'p': 14, 'h': 4, 'density': 0.15}
NOISE, K, N_TOTAL, N_INT = 'gauss', 3, 3000, 1000
SETS = {'calibration': (0, 100, BASE), 'A': (1000, 100, BASE), 'B': (2000, 100, BASE), 'C': (3000, 100, BASE),
        'validation': (4000, 100, BASE), 'test': (5000, 200, BASE), 'transfer': (6000, 100, SHIFT)}
R_RANDOM = 10
LAMBDAS = (0.25, 0.5, 1.0, 2.0, 4.0, 10.0)
N_SEARCH, MAX_EVALS = 4, 3000
ESTABLISHED = ('random', 'degree', 'static_eig', 'eig', 'dec', 'hybrid')
BUILDER = ('decf', 'decfall')
CANDIDATES = ('eig', 'dec', 'hybrid', 'decf', 'decfall')       # + the invented winners, for Genesis's choice
MARGIN = 0.05
ALPHA = 0.05
EPS = 1e-12


def world(set_name, k):
    off, n, st = SETS[set_name]
    if not 0 <= k < n:
        raise ValueError('no such world')
    return SEED + off + k, st


# ------------------------------------------------------------------------------------------------- acquisitions

def acquisition(arm, prepared=None, truth=None, lam=None, invented=None):
    from genesis.causal import active3 as A3
    from genesis.science import acquire as Q
    if arm == 'degree':
        return {'kind': 'order', 'order': A3.degree_order(prepared)}
    if arm == 'oracle':
        return {'kind': 'order', 'order': A3.oracle_order(prepared, truth)}
    if arm in ('random', 'static_eig', 'eig', 'dec'):
        return {'kind': arm}
    if arm == 'hybrid':
        return {'kind': 'hybrid', 'lam': lam}
    if arm == 'decf':
        return {'kind': 'program', 'program': {'agg': 'sum', 'expr': 'decf'}}
    if arm == 'decfall':
        return {'kind': 'program', 'program': {'agg': 'sum', 'expr': 'decfall'}}
    if invented and arm in invented:
        return {'kind': 'program', 'program': invented[arm]}
    raise ValueError(f'unknown arm {arm!r}')


class World:
    """One prepared world under one model: runs strategies, scores answers (cached by decisions)."""

    def __init__(self, row, model):
        from genesis.causal import active3 as A3
        from genesis.science import design as D
        self.row, self.p = row, row['prep']['p']
        self.truth = row['truth']
        self.dom = A3.CausalDomain(row['prep'], model)
        self.beliefs = D.Beliefs(self.dom)
        self._scores = {}
        _, trail = D.run(self.dom, {'kind': 'order', 'order': list(range(self.p))}, self.p, beliefs=self.beliefs)
        self.full = self.scores(trail[-1])['bidirected']['f1']

    def scores(self, decisions):
        from genesis.causal import active3 as A3
        from genesis.causal import admg as A
        k = json.dumps(sorted(decisions.items()))
        if k not in self._scores:
            ans = A3.answer(self.p, decisions)
            problems = A.validate(ans, self.p)
            if problems:
                raise ValueError('; '.join(problems))
            self._scores[k] = A.score(self.truth, ans)
        return self._scores[k]

    def needed(self, f1s):
        return next(k for k, x in enumerate(f1s) if x >= self.full - EPS)

    def run(self, acq, budget=None, rng=None, stop_at_target=False):
        from genesis.science import design as D
        stop = None
        if stop_at_target:
            def stop(k, dec):
                return self.scores(dec)['bidirected']['f1'] >= self.full - EPS
        c0 = time.process_time()
        r, trail = D.run(self.dom, acq, self.p if budget is None else budget, rng=rng, beliefs=self.beliefs,
                         stop=stop)
        return r, trail, time.process_time() - c0

    def experiments_needed(self, acq):
        _, trail, _ = self.run(acq, stop_at_target=True)
        return len(trail) - 1


def rng_for(seed, r):
    return np.random.default_rng([seed, 13, r])


# ------------------------------------------------------------------------------------------------- statistics

def wilcoxon(a, b, names, alternative='two-sided', shift=0.0):
    """Paired Wilcoxon of a - b + shift (higher is better): names = (better, worse, none)."""
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
    """{name: p} -> {name: rejected} by Holm's step-down."""
    order = sorted(tests, key=lambda k: (tests[k], k))
    out, going = {}, True
    for r, k in enumerate(order):
        going = going and tests[k] <= alpha / (len(order) - r)
        out[k] = going
    return out


def ece(probs, hits, bins=10):
    n = len(probs)
    if not n:
        return None
    tot = 0.0
    for b in range(bins):
        idx = [i for i, p in enumerate(probs) if (b / bins <= p < (b + 1) / bins) or (b == bins - 1 and p == 1.0)]
        if idx:
            tot += len(idx) / n * abs(statistics.mean(probs[i] for i in idx) - statistics.mean(hits[i] for i in idx))
    return tot


# ------------------------------------------------------------------------------------------------- analysis

def per_world(rows, set_name, model):
    """{(seed, arm): row} for the full runs of a set and model; random rows averaged over orders."""
    out, rnd = {}, {}
    for r in rows:
        if r['set'] != set_name or r['model'] != model:
            continue
        if r['arm'] == 'random':
            rnd.setdefault(r['seed'], []).append(r)
        else:
            out[(r['seed'], r['arm'])] = r
    for seed, rs in rnd.items():
        n = len(rs[0]['f1'])
        out[(seed, 'random')] = {'seed': seed, 'arm': 'random', 'needed': statistics.mean(x['needed'] for x in rs),
                                 'f1': [statistics.mean(x['f1'][b] for x in rs) for b in range(n)],
                                 'directed_f1': [statistics.mean(x['directed_f1'][b] for x in rs) for b in range(n)],
                                 'full': rs[0]['full'], 'orders': len(rs),
                                 'entropy': [statistics.mean(x['entropy'][b] for x in rs) for b in range(n)],
                                 'choice_cpu_s': statistics.mean(x['choice_cpu_s'] for x in rs)}
    return out


def analyse(rows, choice):
    """The tests and summaries; `choice` is Genesis's choice record (from validation)."""
    g = choice['genesis']
    res = {'genesis_arm': g}
    for set_name in ('test', 'transfer'):
        W_ = per_world(rows, set_name, 'calibrated')
        seeds = sorted({s for s, _ in W_})
        arms = sorted({a for _, a in W_}, key=lambda a: (a not in ESTABLISHED, a))

        def col(arm, f):
            return [f(W_[(s, arm)]) for s in seeds]
        means = {}
        for arm in arms:
            rs = [W_[(s, arm)] for s in seeds]
            n = len(rs[0]['f1'])
            means[arm] = {'needed': statistics.mean(r['needed'] for r in rs),
                          'f1': [round(statistics.mean(r['f1'][b] for r in rs), 6) for b in range(n)],
                          'directed_f1': [round(statistics.mean(r['directed_f1'][b] for r in rs), 6)
                                          for b in range(n)],
                          'entropy_reduction_at_4': statistics.mean(r['entropy'][0] - r['entropy'][4] for r in rs),
                          'choice_cpu_s': statistics.mean(r['choice_cpu_s'] for r in rs)}
        needed = lambda arm: col(arm, lambda r: -r['needed'])          # noqa: E731  (higher is better)
        f1at = lambda arm, b: col(arm, lambda r: r['f1'][b])            # noqa: E731
        fe = ('FEWER_EXPERIMENTS', 'MORE_EXPERIMENTS', 'NO_DIFFERENCE')
        t1 = wilcoxon(needed(g), needed('random'), fe)
        t2 = wilcoxon(f1at(g, 4), f1at('random', 8), ('HALF_SUFFICES', 'NOT_SHOWN', 'NOT_SHOWN'),
                      alternative='greater', shift=MARGIN)
        out = {'means': means, 'worlds': len(seeds), 'T1': t1, 'T2': t2,
               'ceiling': statistics.mean(W_[(s, 'random')]['full'] for s in seeds)}
        r8 = means['random']['f1'][8]
        out['smallest_budget_genesis_reaches_random@8'] = next(
            (b for b, x in enumerate(means[g]['f1']) if x >= r8 - EPS), None)
        if set_name == 'test':
            rej = holm({'T1': t1['p'], 'T2': t2['p']})
            out['holm'] = rej
            t1ok = rej['T1'] and t1['label'] == 'FEWER_EXPERIMENTS'
            if t1ok and rej['T2'] and t2['label'] == 'HALF_SUFFICES':
                verdict = 'ADAPTIVE_SCIENTIST_HALF_THE_EXPERIMENTS'
            elif t1ok:
                verdict = 'ADAPTIVE_SCIENTIST'
            elif rej['T1'] and t1['label'] == 'MORE_EXPERIMENTS':
                verdict = 'WORSE_THAN_RANDOM'
            else:
                verdict = 'NOT_SHOWN'
            res['verdict'] = verdict
            sec = {}
            for arm in ('eig', 'dec', 'hybrid', 'degree'):
                sec[f'{arm}_vs_random'] = wilcoxon(needed(arm), needed('random'), fe)
            sec['eig_vs_static_eig'] = wilcoxon(needed('eig'), needed('static_eig'),
                                                ('ADAPTING_HELPS', 'ADAPTING_HURTS', 'NO_DIFFERENCE'))
            inv, other = choice['best_invented'], choice['best_other']
            if inv:
                sec['invented_vs_eig'] = wilcoxon(needed(inv), needed('eig'),
                                                  ('INVENTED_BETTER', 'INVENTED_WORSE', 'NO_DIFFERENCE'))
                sec['invented_vs_best_other'] = wilcoxon(needed(inv), needed(other),
                                                         ('INVENTED_BETTER', 'INVENTED_WORSE', 'NO_DIFFERENCE'))
            sec['genesis_vs_oracle'] = wilcoxon(needed(g), needed('oracle'),
                                                ('BETTER_THAN_ORACLE', 'ORACLE_BETTER', 'NO_DIFFERENCE'))
            sec['genesis@4_vs_random@8'] = wilcoxon(f1at(g, 4), f1at('random', 8),
                                                    ('GENESIS@4_BETTER', 'RANDOM@8_BETTER', 'NO_DIFFERENCE'))
            sec['regret_vs_oracle'] = {'needed': means[g]['needed'] - means['oracle']['needed'],
                                       'f1_at_4': means['oracle']['f1'][4] - means[g]['f1'][4]}
            Th = per_world(rows, 'test', 'theory')
            for b in (4, 8):
                sec[f'theory_vs_calibrated_f1@{b}'] = wilcoxon(
                    [Th[(s, g)]['f1'][b] for s in seeds], f1at(g, b),
                    ('THEORY_BETTER', 'CALIBRATED_BETTER', 'NO_DIFFERENCE'))
            sec['theory_means'] = {arm: {'needed': statistics.mean(Th[(s, arm)]['needed'] for s in seeds),
                                         'f1': [round(statistics.mean(Th[(s, arm)]['f1'][b] for s in seeds), 6)
                                                for b in range(len(Th[(seeds[0], arm)]['f1']))]}
                                   for arm in sorted({a for _, a in Th})}
            from scipy.stats import spearmanr
            gain_h = [W_[(s, 'eig')]['entropy'][0] - W_[(s, 'eig')]['entropy'][4] for s in seeds]
            gain_f = [W_[(s, 'eig')]['f1'][4] - W_[(s, 'eig')]['f1'][0] for s in seeds]
            if len(set(gain_h)) > 1 and len(set(gain_f)) > 1:
                rho = spearmanr(gain_h, gain_f)
                sec['information_vs_f1_gain_eig'] = {'spearman': float(rho.statistic), 'p': float(rho.pvalue)}
            else:
                sec['information_vs_f1_gain_eig'] = {'spearman': None, 'p': None}
            res['secondary'] = sec
        res[set_name] = out
    return res


def calibration_stats(rows, model):
    """Brier and log score of the true explanation, ECE of P(conf), over the test worlds' pairs at 4 experiments
    under genesis's acquisition (the `beliefs4` field of its rows)."""
    probs, hits, brier, logs = [], [], [], []
    from genesis.causal import active3 as A3
    for r in rows:
        if r['set'] != 'test' or r['model'] != model or not r.get('beliefs4'):
            continue
        for q, pr in r['beliefs4'].items():
            h = r['true'][q]
            brier.append(sum((pr[x] - (x == h)) ** 2 for x in A3.HYPS))
            logs.append(float(np.log(max(pr[h], 1e-12))))
            probs.append(pr['conf'])
            hits.append(1.0 if h == 'conf' else 0.0)
    return {'pairs': len(brier), 'brier': statistics.mean(brier) if brier else None,
            'log_score': statistics.mean(logs) if logs else None, 'ece_conf': ece(probs, hits),
            'mean_p_conf': statistics.mean(probs) if probs else None,
            'rate_conf': statistics.mean(hits) if hits else None}


def instrument_confusion(instances):
    from genesis.causal import active3 as A3
    conf = {r: {o: 0 for o in A3.OUTCOMES} for r in A3.RELATIONS}
    for row in instances:
        prep, truth = row['prep'], row['truth']
        for q in prep['marks']:
            h = A3.true_hypothesis(truth, q)
            i, j = A3.ends(q)
            for t, o in ((i, prep['lab'][str(i)][str(j)]), (j, prep['lab'][str(j)][str(i)])):
                conf[A3.relation(h, t, q)][o] += 1
    return conf


def checks(rows):
    for r in rows:
        if r['problems'] or len(set(r['targets'])) != len(r['targets']) or len(r['targets']) != r['p']:
            return False
    return True


# ------------------------------------------------------------------------------------------------- phases

def load_jsonl(path):
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()] if path.exists() else []


def prepare_set(out, set_name, log):
    from genesis.causal import active3 as A3
    from genesis.causal import sem as S
    path = out / f'worlds_{set_name}.jsonl'
    have = {r['seed'] for r in load_jsonl(path)}
    n = SETS[set_name][1]
    for k in range(n):
        seed, st = world(set_name, k)
        if seed in have:
            continue
        c0 = time.process_time()
        view, truth = S.instance(seed, st['p'], st['h'], st['density'], NOISE, K, N_TOTAL)
        prep = A3.prepare(view, truth, N_INT, seed)
        row = {'set': set_name, 'seed': seed, 'settings': st, 'prep': prep, 'truth': truth,
               'cpu_s': round(time.process_time() - c0, 3)}
        with path.open('a') as f:
            f.write(json.dumps(row, sort_keys=True) + '\n')
    rows = sorted(load_jsonl(path), key=lambda r: r['seed'])
    log(f'{set_name}: {len(rows)} worlds prepared')
    return rows


def full_row(w, set_name, model_name, arm, acq, rng=None, order=None, beliefs_at=None):
    from genesis.causal import active3 as A3
    from genesis.science import design as D
    r, trail, cpu = w.run(acq, rng=rng)
    sc = [w.scores(d) for d in trail]
    f1 = [s['bidirected']['f1'] for s in sc]
    run2 = None
    rr = D.Run(w.dom, w.beliefs)             # replay the targets for the entropies and the beliefs at 4
    ent = [rr.total_entropy()]
    for e in r.done:
        rr.do(e)
        ent.append(rr.total_entropy())
        if beliefs_at is not None and len(rr.done) == beliefs_at:
            run2 = {q: {h: round(float(x), 6) for h, x in zip(A3.HYPS, rr.posterior(q))} for q in rr.qs}
    row = {'set': set_name, 'model': model_name, 'arm': arm, 'seed': w.row['seed'], 'p': w.p, 'targets': r.done,
           'f1': f1, 'precision_at': {str(b): sc[b]['bidirected']['precision'] for b in (4, 8) if b < len(sc)},
           'recall_at': {str(b): sc[b]['bidirected']['recall'] for b in (4, 8) if b < len(sc)},
           'directed_f1': [s['directed']['f1'] for s in sc],
           'shd': [s['shd'] for s in sc], 'full': w.full, 'needed': w.needed(f1),
           'entropy': [round(x, 6) for x in ent], 'choice_cpu_s': round(cpu, 6), 'problems': []}
    if order is not None:
        row['order'] = order
    if beliefs_at is not None:
        row['beliefs4'] = run2
        row['true'] = {q: A3.true_hypothesis(w.truth, q) for q in rr.qs}
    return row


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        raise SystemExit(__doc__.splitlines()[2])
    out = Path(argv[0]).resolve()
    if out != (ROOT / 'evidence' / 'adaptive_scientist_b20r129').resolve():
        raise SystemExit('the registered output is evidence/adaptive_scientist_b20r129')
    out.mkdir(parents=True, exist_ok=True)
    import b20r33_strong_baseline_audit as R33
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
    worlds = {s: prepare_set(out, s, log) for s in SETS}

    # the instrument's model, from the calibration worlds only
    mpath = out / 'model.json'
    if not mpath.exists():
        model = A3.calibrate([(r['prep'], r['truth']) for r in worlds['calibration']])
        mpath.write_text(json.dumps(model, indent=1, sort_keys=True) + '\n')
    model = json.loads(mpath.read_text())
    models = {'calibrated': model, 'theory': A3.THEORY}
    split = {s: [World(r, model) for r in worlds[s]] for s in ('A', 'B', 'C')}

    # hybrid's lambda, on A
    lpath = out / 'lambda.json'
    if not lpath.exists():
        tab = {str(l): statistics.mean(w.experiments_needed({'kind': 'hybrid', 'lam': l}) for w in split['A'])
               for l in LAMBDAS}
        lam = min(LAMBDAS, key=lambda l: (tab[str(l)], l))
        lpath.write_text(json.dumps({'lambda': lam, 'needed_on_A': tab}, indent=1, sort_keys=True) + '\n')
    lam = json.loads(lpath.read_text())['lambda']
    log(f'hybrid lambda {lam}')

    # invention: N_SEARCH searches under the feedback contract, seeded with the state of the art
    spath = out / 'search.json'
    searches = json.loads(spath.read_text()) if spath.exists() else []
    seeds_prog = [Q.EIG, Q.DEC, Q.hybrid(lam), {'agg': 'sum', 'expr': 'decf'}, {'agg': 'sum', 'expr': 'decfall'}]

    def evaluate(prog, s):
        acq = {'kind': 'program', 'program': prog}
        return -statistics.mean(w.experiments_needed(acq) for w in split[s])
    while len(searches) < N_SEARCH:
        k = len(searches)
        c0 = time.process_time()
        win, rep = FB.steady_state_search(Q.ops(seeds_prog), evaluate, MAX_EVALS, SEED + 100 + k, contract=True,
                                          calibrate='BC')
        rep = json.loads(json.dumps(rep, default=float))
        searches.append({'search': k, 'winner': win, 'text': Q.text(win), 'report': rep,
                         'cpu_s': round(time.process_time() - c0, 3)})
        spath.write_text(json.dumps(searches, indent=1, sort_keys=True) + '\n')
        log(f'search {k}: {Q.text(win)}; {rep}')
    invented, seen = {}, set()
    for s in searches:
        kk = json.dumps(s['winner'], sort_keys=True)
        if kk not in seen and s['winner'] not in seeds_prog:
            seen.add(kk)
            invented[f'inv{len(invented) + 1}'] = s['winner']

    # Genesis chooses its scientist on validation
    cpath = out / 'choice.json'
    if not cpath.exists():
        V = [World(r, model) for r in worlds['validation']]
        table = {}
        for arm in list(CANDIDATES) + list(invented):
            acq = acquisition(arm, lam=lam, invented=invented)
            table[arm] = {'needed': statistics.mean(w.experiments_needed(acq) for w in V),
                          'f1_at_4': statistics.mean(w.scores(w.run(acq, 4)[1][-1])['bidirected']['f1'] for w in V)}
        order = list(CANDIDATES) + list(invented)
        rank = lambda a: (table[a]['needed'], -table[a]['f1_at_4'], order.index(a))     # noqa: E731
        genesis = min(order, key=rank)
        best_inv = min(invented, key=rank) if invented else None
        best_other = min(CANDIDATES, key=rank)
        cpath.write_text(json.dumps({'genesis': genesis, 'best_invented': best_inv, 'best_other': best_other,
                                     'validation': table, 'invented': invented,
                                     'invented_text': {a: Q.text(p) for a, p in invented.items()}},
                                    indent=1, sort_keys=True) + '\n')
    choice = json.loads(cpath.read_text())
    log(f"Genesis's scientist: {choice['genesis']} (best invented {choice['best_invented']}, best other "
        f"{choice['best_other']}); validation {choice['validation']}")

    # the test and the transfer, once
    rpath = out / 'runs.jsonl'
    rows = load_jsonl(rpath)
    done = {(r['set'], r['model'], r['arm'], r['seed'], r.get('order')) for r in rows}
    g = choice['genesis']
    arms = list(ESTABLISHED) + list(BUILDER) + list(invented) + ['oracle']
    for set_name in ('test', 'transfer'):
        for mname in ('calibrated', 'theory'):
            if mname == 'theory' and set_name == 'transfer':
                continue
            marms = arms if mname == 'calibrated' else ['random', 'eig', g]
            for row in worlds[set_name]:
                w = World(row, models[mname])
                new = []
                for arm in marms:
                    acq = acquisition(arm, row['prep'], row['truth'], lam, invented)
                    if arm == 'random':
                        for o in range(R_RANDOM):
                            if (set_name, mname, arm, row['seed'], o) not in done:
                                new.append(full_row(w, set_name, mname, arm, acq, rng_for(row['seed'], o), order=o))
                    elif (set_name, mname, arm, row['seed'], None) not in done:
                        new.append(full_row(w, set_name, mname, arm, acq,
                                            beliefs_at=4 if (arm == g and set_name == 'test') else None))
                with rpath.open('a') as f:
                    for r in new:
                        f.write(json.dumps(r, sort_keys=True) + '\n')
                rows.extend(new)
            log(f'{set_name} / {mname}: done')
    valid = checks(rows)
    if not valid:
        (out / 'summary.json').write_text(json.dumps({'study': STUDY, 'valid': False}, indent=1) + '\n')
        log('INVALID')
        return 1
    res = analyse(rows, choice)
    res['calibration'] = {m: calibration_stats(rows, m) for m in models}
    res['instrument_confusion_test'] = instrument_confusion(worlds['test'])
    res['prepare_cpu_s'] = {s: round(sum(r['cpu_s'] for r in worlds[s]), 3) for s in SETS}
    res['search_cpu_s'] = [s['cpu_s'] for s in searches]
    summary = dict(res, study=STUDY, schema='genesis-b20r129-adaptive-scientist-v1', valid=valid, runs=len(rows),
                   lam=lam, choice=choice, code_identity=code_identity(ROOT)['sha256'], status='DEV; licenses nothing')
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True, default=float) + '\n')
    t = res['test']
    log(f"valid {valid}; verdict {res['verdict']}; T1 {t['T1']['label']} (p {t['T1']['p']:.3g}); "
        f"T2 {t['T2']['label']} (p {t['T2']['p']:.3g}); needed " +
        ', '.join(f"{a} {v['needed']:.2f}" for a, v in t['means'].items()))
    return 0


if __name__ == '__main__':
    sys.exit(main())
