"""Responses of the adaptation cell (gene expression): for each caveat type, the adaptations of the next study's design
that address it, in the order to try them.

Each response has a `progress(design, evidence)` in [0, 1]: how far a design goes towards carrying it out for a caveat
with that evidence (1 is the full dose; between 0 and 1 is a partial dose, such as acquiring four of nine missing
baselines, or a longer budget that is still below the competitors' home regime). Numerical responses ignore changes
inside the noise band (`NOISE_RATIO`): certifying for 122 s instead of 121 s is not an attempt. The ledger reads an
attempt as a change of progress between the design of the study where the caveat was last seen and the design of a
later study; a state that was already there when the caveat fired is not an answer to it.

A design is a plain dict (`design.design_of` reads one from a finished study's evidence; `design.compose` writes the
next one; `checkpoint.check` tests one before preregistration):
  study, focal, ladder (run times, s), long_budgets (s), long_arms (int), arms (int), competitors (solver keys), sizes
  (host n), hosts, certification_s, upper_bounds, quality_at_equal_time, new_family, ablation ({'hosts': k} or None),
  valid, resumable, sequential_stopping, harness_fix (str), internal_tts, probes ({arm: budget s}), excluded ({arm:
  reason}), validity ({'min_cpu_at_half', 'max_fail_share'}), fresh_hosts, deferred ({caveat key: reason}).
"""
from dataclasses import dataclass
import math

NOISE_RATIO = 1.1           # a numerical change smaller than 10% is noise, not an attempt


@dataclass(frozen=True)
class Response:
    name: str
    action: str
    progress: object               # (design, caveat evidence) -> float in [0, 1]
    last_resort: bool = False      # removes the observation rather than explaining it: ranked after every other

    def satisfied(self, design, evidence):
        return self.progress(design, evidence) >= 1.0


def _ladder(d):
    return [float(t) for t in d.get('ladder', ())]


def _budgets(d):
    return _ladder(d) + [float(t) for t in d.get('long_budgets', ())]


def _b(x):
    return 1.0 if x else 0.0


def _ratio_dose(new, old, full):
    """Progress of raising a quantity from `old` towards `full` times `old`; changes inside the noise band count 0."""
    old = max(float(old), 1e-9)
    r = float(new) / old
    if r < NOISE_RATIO:
        return 0.0
    return min(1.0, (r - 1.0) / (full - 1.0))


def _log_dose(new, old, target):
    """Progress of raising `old` to `target` on a log scale (budgets span orders of magnitude)."""
    if new >= target:
        return 1.0
    if new < NOISE_RATIO * old or old <= 0:
        return 0.0
    return min(1.0, math.log(new / old) / math.log(target / old))


def _missing_share(d, e):
    keys = set(e['missing_keys'])
    return len(keys & set(d.get('competitors', ()))) / len(keys) if keys else 1.0


RESPONSES = {
    'FLOOR_EFFECT': (
        Response('extend_ladder_down', 'add run times below the floor (a tenth, a fifth and half of it), so the '
                 'margin is measured rather than bounded',
                 lambda d, e: _b(_ladder(d) and min(_ladder(d)) < e['floor_s'] / NOISE_RATIO)),
        Response('internal_time_to_target', "have the method report when it first reached each value (its own CPU "
                 "clock), checked against its final witness", lambda d, e: _b(d.get('internal_tts')))),
    'SATURATION': (
        Response('quality_at_equal_time_on_larger_instances', 'move to instances no method solves to the optimum '
                 'within the budgets, and compare the values found at equal time',
                 lambda d, e: 0.5 * _b(d.get('quality_at_equal_time'))
                 + 0.5 * _b(max(d.get('sizes') or [0]) > NOISE_RATIO * e['largest_n'])),
        Response('harder_family', 'a host family on which the strong methods disagree at the longest budget',
                 lambda d, e: _b(d.get('new_family')))),
    'UNCERTIFIED_TARGETS': (
        Response('upper_bounds', 'compute a proven upper bound per host, so results read against what is possible',
                 lambda d, e: _b(d.get('upper_bounds'))),
        Response('longer_certification', 'give the certification route at least 1.5 times the time',
                 lambda d, e: _ratio_dose(d.get('certification_s', 0), e.get('certification_s', 120), 1.5))),
    'UNRESOLVED_VERDICT': (
        Response('more_hosts', 'at least 1.5 times as many hosts',
                 lambda d, e: _ratio_dose(d.get('hosts', 0), e['hosts'], 1.5)),
        Response('finer_ladder', 'more run times where the arms cross',
                 lambda d, e: _b(len(_ladder(d)) > e.get('ladder_points', 5)))),
    'COMPONENT_EFFECT_UNRESOLVED': (
        Response('dedicated_ablation_with_more_power', 'an ablation study with at least twice the hosts',
                 lambda d, e: _ratio_dose((d.get('ablation') or {}).get('hosts', 0), e['hosts'], 2.0)),
        Response('ablation_on_harder_instances', 'repeat the ablation where the components have room to matter',
                 lambda d, e: _b(d.get('ablation')
                                 and max(d.get('sizes') or [0]) > NOISE_RATIO * e.get('largest_n', 0)))),
    'INVALID_RUN': (
        Response('fix_harness_then_rerun', 'find and fix the defect, add a test that would have caught it, rerun the '
                 'same comparison on fresh hosts',
                 lambda d, e: _b(d.get('harness_fix') or (d.get('valid') is True
                                                         and d.get('focal') == e.get('focal', d.get('focal'))))),),
    'INTERRUPTED': (
        Response('resumable_design', 'per-host rows and a resume that reruns an interrupted host from its start with '
                 'the same seeds, disclosed', lambda d, e: _b(d.get('resumable'))),
        Response('sequential_stopping', 'preregistered interim looks with stopping boundaries, so long studies end '
                 'when decided', lambda d, e: _b(d.get('sequential_stopping')))),
    'MISSING_BASELINE': (
        Response('acquire_baseline', 'obtain, build from source, pin and include the missing solvers',
                 _missing_share),),
    'REGIME_GAP': (
        Response('add_home_budgets', "include the competitors' home budgets",
                 lambda d, e: _log_dose(max(_budgets(d) or [0]), e['longest_budget_s'],
                                        min(e['competitors_home_budgets_s']))),),
    'SIZE_CAP': (
        Response('extend_domain', 'a task model and engine beyond the cap',
                 lambda d, e: _b(max(d.get('sizes') or [0]) > e['model_cap'])),),
    'ARM_NOT_RESPONDING': (
        Response('probe_at_home_budget', "run the arm at its home budget on a few hosts: if it then improves, the "
                 "study's budgets are outside its regime (disclose it); if not, its harness is wrong (fix it)",
                 lambda d, e: _b(set(e['arms']) <= set(d.get('probes') or {}))),
        Response('fix_arm_harness', "check how the arm is run (input format, arguments, output parsing, signals) "
                 "against its Evaluation run script, fix what differs, add a test", lambda d, e: _b(
                     set(d.get('arm_harness_fix') or ()) >= set(e['arms']))),
        Response('exclude_with_disclosure', 'leave the arm out of the comparison and of the virtual best solver, '
                 'with the reason stated (an arm that is no longer in the comparison at all counts as left out)',
                 lambda d, e: _b(all(a in (d.get('excluded') or {}) or ('arm_names' in d and a not in d['arm_names'])
                                     for a in e['arms'])), last_resort=True)),
    'OUTPERFORMED': (
        Response('new_method', "a different method, or the same method re-tuned (its identity changes), as the "
                 "system's focal arm", lambda d, e: _b(d.get('focal_identity') and e.get('focal_identity')
                                                      and d['focal_identity'] != e['focal_identity'])),
        Response('retune_where_lost', 'a configuration race on hosts like the ones lost (their families and sizes), '
                 'against the arms that won there', lambda d, e: _b(set((d.get('tuning') or {}).get('against', ()))
                                                                    >= set(e['arms']))),
        Response('borrow_from_winner', "study the winning competitor's mechanism, add it to the method as a "
                 'component, and ablate it', lambda d, e: _b(set(d.get('components_from') or ()) >= set(e['arms'])))),
    'STALE_KNOWLEDGE': (
        Response('refresh_catalog', "read the newest Evaluation's results and update the baseline catalog (and its "
                 "as-of date) before designing", lambda d, e: _b(d.get('catalog_as_of', '') >= e['due'])),),
}

# The membrane: what no adaptation may do. Checked by `checkpoint.membrane` where a design can show it.
MEMBRANE = (
    'never relax a checker, a threshold or a validity rule to make a result pass',
    'every study is preregistered: the script committed and its SHA-256 sent before it runs',
    'every study draws fresh hosts, excluding all earlier hosts',
    'never invent independence: the builder is not a custodian, reviewer or replicator',
    'negative and unresolved results are recorded as such',
    'a high-severity or chronic caveat is deferred only when it is blocked (a work order names what is missing), '
    'never to save time',
)
CANONICAL_VALIDITY = {'min_cpu_at_half': 0.45, 'max_fail_share': 0.01}


def responses_for(caveat_type):
    return RESPONSES[caveat_type]
