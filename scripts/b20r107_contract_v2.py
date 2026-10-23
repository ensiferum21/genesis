#!/usr/bin/env python3
"""B20_R107: the feedback contract, version 2: can the judge stay honest and keep its power? (DEV, preregistered)

    taskset -c 0 python3 scripts/b20r107_contract_v2.py OUT_DIR      run ALONE (CPU only, no solver runs), then analyse

**Why.** B20_R103 (`evidence/zero_signal_b20r103/`): without the contract, Genesis's program search over-reports by up
to 6.6 sigma_e on a problem with nothing to find; with it (version 1), the search stops and its held-out numbers are
honest, but it keeps only 13% of a real effect where the evaluation data have large quirks. The cause is in the
calibration: version 1 sets its threshold from A - B differences, which carry the worker's own training quirks as well
as the judge's, so the threshold grows with them (5.1, 7.2 and 11.4 sigma_e). Version 2 (`autonomy.feedback`,
`calibrate='BC'`) holds two confirmation splits and sets the threshold from B - C differences, the judge's own noise,
and each confirmation is the mean of K_HOSTS hosts, charged to the budget. This is the second level improving the
first: the judge that decides what counts as progress is itself improved, and tested on the same battery.
Also, B20_R103's headline rule compared the contract with a fraction of the open protocol's claimed gain, which can
be negative; here every label compares with the truth.

**Design (fixed before running).** B20_R103's battery, with fresh seeds:
  * **The search and the oracle** as B20_R103: Genesis's own program search over its real solver language, 1,500
    evaluations; value(p, split) = beta * g(p) + quirk(p, split) + fresh noise; sigma_e from the recorded searches;
    quirk sd in {0, 1, 2} x sigma_e; no signal (beta = 0) or a planted one (beta = 2 sigma_e per `descent`, up to 4).
  * **Protocols:** open (today's practice); contract v1 (B20_R103's: calibration on A - B, one host per confirmation,
    each evaluation costing 1); contract v2 (calibration on B - C; B and C each the mean of K_HOSTS = 4 hosts, each
    with its own quirk and noise, costing 4 evaluations). Both contracts report a held-out final number (split T).
    REPS = 60 searches per (signal, quirk, protocol): 1,080 searches.
  * **Labels, per contract version (all against the truth):**
      - HOLDS if, at every quirk level with no signal: at most 10% of searches release anything, the mean claimed gain
        is at most 0.25 sigma_e, and the mean final optimism (held-out number minus truth) is within +-0.25 sigma_e.
      - POWER_KEPT if, at every quirk level with the planted signal, the contract's mean true gain is at least half
        the open protocol's.
      - WORKS (HOLDS and POWER_KEPT), TOO_STRICT (HOLDS only) or LEAKS (not HOLDS).
  * **Headline:** V2_FIXES_POWER if v2 WORKS and v1 does not keep power; BOTH_WORK; V2_TOO_STRICT; V2_LEAKS.

**Development looks (disclosed).** None for version 2: it was never run on the oracle before this design was fixed. B20_R103's
numbers (version 1) are known and inform the expectation.

**Expectation, stated before running.** Version 1 as in B20_R103: it holds, and under the truth-based rule it is
TOO_STRICT (power lost at quirk 2). Version 2 holds too (release share under 10%, unbiased finals). Its threshold, from
the judge's own noise over 4 hosts, should be about 2.5, 3.6 and 5.7 sigma_e at the three quirk levels against version
1's 5, 7 and 11. So it keeps at least half the open protocol's real gain at quirks 0 and 1, and about half at quirk
2. V2_FIXES_POWER slightly more likely than V2_TOO_STRICT.
**Cost.** About 10 minutes on one core. **Status.** DEV; licenses nothing.
"""
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis.common import code_identity, digest  # noqa: E402
import b20r103_zero_signal as R103  # noqa: E402

STUDY = 'b20r107'
SEED = 20271071
REPS, MAX_EVALS, K_HOSTS = 60, 1500, 4
Q_MULTIPLES = R103.Q_MULTIPLES
PROTOCOLS = ('open', 'v1', 'v2')
MAX_RELEASE_SHARE, MAX_BIAS = 0.10, 0.25          # in searches; in sigma_e


def one_search(ops, signal, q_mult, protocol, rep, s_e):
    from genesis.autonomy import feedback as FB
    seed = int(digest({'study': STUDY, 'signal': signal, 'q': q_mult, 'rep': rep})[:12], 16) ^ SEED
    oracle = R103.Oracle(R103.BETA * s_e if signal == 'planted' else 0.0, s_e, q_mult * s_e, seed)
    calls = []

    def evaluate(p, split):
        if protocol == 'v2' and split in ('B', 'C'):
            v = statistics.mean(oracle(p, f'{split}{i}') for i in range(K_HOSTS))
        else:
            v = oracle(p, split)
        calls.append((json.dumps(p, sort_keys=True), split, v))
        return v
    kw = {'contract': protocol != 'open'}
    if protocol == 'v2':
        kw.update(calibrate='BC', cost={'B': K_HOSTS, 'C': K_HOSTS})
    winner, rep_ = FB.steady_state_search(ops, evaluate, MAX_EVALS, seed, **kw)
    first = {}
    for key, split, v in calls[:FB.POP]:
        first.setdefault(key, v)
    start_key = max(first, key=lambda k: (first[k], -len(k), k))
    start = json.loads(start_key)
    if protocol == 'open':
        claimed, final = rep_['reported'] - first[start_key], rep_['reported']
    else:
        claimed, final = rep_['reported'] - rep_['judge']['start'], oracle(winner, 'T')
    return {'signal': signal, 'q': q_mult, 'protocol': protocol, 'rep': rep, 'reported': rep_['reported'],
            'claimed_gain': claimed, 'final': final, 'truth': oracle.truth(winner),
            'final_optimism': final - oracle.truth(winner), 'true_gain': oracle.truth(winner) - oracle.truth(start),
            'evaluations': rep_['evaluations'], 'generations': rep_['generations'], 'judge': rep_['judge']}


def table(rows):
    out = {}
    for signal in ('none', 'planted'):
        for q in Q_MULTIPLES:
            for protocol in PROTOCOLS:
                rs = [r for r in rows if (r['signal'], r['q'], r['protocol']) == (signal, q, protocol)]
                out[f'{signal}|q{q:g}|{protocol}'] = {
                    'searches': len(rs), 'mean_claimed_gain': statistics.mean(r['claimed_gain'] for r in rs),
                    'mean_final_optimism': statistics.mean(r['final_optimism'] for r in rs),
                    'mean_true_gain': statistics.mean(r['true_gain'] for r in rs),
                    'release_share': (statistics.mean(r['judge']['releases'] > 0 for r in rs)
                                      if protocol != 'open' else None),
                    'mean_tau': statistics.mean(r['judge']['tau'] for r in rs) if protocol != 'open' else None,
                    'stopped_early': sum(bool(r['judge'] and r['judge']['stopped']) for r in rs),
                    'mean_evaluations': statistics.mean(r['evaluations'] for r in rs)}
    return out


def labels(tab, s_e):
    out = {}
    for v in ('v1', 'v2'):
        holds = all(tab[f'none|q{q:g}|{v}']['release_share'] <= MAX_RELEASE_SHARE
                    and tab[f'none|q{q:g}|{v}']['mean_claimed_gain'] <= MAX_BIAS * s_e
                    and abs(tab[f'none|q{q:g}|{v}']['mean_final_optimism']) <= MAX_BIAS * s_e for q in Q_MULTIPLES)
        power = all(tab[f'planted|q{q:g}|{v}']['mean_true_gain'] >= 0.5 * tab[f'planted|q{q:g}|open']['mean_true_gain']
                    for q in Q_MULTIPLES)
        out[v] = {'holds': holds, 'power_kept': power,
                  'label': 'LEAKS' if not holds else ('WORKS' if power else 'TOO_STRICT'),
                  'power_ratio': {f'q{q:g}': (tab[f'planted|q{q:g}|{v}']['mean_true_gain']
                                              / tab[f'planted|q{q:g}|open']['mean_true_gain']
                                              if tab[f'planted|q{q:g}|open']['mean_true_gain'] else None)
                                  for q in Q_MULTIPLES}}
    v1, v2 = out['v1'], out['v2']
    if v2['label'] == 'LEAKS':
        head = 'V2_LEAKS'
    elif v2['label'] == 'TOO_STRICT':
        head = 'V2_TOO_STRICT'
    else:
        head = 'BOTH_WORK' if v1['power_kept'] else 'V2_FIXES_POWER'
    out['headline'] = head
    return out


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        raise SystemExit(__doc__.splitlines()[2])
    out = Path(argv[0]).resolve()
    if out != (ROOT / 'evidence' / 'contract_v2_b20r107').resolve():
        raise SystemExit('the registered output is evidence/contract_v2_b20r107')
    out.mkdir(parents=True, exist_ok=True)
    import b20r33_strong_baseline_audit as R33
    R33.pinned_core()
    s_e = R103.sigma_e()
    ops = R103.language_ops()
    path = out / 'searches.jsonl'
    rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()] if path.exists() else []
    done = {(r['signal'], r['q'], r['protocol'], r['rep']) for r in rows}
    with path.open('a') as f:
        for signal in ('none', 'planted'):
            for q in Q_MULTIPLES:
                for rep in range(REPS):
                    for protocol in PROTOCOLS:
                        if (signal, q, protocol, rep) in done:
                            continue
                        r = one_search(ops, signal, q, protocol, rep, s_e)
                        rows.append(r)
                        f.write(json.dumps(r, sort_keys=True) + '\n')
                        f.flush()
            print(f'{signal} done', flush=True)
    tab = table(rows)
    lab = labels(tab, s_e)
    summary = {'study': STUDY, 'schema': 'genesis-b20r107-contract-v2-v1', 'sigma_e': s_e, 'labels': lab, 'table': tab,
               'constants': {'reps': REPS, 'max_evals': MAX_EVALS, 'k_hosts': K_HOSTS, 'q_multiples': Q_MULTIPLES,
                             'max_release_share': MAX_RELEASE_SHARE, 'max_bias': MAX_BIAS},
               'code_identity': code_identity(ROOT)['sha256'], 'status': 'DEV; licenses nothing; no package changed'}
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n')
    print(json.dumps({k: (v['label'] if isinstance(v, dict) else v) for k, v in lab.items()}), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
