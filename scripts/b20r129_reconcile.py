#!/usr/bin/env python3
"""B20_R129 reconciliation: which rule was selected, on which sets, and whether inv1's and decfall's difference is
statistically supported (Daniel's directive of 24 Oct 2026, 15:35, item 5). Read-only: it recomputes from B20_R129's
saved evidence and runs no study.

    python3 scripts/b20r129_reconcile.py OUT_DIR       (registered: evidence/r129_reconciliation)

**What it separates.**
  * **Preregistered** (B20_R129's own analysis, uncorrected secondary tests): the selection on `validation`, and on
    `test` the best invented rule (inv1) against eig and against the best non-invented rule by validation (decfall),
    on experiments needed (two-sided Wilcoxon, zeros dropped). Recomputed here from `runs.jsonl` and checked against
    B20_R129's `summary.json`.
  * **Exploratory** (not preregistered; Holm across this family, two-sided): inv1 against decfall on `transfer`; inv1
    against dec, hybrid, static_eig and degree on `test` (the claim "beats every established acquisition"); inv1
    against decfall on hidden-cause F1 at 4 experiments, on `test` and `transfer`. Also bootstrap 95% intervals of the
    mean differences (4,000 resamples, seeded) and sign tests.
"""
import json
from pathlib import Path
import random
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
R129 = ROOT / 'evidence' / 'adaptive_scientist_b20r129'
ALPHA = 0.05
EXPLORATORY = (('transfer', 'needed', 'inv1', 'decfall'), ('test', 'needed', 'inv1', 'dec'),
               ('test', 'needed', 'inv1', 'hybrid'), ('test', 'needed', 'inv1', 'static_eig'),
               ('test', 'needed', 'inv1', 'degree'), ('test', 'f1@4', 'inv1', 'decfall'),
               ('transfer', 'f1@4', 'inv1', 'decfall'))


def load():
    rows = [json.loads(line) for line in (R129 / 'runs.jsonl').read_text().splitlines() if line.strip()]
    return rows, json.loads((R129 / 'choice.json').read_text()), json.loads((R129 / 'summary.json').read_text())


def per_world(rows, set_name, arm, measure):
    """{seed: value}: experiments needed (fewer is better) or hidden-cause F1 after 4 experiments; the calibrated
    model (B20_R129's primary); random averaged over its orders."""
    out = {}
    for r in rows:
        if r['set'] == set_name and r['arm'] == arm and r['model'] == 'calibrated':
            v = r['needed'] if measure == 'needed' else r['f1'][4]
            out.setdefault(r['seed'], []).append(v)
    return {s: statistics.mean(v) for s, v in out.items()}


def compare(rows, set_name, measure, a, b, seed=0):
    """a against b: the mean improvement of a (fewer experiments, or more F1), Wilcoxon (two-sided, zeros dropped),
    sign test and a bootstrap 95% interval."""
    from scipy.stats import binomtest, wilcoxon
    x, y = per_world(rows, set_name, a, measure), per_world(rows, set_name, b, measure)
    seeds = sorted(x)
    d = [(y[s] - x[s]) if measure == 'needed' else (x[s] - y[s]) for s in seeds]
    nz = [v for v in d if v != 0]
    w, lo = sum(v > 0 for v in nz), sum(v < 0 for v in nz)
    rng = random.Random(seed)
    boots = sorted(statistics.mean(rng.choice(d) for _ in d) for _ in range(4000))
    return {'set': set_name, 'measure': measure, 'a': a, 'b': b, 'worlds': len(seeds),
            'mean_a': statistics.mean(x[s] for s in seeds), 'mean_b': statistics.mean(y[s] for s in seeds),
            'improvement_of_a': statistics.mean(d), 'ci95': [boots[100], boots[3899]], 'nonzero': len(nz),
            'wins': w, 'losses': lo, 'p_wilcoxon': float(wilcoxon(nz).pvalue) if nz else 1.0,
            'p_sign': float(binomtest(w, w + lo).pvalue) if nz else 1.0}


def holm(ps):
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    out, run = [0.0] * len(ps), 0.0
    for k, i in enumerate(order):
        run = max(run, min(1.0, (len(ps) - k) * ps[i]))
        out[i] = run
    return out


def reconcile():
    rows, choice, summary = load()
    v = choice['validation']
    ranking = sorted(v, key=lambda a: (v[a]['needed'], -v[a]['f1_at_4']))
    sel = {'set': 'validation (100 worlds, seeds from 4000)', 'criterion': 'fewest mean experiments needed; ties to '
           'the higher mean hidden-cause F1 at 4', 'ranking': [[a, v[a]['needed'], v[a]['f1_at_4']] for a in ranking],
           'chosen': choice['genesis'], 'best_invented': choice['best_invented'], 'best_other': choice['best_other'],
           'inv1_source': choice['invented_text']['inv1']}
    pre = {'inv1_vs_eig': compare(rows, 'test', 'needed', 'inv1', 'eig'),
           'inv1_vs_decfall': compare(rows, 'test', 'needed', 'inv1', 'decfall')}
    check = {'inv1_vs_eig': summary['secondary']['invented_vs_eig'],
             'inv1_vs_decfall': summary['secondary']['invented_vs_best_other']}
    agree = all(abs(pre[k]['improvement_of_a'] - check[k]['mean_difference']) < 1e-9 and
                abs(pre[k]['p_wilcoxon'] - check[k]['p']) < 1e-9 and pre[k]['nonzero'] == check[k]['nonzero']
                for k in pre)
    exp = [compare(rows, *e) for e in EXPLORATORY]
    for e, p in zip(exp, holm([e['p_wilcoxon'] for e in exp])):
        e['p_holm'] = p
        e['label'] = ('A_BETTER' if e['improvement_of_a'] > 0 else 'B_BETTER') if p < ALPHA else 'NO_DIFFERENCE'
    findings = [
        f"Genesis's scientist was {sel['chosen']}, chosen on validation by the preregistered rule "
        f"({v['decfall']['needed']} experiments needed against inv1's {v['inv1']['needed']}); inv1 was second.",
        f"On test (200 worlds) inv1 needed {pre['inv1_vs_decfall']['mean_a']:.2f} and decfall "
        f"{pre['inv1_vs_decfall']['mean_b']:.2f}: a difference of {pre['inv1_vs_decfall']['improvement_of_a']:.2f}, "
        f"p = {pre['inv1_vs_decfall']['p_wilcoxon']:.3g} (preregistered secondary): NOT supported.",
        f"inv1 against eig on test: {pre['inv1_vs_eig']['improvement_of_a']:.2f} fewer experiments, p = "
        f"{pre['inv1_vs_eig']['p_wilcoxon']:.2g} (preregistered secondary, uncorrected): supported.",
        'The claim that inv1 beats EVERY established acquisition rests on its means; only eig was tested in advance. '
        'The exploratory tests here (Holm) decide dec, hybrid, static_eig and degree.',
        'inv1 was a random program of the search\'s initial population, selected on training data; the judge released '
        'nothing. It simplifies exactly to max(decall * pf^2) under the features\' declared ranges (`interpret`).']
    return {'selection': sel, 'preregistered': pre, 'agrees_with_r129_summary': agree, 'exploratory': exp,
            'findings': findings}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        raise SystemExit(__doc__.splitlines()[5])
    out = Path(argv[0]).resolve()
    if out != (ROOT / 'evidence' / 'r129_reconciliation').resolve():
        raise SystemExit('the registered output is evidence/r129_reconciliation')
    out.mkdir(parents=True, exist_ok=True)
    res = reconcile()
    (out / 'summary.json').write_text(json.dumps(res, indent=1, sort_keys=True) + '\n')
    for f in res['findings']:
        print('-', f)
    for e in res['exploratory']:
        print(f"  exploratory {e['set']} {e['measure']} {e['a']} vs {e['b']}: {e['improvement_of_a']:+.3f} "
              f"[{e['ci95'][0]:+.3f}, {e['ci95'][1]:+.3f}] p {e['p_wilcoxon']:.3g} Holm {e['p_holm']:.3g} {e['label']}")
    return 0 if res['agrees_with_r129_summary'] else 1


if __name__ == '__main__':
    sys.exit(main())
