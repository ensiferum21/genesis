#!/usr/bin/env python3
"""B19 / W16: Ghost Census diagnostic on a harder DEV family (DEV only, no sealed tasks).

  b19_ghost_census.py OUT_DIR [--quick]

Order: the plan is written first (and hashed); then the translation check (Lean `decide`
against the independent evaluator), parser round trips, labels, the family, the arms at
both budgets in randomized order, Lean replay of every PROVED outcome (deduplicated;
evaluator cost, not charged to arms), and the preregistered decision.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from pathlib import Path
import random
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from genesis.common import code_identity, digest  # noqa: E402
from genesis.discovery import ghost_census as G  # noqa: E402
from genesis.fol import parse, to_tptp  # noqa: E402
from genesis.formal_research import checker  # noqa: E402


def _replay(problem, result):
    w0 = time.monotonic()
    rp = G.replay_outcome(problem, result)
    out = {k: rp.get(k) for k in ('status', 'reason', 'steps', 'hinted_steps', 'lemmas_replayed', 'errors',
                                  'proof_module_sha256', 'statement_sha256')}
    out['wall_s'] = round(time.monotonic() - w0, 2)
    return out


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False, default=str) + '\n')


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--quick', action='store_true')
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=False)
    t0 = time.monotonic()
    log = lambda m: print(f'[{time.monotonic() - t0:7.1f}s] {m}', flush=True)
    plan = dict(G.PLAN)
    if a.quick:
        plan.update(budgets_cpu_s=[2.0], label_budget={'prove_cpu_s': 5, 'ghost_max_size': 4, 'ghost_total_s': 4})
    plan_record = {'plan': plan, 'plan_sha256': digest(plan),
                   'code_identity': code_identity(ROOT)['sha256'], 'theories': G.THEORIES,
                   'statements': G.STATEMENTS}
    dump(out / 'plan.json', plan_record)
    log(f'plan {plan_record["plan_sha256"][:16]} written before any run')

    # 1. translation faithfulness and parser round trips
    items, src = G.translation_checks(plan['seed'])
    rc = checker.accept([{'name': 'GCTruth', 'source': src, 'trusted': True}], [])
    formulas = sorted({t for ax in G.THEORIES.values() for t in ax} | set(G.STATEMENTS.values()))
    round_trip = [t for t in formulas if parse(to_tptp(parse(t))) != parse(t)]
    dump(out / 'validation.json', {
        'translation': {'items': len(items), 'true_items': sum(e for _, _, e in items),
                        'lean_module': rc['modules'][0]['result'],
                        'reading': 'every theorem t_i is `decide`d by Lean; the module compiles only if Lean '
                                   'agrees with genesis.fol.evaluate on every random finite table'},
        'parser_round_trip_failures': round_trip, 'formulas': len(formulas)})
    log(f'translation check {rc["modules"][0]["result"]} on {len(items)} tables; round-trip failures {round_trip}')

    # 2. labels
    cache = {}
    labels = {}
    pools = G.pools()
    for th, names in pools.items():
        for n in names:
            labels[(th, n)] = G.label(th, n, plan=plan, cache=cache)
            L = labels[(th, n)]
            log(f'label {th}/{n}: {L["label"]} (e {L.get("e_status")}, ghost size {L.get("ghost_size")}, '
                f'{L["cpu_s"]}s)')
    dump(out / 'labels.json', {f'{k[0]}/{k[1]}': v for k, v in labels.items()})

    # 3. family
    problems = G.family(labels, plan['seed'], plan['lemmas_per_problem'])
    if a.quick:
        problems = problems[:12]
    dump(out / 'family.json', {'problems': problems, 'family_sha256': digest(problems)})

    # 4. arms
    rng = random.Random(plan['seed'] + 1)
    rows = []
    for bud in plan['budgets_cpu_s']:
        order = list(problems); rng.shuffle(order)
        for p in order:
            arms = list(plan['arms']); rng.shuffle(arms)
            for arm in arms:
                c0 = G._cpu(); w0 = time.monotonic()
                r = G.run_arm(arm, p, bud, labels)
                rows.append({'problem': p['problem_id'], 'theory': p['theory'], 'goal': p['goal'], 'arm': arm,
                             'budget': bud, 'status': r['status'], 'cpu_s': round(G._cpu() - c0, 3),
                             'wall_s': round(time.monotonic() - w0, 3), 'log': r.get('log', []),
                             'reason': r.get('reason'), '_result': r})
            log(f'budget {bud}: {p["problem_id"]} {p["theory"]}/{p["goal"]}: '
                f'{ {r["arm"]: r["status"] for r in rows if r["problem"] == p["problem_id"] and r["budget"] == bud} }')

    # 5. Lean replay of PROVED outcomes (evaluator cost), deduplicated, two workers
    by_id = {p['problem_id']: p for p in problems}
    jobs = {}
    for r in rows:
        if r['status'] != 'PROVED':
            continue
        res = r['_result']
        key = digest({'p': r['problem'], 'g': res['proof'], 'l': [x for _, x in res['lemma_proofs']]})
        jobs.setdefault(key, (by_id[r['problem']], res))
        r['replay_key'] = key
    replays, ev_wall = {}, 0.0
    with ProcessPoolExecutor(max_workers=2) as pool:
        futures = {pool.submit(_replay, prob, res): key for key, (prob, res) in sorted(jobs.items())}
        for fut in as_completed(futures):
            key = futures[fut]
            replays[key] = fut.result()
            ev_wall += replays[key]['wall_s']
            log(f'replay {jobs[key][0]["problem_id"]}: {replays[key]["status"]} ({len(replays)}/{len(jobs)})')
    for r in rows:
        if r['status'] == 'PROVED':
            r['replay'] = replays[r['replay_key']]['status']
    for r in rows:
        res = r.pop('_result')
        if r['status'] == 'PROVED':
            r['proof_sha256'] = digest({'p': res['proof']})
            r['lemmas_used'] = [n for n, _ in res['lemma_proofs']]
    dump(out / 'rows.json', rows)
    dump(out / 'replays.json', {'replays': replays, 'evaluator_wall_s': round(ev_wall, 1), 'workers': 2})

    # 6. decision
    summary = G.summarize(plan, problems, rows, labels)
    summary['labels'] = {lab: sum(v['label'] == lab for v in labels.values())
                         for lab in ('TRUE', 'TRUE_UNCHECKED', 'FALSE', 'UNKNOWN')}
    summary['replays'] = {s: sum(v['status'] == s for v in replays.values()) for s in ('THEOREM_CHECKED',
                                                                                       'NOT_REPLAYED')}
    summary['plan_sha256'] = plan_record['plan_sha256']
    summary['wall_seconds'] = round(time.monotonic() - t0, 1)
    dump(out / 'summary.json', summary)
    print(json.dumps({k: v for k, v in summary.items()}, indent=1, sort_keys=True, default=str))
    return 0


if __name__ == '__main__':
    sys.exit(main())
