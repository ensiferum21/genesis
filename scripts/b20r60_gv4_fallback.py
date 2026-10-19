"""B20_R60: the GV4 fallback claim, DRAFT (documentation; no run, no new evidence).

**Why.** No probed domain has a research decision with headroom (B20_R3, R6, R9, R13, RX5, R53, R54, R58),
so a learned-versus-fixed improver comparison has nowhere to show a difference. The handover's GV4 step is: if a
reviewer names a new domain, pilot its headroom first; otherwise write the roadmap's fallback claim, "report a
useful solver without claiming a better improver". This batch writes that claim as a DRAFT
(`handoff/gv4/FALLBACK_CLAIM_DRAFT.md`) so that the reviewer can accept, narrow or reject it with the text in hand.
It adopts nothing.

**What this script does.** It derives, from the committed evidence summaries only:
  * `ATTEMPTS`: the running family of preregistered component attempts (handoff/gv4 README, MISSING-BIT-1), each
    with its verdict and the p-value its rule used. Construction attempts were decided by multi-comparison rules
    with intervals, not one test, so they carry no p-value; they count in the family size at p = 1. That is
    conservative for every other attempt: under Benjamini-Yekutieli step-up, larger p-values elsewhere never
    remove a rejection.
  * `by_family()`: Benjamini-Yekutieli at q = 0.1 over that family, and for each surviving attempt the largest
    family size it would still survive at its current rank.
  * `CITATIONS`: every number the draft quotes, with the file and key it comes from and how it is rendered. The
    test renders each one and requires the rendering to appear in the draft verbatim.

`python3 scripts/b20r60_gv4_fallback.py --write` writes `handoff/gv4/attempt_family.json`. The test recomputes it.

**Not attempts, disclosed.** B20_R49 attributes B20_R48 (an ablation of the same attempt); B20_R59 replicates
B20_R57 (the same hypothesis on fresh hosts); B20_R44/R45 attribute E1d's effect; B20_R58 and the other pilots
measure research-decision headroom, not a component.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / 'evidence'
OUT = ROOT / 'handoff' / 'gv4' / 'attempt_family.json'
DRAFT = ROOT / 'handoff' / 'gv4' / 'FALLBACK_CLAIM_DRAFT.md'
Q = 0.1
FAMILY_CAP = 10_000          # search limit for survives_up_to_family_size; a value equal to it means "at least"

# (batch, kind, component, evidence directory, key path of the p-value or None)
ATTEMPTS = (
    ('B20_R17', 'construction', 'generated relational decoders v1', 'relation_invention_b20r17', None),
    ('B20_R19', 'construction', 'generated relational decoders v2', 'relation_invention_b20r19', None),
    ('B20_R26', 'construction', 'quotient representation', 'quotient_invention_b20r26', None),
    ('B20_R27', 'construction', 'decomposition', 'decomposition_invention_b20r27', None),
    ('B20_R31', 'construction', 'generated relaxation rows (K5/W5)', 'relaxation_invention_b20r31', None),
    ('B20_R36', 'construction', 'K5 rows in the dense regime', 'dense_construction_b20r36', None),
    ('B20_R32', 'certification', 'generated rows, exact LP certificates (unenriched)', 'generated_certification_b20r32',
     ('mcnemar_p_one_sided',)),
    ('B20_R35', 'certification', 'generated rows, enriched by setting', 'dense_certification_b20r35',
     ('mcnemar_p_one_sided',)),
    ('B20_R37', 'certification', 'generator v2, 7-vertex rows', 'generator_v2_b20r37', ('part_b', 'mcnemar_p_one_sided')),
    ('B20_R47', 'certification', 'transferred C4 rows alone', 'c4_certification_b20r47', ('mcnemar_p_one_sided',)),
    ('B20_R48', 'certification', 'transferred C4 rows with certified branch and bound', 'c4_tree_certification_b20r48',
     ('mcnemar_p_one_sided',)),
    ('B20_R56', 'certification', 'transferred sum-free rows (unenriched)', 'sf_tree_certification_b20r56',
     ('mcnemar_p_one_sided',)),
    ('B20_R57', 'certification', 'transferred sum-free rows, hosts hard for the conventional route',
     'sf_hard_certification_b20r57', ('mcnemar_p_one_sided',)),
)
NOT_ATTEMPTS = {
    'B20_R44': 'registered ablation of E1d (attribution of a GV3 effect)',
    'B20_R45': 'custody rehearsal of the B20_R44 ablation',
    'B20_R49': 'registered ablation of B20_R48 (attribution of the same attempt)',
    'B20_R58': 'research-decision headroom pilot (no component)',
    'B20_R59': 'internal replication of B20_R57 (the same hypothesis on fresh hosts): NOT_REPLICATED',
}


def _get(obj, path):
    for k in path:
        obj = obj[k]
    return obj


def _summary(d):
    return json.loads((EV / d / 'summary.json').read_text())


def _verdict(s):
    return s.get('verdict') or s['part_b']['verdict']


def harmonic(m):
    return sum(1.0 / i for i in range(1, m + 1))


def by_rejections(pvals, q=Q):
    """Benjamini-Yekutieli step-up: the set of indices rejected at level q (valid under any dependence)."""
    m = len(pvals)
    order = sorted(range(m), key=lambda i: (pvals[i], i))
    c = harmonic(m)
    k = 0
    for r, i in enumerate(order, 1):
        if pvals[i] <= r * q / (m * c):
            k = r
    return set(order[:k])


def max_family_size(p, rank, q=Q, cap=FAMILY_CAP):
    """Largest m >= rank with p <= rank q / (m H_m): how far the family can grow before this rank fails."""
    best = None
    for m in range(rank, cap + 1):
        if p <= rank * q / (m * harmonic(m)):
            best = m
        else:
            break
    return best


def by_family():
    rows = []
    for batch, kind, component, d, key in ATTEMPTS:
        s = _summary(d)
        p = _get(s, key) if key else None
        rows.append({'batch': batch, 'kind': kind, 'component': component, 'evidence': f'evidence/{d}/summary.json',
                     'verdict': _verdict(s), 'p_one_sided': p, 'p_for_family': 1.0 if p is None else p})
    pv = [r['p_for_family'] for r in rows]
    rejected = by_rejections(pv)
    ranks = {i: r for r, i in enumerate(sorted(range(len(pv)), key=lambda i: (pv[i], i)), 1)}
    for i, r in enumerate(rows):
        r['rank'] = ranks[i]
        r['survives_by'] = i in rejected
        r['survives_up_to_family_size'] = max_family_size(r['p_for_family'], ranks[i]) if i in rejected else None
    return {'schema': 'genesis-b20r60-gv4-attempt-family-v1', 'method': 'Benjamini-Yekutieli step-up', 'q': Q,
            'family_size': len(rows), 'harmonic_c_m': round(harmonic(len(rows)), 6),
            'family_size_search_cap': FAMILY_CAP,
            'no_p_value_rule': 'construction attempts were decided by multi-comparison interval rules; they count '
                               'in the family size at p = 1, which is conservative for every other attempt',
            'attempts': rows, 'survivors': [r['batch'] for r in rows if r['survives_by']],
            'not_attempts': NOT_ATTEMPTS}


def _json(rel, *path):
    return _get(json.loads((ROOT / rel).read_text()), path)


E1D_PILOT = 'handoff/e1d/pilot_summary_b20r41.json'
E1D_REH = 'handoff/e1d/rehearsal_summary_b20r43.json'
ABL = 'evidence/e1d_ablation_b20r44/summary.json'
ABL_REH = 'evidence/e1d_ablation_rehearsal_b20r45/rehearsal_summary.json'


def _iv(v):
    return f'[{v[0]:.2f}, {v[1]:.2f}]'


# (what, file, key path, renderer); the rendering must appear in the draft verbatim.
CITATIONS = (
    ('E1d re-pilot mean', E1D_PILOT, ('mean_difference',), lambda v: f'+{v:.1f}'),
    ('E1d re-pilot interval', E1D_PILOT, ('draft_plan_dry_run', 'interval'), lambda v: f'[{v[0]:.1f}, {v[1]:.1f}]'),
    ('E1d re-pilot optimum hits', E1D_PILOT, ('optimum_hits', 'candidate'), lambda v: f'{v}/30'),
    ('E1d re-pilot comparator', E1D_PILOT, ('comparator',), lambda v: f'`{v}`'),
    ('E1d re-pilot MIP optimum hits', E1D_PILOT, ('optimum_hits', 'milp_highs_4x'), lambda v: f'only {v} of 30'),
    ('E1d rehearsal estimate', E1D_REH, ('receipt_payload', 'analysis_result', 'estimate'), lambda v: f'+{v:.2f}'),
    ('E1d rehearsal interval', E1D_REH, ('receipt_payload', 'analysis_result', 'interval'), _iv),
    ('E1d rehearsal scored', E1D_REH, ('receipt_payload', 'analysis_result', 'scored'), lambda v: f'{v} certified hosts'),
    ('E1d rehearsal W/T/L', E1D_REH, ('receipt_payload',),
     lambda v: f'{v["wins"]}/{v["ties"]}/{v["losses"]}'),
    ('E1d rehearsal cost ratio', E1D_REH, ('receipt_payload', 'analysis_result', 'cost_ratio'), lambda v: f'{v:.2f}'),
    ('E1d rehearsal judge', E1D_REH, ('judge', 'witnesses_rechecked'), lambda v: f'{v} witnesses'),
    ('E1d ablation estimate', ABL, ('pilot', 'draft_plan_dry_run', 'estimate'), lambda v: f'+{v:.2f}'),
    ('E1d ablation interval', ABL, ('pilot', 'draft_plan_dry_run', 'interval'), _iv),
    ('E1d null control', ABL, ('pilot', 'negative_control'),
     lambda v: f'+{v["mean"]:.2f} [{v["interval_90"][0]:.2f}, {v["interval_90"][1]:.2f}]'),
    ('E1d ablation rehearsal estimate', ABL_REH, ('receipt_payload', 'analysis_result', 'estimate'), lambda v: f'+{v:.2f}'),
    ('E1d ablation rehearsal interval', ABL_REH, ('receipt_payload', 'analysis_result', 'interval'), _iv),
    ('E1d ablation rehearsal W/T/L', ABL_REH, ('receipt_payload',),
     lambda v: f'{v["wins"]}/{v["ties"]}/{v["losses"]}'),
    ('B20_R35 coverage', 'evidence/dense_certification_b20r35/summary.json', ('pooled',),
     lambda v: f'{v["certified_b"]} vs {v["certified_a"]} of {v["hosts"]}'),
    ('B20_R48 coverage', 'evidence/c4_tree_certification_b20r48/summary.json', ('pooled',),
     lambda v: f'{v["certified_c"]} vs {v["certified_a"]} of {v["hosts"]}'),
    ('B20_R49 coverage', 'evidence/c4_rows_ablation_b20r49/summary.json', ('pooled',),
     lambda v: f'{v["certified_c"]} vs {v["certified_c0"]} of {v["hosts"]}'),
    ('B20_R57 coverage', 'evidence/sf_hard_certification_b20r57/summary.json', ('pooled',),
     lambda v: f'{v["certified_c"]} vs {v["certified_a"]} of {v["hosts"]}'),
    ('B20_R57 bound', 'evidence/sf_hard_certification_b20r57/summary.json', ('bound',),
     lambda v: f'+{v["mean"]:.3f} [{v["interval_90"][0]:.3f}, {v["interval_90"][1]:.3f}]'),
    ('B20_R59 coverage', 'evidence/sf_replication_b20r59/summary.json', ('pooled',),
     lambda v: f'{v["certified_c"]} vs {v["certified_a"]} of 40'),
    ('B20_R59 bound', 'evidence/sf_replication_b20r59/summary.json', ('bound',),
     lambda v: f'+{v["mean"]:.3f} [{v["interval_90"][0]:.3f}, {v["interval_90"][1]:.3f}]'),
    ('B20_R59 p', 'evidence/sf_replication_b20r59/summary.json', ('mcnemar_p_one_sided',), lambda v: f'p {v:.2f}'),
    ('B20_R63 verdict', 'evidence/e1d_crossover_b20r63/summary.json', ('verdict',), lambda v: f'**{v}**'),
    ('B20_R63 at 4x', 'evidence/e1d_crossover_b20r63/summary.json', ('per_budget', 'highs_2s'),
     lambda v: f'+{v["estimate"]:.2f} [{v["interval_90"][0]:.2f}, {v["interval_90"][1]:.2f}]'),
    ('B20_R63 at 8x', 'evidence/e1d_crossover_b20r63/summary.json', ('per_budget', 'highs_4s'),
     lambda v: f'+{v["estimate"]:.2f} [{v["interval_90"][0]:.2f}, {v["interval_90"][1]:.2f}]'),
    ('B20_R63 at 16x', 'evidence/e1d_crossover_b20r63/summary.json', ('per_budget', 'highs_8s', 'estimate'),
     lambda v: f'+{v:.2f}, no longer a material advantage'),
    ('B20_R63 HiGHS optimal at 16 s', 'evidence/e1d_crossover_b20r63/summary.json',
     ('descriptive', 'optimum_hits', 'highs_16s'), lambda v: f'optimal on {v} of 30 at 16 s'),
    ('B20_R63 HiGHS CPU at 16 s', 'evidence/e1d_crossover_b20r63/summary.json', ('per_budget', 'highs_16s', 'cpu_s_median'),
     lambda v: f'about {v:.0f} CPU s per host'),
    ('B20_R64 verdict', 'evidence/e1d_scaling_b20r64/summary.json', ('verdict',), lambda v: f'**{v}**'),
    ('B20_R64 n60 at 64x', 'evidence/e1d_scaling_b20r64/summary.json', ('by_n', '60', 'per_budget', 'highs_32s'),
     lambda v: f'+{v["estimate"]:.1f} [{v["interval_90"][0]:.1f}, {v["interval_90"][1]:.1f}], '
               f'{v["wins_ties_losses"][0]}/{v["wins_ties_losses"][1]}/{v["wins_ties_losses"][2]}'),
    ('B20_R66 verdict', 'evidence/e1d_n60_b20r66/summary.json', ('verdict',), lambda v: f'**{v}**'),
    ('B20_R66 n60 at 64x', 'evidence/e1d_n60_b20r66/summary.json', ('per_budget', 'highs_32s'),
     lambda v: f'+{v["estimate"]:.2f} [{v["interval_90"][0]:.1f}, {v["interval_90"][1]:.1f}], '
               f'{v["wins_ties_losses"][0]}/{v["wins_ties_losses"][1]}/{v["wins_ties_losses"][2]}'),
    ('B20_R66 n60 at 120x', 'evidence/e1d_n60_b20r66/summary.json', ('per_budget', 'highs_60s'),
     lambda v: f'+{v["estimate"]:.2f} [{v["interval_90"][0]:.2f}, {v["interval_90"][1]:.2f}], '
               f'{v["wins_ties_losses"][0]}/{v["wins_ties_losses"][1]}/{v["wins_ties_losses"][2]}'),
    ('B20_R68 verdict', 'evidence/e1d_domain_heuristic_b20r68/summary.json', ('verdict',), lambda v: f'**{v}**'),
    ('B20_R68 Part A', 'evidence/e1d_domain_heuristic_b20r68/summary.json',
     ('parts', 'A', 'primary_candidate_minus_tabu_0.5s'),
     lambda v: f'{v["estimate"]:+.2f} [{v["interval_90"][0]:.2f}, {v["interval_90"][1]:.2f}], '
               f'{v["wins_ties_losses"][0]}/{v["wins_ties_losses"][1]}/{v["wins_ties_losses"][2]}'),
    ('B20_R68 Part B', 'evidence/e1d_domain_heuristic_b20r68/summary.json',
     ('parts', 'B', 'primary_candidate_minus_tabu_0.5s'),
     lambda v: f'{v["estimate"]:+.2f} [{v["interval_90"][0]:.2f}, {v["interval_90"][1]:.2f}], '
               f'{v["wins_ties_losses"][0]}/{v["wins_ties_losses"][1]}/{v["wins_ties_losses"][2]}'),
    ('B20_R68 tabu over HiGHS', 'evidence/e1d_domain_heuristic_b20r68/summary.json',
     ('parts', 'A', 'secondary', 'tabu_0.5s_minus_highs_2s', 'estimate'), lambda v: f'by +{v:.2f}'),
    ('B20_R76 verdict', 'evidence/sota_b20r76/summary.json', ('verdict',), lambda v: f'the preregistered verdict is **{v}**'),
    ('B20_R76 candidate vs CP-SAT n60', 'evidence/sota_b20r76/summary.json', ('by_n', '60', 'versus_sota', 'cpsat', 'candidate'),
     lambda v: f'{v["verdict"]}, log2 interval [{v["interval_90"][0]:.1f}, {v["interval_90"][1]:.1f}]'),
    ('B20_R76 candidate vs BURER2002 n63', 'evidence/sota_b20r76/summary.json', ('by_n', '63', 'versus_sota', 'burer', 'candidate'),
     lambda v: f'{v["verdict"]}, [{v["interval_90"][0]:.2f}, {v["interval_90"][1]:.2f}]'),
    ('B20_R76 CP-SAT anytime', 'evidence/sota_b20r76/summary.json', ('by_n',),
     lambda v: f'on {v["60"]["arms"]["cpsat"]["solved"] + v["63"]["arms"]["cpsat"]["solved"]} of 12 hosts'),
    ('B20_R70 verdict', 'evidence/tts_scaling_b20r70/summary.json', ('verdict',), lambda v: f'**{v}**'),
    ('B20_R70 dSB at n60', 'evidence/tts_scaling_b20r70/summary.json', ('by_n', '60', 'per_heuristic', 'dsb'),
     lambda v: f'{v["median_log2_ratio"]:.2f} [{v["interval_90"][0]:.2f}, {v["interval_90"][1]:.2f}]'),
    ('B20_R58 table', 'evidence/sf_pattern_selection_b20r58/summary.json', ('table',),
     lambda v: f'all {v["ALL"]["certified"]}, none {v["NONE"]["certified"]}, best subset '
               f'{max(v[k]["certified"] for k in v if k.startswith("TOP"))} of {v["ALL"]["hosts"]}'),
)


def rendered():
    """[(what, rendering)] for every citation with a renderer."""
    return [(what, fn(_json(rel, *path))) for what, rel, path, fn in CITATIONS if fn is not None]


def main(argv):
    fam = by_family()
    if '--write' in argv:
        OUT.write_text(json.dumps(fam, indent=1, sort_keys=True) + '\n')
    for r in fam['attempts']:
        print(f"{r['batch']:8} {r['kind']:13} p={r['p_one_sided']!s:12} rank {r['rank']:2} "
              f"{'SURVIVES up to m=' + str(r['survives_up_to_family_size']) if r['survives_by'] else ''}")
    for what, s in rendered():
        print(f'{what:34} {s}')


if __name__ == '__main__':
    main(sys.argv[1:])
