#!/usr/bin/env python3
"""B20_R36 (s15.3 / W10, GV4): generated rows as a construction component in the dense regime
(relaxation family, attempt 2).

    b20r36_dense_construction.py OUT_DIR

Attempt 2 of the relaxation family, preregistered here. Every attempt counts. Attempt 1
(B20_R31) used the generated rows to order the LP greedy on the `e1b` family. There the triangle
LP is nearly tight, and the gain over the plain LP greedy was +0.19 per host: interval above 0, but
below the 0.5 minimum useful effect (NO_UTILITY_AFTER_COST).

B20_R35 then showed that in two denser settings the triangle LP is far from the optimum (gaps of
6–10 edges), and that the Lean-checked K5 rows close most of that gap. This attempt asks whether
the tighter LP also gives a better *construction* there. The settings are chosen because the
relaxation is loose in them, and that choice is declared here. Everything below is fixed before
running.

**Component.** `invention.cuts.cut_lp_greedy` with B20_R31's Lean-checked K5 bound only (pattern
`pat5_10_…`, ex 6). The W5 bound is left out: on three dense hosts it added nothing to the bound
and cost 25–44 s of enumeration (B20_R35 development look). Copies are enumerated within half the
budget, and then the LP-ordered greedy with LP-perturbed restarts runs (B20_RX3 lp_greedy). Every
witness is re-checked by the domain checker.

**Construction cost.** This is B20_R31's artifact, at B20_R31's cost: max(46.661 process CPU s,
28.14 checker CPU s) = 46.661 s. Over the B20_R17 horizon of 100 hosts, the matched arm gets
+0.4666 s.

**Design.** B20_R17's, at E1b's budget:
  * settings: planted_cluster n40 p_in 0.8 p_out 0.06, and erdos n30 p0.42;
  * SELECT 8 and EVAL 16 hosts per setting, generator seeds 20263601 + 10 i (SELECT) and
    20263602 + 10 i (EVAL). They exclude every identity b20r24_repilots.exposure excludes
    (B20_R35's hosts included). On resume the script reloads its own hosts.json;
  * the whole study is pinned to one core, as in B20_R33;
  * every arm gets 2.0 CPU s per host, its children included, with seeds taken from the task
    identity.

**Arms:**
    new           cut_lp_greedy with the K5 rows;
    control       discovery.construct.lp_greedy on the triangle LP: the same component without
                  the generated rows;
    menu          the best SELECT total among cross_2, ordered_2, adjacent_2 and adjacent_3;
    conventional  the best SELECT total among the time-matched DSL programs;
    matched       the control with 2.0 s + 0.4666 s;
    mip           an exact HiGHS MILP at 2.0 s (B20_R33's arm). This is a secondary strong
                  baseline, reported with its own flag.

**Analysis.** Paired differences new − X, stratified by setting, bootstrap of 4000 resamples
(seed 20263699), 90% interval. A comparison passes iff its mean is ≥ 0.5 and its lower bound
is > 0.

**Verdict (fixed here):**
  * UTILITY_AFTER_COST iff the control, menu, conventional and matched comparisons all pass
    (the B20_R17 rule); otherwise NO_UTILITY_AFTER_COST;
  * reported separately: BEYOND_MIP iff the new − mip comparison passes.

**Reference (descriptive).** generated_certify.certify_with_rows at 60 s, with B20_R35's limits,
seeded with the better of the evaluator's seed witness and the MIP arm's witness. It gives each
arm's gap to a certified optimum where there is one; the certification's own SAT step may raise
the witness.

**Development look before preregistration.** The builder ran the new, control and MIP arms once
on a B20_R35 host (excluded here), while the B20_R35 checkpoint rehearsal was using the other
core. The values were new 118, control 116 and MIP 109 (no proof at 2 s). The new arm's K5 copy
enumeration did not finish within its 1.0 s share on that host: it found 2,438 copies, and the LP
bound was 125.75. The component is B20_R31's, unchanged; its generic copy enumeration is part of
its cost. The design was not changed after this look, and the study runs with nothing else on
the machine.

A DEV study. It licenses no claim, and its hosts are exposed.
"""
import os

if __name__ == '__main__':                      # pin before any library starts a thread
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})

import json  # noqa: E402
from pathlib import Path  # noqa: E402
import statistics  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis.common import canonical, code_identity, digest  # noqa: E402
from genesis.discovery import generated_certify as GC  # noqa: E402
from genesis.domains import ADAPTERS  # noqa: E402
from genesis.dsl import baseline_programs  # noqa: E402
from genesis.invention import cuts as C  # noqa: E402
from genesis.invention import representations as RP  # noqa: E402
from genesis.models import GraphTask  # noqa: E402

import b20r11_e1_readiness as R11  # noqa: E402
import b20r17_relation_invention as R17  # noqa: E402
import b20r23_e1b_readiness as RD  # noqa: E402
import b20r24_repilots as R24  # noqa: E402
import b20r31_relaxation_invention as R31  # noqa: E402
import b20r32_generated_certification as R32  # noqa: E402
import b20r33_strong_baseline_audit as R33  # noqa: E402

TF = RD.TF
SETTINGS = [('planted_cluster', {'n': 40, 'p_in': 0.8, 'p_out': 0.06}), ('erdos', {'n': 30, 'p': 0.42})]
SEEDS = (20263601, 20263602)
SELECT_PER, EVAL_PER = 8, 16
BUDGET_S, CONSTRUCTION_CPU_S = 2.0, 46.661
BOOT_SEED = 20263699
K5_ID = 'pat5_10_01020304121314232434'


def k5_rows():
    pats = {p['id']: p for p in C.generate()}
    a = json.loads((ROOT / 'evidence' / 'relaxation_invention_b20r31' / 'part_a.json').read_text())
    if K5_ID not in a['usable'] or a['obligations'].get(f'pc_{K5_ID}') != 'CHECKED':
        raise RuntimeError('the K5 bound is not a CHECKED, usable B20_R31 pattern')
    return [pats[K5_ID]]


def hosts(out, log):
    path = out / 'hosts.json'
    excluded, scan, _ = R24.exposure(log)
    if path.exists():                                    # resume: never regenerate (B20R34-OPEN-1)
        h = json.loads(path.read_text())
        load = lambda ts: [GraphTask.model_validate_json(canonical(t)) for t in ts]
        log('resume: hosts reloaded from hosts.json')
        return {'select': load(h['select']), 'eval': load(h['eval'])}, scan
    a = ADAPTERS[TF]
    seen, sel, ev = set(excluded), [], []
    for i, (family, params) in enumerate(SETTINGS):
        s, seen, _ = a.generate(SEEDS[0] + 10 * i, SELECT_PER, 'DEV', family, params, excluded=seen)
        e, seen, _ = a.generate(SEEDS[1] + 10 * i, EVAL_PER, 'DEV', family, params, excluded=seen)
        sel += s; ev += e
    if RD.identities(sel + ev) & set(excluded):
        raise RuntimeError('a generated host collides with a named host')
    R11.dump(path, {'select': [t.model_dump(mode='json') for t in sel], 'eval': [t.model_dump(mode='json') for t in ev]})
    return {'select': sel, 'eval': ev}, scan


def run_arm(task, arm, seed, seconds):
    if arm['kind'] == 'mip':
        m = R33.mip(task, seconds)
        return m['value'], m['cpu_s'], {'proved_optimal': m['proved_optimal'], 'overrun': m['overrun']}, m['selected']
    if arm['kind'] in ('representation', 'program'):
        value, cpu = R17.run_arm(task, arm, seed, seconds)
        return value, cpu, None, None
    value, cpu, diag = R31.run_arm(task, arm, seed, seconds)
    return value, cpu, diag, None


def boot(by):
    real = R17.BOOT_SEED
    R17.BOOT_SEED = BOOT_SEED
    try:
        return R17.boot(by)
    finally:
        R17.BOOT_SEED = real


def compare(rows, other):
    by = {}
    for r in rows:
        by.setdefault(r['setting'], []).append(r['values']['new'] - r['values'][other])
    est, ci = boot(by)
    flat = [d for ds in by.values() for d in ds]
    return {'mean': round(est, 4), 'interval_90': [round(ci[0], 4), round(ci[1], 4)],
            'by_setting': {k: round(statistics.fmean(d), 4) for k, d in sorted(by.items())},
            'wins_ties_losses': [sum(d > 0 for d in flat), sum(d == 0 for d in flat), sum(d < 0 for d in flat)],
            'passes': est >= R17.MUE and ci[0] > 0}


def main(argv=None):
    out = Path((argv or sys.argv[1:])[0])
    if (out / 'summary.json').exists():
        raise FileExistsError(out / 'summary.json')
    out.mkdir(parents=True, exist_ok=True)
    cpu = R33.pinned_core()
    logf = (out / 'run.log').open('a')
    t0 = time.monotonic()

    def log(m):
        line = f'[{time.monotonic() - t0:7.1f}s] {m}'
        print(line, flush=True)
        logf.write(line + '\n')
        logf.flush()
    log(f'pinned to CPU {cpu}')
    registry = GC.load_registry()
    patterns = k5_rows()
    hs, scan = hosts(out, log)
    seed_of = lambda t: int(digest({'b20r36': t.task_id})[:12], 16)
    reps = {r['id']: r for r in RP.proposals()}
    arms = {'new:cut_lp_greedy_k5': {'kind': 'cuts', 'patterns': patterns}, 'control:lp_greedy': {'kind': 'lp'},
            'mip:highs': {'kind': 'mip'}}
    arms.update({f'menu:{m}': {'kind': 'representation', 'rep': reps[m]} for m in R17.MENU})
    arms.update({f'conv:{n}_tm': {'kind': 'program', 'program': p.model_dump(mode='json')}
                 for n, p in sorted(baseline_programs().items())})
    select = {name: 0 for name in arms if name.startswith(('menu:', 'conv:'))}
    for t in hs['select']:
        for name in select:
            select[name] += run_arm(t, arms[name], seed_of(t), BUDGET_S)[0]
    pick = lambda prefix: max((n for n in select if n.startswith(prefix)), key=lambda n: (select[n], n))
    chosen = {'new': 'new:cut_lp_greedy_k5', 'control': 'control:lp_greedy', 'menu': pick('menu:'),
              'conventional': pick('conv:'), 'mip': 'mip:highs'}
    extra = CONSTRUCTION_CPU_S / R17.HORIZON
    log(f'SELECT totals {select} -> {chosen}; matched arm gets {BUDGET_S + extra:.4f} s')
    path = out / 'part_b_rows.jsonl'
    done = {json.loads(l)['task_id'] for l in path.read_text().splitlines() if l.strip()} if path.exists() else set()
    with path.open('a') as fh:
        for t in hs['eval']:
            if t.task_id in done:
                continue
            s = seed_of(t)
            v, cpu_s, diag, mip_witness = {}, {}, {}, None
            for role in ('new', 'control', 'menu', 'conventional', 'mip'):
                v[role], cpu_s[role], diag[role], sel = run_arm(t, arms[chosen[role]], s, BUDGET_S)
                if role == 'mip':
                    mip_witness = sel
            v['matched'], cpu_s['matched'], _, _ = run_arm(t, arms[chosen['control']], s, BUDGET_S + extra)
            seed_w = R32.seed_witness(t)
            witness = max((tuple(seed_w), tuple(map(tuple, mip_witness or ()))), key=len)
            ref = GC.certify_with_rows(t, witness, registry, seconds=60, separation_seconds=10, max_rows=50000)
            opt = ref['lower'] if ref['lower'] == ref['upper'] else None
            r = {'setting': t.family, 'task_id': t.task_id, 'values': v, 'cpu_s': cpu_s,
                 'diagnostics': {k: x for k, x in diag.items() if x is not None},
                 'reference': {'lower': ref['lower'], 'upper': ref['upper'], 'method': ref['method'],
                               'wall_s': ref['wall_s'], 'seed_witness': len(witness)}, 'optimum': opt}
            fh.write(json.dumps(r, sort_keys=True) + '\n')
            fh.flush()
            log(f'{t.family} {t.task_id[-4:]}: {v} opt {opt}')
    rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    comparisons = {o: compare(rows, o) for o in ('control', 'menu', 'conventional', 'matched', 'mip')}
    verdict = ('UTILITY_AFTER_COST' if all(comparisons[o]['passes'] for o in ('control', 'menu', 'conventional', 'matched'))
               else 'NO_UTILITY_AFTER_COST')
    scored = [r for r in rows if r['optimum'] is not None]
    summary = {'schema': 'genesis-b20r36-dense-construction-v1', 'family': C.FAMILY, 'attempt': 2,
               'attempts_in_family': ['B20_R31', 'B20_R36'], 'patterns': [K5_ID],
               'settings': [{'family': f, 'params': p} for f, p in SETTINGS], 'budget_s': BUDGET_S,
               'construction_cpu_s': CONSTRUCTION_CPU_S, 'matched_extra_s_per_host': round(extra, 4),
               'select_totals': select, 'chosen': chosen, 'comparisons': comparisons, 'verdict': verdict,
               'beyond_mip': comparisons['mip']['passes'],
               'at_certified_optimum': {role: sum(r['values'][role] == r['optimum'] for r in scored)
                                        for role in ('new', 'control', 'menu', 'conventional', 'matched', 'mip')},
               'certified_hosts': len(scored), 'eval_hosts': len(rows),
               'mean_cpu_s': {role: round(statistics.fmean(r['cpu_s'][role] for r in rows), 3)
                              for role in ('new', 'control', 'menu', 'conventional', 'matched', 'mip')},
               'exposure_scan': scan, 'code_identity': code_identity(ROOT)['sha256'], 'status': 'DEV; licenses no claim'}
    R11.dump(out / 'summary.json', summary)
    log(f'verdict {verdict}; beyond_mip {summary["beyond_mip"]}: ' +
        json.dumps({k: (c['mean'], c['interval_90']) for k, c in comparisons.items()}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
