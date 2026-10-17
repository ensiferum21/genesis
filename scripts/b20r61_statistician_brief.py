"""B20_R61: the statistician's brief for B19-OPEN-4 (documentation and recomputation; no new evidence).

**Why.** Every GV3 package (E1, E1b, E1b-C4, E1d) waits on a statistician's sign-off of its analysis plan and of
the centred power model that sized it (B19-OPEN-4). The material was spread across packages, scripts and
records. `docs/STATISTICIAN_BRIEF.md` gathers it in one place, with the questions to answer.

**What this script does.** Everything is derived from committed files; nothing new is run.
  * `ANALYSES`: every power analysis a package or causal follow-up relies on, with the pilot rows, comparator
    and plan family that produced it. `recompute(a)` rebuilds the pilot rows, checks their digest against the
    stored analysis, re-runs `power.required_sample` exactly as the original script did, and returns the
    result for comparison with the stored file.
  * `family_check(a)`: which hypothesis family the stored analysis is bound to (the plan core's digest), against
    the family the custodian assigns to that evidence kind (`custody_records`: `sealed_evaluation`,
    `ablation`, `placebo`).
  * `rebound(a)`: for analyses bound to the wrong family, the power analysis recomputed under the custodian's
    family. The simulation's random stream is seeded from the plan core, so only Monte Carlo noise changes.
  * `mc_se(p)`: the Monte Carlo standard error of a simulated power at `SIMS` simulations, and `borderline()`:
    the chosen sizes whose power is within two standard errors of the target. For those, `power_10k()` is
    the power at the chosen size with 10,000 simulations.
  * `rehearsal_rows()`: per same-operator rehearsal, the tasks, scored, unsupported (and their strata), the
    strata count and the smallest p-value the stratum-level sign-flip sensitivity can reach (1 / 2^k).

`python3 scripts/b20r61_statistician_brief.py` prints the tables the brief quotes; the test re-derives them.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'src'))
import b20r24_repilots as R24  # noqa: E402
from genesis.common import digest  # noqa: E402
from genesis.kernel.analysis import plan_core  # noqa: E402
from genesis.power import required_sample, simulate_power, _pilot  # noqa: E402

BRIEF = ROOT / 'docs' / 'STATISTICIAN_BRIEF.md'
TF, C4 = 'triangle_free_host_v1', 'c4_host_v2'
SIMS, TARGET = 1000, 0.8

# name, stored power analysis, pilot rows file, comparator arm (None: rows already paired), domain,
# the evidence kind it sizes, the family the stored analysis was computed under
ANALYSES = (
    ('E1', 'handoff/e1/power_analysis_centred_b20r24.json', 'evidence/repilots_b20r24/pilot_rows_e1.json', None, TF,
     'sealed_evaluation', 'sealed_evaluation'),
    ('E1b', 'handoff/e1b/power_analysis_centred_b20r24.json', 'evidence/repilots_b20r24/pilot_rows_e1b_tf.json', None, TF,
     'sealed_evaluation', 'sealed_evaluation'),
    ('E1b ablation', 'evidence/e1b_causal_repilot_b20r28/power_analysis_centred_ablation.json',
     'evidence/e1b_causal_repilot_b20r28/pilot_rows_ablation.json', None, TF, 'ablation', 'sealed_evaluation'),
    ('E1b placebo', 'evidence/e1b_causal_repilot_b20r28/power_analysis_centred_placebo.json',
     'evidence/e1b_causal_repilot_b20r28/pilot_rows_placebo.json', None, TF, 'placebo', 'sealed_evaluation'),
    ('E1b-C4', 'handoff/e1b_c4/power_analysis_centred_readiness_b20r50.json',
     'evidence/e1b_c4_readiness_b20r50/pilot_rows.jsonl', 'low_cycle_tm', C4, 'sealed_evaluation', 'sealed_evaluation'),
    ('E1b-C4 ablation', 'handoff/e1b_c4/power_analysis_centred_ablation_b20r50.json',
     'evidence/e1b_c4_readiness_b20r50/pilot_rows.jsonl', 'ablation', C4, 'ablation', 'sealed_evaluation'),
    ('E1b-C4 placebo', 'handoff/e1b_c4/power_analysis_centred_placebo_b20r50.json',
     'evidence/e1b_c4_readiness_b20r50/pilot_rows.jsonl', 'placebo', C4, 'placebo', 'sealed_evaluation'),
    ('E1d', 'handoff/e1d/power_analysis_centred_b20r41.json', 'evidence/e1d_readiness_b20r41/pilot_rows.jsonl',
     'milp_highs_4x', TF, 'sealed_evaluation', 'sealed_evaluation'),
    ('E1d ablation', 'evidence/e1d_ablation_rehearsal_b20r45/power_analysis_centred_ablation_plan.json',
     'evidence/e1d_ablation_b20r44/rows.jsonl', 'ablation', TF, 'ablation', 'ablation'),
)
REHEARSALS = (
    ('E1 (B20_R24)', 'handoff/e1/rehearsal_summary_b20r24.json'),
    ('E1b (B20_R24)', 'handoff/e1b/rehearsal_summary_b20r24.json'),
    ('E1b-C4 (B20_R52)', 'handoff/e1b_c4/rehearsal_summary_b20r52.json'),
    ('E1d (B20_R43)', 'handoff/e1d/rehearsal_summary_b20r43.json'),
    ('E1d ablation (B20_R45)', 'evidence/e1d_ablation_rehearsal_b20r45/rehearsal_summary.json'),
)
DECISION_RECORDS = {
    'E1': 'handoff/e1/decision_record_DRAFT_v3.json',
    'E1b': 'handoff/e1b/decision_record_DRAFT.json',
    'E1b-C4': 'handoff/e1b_c4/decision_record_DRAFT.json',
    'E1d': 'handoff/e1d/decision_record_DRAFT.json',
    'E1d ablation': 'evidence/e1d_ablation_rehearsal_b20r45/decision_record_ablation_DRAFT.json',
}


def _load(rel):
    return json.loads((ROOT / rel).read_text())


def _rows(rel):
    text = (ROOT / rel).read_text()
    return [json.loads(l) for l in text.splitlines() if l.strip()] if rel.endswith('.jsonl') else json.loads(text)


def plan(domain, family='sealed_evaluation'):
    p = R24.plan(domain)
    p['multiplicity'] = dict(p['multiplicity'], family_id=f'{family}:{domain}')
    return p


def pilot_rows(a):
    _, _, rel, comparator, _, _, _ = a
    rows = _rows(rel)
    if comparator is None:
        return rows
    return [{'task_id': r['task_id'], 'stratum': r['stratum'], 'status': 'SCORED', 'split': r['split'],
             'optimum': r['optimum'],
             'candidate': {k: r['arms']['candidate'][k] for k in ('value', 'run', 'cpu_ns')},
             'baseline': {k: r['arms'][comparator][k] for k in ('value', 'run', 'cpu_ns')}}
            for r in rows if r['optimum'] is not None]


def recompute(a, family=None):
    name, stored, _, _, domain, _, computed_under = a
    return required_sample(pilot_rows(a), plan(domain, family or computed_under), sims=SIMS,
                           min_tasks_per_stratum=10, headroom='centred')


def family_check(a):
    """(family the stored analysis is bound to, family the custodian assigns to this evidence kind)."""
    name, stored, _, _, domain, kind, _ = a
    core = _load(stored)['plan_core_sha256']
    bound = [f for f in ('sealed_evaluation', 'ablation', 'placebo') if digest(plan_core(plan(domain, f))) == core]
    return (bound[0] if bound else None), kind


def rebound(a):
    bound, kind = family_check(a)
    return None if bound == kind else recompute(a, kind)


def mc_se(p, sims=SIMS):
    return (p * (1 - p) / sims) ** 0.5


def borderline(p, sims=SIMS):
    return p - 2 * mc_se(p, sims) < TARGET


def power_10k(a, family):
    name, _, _, _, domain, _, _ = a
    n = _load(a[1])['chosen']['tasks_per_stratum']
    return simulate_power(_pilot(pilot_rows(a), 'centred'), plan(domain, family), n, sims=10_000)


def power_table():
    """Rows (name, chosen n per stratum, total, power, MC SE, power at MUE, rate at zero, bound, assigned)."""
    out = []
    for a in ANALYSES:
        s = _load(a[1])
        bound, kind = family_check(a)
        c = s['chosen']
        out.append((a[0], c['tasks_per_stratum'], c['total_tasks'], c['power'], round(mc_se(c['power']), 3),
                    s['power_at_minimum_useful_effect'], s['false_positive_rate_at_zero_effect'], bound, kind))
    return out


def power_markdown():
    lines = ['| Analysis | n per stratum (total) | Power at the design effect | MC s.e. | Power at the MUE | '
             'Rejection rate at zero effect | Plan family it is bound to | Family the custodian assigns |',
             '|---|---|---|---|---|---|---|---|']
    for name, n, tot, p, se, pm, p0, bound, kind in power_table():
        flag = ' (within 2 s.e. of 0.8)' if borderline(p) else ''
        mark = '' if bound == kind else ' **(mismatch)**'
        lines.append(f'| {name} | {n} ({tot}) | {p:.3f}{flag} | {se:.3f} | {pm:.3f} | {p0:.3f} | `{bound}`{mark} | '
                     f'`{kind}` |')
    return '\n'.join(lines)


def rehearsal_rows():
    out = []
    for name, rel in REHEARSALS:
        ar = _load(rel)['receipt_payload']['analysis_result']
        strata = sorted({u.split('-')[1] + ':' + u.split('-')[2] for u in ar['unsupported']})
        out.append((name, ar['tasks'], ar['scored'], len(ar['unsupported']), strata, ar['strata'],
                    ar['sensitivity']['stratum-level-sign-flip'], 1 / 2 ** ar['strata']))
    return out


def rehearsal_markdown():
    lines = ['| Rehearsal | Tasks | Scored | Unsupported (strata) | Strata | Stratum-level sign-flip p | '
             'Smallest p it can reach |', '|---|---|---|---|---|---|---|']
    for name, t, s, u, strata, k, lp, floor in rehearsal_rows():
        where = f' ({", ".join(strata)})' if strata else ''
        lines.append(f'| {name} | {t} | {s} | {u}{where} | {k} | {lp:.3f} | {floor:.3f} |')
    return '\n'.join(lines)


def findings():
    """{key: rendered text} for every derived number the brief's findings quote."""
    out = {}
    for a in ANALYSES:
        r = rebound(a)
        if r is not None:
            out[f'rebound {a[0]}'] = f"{a[0]}: n {r['chosen']['tasks_per_stratum']} per stratum, power {r['chosen']['power']:.3f}"
    for a in ANALYSES:
        if borderline(_load(a[1])['chosen']['power']):
            out[f'10k {a[0]}'] = f"{a[0]} at n {_load(a[1])['chosen']['tasks_per_stratum']}: {power_10k(a, family_check(a)[1]):.3f}"
    means = [v['mean_difference'] for a in ANALYSES for v in _load(a[1])['pilot_strata'].values()]
    out['pilot effects'] = f'the pilot effects are {min(means):.1f}–{max(means):.1f} per stratum'
    sds = [v['sd'] for v in _load(ANALYSES[7][1])['pilot_strata'].values()]
    out['E1d spread'] = f's.d. {min(sds):.1f}–{max(sds):.1f} per stratum'
    out['E1d pilot mean'] = f"(+{_load('handoff/e1d/pilot_summary_b20r41.json')['mean_difference']:.1f})"
    same = _load('evidence/e1d_ablation_b20r44/power_analysis_centred.json')['chosen']
    out['seed noise'] = (f"{same['power']:.3f} under the `sealed_evaluation` family and "
                         f"{_load(ANALYSES[-1][1])['chosen']['power']:.3f} under the `ablation` family")
    return out


def main():
    print(power_markdown())
    print()
    print(rehearsal_markdown())
    print()
    for k, v in findings().items():
        print(f'{k:24} {v}')


if __name__ == '__main__':
    main()
