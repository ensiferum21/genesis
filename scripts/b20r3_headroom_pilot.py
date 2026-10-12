#!/usr/bin/env python3
"""B20_R3 design pilot (DEV): where does a research library have headroom over fixed rules?

    b20r3_headroom_pilot.py OUT_DIR VARIANT [VARIANT ...]

A design-time diagnostic, not a study: it chooses nothing by itself and licenses no claim.
Its question is whether, on a given system and target range, *any* selection from the research
pool could beat the fixed policy under the calibrated cap. Per system:

  * pool as in the B20/B20_R2 design (true equations up to POOL_MAX nodes, 8 per bucket, plus
    30 false), seed 700;
  * EXHAUST: the fixed policy runs the whole pool with a generous budget (every attempt 1 s);
    cap = 0.25 x its CPU (the B20 rule); FIXED@CAP: the fixed policy under that cap;
  * per target range, 12 targets (seed 710 + range index, pool excluded), each evaluated with
    1 s per target under four libraries: EMPTY, FIXED@CAP, EXHAUST and ORACLE, the lemmas that
    eligible EXHAUST target proofs used (closed under lemma dependencies). ORACLE's research
    cost (the attempts that proved its lemmas) is reported against the cap; it is an upper
    reference built from the targets themselves, so it is optimistic by construction.

Variants named after a system are the E3 configuration (round 1); the ``:t6`` variants
(round 2, added after round 1 found no headroom) keep the pool and draw larger targets from
terms of up to 6 nodes per side.

Round 3 (``--scarcity``, added after round 2 found fixed@cap equal to the oracle everywhere):
the same pools and round-2 targets under tighter caps (SCARCITY shares of the exhaust CPU).
FIXED@SHARE is the fixed policy run under that cap; ORACLE@SHARE adds exhaust-proof lemmas
by how many target proofs used them, each with its dependency closure, while the summed
attempt CPU fits the cap.

Round 4 (``--mined``, added after round 3: on Huntington the smallest pool lemma,
idempotence, is the expensive key lemma (0.26 s; every later lemma ~6 ms), so smallest-first
*is* the oracle and a pool of small enumerated equations leaves no room for selection). The
research pool is extended with conjectures mined from 10 development targets per range: every
pair of distinct non-variable subterms of a development target (its two sides included) that
is true in the variety, up to MINED_MAX nodes. Evaluation targets with any declared relation
(EXACT/ALPHA/INSTANCE/GENERALIZES) to the research pool are dropped. Libraries: EMPTY,
FIXED@CAP, HEURISTIC@CAP (development-related smallest first), EXHAUST, ORACLE and ORACLE@CAP.

Round 5 (``--strategy``, added after round 4 found mined lemmas unused): is the prover's
strategy, rather than the library, a dimension with headroom? The round-2 targets with the
empty library under E's single automatic strategy at 1 s and 3 s, and its strategy schedule
at 1 s.

Every target and pool statement is written to OUT_DIR so later studies count it as exposed.
"""
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from genesis.common import digest  # noqa: E402
from genesis.learning import equational as Q  # noqa: E402
from genesis.learning import research as RS  # noqa: E402
from genesis.learning.budget import Account, StudyBudget  # noqa: E402

PILOT = {
    'ba_sheffer': {'pool_max': 5, 'max_term': 5, 'grid': [(6, 9), (7, 10), (8, 10)]},
    'ba_wolfram': {'pool_max': 5, 'max_term': 5, 'grid': [(5, 8), (6, 9), (7, 10)]},
    'grp_div': {'pool_max': 5, 'max_term': 5, 'grid': [(5, 8), (6, 9), (7, 10)]},
    'ba_huntington': {'pool_max': 5, 'max_term': 5, 'grid': [(7, 10), (8, 10)]},
    'grp_std': {'pool_max': 4, 'max_term': 4, 'grid': [(5, 8), (6, 8)]},
    'dist_lattice': {'pool_max': 4, 'max_term': 4, 'grid': [(5, 8), (6, 8)]},
    # round 2: larger targets
    'ba_huntington:t6': {'pool_max': 5, 'max_term': 6, 'grid': [(9, 12), (10, 12), (11, 12)]},
    'ba_sheffer:t6': {'pool_max': 5, 'max_term': 6, 'grid': [(9, 12), (10, 12), (11, 12)]},
    'grp_div:t6': {'pool_max': 5, 'max_term': 6, 'grid': [(10, 12), (11, 12)]},
    'grp_std:t6': {'pool_max': 4, 'max_term': 6, 'grid': [(9, 12), (10, 12)]},
    'dist_lattice:t6': {'pool_max': 4, 'max_term': 6, 'grid': [(9, 12), (10, 12)]},
}
SEED, TARGETS, SHARE = 700, 12, 0.25
SCARCITY = (0.02, 0.05, 0.1)
MINED_MAX, DEV_TARGETS = 12, 10
KW = {'enforcement': 'OUTER_SUPERVISED', 'quantum_ns': 100_000_000}


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False, default=str) + '\n')


def budget(cap_s):
    return StudyBudget.from_seconds(cap_s, attempt_s=1, **KW)


def closure(library, ids):
    by, out, stack = {l['id']: l for l in library}, set(), list(ids)
    while stack:
        i = stack.pop()
        if i not in out:
            out.add(i)
            stack += by[i]['uses']
    return [l for l in library if l['id'] in out]


def pilot(variant, out, log):
    cfg = PILOT[variant]
    system = variant.split(':')[0]
    pool = Q.true_equations(system, cfg['pool_max'], per_bucket=8, seed=SEED) + \
        Q.false_equations(system, cfg['pool_max'], 30, seed=SEED)
    ex = RS.run(system, RS.Fixed(), pool, account=Account(budget(10 ** 4), label=f'pilot-exhaust:{system}'),
                prove_s=1, premise_k=8)
    cap = round(SHARE * ex['account']['cpu_ns_total'] / 1e9, 3)
    fc = RS.run(system, RS.Fixed(), pool, account=Account(budget(cap), label=f'pilot-fixedcap:{system}'),
                prove_s=1, premise_k=8)
    attempt_cpu = {s['eq']: s.get('cpu_s', 0.0) for s in ex['trajectory']}
    log(f'{system}: pool {len(pool)}, exhaust library {len(ex["library"])} in {ex["cpu_s"]} s, cap {cap} s, '
        f'fixed@cap library {len(fc["library"])}')
    ranges = []
    for i, (lo, hi) in enumerate(cfg['grid']):
        T = Q.sample_targets(system, TARGETS, min_total=lo, max_total=hi, max_term=cfg['max_term'],
                             seed=SEED + 10 + i, exclude=pool)
        e0 = RS.evaluate_successor(system, [], T, eval_s=1, label=f'pilot-empty:{system}:{lo}-{hi}')
        e1 = RS.evaluate_successor(system, fc['library'], T, eval_s=1, label=f'pilot-fixedcap:{system}:{lo}-{hi}')
        e2 = RS.evaluate_successor(system, ex['library'], T, eval_s=1, label=f'pilot-exhaust:{system}:{lo}-{hi}')
        used = sorted({u for r in e2['rows'] if r['status'] == 'PROVED' for u in r['lemmas_used']})
        orc = closure(ex['library'], used)
        e3 = RS.evaluate_successor(system, orc, T, eval_s=1, label=f'pilot-oracle:{system}:{lo}-{hi}')
        oracle_cost = round(sum(attempt_cpu.get(l['text'], 0.0) for l in orc), 3)
        row = {'range': [lo, hi], 'targets': [Q.text(t) for t in T], 'empty': e0['proved'], 'fixed_cap': e1['proved'],
               'exhaust': e2['proved'], 'oracle': e3['proved'], 'oracle_lemmas': [l['text'] for l in orc],
               'oracle_cost_s': oracle_cost, 'cap_s': cap,
               'per_target': [{'target': Q.text(t), 'empty': a['status'], 'fixed_cap': b['status'],
                               'exhaust': c['status'], 'oracle': d['status']}
                              for t, a, b, c, d in zip(T, e0['rows'], e1['rows'], e2['rows'], e3['rows'])]}
        ranges.append(row)
        log(f'{system} {lo}-{hi}: empty {e0["proved"]}/{len(T)}, fixed@cap {e1["proved"]}, exhaust {e2["proved"]}, '
            f'oracle {e3["proved"]} ({len(orc)} lemmas, {oracle_cost} s vs cap {cap} s)')
    dump(out / f'{variant.replace(":", "_")}.json', {
        'variant': variant, 'system': system, 'config': {**cfg, 'seed': SEED, 'targets': TARGETS, 'share': SHARE},
        'pool': [Q.text(e) for e in pool], 'pool_sha256': digest([Q.text(e) for e in pool]),
        'exhaust': {'library': [l['text'] for l in ex['library']], 'cpu_s': ex['cpu_s'],
                    'attempts': ex['account']['attempts']},
        'fixed_cap': {'library': [l['text'] for l in fc['library']], 'cpu_s': fc['cpu_s']},
        'cap_s': cap, 'ranges': ranges,
        'status': 'DESIGN_PILOT_DEV', 'claim': 'none; a design diagnostic for choosing a family to study'})


def scarcity(variant, out, log):
    cfg = PILOT[variant]
    system = variant.split(':')[0]
    pool = Q.true_equations(system, cfg['pool_max'], per_bucket=8, seed=SEED) + \
        Q.false_equations(system, cfg['pool_max'], 30, seed=SEED)
    ex = RS.run(system, RS.Fixed(), pool, account=Account(budget(10 ** 4), label=f'pilot-exhaust:{system}'),
                prove_s=1, premise_k=8)
    attempt_cpu = {s['eq']: s.get('cpu_s', 0.0) for s in ex['trajectory']}
    total = ex['account']['cpu_ns_total'] / 1e9
    rows = []
    for i, (lo, hi) in enumerate(cfg['grid']):
        T = Q.sample_targets(system, TARGETS, min_total=lo, max_total=hi, max_term=cfg['max_term'],
                             seed=SEED + 10 + i, exclude=pool)
        e0 = RS.evaluate_successor(system, [], T, eval_s=1, label=f'scarce-empty:{system}:{lo}-{hi}')
        e2 = RS.evaluate_successor(system, ex['library'], T, eval_s=1, label=f'scarce-exhaust:{system}:{lo}-{hi}')
        uses = {}
        for r in e2['rows']:
            if r['status'] == 'PROVED':
                for u in r['lemmas_used']:
                    uses[u] = uses.get(u, 0) + 1
        for share in SCARCITY:
            cap = round(share * total, 3)
            fc = RS.run(system, RS.Fixed(), pool, account=Account(budget(cap), label=f'scarce-fixed:{system}:{share}'),
                        prove_s=1, premise_k=8)
            e1 = RS.evaluate_successor(system, fc['library'], T, eval_s=1, label=f'scarce-fixed:{system}:{lo}-{hi}')
            chosen, cost = set(), 0.0
            for u in sorted(uses, key=lambda k: (-uses[k], int(k[1:]))):
                add = {l['id'] for l in closure(ex['library'], [u])} - chosen
                c = sum(attempt_cpu.get(l['text'], 0.0) for l in ex['library'] if l['id'] in add)
                if cost + c <= cap:
                    chosen |= add
                    cost += c
            orc = [l for l in ex['library'] if l['id'] in chosen]
            e3 = RS.evaluate_successor(system, orc, T, eval_s=1, label=f'scarce-oracle:{system}:{lo}-{hi}')
            rows.append({'range': [lo, hi], 'share': share, 'cap_s': cap, 'empty': e0['proved'], 'exhaust': e2['proved'],
                         'fixed_share': e1['proved'], 'fixed_library': len(fc['library']), 'oracle_share': e3['proved'],
                         'oracle_library': [l['text'] for l in orc], 'oracle_cost_s': round(cost, 3),
                         'targets': [Q.text(t) for t in T]})
            log(f'{variant} {lo}-{hi} share {share} (cap {cap} s): empty {e0["proved"]}, fixed {e1["proved"]} '
                f'({len(fc["library"])} lemmas), oracle {e3["proved"]} ({len(orc)} lemmas, {cost:.3f} s), '
                f'exhaust {e2["proved"]} /{len(T)}')
    dump(out / f'{variant.replace(":", "_")}_scarcity.json', {
        'variant': variant, 'system': system, 'round': 3, 'shares': list(SCARCITY), 'exhaust_cpu_s': round(total, 3),
        'rows': rows, 'status': 'DESIGN_PILOT_DEV', 'claim': 'none; a design diagnostic for choosing a family to study'})


def fn_subterms(t, out):
    if t[0] == 'fn' and t[2]:
        out.append(t)
        for x in t[2]:
            fn_subterms(x, out)
    return out


def mine(dev, system, max_total=MINED_MAX):
    """True equations between distinct non-variable subterms of development targets."""
    dec, out = Q.SYSTEMS[system]['decider'], set()
    for l, r in dev:
        subs = sorted({x for x in fn_subterms(l, []) + fn_subterms(r, [])}, key=repr)
        for i, a in enumerate(subs):
            for b in subs[i + 1:]:
                if Q.size(a) + Q.size(b) <= max_total and Q.holds((a, b), dec):
                    c = Q.canon((a, b))
                    if c[0] != c[1]:
                        out.add(c)
    return sorted(out, key=repr)


def oracle_at(library, uses, attempt_cpu, cap):
    chosen, cost = set(), 0.0
    for u in sorted(uses, key=lambda k: (-uses[k], int(k[1:]))):
        add = {l['id'] for l in closure(library, [u])} - chosen
        c = sum(attempt_cpu.get(l['text'], 0.0) for l in library if l['id'] in add)
        if cost + c <= cap:
            chosen |= add
            cost += c
    return [l for l in library if l['id'] in chosen], round(cost, 3)


def mined(variant, out, log):
    from genesis.learning.partitions import EquationalAdapter
    ad = EquationalAdapter()
    cfg = PILOT[variant]
    system = variant.split(':')[0]
    base = Q.true_equations(system, cfg['pool_max'], per_bucket=8, seed=SEED) + \
        Q.false_equations(system, cfg['pool_max'], 30, seed=SEED)
    rows = []
    for i, (lo, hi) in enumerate(cfg['grid'][:2]):
        dev = Q.sample_targets(system, DEV_TARGETS, min_total=lo, max_total=hi, max_term=cfg['max_term'],
                               seed=800 + i, exclude=base)
        seen = {Q.canon(e) for e in base}
        extra = [e for e in mine(dev, system) if e not in seen]
        pool = base + extra
        T0 = Q.sample_targets(system, TARGETS + 8, min_total=lo, max_total=hi, max_term=cfg['max_term'],
                              seed=SEED + 10 + i, exclude=pool + dev)
        T = [t for t in T0 if not any(ad.relation(t, v) for v in pool + dev)][:TARGETS]
        ex = RS.run(system, RS.Fixed(), pool, account=Account(budget(10 ** 4), label=f'mined-exhaust:{system}'),
                    prove_s=1, premise_k=8)
        attempt_cpu = {s['eq']: s.get('cpu_s', 0.0) for s in ex['trajectory']}
        cap = round(SHARE * ex['account']['cpu_ns_total'] / 1e9, 3)
        fc = RS.run(system, RS.Fixed(), pool, account=Account(budget(cap), label=f'mined-fixed:{system}'),
                    prove_s=1, premise_k=8)
        hc = RS.run(system, RS.Heuristic(), pool, account=Account(budget(cap), label=f'mined-heur:{system}'),
                    dev_targets=dev, prove_s=1, premise_k=8)
        ev = {k: RS.evaluate_successor(system, lib, T, eval_s=1, label=f'mined-{k}:{system}:{lo}-{hi}')
              for k, lib in (('empty', []), ('fixed_cap', fc['library']), ('heuristic_cap', hc['library']),
                             ('exhaust', ex['library']))}
        uses = {}
        for r in ev['exhaust']['rows']:
            if r['status'] == 'PROVED':
                for u in r['lemmas_used']:
                    uses[u] = uses.get(u, 0) + 1
        orc = closure(ex['library'], list(uses))
        orc_cap, orc_cost = oracle_at(ex['library'], uses, attempt_cpu, cap)
        ev['oracle'] = RS.evaluate_successor(system, orc, T, eval_s=1, label=f'mined-oracle:{system}:{lo}-{hi}')
        ev['oracle_cap'] = RS.evaluate_successor(system, orc_cap, T, eval_s=1, label=f'mined-oraclecap:{system}')
        mined_ids = {l['id'] for l in ex['library'] if l['eq'] in set(extra)}
        row = {'range': [lo, hi], 'dev': [Q.text(e) for e in dev], 'mined': [Q.text(e) for e in extra],
               'mined_proved': len(mined_ids), 'targets': [Q.text(t) for t in T], 'cap_s': cap,
               'exhaust_cpu_s': ex['cpu_s'], 'fixed_library': len(fc['library']), 'heuristic_library': len(hc['library']),
               'oracle_lemmas': [l['text'] for l in orc], 'oracle_cap_lemmas': [l['text'] for l in orc_cap],
               'oracle_cap_cost_s': orc_cost, 'mined_used_by_exhaust_proofs': len(mined_ids & set(uses)),
               **{k: v['proved'] for k, v in ev.items()}}
        rows.append(row)
        log(f'{variant} {lo}-{hi}: mined {len(extra)} ({len(mined_ids)} proved, {row["mined_used_by_exhaust_proofs"]} '
            f'used), cap {cap} s | empty {row["empty"]}, fixed@cap {row["fixed_cap"]}, heuristic@cap '
            f'{row["heuristic_cap"]}, exhaust {row["exhaust"]}, oracle {row["oracle"]}, oracle@cap {row["oracle_cap"]} '
            f'/{len(T)}')
    dump(out / f'{variant.replace(":", "_")}_mined.json', {
        'variant': variant, 'system': system, 'round': 4, 'rows': rows, 'mined_max': MINED_MAX,
        'status': 'DESIGN_PILOT_DEV', 'claim': 'none; a design diagnostic for choosing a family to study'})


def strategy(variant, out, log):
    from genesis.verification.eprover import prove_bounded
    cfg = PILOT[variant]
    system = variant.split(':')[0]
    pool = Q.true_equations(system, cfg['pool_max'], per_bucket=8, seed=SEED) + \
        Q.false_equations(system, cfg['pool_max'], 30, seed=SEED)

    def prover(mode):
        def p(axioms, goal, *, res, label):
            return prove_bounded(axioms, goal, limit_s=res.prover_limit_s, cpu_ns=res.cpu_ns, wall_ns=res.wall_ns,
                                 mode=mode, label=label)
        return p
    rows = []
    for i, (lo, hi) in enumerate(cfg['grid']):
        T = Q.sample_targets(system, TARGETS, min_total=lo, max_total=hi, max_term=cfg['max_term'],
                             seed=SEED + 10 + i, exclude=pool)
        r = {'range': [lo, hi], 'targets': [Q.text(t) for t in T]}
        for name, mode, sec in (('auto_1s', 'auto', 1), ('schedule_1s', 'schedule', 1), ('auto_3s', 'auto', 3)):
            ev = RS.evaluate_successor(system, [], T, eval_s=sec, label=f'strategy-{name}:{system}', prover=prover(mode))
            r[name] = ev['proved']
            r[name + '_rows'] = [x['status'] for x in ev['rows']]
        rows.append(r)
        log(f'{variant} {lo}-{hi}: auto@1s {r["auto_1s"]}, schedule@1s {r["schedule_1s"]}, auto@3s {r["auto_3s"]} /{len(T)}')
    dump(out / f'{variant.replace(":", "_")}_strategy.json', {
        'variant': variant, 'system': system, 'round': 5, 'rows': rows,
        'status': 'DESIGN_PILOT_DEV', 'claim': 'none; a design diagnostic for choosing a family to study'})


def summarize(out, log):
    """summary.json: per variant and range, the selection headroom (ORACLE - FIXED@CAP) and the
    library headroom (EXHAUST - EMPTY), from the round files present."""
    rows = []
    for f in sorted(out.glob('*.json')):
        if f.name == 'summary.json':
            continue
        d = json.loads(f.read_text())
        rnd = d.get('round', 1 if ':' not in d.get('variant', d['system']) else 2)
        for r in d.get('ranges', []):
            rows.append({'file': f.name, 'round': rnd, 'variant': d.get('variant', d['system']), 'range': r['range'],
                         'targets': len(r['targets']), 'empty': r['empty'], 'fixed_cap': r['fixed_cap'],
                         'exhaust': r['exhaust'], 'oracle': r['oracle'],
                         'selection_headroom': r['oracle'] - r['fixed_cap'], 'library_headroom': r['exhaust'] - r['empty']})
        for r in d['rows'] if d.get('round') == 4 else []:
            rows.append({'file': f.name, 'round': 4, 'variant': d['variant'], 'range': r['range'],
                         'targets': len(r['targets']), 'empty': r['empty'], 'fixed_cap': r['fixed_cap'],
                         'heuristic_cap': r['heuristic_cap'], 'exhaust': r['exhaust'], 'oracle': r['oracle'],
                         'oracle_cap': r['oracle_cap'], 'mined': len(r['mined']),
                         'mined_used': r['mined_used_by_exhaust_proofs'],
                         'selection_headroom': r['oracle'] - r['fixed_cap'], 'library_headroom': r['exhaust'] - r['empty']})
        for r in d['rows'] if d.get('round') == 5 else []:
            rows.append({'file': f.name, 'round': 5, 'variant': d['variant'], 'range': r['range'],
                         'targets': len(r['targets']), 'auto_1s': r['auto_1s'], 'schedule_1s': r['schedule_1s'],
                         'auto_3s': r['auto_3s'], 'strategy_headroom': max(r['schedule_1s'], r['auto_3s']) - r['auto_1s']})
        for r in d['rows'] if d.get('round') == 3 else []:
            rows.append({'file': f.name, 'round': 3, 'variant': d['variant'], 'range': r['range'], 'share': r['share'],
                         'targets': len(r['targets']), 'empty': r['empty'], 'fixed_share': r['fixed_share'],
                         'oracle_share': r['oracle_share'], 'fixed_library': r['fixed_library'],
                         'oracle_library': len(r['oracle_library'])})
    sel = [r['selection_headroom'] for r in rows if 'selection_headroom' in r]
    summary = {'rows': rows, 'max_selection_headroom': max(sel), 'max_selection_headroom_share': max(
        r['selection_headroom'] / r['targets'] for r in rows if 'selection_headroom' in r),
        'max_strategy_headroom': max((r['strategy_headroom'] for r in rows if 'strategy_headroom' in r), default=None),
        'status': 'DESIGN_PILOT_DEV'}
    dump(out / 'summary.json', summary)
    log(f'{len(rows)} rows; max selection headroom {summary["max_selection_headroom"]} targets '
        f'({summary["max_selection_headroom_share"]:.2f}); max strategy headroom {summary["max_strategy_headroom"]}')


def main(argv=None):
    a = argv or sys.argv[1:]
    if '--summary' in a:
        out = Path([x for x in a if x != '--summary'][0])
        summarize(out, print)
        return 0
    mode = scarcity if '--scarcity' in a else mined if '--mined' in a else strategy if '--strategy' in a else pilot
    a = [x for x in a if x not in ('--scarcity', '--mined', '--strategy')]
    out = Path(a[0])
    t0 = time.monotonic()
    log = lambda m: print(f'[{time.monotonic() - t0:7.1f}s] {m}', flush=True)
    for s in a[1:]:
        mode(s, out, log)
    return 0


if __name__ == '__main__':
    sys.exit(main())
