"""Designs: what a study did (read from its evidence) and what the next one should do (composed by the cell).

`design_of` reads a finished study's design from its evidence in the vocabulary of `responses.py`, so the cell can
tell, without being told, which caveats a later study tried to answer.

`compose` writes the next study's design. It works like a cell deciding what to express under a limited energy
budget:
  * every open caveat is ranked (severity, then chronic before acute, then age); for each, the response the ledger's
    memory ranks best is chosen among those that would change the design (a response already fully present in the
    latest study cannot be the answer to a weakness that study still showed: the cell moves to the next one), at the
    dose the latest evidence calls for (`_apply`);
  * a response that cannot be carried out at all (a ladder already at the harness's resolution) is skipped for the
    next in the library;
  * long budgets are run only by the arms that can change the comparison (the focal method, every competitor that
    was best on some host in the latest study, and every newly acquired baseline): the cheapest design that still
    answers the caveat;
  * the cost is predicted with the cost model the cell fitted to its own earlier runs (`metabolism.py`); the budget
    is limited by growth (a study may cost at most `GROWTH` times the most expensive one so far, unless the builder
    gives a budget); if the design does not fit, low and medium caveats that are not chronic are deferred, cheapest
    benefit first, with the reason stated; high-severity and chronic ones never are (the membrane);
  * a design longer than one background window plans resumption and sequential stopping before the interruption;
  * what the design needs that the system cannot do yet becomes a work order (`capabilities.py`).
"""
import math

from .responses import CANONICAL_VALIDITY, RESPONSES

BACKGROUND_WINDOW_S = 7200          # a background job's limit in this workspace (B20_R90, B20_R92)
MIN_RUN_S = 0.001                   # below a millisecond, process start and signal delivery dominate a run
GROWTH = 2.0                        # homeostasis: a study may cost at most twice the most expensive one so far
PROBE_BUDGET_S, PROBE_HOSTS = 60.0, 4   # a probe: the flagged arm at the shortest home budget on a few hosts
_RANK = {'high': 3, 'medium': 2, 'low': 1}


def _labels_invalid(study):
    return any(isinstance(v, str) and v.startswith('INVALID') for v in study.labels().values())


def design_of(study):
    """The design a finished study carried out, as far as its evidence shows."""
    rows, s = study.rows, study.summary
    ablation_arms = [k[len('ablation_'):] for k in study.labels() if k.startswith('ablation_')]
    ablated = [r for r in rows if any(a in r['runs'] for a in ablation_arms)]
    arms = sorted({a for r in rows for a in r['runs']})
    long_arms = sorted({a for r in rows for a in (r.get('long') or {})})

    def cert(r):
        ref = (r.get('reference') or {}).get('wall_s') or 0
        ex = sum((x or {}).get('wall_s') or 0 for x in (r.get('exact') or {}).values()) \
            if isinstance(r.get('exact'), dict) else 0
        return ref + ex
    from .receptors import focal_identity
    return {
        'study': study.profile.study,
        'focal': study.profile.focal,
        'focal_identity': focal_identity(study),
        'ladder': list(study.ladder()),
        'reps': int(s.get('reps') or 3),
        'long_budgets': [float(s['long_seconds'])] if s.get('long_seconds') else [],
        'long_arm_names': long_arms,
        'arms': len(arms),
        'arm_names': arms,
        'competitors': sorted((s.get('champions') or {}).keys()),
        'sizes': sorted({r['n'] for r in rows}),
        'hosts': len(rows),
        'certification_s': round(max((r.get('reference', {}).get('wall_s') or 0 for r in rows), default=0)),
        'certification_mean_s': round(sum(cert(r) for r in rows) / len(rows), 1) if rows else 0,
        'upper_bounds': any('upper_bound' in r or (r.get('reference') or {}).get('upper') is not None for r in rows),
        'quality_at_equal_time': bool(s.get('quality_at_equal_time')),
        'internal_tts': any('first_hit' in x for r in rows for xs in r['runs'].get(study.profile.focal, {}).values()
                            for x in xs),
        'ablation': {'hosts': len(ablated)} if ablation_arms else None,
        'valid': not _labels_invalid(study),
        'resumable': True,                 # every TTS study here writes one row per host and resumes from them
        'sequential_stopping': bool(s.get('sequential_stopping')),
        'probes': dict(s.get('probes') or {}),
        'excluded': dict(s.get('excluded') or {}),
        'fresh_hosts': True,
        'validity': dict(CANONICAL_VALIDITY),
    }


def _norm(x):
    return ''.join(ch for ch in x.lower() if ch.isalnum())


def _subsequence(a, b):
    it = iter(b)
    return all(ch in it for ch in a)


def arm_keys(arms, keys):
    """Which pinned solver key each arm stands for, inferred from the names alone: the key whose normalised name
    contains the arm's as a subsequence, starting with the same letter, with the fewest extra letters; an arm that
    matches no key, or two keys equally well, stands for none (it is not a published solver here)."""
    out = {}
    for a in arms:
        na = _norm(a)
        cands = [(len(_norm(k)) - len(na), k) for k in keys
                 if na and _norm(k)[:1] == na[:1] and _subsequence(na, _norm(k))]
        if not cands:
            continue
        cands.sort()
        if len(cands) == 1 or cands[0][0] < cands[1][0]:
            out[a] = cands[0][1]
    return out


def vbs_contributors(study):
    """Competitor arms that were the fastest competitor on at least one host of `study` (finite TTS*)."""
    out = set()
    ablations = {k[len('ablation_'):] for k in study.labels() if k.startswith('ablation_')}
    comps = [a for a in study.profile.competitors if a not in ablations]
    for r in study.rows:
        tts = {a: study.tts(r, a) for a in comps if a in r['runs']}
        finite = {a: v for a, v in tts.items() if v < math.inf}
        if finite:
            best = min(finite.values())
            out |= {a for a, v in finite.items() if v == best}
    return sorted(out)


def _new_rungs(floor):
    return sorted({round(f, 6) for f in (floor / 10, floor / 5, floor / 2) if f >= MIN_RUN_S})


def feasible(response, design, entry):
    """Whether a response can be carried out at all from this design."""
    if response == 'extend_ladder_down':
        return bool(_new_rungs(entry['evidence']['floor_s']))
    return True


def _apply(d, response, entry, available_keys=None):
    e = entry['evidence']
    if response == 'extend_ladder_down':
        d['ladder'] = sorted(set(d['ladder']) | set(_new_rungs(e['floor_s'])))
    elif response == 'internal_time_to_target':
        d['internal_tts'] = True
    elif response == 'quality_at_equal_time_on_larger_instances':
        d['quality_at_equal_time'] = True
        d['sizes'] = sorted(set(d['sizes']) | {2 * e['largest_n'] + 2, 4 * e['largest_n'] + 4})
    elif response == 'harder_family':
        d['new_family'] = True
    elif response == 'upper_bounds':
        d['upper_bounds'] = True
    elif response == 'longer_certification':
        old = max(d.get('certification_s', 0), 1)
        d['certification_s'] = max(d.get('certification_s', 0), round(1.5 * e.get('certification_s', 120)))
        d['certification_mean_s'] = round(d.get('certification_mean_s', 0) * d['certification_s'] / old, 1)
    elif response == 'more_hosts':
        d['hosts'] = max(d['hosts'], math.ceil(1.5 * e['hosts']))
    elif response == 'finer_ladder':
        lad = sorted(d['ladder'])
        d['ladder'] = sorted(set(lad) | {round(math.sqrt(a * b), 6) for a, b in zip(lad, lad[1:])})
    elif response == 'dedicated_ablation_with_more_power':
        d['ablation'] = {'hosts': max((d.get('ablation') or {}).get('hosts', 0), 2 * e['hosts'])}
    elif response == 'ablation_on_harder_instances':
        d['ablation'] = {'hosts': max((d.get('ablation') or {}).get('hosts', 0), e['hosts'])}
        d['sizes'] = sorted(set(d['sizes']) | {2 * e.get('largest_n', 63) + 2})
    elif response == 'fix_harness_then_rerun':
        d['harness_fix'] = 'required: find the defect, add a test that would have caught it'
    elif response == 'resumable_design':
        d['resumable'] = True
    elif response == 'sequential_stopping':
        d['sequential_stopping'] = True
    elif response == 'acquire_baseline':
        new = [k for k in e['missing_keys'] if k not in d['competitors']]
        d['competitors'] = sorted(set(d['competitors']) | set(new))
        d['arms'] = d.get('arms', 0) + len(new)
        d['long_arm_names'] = sorted(set(d.get('long_arm_names', ())) | set(new))
    elif response == 'add_home_budgets':
        d['long_budgets'] = sorted(set(d['long_budgets']) | {float(min(e['competitors_home_budgets_s']))})
    elif response == 'extend_domain':
        d['sizes'] = sorted(set(d['sizes']) | {2 * e['largest_n'] + 2})
    elif response == 'probe_at_home_budget':
        d['probes'] = dict(d.get('probes') or {}, **{a: {'budget_s': PROBE_BUDGET_S, 'hosts': PROBE_HOSTS}
                                                      for a in e['arms']})
    elif response == 'fix_arm_harness':
        d['arm_harness_fix'] = sorted(set(d.get('arm_harness_fix') or ()) | set(e['arms']))
    elif response == 'exclude_with_disclosure':
        d['excluded'] = dict(d.get('excluded') or {}, **{a: 'does not respond to its run time (ARM_NOT_RESPONDING)'
                                                         for a in e['arms']})
    elif response == 'new_method':
        d['focal_identity'] = 'new: a re-tuned or different method'
    elif response == 'retune_where_lost':
        d['tuning'] = {'against': sorted(e['arms']),
                       'families': sorted({f for v in e['arms'].values() for f in v['families']}),
                       'sizes': sorted({int(n) for v in e['arms'].values() for n in v['sizes']})}
    elif response == 'borrow_from_winner':
        d['components_from'] = sorted(set(d.get('components_from') or ()) | set(e['arms']))
    elif response == 'refresh_catalog':
        d['catalog_refresh'] = 'required'
    return d


def deferrable(entry):
    """The membrane: high-severity and chronic caveats are never deferred to save time."""
    return entry['severity'] != 'high' and entry['status'] not in ('CHRONIC', 'RELAPSE')


def _copy(base):
    return {k: (list(v) if isinstance(v, list) else (dict(v) if isinstance(v, dict) else v)) for k, v in base.items()}


def _rank_of(entry):
    return (_RANK[entry['severity']], entry['status'] in ('CHRONIC', 'RELAPSE'))


def _order(entries):
    """Most urgent first: severity, then chronic or relapsed before acute, then key (which carries the age)."""
    return sorted(entries, key=lambda kv: (-_RANK[kv[1]['severity']], kv[1]['status'] not in ('CHRONIC', 'RELAPSE'),
                                           kv[0]))


def _build(base, entries, ledger):
    d = _copy(base)
    d['study'] = 'next'
    for k in ('harness_fix', 'deferred', 'estimated_runtime_s', 'cost_extrapolated'):
        d.pop(k, None)
    chosen, applied, skipped, escalate = {}, {}, {}, {}
    for key, entry in entries:
        picked = None
        for name in ledger.ranked_responses(entry):
            resp = next(x for x in RESPONSES[entry['type']] if x.name == name)
            if resp.satisfied(d, entry['evidence']):
                skipped.setdefault(key, []).append(f'{name}: already in the design')
                continue
            if not feasible(name, d, entry):
                skipped.setdefault(key, []).append(f'{name}: cannot be carried out (below the harness resolution)')
                continue
            picked = name
            break
        if picked is None:
            kept = [x.name for x in RESPONSES[entry['type']] if x.name not in entry['retired']
                    and x.satisfied(d, entry['evidence'])]
            if kept:
                chosen[key] = kept[0]      # carried out already by an element this design keeps
            else:
                escalate[key] = 'every response in the library is retired or infeasible: a new response is needed'
            continue
        _apply(d, picked, entry)
        chosen[key] = applied[key] = picked
    return d, chosen, applied, skipped, escalate


def long_arms(d, base, contributors, leading):
    """The arms worth a long budget: the focal method, every arm that stands for a leading published solver, every
    arm that was fastest on some host and stands for a published solver, and every newly acquired leading
    baseline. Weak or internal arms are not given long budgets: they cannot change the comparison there."""
    names = list(base.get('arm_names') or base.get('long_arm_names') or ())
    keys = arm_keys(names, base.get('competitors', ()))
    keep = {d.get('focal')}
    keep |= {a for a, k in keys.items() if k in leading}
    keep |= {a for a in (contributors or ()) if a in keys}
    keep |= {k for k in set(d['competitors']) - set(base.get('competitors', ())) if k in leading}
    return sorted(a for a in keep if a)


def _finish(d, base, contributors, model, leading=None):
    from . import metabolism
    if contributors is not None and d.get('long_budgets'):
        d['long_arm_names'] = long_arms(d, base, contributors, leading or set())
    anticipated = False
    if metabolism.predict(d, model) > BACKGROUND_WINDOW_S:
        d['resumable'] = True
        if not d.get('sequential_stopping'):
            d['sequential_stopping'] = anticipated = True
    d['estimated_runtime_s'] = round(metabolism.predict(d, model))
    d['cost_extrapolated'] = max(d['sizes'] or [0]) > model.get('largest_n_seen', 63)
    d['fresh_hosts'] = True
    d['validity'] = dict(CANONICAL_VALIDITY)
    return d, anticipated


def compose(ledger, base, catalog=None, model=None, budget_s=None, contributors=None, caps=None, today=None):
    """The cell's proposal for the next study and its reasons: (design, plan). `base` is the latest study's design;
    `model` the cost model fitted to earlier runs (`metabolism.fit`); `budget_s` an explicit cost limit (default:
    `GROWTH` times the most expensive study in the model, at least one background window); `contributors` the
    latest study's VBS contributors (with the focal method and new baselines, the only arms given long budgets);
    `caps` the system's capabilities (`capabilities.scan`): what the design needs beyond them becomes work orders;
    `today` (with `catalog`) lets the autoreceptor check the cell's own knowledge."""
    from . import metabolism
    from .receptors import stale_knowledge
    model = model or metabolism.DEFAULT_MODEL
    entries = _order(ledger.open().items())
    if catalog is not None and today is not None:
        for c in stale_knowledge(catalog, today):
            entries.insert(0, (f'STALE_KNOWLEDGE@{c.evidence["problem_class"]}',
                               {'type': 'STALE_KNOWLEDGE', 'study': 'CELL', 'status': 'OPEN', 'severity': 'high',
                                'evidence': c.evidence, 'retired': []}))
    limit = budget_s if budget_s is not None else GROWTH * max(model.get('largest_study_s', 0), BACKGROUND_WINDOW_S)
    leading = {e['solver_key'] for cls in (catalog or {}).get('problem_classes', {}).values()
               for e in cls['entries'] if e.get('leading')}

    def attempt(es):
        d, chosen, applied, skipped, escalate = _build(base, es, ledger)
        d, anticipated = _finish(d, base, contributors, model, leading)
        return d, chosen, applied, skipped, escalate, anticipated
    answer, deferred = list(entries), {}
    d, chosen, applied, skipped, escalate, anticipated = attempt(answer)
    full_cost = d['estimated_runtime_s']
    marginal = {k: full_cost - attempt([x for x in answer if x[0] != k])[0]['estimated_runtime_s'] for k in applied}
    # triage: only when deferring what may be deferred can bring the design within the limit; the least urgent first
    if full_cost > limit:
        optional = [kv for kv in reversed(answer) if kv[0] in applied and deferrable(kv[1])]
        floor_cost = attempt([x for x in answer if x not in optional])[0]['estimated_runtime_s']
        if floor_cost <= limit:
            pending = [kv for kv in optional if marginal.get(kv[0], 0) > 0]
            while d['estimated_runtime_s'] > limit and pending:
                # within the least urgent class, the smallest deferral that fits, else the largest one
                cls = _rank_of(pending[0][1])
                group = [kv for kv in pending if _rank_of(kv[1]) == cls]
                excess = d['estimated_runtime_s'] - limit
                enough = [kv for kv in group if marginal[kv[0]] >= excess]
                kv = min(enough, key=lambda x: marginal[x[0]]) if enough else max(group, key=lambda x: marginal[x[0]])
                pending.remove(kv)
                answer = [x for x in answer if x[0] != kv[0]]
                deferred[kv[0]] = (f"cost: {applied[kv[0]]} adds about {marginal[kv[0]]} s and the study would pass "
                                   f"{round(limit)} s; deferred to the study after")
                d, chosen, applied, skipped, escalate, anticipated = attempt(answer)
    if catalog is not None:
        d['catalog_as_of'] = min((cls.get('as_of', '') for cls in catalog.get('problem_classes', {}).values()),
                                 default='')
    if deferred:
        d['deferred'] = dict(deferred)
    plan = {'chosen': chosen, 'applied': applied, 'skipped': skipped, 'deferred': deferred, 'escalate': escalate,
            'limit_s': round(limit), 'estimated_runtime_s': d['estimated_runtime_s'],
            'marginal_cost_s': dict(sorted(marginal.items(), key=lambda kv: -kv[1]))}
    if anticipated:
        plan['chosen']['ANTICIPATED_INTERRUPTION'] = 'sequential_stopping'
    if d['estimated_runtime_s'] > limit:
        top = next(iter(plan['marginal_cost_s']), None)
        plan['over_budget'] = (f"{d['estimated_runtime_s']} s against a limit of {round(limit)} s, and deferring "
                               'every caveat the membrane lets the cell defer would not bring it within the limit '
                               '(high-severity and chronic caveats are not deferred to save time); the largest share '
                               f"is {top} ({plan['marginal_cost_s'].get(top)} s): split the study there or raise the "
                               'limit')
    if caps is not None:
        from .capabilities import work_orders
        plan['work_orders'] = work_orders(d, caps)
    return d, plan


def known_responses():
    return {t: [r.name for r in rs] for t, rs in RESPONSES.items()}
