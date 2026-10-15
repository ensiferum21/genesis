#!/usr/bin/env python3
"""B20_R26 (handoff s15.3, W10): quotient representations with a proved transport condition.

    b20r26_quotient_invention.py OUT_DIR

This is the first attempt in a new family, preregistered here. The relational family (B20_R17,
B20_R19) is retired as a utility source after two attempts. Every attempt in this family counts.

The family is `invention.quotients`. Each host's representation is a partition q into K blocks
and a pattern Q on the blocks, and the method optimises both per host:
  * the exact best transitive-triple-free pattern for the partition (branch and bound);
  * vertex moves under that pattern;
  * greedy completion under the domain checker.
One Lean theorem covers every q, Q and H: GT.TriangleFree Q → GT.TriangleFree (QT.lift q Q H),
together with QT.lift q Q H ⊆ H.

Part A — checking (rules fixed here, before running):
  * the two obligations (image, transport) are stated over the repository definitions,
    screened by sampling, then proved through formal_research.loop with the builder-written
    recipes in quotients.recipes (named in the receipts);
  * construction cost: the CPU of this process and its waited-for children from the start of
    Part A to the end of the proofs (discovery.construct.Budget), or the Lean checker's own
    reported CPU if that is larger (the larger is charged);
  * NEW_CHECKED: both obligations CHECKED. Otherwise NO_NEW_CHECKED_REPRESENTATION, and Part B
    does not run;
  * candidates: quotient_K for K = 3, 4, 5, 6. K = 2 is excluded because it equals cross_2: on two
    blocks the best pattern is always both arcs.

Part B — the B20_R17 design unchanged, with fresh seeds:
  * settings S2 (erdos n30 p0.3) and S3 (erdos n40 p0.2);
  * SELECT 8 and EVAL 16 hosts per setting, generator seeds 20262601 + 10 i and 20262602 + 10 i;
  * excluded: every host named in the B20_R13..RX5 evidence (scripts/b20r12_e1_redo.py), every
    E1 host, every host in handoff/e1 and handoff/e1b exposure_hosts_all.json, and every
    B20_R17 and B20_R19 host;
  * every arm 1.0 CPU s per host, in this process, with the domain checker validating every
    witness and seeds taken from the task identity;
  * arms: new (the best SELECT total among the candidates); menu (the best SELECT total among
    cross_2, ordered_2, adjacent_2 and adjacent_3); conventional (the best time-matched DSL
    program); matched (the chosen menu decoder with 1.0 s + construction / 100 hosts);
  * paired differences new − menu, new − conventional and new − matched, stratified bootstrap
    (4000 resamples, seed 20262699);
  * verdict: UTILITY_AFTER_COST iff every comparison has mean ≥ 0.5 edge per host and a 90%
    interval lower bound > 0; otherwise NO_UTILITY_AFTER_COST.
Diagnostics, which do not enter the verdict: per EVAL host, the chosen quotient's block count,
pattern size and the decoded size before repair.

A DEV study. It licenses no claim, its hosts are exposed, and this is attempt 1 of the quotient
family.
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
from genesis.common import canonical, code_identity, digest  # noqa: E402
from genesis.discovery.construct import Budget  # noqa: E402
from genesis.domains import ADAPTERS  # noqa: E402
from genesis.dsl import baseline_programs  # noqa: E402
from genesis.formal_research import loop as L  # noqa: E402
from genesis.graphs import check_witness  # noqa: E402
from genesis.invention import quotients as QT  # noqa: E402
from genesis.invention import representations as RP  # noqa: E402
from genesis.models import GraphTask  # noqa: E402

CANDIDATES = (3, 4, 5, 6)
SEEDS = (20262601, 20262602)
BOOT_SEED = 20262699
PRIOR_HOSTS = ('relation_invention_b20r17', 'relation_invention_b20r19')
EXPOSURE_LISTS = ('handoff/e1/exposure_hosts_all.json', 'handoff/e1b/exposure_hosts_all.json')


def part_a(out, log):
    budget = Budget(1e9)
    conjs = QT.conjectures()
    screened = {c['id']: 'COUNTEREXAMPLE' if L.screen(c)[0] is not None else 'NO_COUNTEREXAMPLE' for c in conjs}
    base = [R17.DEFS, {'name': QT.MODULE, 'source': QT.SOURCE, 'trusted': True}]
    state = L.prove_all(conjs, base_modules=base, conj_name='QTConj', proof_prefix='QTP',
                        unfold=['GT.TriangleFree', 'QT.lift'], extra_recipes=QT.recipes, log=log)
    st = {s['id']: s for s in state['statements']}
    obligations = {k: st.get(f'quotient_{k}', {}).get('status') for k in ('image', 'sound_tf')}
    props = [QT.proposal(K) for K in CANDIDATES]
    pkg, _ = L.assemble(state, name='quotient representations (s15.3, attempt 1 of the family)', domain=R17.TF,
                        scope=('The quotient lift of a host by a block map and a pattern, with its image and the '
                               'transport condition (a triangle-free pattern lifts to a triangle-free edge set), '
                               'proved once for every block map, pattern and host. Conservative definitions only.'),
                        conventions=['hosts list each edge once as (u, v) with u < v',
                                     'statements quantify over all pair sets, loops and reversed pairs included'],
                        extra={'candidates': [R17.public(p) for p in props],
                               'excluded': {'quotient_2': 'equals cross_2 (two blocks: the best pattern is both arcs)'}})
    construction = budget.used()
    checker = R17._cpu_ns(state) / 1e9
    ok = obligations == {'image': 'CHECKED', 'sound_tf': 'CHECKED'}
    R17.dump(out / 'package.json', pkg)
    summary = {'obligations': obligations, 'screen': screened, 'candidates': [p['id'] for p in props],
               'construction_cpu_s': round(construction, 3), 'checker_cpu_s_reported': round(checker, 3),
               'verdict_a': 'NEW_CHECKED' if ok else 'NO_NEW_CHECKED_REPRESENTATION'}
    R17.dump(out / 'part_a.json', summary)
    log(f'Part A: {obligations}; construction {construction:.1f} CPU s -> {summary["verdict_a"]}')
    return (props if ok else []), max(construction, checker), summary


def excluded_identities():
    import b20r12_e1_redo as E
    named = E.prior_e1_hosts() + E.evidence_hosts()
    for d in PRIOR_HOSTS:
        prior = json.loads((ROOT / 'evidence' / d / 'hosts.json').read_text())
        named += [GraphTask.model_validate_json(canonical(t)) for v in prior.values() for k in v for t in v[k]]
    for f in EXPOSURE_LISTS:
        named += [GraphTask.model_validate_json(canonical(t)) for t in json.loads((ROOT / f).read_text())
                  if t.get('domain') == R17.TF]
    return E.identities(named), len(named)


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
    if arm['kind'] != 'quotient':
        value, cpu = R17.run_arm(task, arm, seed, seconds)
        return value, cpu, None
    start = time.process_time_ns()
    o = QT.quotient_and_repair(task.n, task.edges, arm['rep']['k'], RP.tf_add_ok, cpu_seconds=seconds, seed=seed)
    cpu = (time.process_time_ns() - start) / 1e9
    value = check_witness(task, [tuple(e) for e in o['witness']])['value']      # raises on an invalid witness
    diag = {'blocks': o['blocks'], 'pattern_arcs': len(o['pattern']), 'decoded_before_repair': o['decoded_before_repair'],
            'rounds': o['rounds']}
    return value, cpu, diag


def part_b(out, log, new, construction):
    excluded, named = excluded_identities()
    hs = hosts(excluded)
    seed_of = lambda t: int(digest({'b20r26': t.task_id})[:12], 16)
    arms = {f'new:{p["id"]}': {'kind': 'quotient', 'rep': p} for p in new}
    reps = {r['id']: r for r in RP.proposals()}
    arms.update({f'menu:{m}': {'kind': 'representation', 'rep': reps[m]} for m in R17.MENU})
    arms.update({f'conv:{n}_tm': {'kind': 'program', 'program': p.model_dump(mode='json')}
                 for n, p in sorted(baseline_programs().items())})
    select = {name: 0 for name in arms}
    for sid in hs:
        for t in hs[sid]['select']:
            for name, arm in arms.items():
                select[name] += run_arm(t, arm, seed_of(t), R17.BUDGET_S)[0]
    pick = lambda prefix: max((n for n in arms if n.startswith(prefix)), key=lambda n: (select[n], n))
    chosen = {'new': pick('new:'), 'menu': pick('menu:'), 'conventional': pick('conv:')}
    extra_s = construction / R17.HORIZON
    log(f'SELECT totals {select} -> {chosen}; matched arm gets {R17.BUDGET_S + extra_s:.3f} s')
    rows = []
    for sid in hs:
        for t in hs[sid]['eval']:
            s = seed_of(t)
            v, cpu = {}, {}
            v['new'], cpu['new'], diag = run_arm(t, arms[chosen['new']], s, R17.BUDGET_S)
            for role in ('menu', 'conventional'):
                v[role], cpu[role], _ = run_arm(t, arms[chosen[role]], s, R17.BUDGET_S)
            v['matched'], cpu['matched'], _ = run_arm(t, arms[chosen['menu']], s, R17.BUDGET_S + extra_s)
            rows.append({'setting': sid, 'task_id': t.task_id, 'values': v, 'cpu_s': cpu, 'new_diagnostics': diag})
            log(f'{sid} {t.task_id[-4:]}: {v} {diag}')
    real = R17.BOOT_SEED
    R17.BOOT_SEED = BOOT_SEED
    try:
        comparisons = {}
        for other in ('menu', 'conventional', 'matched'):
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
                              for role in ('new', 'menu', 'conventional', 'matched')},
               'diagnostics': {'mean_pattern_arcs': round(statistics.fmean(r['new_diagnostics']['pattern_arcs']
                                                                          for r in rows), 3),
                               'mean_decoded_before_repair': round(statistics.fmean(
                                   r['new_diagnostics']['decoded_before_repair'] for r in rows), 3)}}
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
    R17.dump(out / 'summary.json', {'schema': 'genesis-b20r26-quotient-invention-v1', 'part_a': a, 'part_b': b,
                                    'verdict': verdict, 'family': 'quotient', 'attempts_in_family': ['B20_R26'],
                                    'retired_families': {'relational': ['B20_R17', 'B20_R19']},
                                    'code_identity': code_identity(ROOT)['sha256'], 'status': 'DEV; licenses no claim'})
    log(f'verdict {verdict}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
