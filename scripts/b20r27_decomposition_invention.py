#!/usr/bin/env python3
"""B20_R27 (handoff s15.3, W10): decompositions with verified witness composition.

    b20r27_decomposition_invention.py OUT_DIR

This is the first attempt in the decomposition family, preregistered here. Every attempt counts.
The family is `invention.decompositions`:
  * a balanced m-way vertex partition that reduces the number of edges between parts;
  * each part solved by the B20_RX3 exact components (LP-ordered greedy, then CaDiCaL climbing);
  * the parts' witnesses composed;
  * the edges between parts repaired greedily under the domain checker.
One Lean theorem certifies the composition: vertex-disjoint triangle-free edge sets have a
triangle-free union.

Part A — checking (rules fixed here, before running):
  * the composition obligation is stated over the repository definitions, screened by
    sampling, then proved through formal_research.loop with the builder-written recipe in
    decompositions.recipes (named in the receipts);
  * construction cost as in B20_R17: the larger of this process's CPU, its waited-for children
    included, and the checker's own report;
  * NEW_CHECKED iff CHECKED; otherwise NO_NEW_CHECKED_REPRESENTATION, and Part B does not run;
  * candidates: decomp_m for m = 2, 3, 4.

Part B — the B20_R17 design with fresh seeds and one more control:
  * settings S2 (erdos n30 p0.3) and S3 (erdos n40 p0.2);
  * SELECT 8 and EVAL 16 hosts per setting, generator seeds 20262701 + 10 i and 20262702 + 10 i;
  * excluded: everything B20_R26 excluded, plus B20_R26's hosts, plus three DEV hosts the builder
    looked at while developing this family (generator seed 999001, erdos n40 p0.2);
  * every arm 1.0 CPU s per host, children included (discovery.construct.Budget), with the domain
    checker validating every witness and seeds taken from the task identity;
  * arms:
    - new: the best SELECT total among the candidates;
    - whole: the same exact components on the whole host, at the same budget. This control
      isolates the decomposition from the components, which are an existing capability
      (B20_RX3);
    - menu: the best SELECT total among cross_2, ordered_2, adjacent_2 and adjacent_3;
    - conventional: the best time-matched DSL program;
    - matched: the chosen menu decoder with 1.0 s + construction / 100 hosts;
  * paired differences new − whole, new − menu, new − conventional and new − matched, stratified
    bootstrap (4000 resamples, seed 20262799);
  * verdict: UTILITY_AFTER_COST iff every comparison has mean ≥ 0.5 edge per host and a 90%
    interval lower bound > 0; otherwise NO_UTILITY_AFTER_COST.

Before preregistration, the builder ran the method and the control once on three DEV hosts while
developing it. Those hosts are excluded above. On all three, decomp_2 scored 3–4 edges and decomp_3
3–5 edges below `whole`. The design was not changed after seeing this.

A DEV study. It licenses no claim, its hosts are exposed, and this is attempt 1 of the
decomposition family.
"""
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

import b20r17_relation_invention as R17  # noqa: E402
import b20r26_quotient_invention as R26  # noqa: E402
from genesis.common import canonical, code_identity, digest  # noqa: E402
from genesis.discovery.construct import Budget  # noqa: E402
from genesis.domains import ADAPTERS  # noqa: E402
from genesis.dsl import baseline_programs  # noqa: E402
from genesis.formal_research import loop as L  # noqa: E402
from genesis.graphs import check_witness  # noqa: E402
from genesis.invention import decompositions as D  # noqa: E402
from genesis.invention import representations as RP  # noqa: E402
from genesis.models import GraphTask  # noqa: E402

CANDIDATES = (2, 3, 4)
SEEDS = (20262701, 20262702)
BOOT_SEED = 20262799
DEVELOPMENT_LOOK = (999001, 3, 'erdos', {'n': 40, 'p': 0.2})


def part_a(out, log):
    budget = Budget(1e9)
    conjs = D.conjectures()
    screened = {c['id']: 'COUNTEREXAMPLE' if L.screen(c)[0] is not None else 'NO_COUNTEREXAMPLE' for c in conjs}
    state = L.prove_all(conjs, base_modules=[R17.DEFS], conj_name='DCConj', proof_prefix='DCP',
                        unfold=['GT.TriangleFree'], extra_recipes=D.recipes, log=log)
    st = {s['id']: s for s in state['statements']}
    status = st.get('decomposition_union', {}).get('status')
    props = [D.proposal(m) for m in CANDIDATES]
    pkg, _ = L.assemble(state, name='decompositions (s15.3, attempt 1 of the family)', domain=R17.TF,
                        scope=('Vertex-disjoint triangle-free edge sets have a triangle-free union: the composition '
                               'step of a decomposition, proved once for all edge sets.'),
                        conventions=['hosts list each edge once as (u, v) with u < v',
                                     'statements quantify over all pair sets, loops and reversed pairs included'],
                        extra={'candidates': [R17.public(p) for p in props]})
    construction = budget.used()
    checker = R17._cpu_ns(state) / 1e9
    R17.dump(out / 'package.json', pkg)
    summary = {'obligations': {'composition': status}, 'screen': screened, 'candidates': [p['id'] for p in props],
               'construction_cpu_s': round(construction, 3), 'checker_cpu_s_reported': round(checker, 3),
               'verdict_a': 'NEW_CHECKED' if status == 'CHECKED' else 'NO_NEW_CHECKED_REPRESENTATION'}
    R17.dump(out / 'part_a.json', summary)
    log(f'Part A: composition {status}; construction {construction:.1f} CPU s -> {summary["verdict_a"]}')
    return (props if status == 'CHECKED' else []), max(construction, checker), summary


def excluded_identities():
    import b20r12_e1_redo as E
    ids, named = R26.excluded_identities()
    prior = json.loads((ROOT / 'evidence' / 'quotient_invention_b20r26' / 'hosts.json').read_text())
    extra = [GraphTask.model_validate_json(canonical(t)) for v in prior.values() for k in v for t in v[k]]
    seed, count, family, params = DEVELOPMENT_LOOK
    look, _, _ = ADAPTERS[R17.TF].generate(seed, count, 'DEV', family, params)
    return ids | E.identities(extra + list(look)), named + len(extra) + len(look)


def hosts(excluded):
    a = ADAPTERS[R17.TF]
    out = {}
    for i, (sid, family, params) in enumerate(R17.SETTINGS):
        sel, seen, _ = a.generate(SEEDS[0] + 10 * i, R17.SELECT_N, 'DEV', family, params, excluded=excluded)
        ev, seen, _ = a.generate(SEEDS[1] + 10 * i, R17.EVAL_N, 'DEV', family, params, excluded=seen)
        excluded = set(seen)
        out[sid] = {'select': sel, 'eval': ev}
    return out


def run_arm(task, arm, seed, seconds):
    if arm['kind'] in ('representation', 'program'):
        value, cpu = R17.run_arm(task, arm, seed, seconds)
        return value, cpu, None
    b = Budget(1e9)
    if arm['kind'] == 'decomposition':
        o = D.decompose_and_repair(task, arm['rep']['parts'], cpu_seconds=seconds, seed=seed)
        diag = {k: o[k] for k in ('parts', 'composed', 'cut', 'part_stops', 'repair_tries')}
    else:
        o = D.whole(task, cpu_seconds=seconds, seed=seed)
        diag = {'stop': o['stop']}
    cpu = b.used()
    value = check_witness(task, [tuple(e) for e in o['witness']])['value']      # raises on an invalid witness
    return value, cpu, diag


def part_b(out, log, new, construction):
    excluded, named = excluded_identities()
    hs = hosts(excluded)
    seed_of = lambda t: int(digest({'b20r27': t.task_id})[:12], 16)
    arms = {f'new:{p["id"]}': {'kind': 'decomposition', 'rep': p} for p in new}
    arms['whole:exact_components'] = {'kind': 'whole'}
    reps = {r['id']: r for r in RP.proposals()}
    arms.update({f'menu:{m}': {'kind': 'representation', 'rep': reps[m]} for m in R17.MENU})
    arms.update({f'conv:{n}_tm': {'kind': 'program', 'program': p.model_dump(mode='json')}
                 for n, p in sorted(baseline_programs().items())})
    select = {name: 0 for name in arms if not name.startswith('whole:')}
    for sid in hs:
        for t in hs[sid]['select']:
            for name in select:
                select[name] += run_arm(t, arms[name], seed_of(t), R17.BUDGET_S)[0]
    pick = lambda prefix: max((n for n in select if n.startswith(prefix)), key=lambda n: (select[n], n))
    chosen = {'new': pick('new:'), 'whole': 'whole:exact_components', 'menu': pick('menu:'),
              'conventional': pick('conv:')}
    extra_s = construction / R17.HORIZON
    log(f'SELECT totals {select} -> {chosen}; matched arm gets {R17.BUDGET_S + extra_s:.3f} s')
    rows = []
    for sid in hs:
        for t in hs[sid]['eval']:
            s = seed_of(t)
            v, cpu, diag = {}, {}, {}
            for role in ('new', 'whole', 'menu', 'conventional'):
                v[role], cpu[role], diag[role] = run_arm(t, arms[chosen[role]], s, R17.BUDGET_S)
            v['matched'], cpu['matched'], _ = run_arm(t, arms[chosen['menu']], s, R17.BUDGET_S + extra_s)
            rows.append({'setting': sid, 'task_id': t.task_id, 'values': v, 'cpu_s': cpu,
                         'diagnostics': {k: x for k, x in diag.items() if x is not None}})
            log(f'{sid} {t.task_id[-4:]}: {v}')
    real = R17.BOOT_SEED
    R17.BOOT_SEED = BOOT_SEED
    try:
        comparisons = {}
        for other in ('whole', 'menu', 'conventional', 'matched'):
            by = {}
            for r in rows:
                by.setdefault(r['setting'], []).append(r['values']['new'] - r['values'][other])
            est, ci = R17.boot(by)
            flat = [d for ds in by.values() for d in ds]
            comparisons[other] = {'mean': round(est, 4), 'interval_90': [round(ci[0], 4), round(ci[1], 4)],
                                  'by_setting': {k: round(statistics.fmean(d), 4) for k, d in sorted(by.items())},
                                  'wins_ties_losses': [sum(d > 0 for d in flat), sum(d == 0 for d in flat),
                                                       sum(d < 0 for d in flat)],
                                  'passes': est >= R17.MUE and ci[0] > 0}
    finally:
        R17.BOOT_SEED = real
    verdict = 'UTILITY_AFTER_COST' if all(c['passes'] for c in comparisons.values()) else 'NO_UTILITY_AFTER_COST'
    summary = {'select_totals': select, 'chosen': chosen, 'budget_s': R17.BUDGET_S, 'horizon': R17.HORIZON,
               'construction_cpu_s': round(construction, 3), 'matched_extra_s_per_host': round(extra_s, 4),
               'comparisons': comparisons, 'verdict': verdict, 'excluded_named_hosts': named,
               'hosts': {sid: {'select': [t.task_id for t in v['select']], 'eval': [t.task_id for t in v['eval']]}
                         for sid, v in hs.items()},
               'mean_cpu_s': {role: round(statistics.fmean(r['cpu_s'][role] for r in rows), 3)
                              for role in ('new', 'whole', 'menu', 'conventional', 'matched')}}
    R17.dump(out / 'part_b_rows.json', rows)
    R17.dump(out / 'hosts.json', {sid: {k: [t.model_dump(mode='json') for t in v[k]] for k in v} for sid, v in hs.items()})
    R17.dump(out / 'part_b.json', summary)
    log(f'Part B: {json.dumps(comparisons)} -> {verdict}')
    return summary


def main(argv=None):
    out = Path((argv or sys.argv[1:])[0])
    if (out / 'summary.json').exists():
        raise FileExistsError(out / 'summary.json')
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    log = lambda m: print(f'[{time.monotonic() - t0:7.1f}s] {m}', flush=True)
    new, construction, a = part_a(out, log)
    b = part_b(out, log, new, construction) if new else None
    verdict = b['verdict'] if b else a['verdict_a']
    R17.dump(out / 'summary.json', {'schema': 'genesis-b20r27-decomposition-invention-v1', 'part_a': a, 'part_b': b,
                                    'verdict': verdict, 'family': 'decomposition', 'attempts_in_family': ['B20_R27'],
                                    'retired_families': {'relational': ['B20_R17', 'B20_R19']},
                                    'code_identity': code_identity(ROOT)['sha256'], 'status': 'DEV; licenses no claim'})
    log(f'verdict {verdict}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
