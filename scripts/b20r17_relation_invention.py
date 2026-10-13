#!/usr/bin/env python3
"""B20_R17 (handoff s15.3, W10): a machine-generated representation outside the hand-written menu.

    b20r17_relation_invention.py OUT_DIR

Acceptance asked by s15.3: "at least one machine-generated representation outside the hard-coded
menu has checked semantics, a valid decoder/transport path and prospective utility after
construction cost. A renamed existing feature meets none of those requirements by itself."

Part A — generation and checking (rules fixed here, before running):
  * generator: invention.relations.generate() — every inclusion-maximal oriented relational decoder
    over k <= 3 classes that is exactly triangle-free-sound, one representative per class-relabelling
    orbit after removing unused classes; each marked NEW or with the menu decoder it equals;
  * obligations for every generated decoder: image (decode ⊆ host) and triangle-free soundness, as
    Lean statements over the repository definitions, screened by sampling, then proved through
    formal_research.loop with the builder-written recipes in relations.recipes (named in receipts);
  * construction cost: CPU of this process and its waited-for children from the start of Part A to the
    end of the proofs (discovery.construct.Budget), or the Lean checker's own reported cgroup CPU if
    that is larger (the larger is charged);
  * NEW_CHECKED: generated, NEW, and both obligations CHECKED. None -> NO_NEW_CHECKED_REPRESENTATION,
    and Part B does not run.

Part B — prospective DEV utility (fresh hosts; rules fixed here):
  * settings: B20_R13's S2 (erdos n30 p0.3) and S3 (erdos n40 p0.2), where B20_R14 found capability
    headroom to the optimum; generator seeds 20262101 + 10 i (SELECT, 8 hosts) and 20262102 + 10 i
    (EVAL, 16 hosts) for setting i, excluding every triangle-free host named in the B20_R13..RX5
    evidence and every E1 host (scripts/b20r12_e1_redo.py lists);
  * every arm runs in this process with the same CPU budget B = 1.0 s per host (process CPU), the
    domain checker validates every witness, seeds from the task identity:
      new           represent_and_repair with the NEW_CHECKED decoder (if several, the best SELECT total)
      menu          represent_and_repair with the best SELECT total among the menu decoders whose B18
                    triangle-free soundness is CHECKED (cross_2, ordered_2, adjacent_2, adjacent_3)
      conventional  the best SELECT total among the time-matched fixed DSL programs (multistart,
                    low_cycle, exchange; restarts until B is spent, 1000 queries per restart)
      matched       the chosen menu decoder with B + C / HORIZON seconds, where C is the Part A
                    construction cost and HORIZON = 100 hosts (the construction amortised over a stated
                    deployment horizon; the break-even horizon is reported too)
  * per EVAL host the paired differences new − menu, new − conventional, new − matched; mean over
    hosts, stratified by setting; 90% bootstrap interval (4000 resamples, seed 20262199);
  * verdict:
      UTILITY_AFTER_COST     every comparison has mean >= 0.5 edge per host and interval lower bound > 0;
      NO_UTILITY_AFTER_COST  otherwise (each comparison reported).
A DEV study: it licenses no claim, its hosts are exposed, and a prospective GV4 study would need its
own frozen design.
"""
import json
from pathlib import Path
import random
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis.common import canonical, code_identity, digest  # noqa: E402
from genesis.discovery.construct import Budget  # noqa: E402
from genesis.domains import ADAPTERS  # noqa: E402
from genesis.dsl import baseline_programs, solve  # noqa: E402
from genesis.formal_research import loop as L  # noqa: E402
from genesis.formal_research import triangle_theory as T  # noqa: E402
from genesis.graphs import check_witness  # noqa: E402
from genesis.invention import relations as RL  # noqa: E402
from genesis.invention import representations as RP  # noqa: E402
from genesis.models import SolverProgram  # noqa: E402

TF = 'triangle_free_host_v1'
SETTINGS = [('S2', 'erdos', {'n': 30, 'p': 0.3}), ('S3', 'erdos', {'n': 40, 'p': 0.2})]
SELECT_N, EVAL_N = 8, 16
BUDGET_S, QUERIES, HORIZON, MUE = 1.0, 1000, 100, 0.5
MENU = ('cross_2', 'ordered_2', 'adjacent_2', 'adjacent_3')
BOOT, BOOT_SEED = 4000, 20262199
DEFS = {'name': T.DEFS_MODULE, 'source': T.DEFS_SOURCE, 'trusted': True}


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False, default=str) + '\n')


def public(rec):
    return {k: v for k, v in rec.items() if not k.startswith('_')}


# ------------------------------------------------------------------ Part A

def part_a(out, log):
    budget = Budget(1e9)
    gen = RL.generate()
    props = [RL.proposal(g['k'], g['relation']) for g in gen]
    conjs = RL.conjectures(props)
    screened = {}
    for c in conjs:
        cx, _ = L.screen(c)
        screened[c['id']] = 'COUNTEREXAMPLE' if cx is not None else 'NO_COUNTEREXAMPLE'
    base = [DEFS, {'name': RL.MODULE, 'source': RL.source(props), 'trusted': True}]
    unfold = ['GT.TriangleFree'] + [f'RL.{p["id"]}' for p in props]
    state = L.prove_all(conjs, base_modules=base, conj_name='RLConj', proof_prefix='RLP', unfold=unfold,
                        extra_recipes=RL.recipes(props), log=log)
    st = {s['id']: s for s in state['statements']}
    records = []
    for g, p in zip(gen, props):
        rec = dict(public(p), equals_menu=g['equals_menu'], enumerated_at_k=g['enumerated_at_k'],
                   screen={k: screened[f'{p["id"]}_{k}'] for k in ('image', 'sound_tf')},
                   obligations={k: st.get(f'{p["id"]}_{k}', {}).get('status') for k in ('image', 'sound_tf')})
        records.append(rec)
    pkg, _ = L.assemble(state, name='relational decoders (s15.3, generated)', domain=TF,
                        scope=('Machine-generated oriented relational decoders over at most 3 classes, their checked '
                               'image and triangle-free soundness. Conservative definitions only.'),
                        conventions=['hosts list each edge once as (u, v) with u < v',
                                     'statements quantify over all pair sets, loops and reversed pairs included'],
                        extra={'relations': records})
    construction = budget.used()
    checker_cpu = _cpu_ns(state) / 1e9
    new = [p for p, r in zip(props, records) if r['equals_menu'] is None
           and r['obligations'] == {'image': 'CHECKED', 'sound_tf': 'CHECKED'}]
    dump(out / 'package.json', pkg)
    summary = {'generated': [{k: r[k] for k in ('id', 'k', 'relation', 'equals_menu', 'obligations', 'screen')}
                             for r in records],
               'new_checked': [p['id'] for p in new], 'construction_cpu_s': round(construction, 3),
               'checker_cpu_s_reported': round(checker_cpu, 3),
               'cost_note': ('construction = CPU of this process and its waited-for children (getrusage); the Lean '
                             'checker also reports its own cgroup CPU (checker_cpu_s_reported); the larger is charged'),
               'verdict_a': 'NEW_CHECKED' if new else 'NO_NEW_CHECKED_REPRESENTATION'}
    dump(out / 'part_a.json', summary)
    log(f'Part A: generated {[r["id"] + ("=" + r["equals_menu"] if r["equals_menu"] else " NEW") for r in records]}; '
        f'obligations {[(r["id"], r["obligations"]) for r in records]}; construction {construction:.1f} CPU s '
        f'-> {summary["verdict_a"]}')
    return new, max(construction, checker_cpu), summary


def _cpu_ns(obj):
    if isinstance(obj, dict):
        return sum(v if k == 'cpu_ns' and type(v) is int else _cpu_ns(v) for k, v in obj.items())
    if isinstance(obj, list):
        return sum(_cpu_ns(v) for v in obj)
    return 0


# ------------------------------------------------------------------ Part B

def run_arm(task, arm, seed, seconds):
    start = time.process_time_ns()
    if arm['kind'] == 'representation':
        o = RP.represent_and_repair(task.n, task.edges, arm['rep'], RP.tf_add_ok, cpu_seconds=seconds, seed=seed)
        witness = o['witness']
    else:
        program = SolverProgram.model_validate_json(canonical(arm['program']))
        best, k = None, 0
        while best is None or time.process_time_ns() - start < int(seconds * 1e9):
            o = solve(task, program, QUERIES, (seed + 1_000_003 * k) % (1 << 62))
            if best is None or o['value'] > best['value']:
                best = o
            k += 1
        witness = best['selected']
    cpu = (time.process_time_ns() - start) / 1e9
    value = check_witness(task, [tuple(e) for e in witness])['value']      # raises on an invalid witness
    return value, cpu


def hosts(excluded):
    a = ADAPTERS[TF]
    out = {}
    for i, (sid, family, params) in enumerate(SETTINGS):
        sel, seen, _ = a.generate(20262101 + 10 * i, SELECT_N, 'DEV', family, params, excluded=excluded)
        ev, seen, _ = a.generate(20262102 + 10 * i, EVAL_N, 'DEV', family, params, excluded=seen)
        excluded = set(seen)
        out[sid] = {'select': sel, 'eval': ev}
    return out


def boot(diffs_by_stratum):
    rng = random.Random(BOOT_SEED)
    strata = sorted(diffs_by_stratum)
    est = statistics.fmean(statistics.fmean(diffs_by_stratum[s]) for s in strata)
    sims = []
    for _ in range(BOOT):
        sims.append(statistics.fmean(statistics.fmean(rng.choice(diffs_by_stratum[s]) for _ in diffs_by_stratum[s])
                                     for s in strata))
    sims.sort()
    return est, [sims[int(0.05 * BOOT)], sims[int(0.95 * BOOT) - 1]]


def part_b(out, log, new, construction):
    import b20r12_e1_redo as E
    excluded = E.identities(E.prior_e1_hosts() + E.evidence_hosts())
    hs = hosts(excluded)
    seed_of = lambda t: int(digest({'b20r17': t.task_id})[:12], 16)
    arms = {f'new:{p["id"]}': {'kind': 'representation', 'rep': p} for p in new}
    reps = {r['id']: r for r in RP.proposals()}
    arms.update({f'menu:{m}': {'kind': 'representation', 'rep': reps[m]} for m in MENU})
    arms.update({f'conv:{n}_tm': {'kind': 'program', 'program': p.model_dump(mode='json')}
                 for n, p in sorted(baseline_programs().items())})
    select = {name: 0 for name in arms}
    for sid in hs:
        for t in hs[sid]['select']:
            for name, arm in arms.items():
                select[name] += run_arm(t, arm, seed_of(t), BUDGET_S)[0]
    pick = lambda prefix: max((n for n in arms if n.startswith(prefix)), key=lambda n: (select[n], n))
    chosen = {'new': pick('new:'), 'menu': pick('menu:'), 'conventional': pick('conv:')}
    extra_s = construction / HORIZON
    log(f'SELECT totals {select} -> {chosen}; matched arm gets {BUDGET_S + extra_s:.3f} s')
    rows = []
    for sid in hs:
        for t in hs[sid]['eval']:
            s = seed_of(t)
            v = {}
            cpu = {}
            for role in ('new', 'menu', 'conventional'):
                v[role], cpu[role] = run_arm(t, arms[chosen[role]], s, BUDGET_S)
            v['matched'], cpu['matched'] = run_arm(t, arms[chosen['menu']], s, BUDGET_S + extra_s)
            rows.append({'setting': sid, 'task_id': t.task_id, 'values': v, 'cpu_s': cpu})
            log(f'{sid} {t.task_id[-4:]}: {v}')
    comparisons = {}
    for other in ('menu', 'conventional', 'matched'):
        by = {}
        for r in rows:
            by.setdefault(r['setting'], []).append(r['values']['new'] - r['values'][other])
        est, ci = boot(by)
        flat = [d for ds in by.values() for d in ds]
        comparisons[other] = {'mean': round(est, 4), 'interval_90': [round(ci[0], 4), round(ci[1], 4)],
                              'by_setting': {k: round(statistics.fmean(d), 4) for k, d in sorted(by.items())},
                              'wins_ties_losses': [sum(d > 0 for d in flat), sum(d == 0 for d in flat),
                                                   sum(d < 0 for d in flat)],
                              'passes': est >= MUE and ci[0] > 0}
    verdict = 'UTILITY_AFTER_COST' if all(c['passes'] for c in comparisons.values()) else 'NO_UTILITY_AFTER_COST'
    gain = comparisons['menu']['mean']
    summary = {'select_totals': select, 'chosen': chosen, 'budget_s': BUDGET_S, 'horizon': HORIZON,
               'construction_cpu_s': round(construction, 3), 'matched_extra_s_per_host': round(extra_s, 4),
               'comparisons': comparisons, 'verdict': verdict,
               'note': ('break-even horizon is not computed from edges: the matched arm shows what the construction '
                        'CPU buys as extra search at HORIZON = 100 hosts'),
               'hosts': {sid: {'select': [t.task_id for t in v['select']], 'eval': [t.task_id for t in v['eval']]}
                         for sid, v in hs.items()},
               'mean_cpu_s': {role: round(statistics.fmean(r['cpu_s'][role] for r in rows), 3)
                              for role in ('new', 'menu', 'conventional', 'matched')}}
    dump(out / 'part_b_rows.json', rows)
    dump(out / 'hosts.json', {sid: {k: [t.model_dump(mode='json') for t in v[k]] for k in v} for sid, v in hs.items()})
    dump(out / 'part_b.json', summary)
    log(f'Part B: {json.dumps(comparisons)} -> {verdict}')
    return summary


def main(argv=None):
    out = Path((argv or sys.argv[1:])[0])
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    log = lambda m: print(f'[{time.monotonic() - t0:7.1f}s] {m}', flush=True)
    new, construction, a = part_a(out, log)
    b = part_b(out, log, new, construction) if new else None
    verdict = b['verdict'] if b else a['verdict_a']
    dump(out / 'summary.json', {'schema': 'genesis-b20r17-relation-invention-v1', 'part_a': a, 'part_b': b,
                                'verdict': verdict, 'code_identity': code_identity(ROOT)['sha256'],
                                'status': 'DEV; licenses no claim'})
    log(f'verdict {verdict}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
