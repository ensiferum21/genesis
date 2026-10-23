#!/usr/bin/env python3
"""B20_R103: can Genesis's improvers tell progress from noise? The feedback contract and the zero-signal battery
(Daniel's research alert of 22 Oct 2026; DEV, preregistered)

    python3 scripts/b20r103_zero_signal.py OUT_DIR       run (CPU only, no solver runs) and analyse

**Why.** `docs/RESEARCH_ALERTS.md`: iterative agents manufacture gains by optimising against the same evaluation
data, and a feedback contract cuts the spurious gain. Genesis's claims are judged on fresh hosts. Its improvers,
however, select on repeated training feedback: the program search (B20_R79–R85) and the research loop's analyses.
They have never been shown to stop where there is nothing to find. This study shows whether they do, with and without
the contract (`autonomy.feedback`).

**Design (fixed before running).**
  * **L1, the program search.** Genesis's own search (`feedback.steady_state_search`, `solver_search`'s algorithm)
    over its real solver language (`solver_programs` random programs, mutation and crossover; the licensed
    representations), 1,500 evaluations per search, as in B20_R79–R85. It is scored by an *oracle* whose truth is
    known: value(p, split) = beta * g(p) + q_split(p) + e.
      - e ~ N(0, sigma_e) is fresh on every evaluation.
      - q_split(p) ~ N(0, sigma_q) is a quirk, fixed per program and split. It is what a fixed set of training hosts
        adds or takes away.
      - sigma_e is the pooled standard deviation of repeated evaluations of the same program in the four recorded
        searches (computed from their `history.jsonl`).
      - sigma_q is in {0, 1, 2} x sigma_e.
      - **No signal:** beta = 0, so every program is equally good.
      - **Planted signal:** g(p) = min(number of `descent` statements, 4), and beta = 2 sigma_e. A real effect of up
        to 8 sigma_e (about 1.2 edges), built step by step, as real progress is.
  * **Protocols.**
      - *Open:* today's practice. The search reports its winner's mean of 4 fresh training evaluations.
      - *Contract:* the judge holds a confirmation split, with a fixed threshold, one evaluation per distinct program,
        and a stop after 40 generations without a release. The search reports the released confirmation score; the
        final number is measured on held-out test data (split T).
  * **Replicates.** REPS = 60 searches per (signal, sigma_q, protocol), seeds from SEED.
  * **Measures, per search.**
      - *Claimed gain*, the improvement the worker would report through its own channel. Open: its final training
        mean minus the initial incumbent's first training score. Contract: its released score minus the start's
        confirmation score; it is 0 unless something was released.
      - *Final optimism*: the final number minus the winner's truth, where truth is beta * g(winner). Open: the
        training mean. Contract: a fresh evaluation on held-out test data (split T).
      - *True gain*: the winner's truth minus the initial incumbent's. The initial incumbent is the initial
        population's best by its first training score, the same in both protocols.
      - Releases, and whether the search stopped before its budget.
  * **L2, the research loop's analyses on identical arms.**
      - SIMS = 400 synthetic quality-at-equal-time studies (56 hosts, looks at 19/38/56, margin 0.002, alpha 0.1:
        `anytime.sequential`, as B20_R97). Both arms draw per-host scores from one distribution: host level from
        B20_R97's focal arm, per-arm noise with B20_R97's paired sd.
      - SIMS synthetic time-to-target comparisons (24 hosts, the quantile-ratio labels of B20_R81/R86) with
        identical arms.
      - Measured: the rate of a "better" verdict (either direction).
  * **Labels.**
      - *L1 with no signal:* CONTRACT_HOLDS if, for every sigma_q, the contract's mean claimed gain is at most a
        quarter of the open protocol's and below sigma_e; otherwise CONTRACT_LEAKS.
      - *L1 with the planted signal:* POWER_KEPT if, for every sigma_q, the contract's mean true gain is at least
        half the open protocol's; otherwise TOO_STRICT.
      - *L2:* CALIBRATED if both false-"better" rates are at most alpha = 0.10; otherwise OVERCONFIDENT.
      - *Headline:* CONTRACT_WORKS (HOLDS and POWER_KEPT), CONTRACT_TOO_STRICT, or CONTRACT_LEAKS. L2 is reported
        beside it.

**Expectation, stated before running.**
- Open: a claimed gain of 2–6 sigma_e with no signal, growing with sigma_q. This is the alert's effect in Genesis's
  own search.
- Contract: a claimed gain near zero, a final optimism near zero (held-out data), and an early stop in most
  no-signal runs.
- Power: kept at sigma_q = 0. At 2 sigma_e, tau (3 x the upper confidence limit of sqrt(2) x sqrt(5) sigma_e, about
  11 sigma_e) exceeds the whole planted effect (8 sigma_e), so the contract cannot release it there. So
  CONTRACT_TOO_STRICT is expected: the price of not mistaking noise for progress is missing real effects smaller than
  the noise of one confirmation. Larger confirmation data, which shrinks sigma_q, is the remedy the battery points to.

**Development looks (disclosed).** The contract was built against the oracle with development-only seeds (study
"dev-only", seed 777), 4 searches per condition. With a first threshold (Z = 2.5, tau from 16 programs), it released
noise in 2 of 8 no-signal searches. The threshold was then set before this preregistration: Z = 3, tau from 32
programs at the 90% upper confidence limit, patience 40. After that it released none of 8, and still released the
planted effect at sigma_q = 0. The study's seeds differ (SEED).
- L2: CALIBRATED, because the margin and Bonferroni looks are conservative.

**Status.** DEV; licenses nothing; no package changes.
"""
import hashlib
import json
from pathlib import Path
import random
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis.common import code_identity, digest  # noqa: E402

STUDY = 'b20r103'
SEED = 20270301
REPS, MAX_EVALS, SIMS = 60, 1500, 400
BETA = 2.0                       # the planted effect per `descent` statement, in sigma_e (up to 4 statements)
Q_MULTIPLES = (0.0, 1.0, 2.0)
HISTORIES = ('program_search_b20r79', 'generation2_b20r83', 'generation2_control_b20r84', 'generation3_b20r85')
QET = {'hosts': 56, 'looks': (19, 38, 56), 'delta': 0.002, 'alpha': 0.10, 'resamples': 2000}
TTS = {'hosts': 24, 'ladder': (0.05, 0.1, 0.25, 0.5, 2.0), 'reps': 3}


def sigma_e():
    """Pooled sd of repeated evaluations of one program in the recorded searches."""
    num = den = 0.0
    for name in HISTORIES:
        by = {}
        for line in (ROOT / 'evidence' / name / 'history.jsonl').read_text().splitlines():
            if line.strip():
                h = json.loads(line)
                by.setdefault(json.dumps(h.get('program') or [h['body'], h['rep']], sort_keys=True), []).append(h['mean'])
        for v in by.values():
            if len(v) >= 3:
                num += statistics.pvariance(v) * len(v)
                den += len(v)
    return (num / den) ** 0.5


def descents(program):
    n = 0

    def walk(b):
        nonlocal n
        for s in b:
            if s[0] == 'descent':
                n += 1
            elif s[0] in ('repeat',):
                walk(s[2])
            elif s[0] == 'loop':
                walk(s[1])
            elif s[0] == 'split':
                walk(s[2])
                walk(s[3])
    walk(program['body'])
    return n


class Oracle:
    """value(p, split) = beta * g(p) + quirk(p, split) + fresh noise; truth(p) = beta * g(p)."""

    def __init__(self, beta, s_e, s_q, seed):
        self.beta, self.s_e, self.s_q, self.seed = beta, s_e, s_q, seed
        self.rng = random.Random(seed)

    def truth(self, p):
        return self.beta * min(descents(p), 4)

    def quirk(self, p, split):
        h = int(hashlib.sha256(json.dumps([self.seed, split, p], sort_keys=True).encode()).hexdigest()[:15], 16)
        return self.s_q * random.Random(h).gauss(0, 1)

    def __call__(self, p, split):
        return self.truth(p) + self.quirk(p, split) + self.rng.gauss(0, self.s_e)


def language_ops():
    from genesis.candidate_kinds import solver_program as KP
    from genesis.invention import solver_programs as SP
    reps = list(KP.licensed_reps('triangle_free_host_v1'))
    return {'random': lambda rng: SP.random_program(rng, reps), 'mutate': lambda p, rng: SP.mutate(p, rng, reps),
            'crossover': lambda a, b, rng: SP.crossover(a, b, rng, reps), 'size': SP.size}


def one_search(ops, signal, q_mult, protocol, rep, s_e):
    from genesis.autonomy import feedback as FB
    seed = int(digest({'study': STUDY, 'signal': signal, 'q': q_mult, 'rep': rep})[:12], 16) ^ SEED
    oracle = Oracle(BETA * s_e if signal == 'planted' else 0.0, s_e, q_mult * s_e, seed)
    calls = []

    def evaluate(p, split):                            # the oracle, recording what the worker's channel saw
        v = oracle(p, split)
        calls.append((json.dumps(p, sort_keys=True), split, v))
        return v
    winner, rep_ = FB.steady_state_search(ops, evaluate, MAX_EVALS, seed, contract=(protocol == 'contract'))
    # the initial incumbent: the initial population's best by its first A evaluation (identical in both protocols)
    first = {}
    for key, split, v in calls[:FB.POP]:
        first.setdefault(key, v)
    start_key = max(first, key=lambda k: (first[k], -len(k), k))
    start = json.loads(start_key)
    if protocol == 'open':
        claimed = rep_['reported'] - first[start_key]
        final = rep_['reported']                        # today's practice: the training mean is the number
    else:
        claimed = rep_['reported'] - rep_['judge']['start']
        final = oracle(winner, 'T')                    # the contract's final number: held-out test data
    return {'signal': signal, 'q': q_mult, 'protocol': protocol, 'rep': rep, 'reported': rep_['reported'],
            'claimed_gain': claimed, 'final': final, 'truth': oracle.truth(winner),
            'final_optimism': final - oracle.truth(winner), 'true_gain': oracle.truth(winner) - oracle.truth(start),
            'evaluations': rep_['evaluations'], 'generations': rep_['generations'], 'judge': rep_['judge']}


# -------------------------------------------------------------------------------- L2: analyses on identical arms

def qet_false_rate(rng):
    from genesis import anytime as AT
    false = 0
    for k in range(SIMS):
        host = [min(1.0, rng.gauss(0.995, 0.004)) for _ in range(QET['hosts'])]
        a = [min(1.0, h + rng.gauss(0, 0.0015)) for h in host]
        b = [min(1.0, h + rng.gauss(0, 0.0015)) for h in host]
        r = AT.sequential(a, b, QET['looks'], QET['delta'], QET['alpha'], resamples=QET['resamples'], seed=SEED + k)
        false += r['verdict'] in ('A_BETTER', 'B_BETTER')
    return false / SIMS


def tts_false_rate(rng):
    import b20r86_generations_eval as R86
    import math
    false = 0
    for k in range(SIMS):
        T = {'a': [], 'b': []}
        for _ in range(TTS['hosts']):
            hard = rng.random()                         # one host difficulty, shared by both arms
            for arm in ('a', 'b'):
                best = math.inf
                for t in TTS['ladder']:
                    p = min(1.0, max(0.0, t / (0.05 + 1.5 * hard)) * rng.uniform(0.6, 1.0))
                    s = sum(rng.random() < p for _ in range(TTS['reps'])) / TTS['reps']
                    v = t if s >= 1 else (math.inf if s <= 0 else t * math.ceil(math.log(0.01) / math.log(1 - s)))
                    best = min(best, v)
                T[arm].append(best)
        p = R86.pair(T, 'a', 'b')
        false += any(p[f'q{q}']['verdict'] in ('A_FASTER', 'B_FASTER') for q in R86.QS)
    return false / SIMS


# -------------------------------------------------------------------------------- labels

def labels(rows, s_e, qet_rate, tts_rate):
    def mean(signal, q, protocol, key):
        return statistics.mean(r[key] for r in rows if (r['signal'], r['q'], r['protocol']) == (signal, q, protocol))
    holds = all(mean('none', q, 'contract', 'claimed_gain') <= 0.25 * mean('none', q, 'open', 'claimed_gain')
                and mean('none', q, 'contract', 'claimed_gain') < s_e for q in Q_MULTIPLES)
    power = all(mean('planted', q, 'contract', 'true_gain') >= 0.5 * mean('planted', q, 'open', 'true_gain')
                for q in Q_MULTIPLES)
    l1_null = 'CONTRACT_HOLDS' if holds else 'CONTRACT_LEAKS'
    l1_signal = 'POWER_KEPT' if power else 'TOO_STRICT'
    head = 'CONTRACT_LEAKS' if not holds else ('CONTRACT_WORKS' if power else 'CONTRACT_TOO_STRICT')
    l2 = 'CALIBRATED' if qet_rate <= QET['alpha'] and tts_rate <= QET['alpha'] else 'OVERCONFIDENT'
    return {'l1_no_signal': l1_null, 'l1_planted_signal': l1_signal, 'headline': head, 'l2': l2}


def table(rows):
    out = {}
    for signal in ('none', 'planted'):
        for q in Q_MULTIPLES:
            for protocol in ('open', 'contract'):
                rs = [r for r in rows if (r['signal'], r['q'], r['protocol']) == (signal, q, protocol)]
                out[f'{signal}|q{q:g}|{protocol}'] = {
                    'searches': len(rs), 'mean_claimed_gain': statistics.mean(r['claimed_gain'] for r in rs),
                    'mean_final_optimism': statistics.mean(r['final_optimism'] for r in rs),
                    'mean_true_gain': statistics.mean(r['true_gain'] for r in rs),
                    'mean_releases': statistics.mean(r['judge']['releases'] for r in rs) if protocol == 'contract' else None,
                    'stopped_early': sum(bool(r['judge'] and r['judge']['stopped']) for r in rs),
                    'mean_evaluations': statistics.mean(r['evaluations'] for r in rs)}
    return out


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        raise SystemExit(__doc__.splitlines()[2])
    out = Path(argv[0]).resolve()
    if out != (ROOT / 'evidence' / 'zero_signal_b20r103').resolve():
        raise SystemExit('the registered output is evidence/zero_signal_b20r103')
    out.mkdir(parents=True, exist_ok=True)
    s_e = sigma_e()
    ops = language_ops()
    rows_path = out / 'searches.jsonl'
    rows = [json.loads(l) for l in rows_path.read_text().splitlines() if l.strip()] if rows_path.exists() else []
    done = {(r['signal'], r['q'], r['protocol'], r['rep']) for r in rows}
    with rows_path.open('a') as f:
        for signal in ('none', 'planted'):
            for q in Q_MULTIPLES:
                for rep in range(REPS):
                    for protocol in ('open', 'contract'):
                        if (signal, q, protocol, rep) in done:
                            continue
                        r = one_search(ops, signal, q, protocol, rep, s_e)
                        rows.append(r)
                        f.write(json.dumps(r, sort_keys=True) + '\n')
                        f.flush()
            print(f'{signal} done', flush=True)
    rng = random.Random(SEED)
    qet_rate, tts_rate = qet_false_rate(rng), tts_false_rate(rng)
    summary = {'study': STUDY, 'schema': 'genesis-b20r103-zero-signal-v1', 'sigma_e': s_e,
               'labels': labels(rows, s_e, qet_rate, tts_rate), 'l1': table(rows),
               'l2': {'qet_false_better_rate': qet_rate, 'tts_false_faster_rate': tts_rate, 'sims': SIMS},
               'constants': {'reps': REPS, 'max_evals': MAX_EVALS, 'q_multiples': Q_MULTIPLES, 'qet': QET, 'tts': TTS},
               'code_identity': code_identity(ROOT)['sha256'],
               'status': 'DEV; licenses nothing; no package changed'}
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n')
    print(json.dumps(summary['labels']), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
