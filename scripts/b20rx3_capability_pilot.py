#!/usr/bin/env python3
"""B20_RX3 design pilot (DEV): capability headroom for GV4 in graph construction.

    b20rx3_capability_pilot.py OUT_DIR [--workers N]     run (resumable) and summarise
    b20rx3_capability_pilot.py OUT_DIR --summary         summarise existing rows only

The user chose this design on 13 Oct 2026, after B20_R13 (no headroom in choosing among the
existing solver configurations) and B20_R14 (those configurations stay below the certified
optimum on harder families): a DEV pilot in which research can produce new methods, here LP- and
SAT-guided constructions (``discovery/construct.py``, builder-written components), at matched CPU
budgets on families with room to the optimum. A design diagnostic, not a study: it licenses no
claim; a positive setting is a lead for a fresh replication and for a GV4 study design.

Everything below is fixed before running.

Budget: every method gets B = 2.0 CPU seconds per host, children (the SAT solver) included. A run
over 1.25 B scores 0 (matched budgets are enforced, not averaged away).

Menu (the R13 solver space at budget B): the represent-and-repair representations licensed on the
domain (triangle-free only), the three time-matched DSL baselines, low_cycle with exchange, and the
16 R13 grammar points; registry order as in R13.
New methods (appended after the menu, in this order):
  lp_greedy                     LP-ordered greedy, then LP-perturbed restarts for the whole budget
  lp_greedy+sat_25_75           LP greedy for 0.25 B, then SAT climbing for the rest
  lp_greedy+sat_50_50           the same with 0.5 B
  head+sat_25_75                the domain's default menu head (cross_2 on triangle-free hosts,
                                low_cycle_tm on C4 hosts) for 0.25 B, then SAT climbing
  head+sat_50_50                the same with 0.5 B
  greedy+sat                    one random-order greedy, then SAT climbing for the whole budget

Settings (fresh generator seeds; select 20261401 + 10 i, held-out 20261402 + 10 i):
  C1 tf erdos n30 p0.3 (S2-like)   C2 tf erdos n40 p0.2 (S3-like)   C3 c4 erdos n30 p0.2 (S7-like)
  D = 10 selection hosts, H = 16 held-out hosts per setting.

Improvers, all with the same research budget CAP = 0.25 x K_menu x D evaluations:
  menu only: FIXED@CAP[registry], FIXED@CAP[baselines_first], RANDOM@CAP (20 orders), SH@CAP[menu]
  with the new methods: SH@CAP[all] (successive halving over menu + new), RANDOM@CAP[all]
References: ORACLE[menu], ORACLE[all], ORACLE_CV[all], BEST_OF[all].

Verdict per setting (means are edges per held-out host; MUE = 0.5 as in E1, R13, R14):
  BASE = max(FIXED@CAP[registry], FIXED@CAP[baselines_first], RANDOM@CAP, SH@CAP[menu])
  DEPLOYABLE_CAPABILITY_HEADROOM  SH@CAP[all] - BASE >= MUE
  CAPABILITY_HEADROOM             otherwise ORACLE[all] - ORACLE[menu] >= MUE
  NO_CAPABILITY_HEADROOM          otherwise
Paired bootstrap 90% intervals (2000 resamples, random.Random(1415)) are diagnostics only.

Replication (--replication, added after the first run, before any replication host existed): the
same design with fresh generator seeds 20261601 + 10 i (selection) and 20261602 + 10 i (held-out).
Everything else, including the rule above, is unchanged. Hosts of the first run are excluded.
"""
import json
import math
from multiprocessing import get_context
from pathlib import Path
import random
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

import b20r13_graph_headroom_pilot as P13  # noqa: E402
from genesis.common import canonical, digest  # noqa: E402
from genesis.domains import ADAPTERS  # noqa: E402
from genesis.graphs import check_witness  # noqa: E402
from genesis.models import GraphTask  # noqa: E402

TF, C4 = P13.TF, P13.C4
SETTINGS = [
    ('C1', TF, 'erdos', {'n': 30, 'p': 0.3}),
    ('C2', TF, 'erdos', {'n': 40, 'p': 0.2}),
    ('C3', C4, 'erdos', {'n': 30, 'p': 0.2}),
]
D, H = 10, 16
BUDGET, OVER = 2.0, 1.25
SHARE, MUE = 0.25, 0.5
NEW = ['lp_greedy', 'lp_greedy+sat_25_75', 'lp_greedy+sat_50_50', 'head+sat_25_75', 'head+sat_50_50', 'greedy+sat']


def menu(domain):
    return [(n, g, s) for n, g, s in P13.configurations(domain)]


def configurations(domain):
    return menu(domain) + [(n, 'NEW', {'method': n}) for n in NEW]


def _head(domain):
    return {'representation': 'cross_2'} if domain == TF else \
        {'program': next(s for n, _, s in P13.configurations(domain) if n == 'low_cycle_tm')['program']}


def _menu_witness(task, spec, seed, seconds):
    """A menu configuration's witness under ``seconds`` of CPU (the R13 code path)."""
    from genesis.dsl import solve
    from genesis.models import SolverProgram
    if 'representation' in spec:
        from genesis.invention import representations as R
        rep = next(r for r in R.proposals() if r['id'] == spec['representation'])
        return R.represent_and_repair(task.n, task.edges, rep, R.tf_add_ok, cpu_seconds=seconds, seed=seed)['witness']
    program = SolverProgram.model_validate_json(canonical(spec['program']))
    start, best, k = time.process_time_ns(), None, 0
    while best is None or time.process_time_ns() - start < int(seconds * 1e9):
        o = solve(task, program, P13.QUERIES, (seed + 1_000_003 * k) % (1 << 62))
        if best is None or o['value'] > best['value']:
            best = o
        k += 1
    return best['selected']


def run_new(task, name, seed):
    from genesis.discovery import construct as K
    b = K.Budget(BUDGET)
    extra = {}
    if name == 'lp_greedy':
        w = K.lp_greedy(task, b, seed)['witness']
    elif name.startswith('lp_greedy+sat'):
        frac = 0.25 if name.endswith('25_75') else 0.5
        w = K.lp_greedy(task, K.Budget(frac * BUDGET), seed)['witness']
        r = K.sat_climb(task, w, b)
        w, extra = r['witness'], {'sat_calls': r['sat_calls'], 'stop': r['stop']}
    elif name.startswith('head+sat'):
        frac = 0.25 if name.endswith('25_75') else 0.5
        w = _menu_witness(task, _head(task.domain), seed, frac * BUDGET)
        r = K.sat_climb(task, w, b)
        w, extra = r['witness'], {'sat_calls': r['sat_calls'], 'stop': r['stop']}
    elif name == 'greedy+sat':
        order = list(range(len(task.edges)))
        random.Random(seed).shuffle(order)
        r = K.sat_climb(task, K.greedy(task, order), b)
        w, extra = r['witness'], {'sat_calls': r['sat_calls'], 'stop': r['stop']}
    else:
        raise ValueError(name)
    return w, b.used(), extra


def run_config(task, spec, seed):
    if 'method' in spec:
        w, cpu, extra = run_new(task, spec['method'], seed)
        cpu_ns = int(cpu * 1e9)
    else:
        from genesis.discovery import construct as K
        b = K.Budget(BUDGET)
        w = _menu_witness(task, spec, seed, BUDGET)
        cpu_ns, extra = int(b.used() * 1e9), {}
    try:
        value = check_witness(task, [tuple(e) for e in w])['value']
        status = 'VALID'
    except (ValueError, RuntimeError) as exc:
        value, status = 0, f'INVALID: {exc}'
    if cpu_ns > OVER * BUDGET * 1e9:
        value, status = 0, f'OVER_BUDGET: {cpu_ns / 1e9:.2f} s'
    return {'value': value, 'status': status, 'cpu_ns': cpu_ns, **extra}


SEED_BASE = 20261401
REPLICATION_SEED_BASE = 20261601


def _first_run_hosts(domain, family, params, i):
    a = ADAPTERS[domain]
    _, seen, _ = a.generate(SEED_BASE + 10 * i, D, 'DEV', family, params)
    _, seen, _ = a.generate(SEED_BASE + 1 + 10 * i, H, 'DEV', family, params, excluded=seen)
    return set(seen)


def hosts():
    out = {}
    base = REPLICATION_SEED_BASE if '--replication' in sys.argv else SEED_BASE
    for i, (sid, domain, family, params) in enumerate(SETTINGS):
        a = ADAPTERS[domain]
        excluded = _first_run_hosts(domain, family, params, i) if base != SEED_BASE else set()
        sel, seen, g1 = a.generate(base + 10 * i, D, 'DEV', family, params, excluded=excluded)
        held, _, g2 = a.generate(base + 1 + 10 * i, H, 'DEV', family, params, excluded=set(seen) | excluded)
        out[sid] = {'domain': domain, 'family': family, 'params': params, 'select': sel, 'held_out': held,
                    'generator': {'select': g1, 'held_out': g2}}
    return out


def _init():
    import scipy.optimize  # noqa: F401  (import cost is not charged to the first method a worker runs)
    import numpy  # noqa: F401


def _job(args):
    sid, role, task_raw, name, spec = args
    task = GraphTask.model_validate_json(canonical(task_raw))
    seed = int(digest({'pilot': 'b20rx3', 'task': task.task_id})[:12], 16)
    r = run_config(task, spec, seed)
    return {'setting': sid, 'role': role, 'task_id': task.task_id, 'config': name, **r}


def run(out, workers, log):
    H_ = hosts()
    (out / 'hosts.json').write_text(json.dumps(
        {sid: {k: ([t.model_dump(mode='json') for t in v] if k in ('select', 'held_out') else v) for k, v in s.items()}
         for sid, s in H_.items()}, indent=1, sort_keys=True) + '\n')
    (out / 'solver_space.json').write_text(json.dumps(
        {d: [{'name': n, 'group': g, 'spec': s} for n, g, s in configurations(d)] for d in (TF, C4)},
        indent=1, sort_keys=True) + '\n')
    rows_path = out / 'rows.jsonl'
    done = set()
    if rows_path.exists():
        for line in rows_path.read_text().splitlines():
            r = json.loads(line)
            done.add((r['setting'], r['task_id'], r['config']))
    jobs = [(sid, role, t.model_dump(mode='json'), n, spec) for sid, s in H_.items() for role in ('select', 'held_out')
            for t in s[role] for n, _, spec in configurations(s['domain']) if (sid, t.task_id, n) not in done]
    log(f'{len(done)} rows on disk, {len(jobs)} to run with {workers} workers')
    t0 = time.time()
    with rows_path.open('a') as fh, get_context('fork').Pool(workers, initializer=_init) as pool:
        for k, r in enumerate(pool.imap_unordered(_job, jobs, chunksize=2), 1):
            fh.write(json.dumps(r, sort_keys=True) + '\n')
            fh.flush()
            if k % 100 == 0 or k == len(jobs):
                log(f'{k}/{len(jobs)} runs, {time.time() - t0:.0f} s')


def analyse(out):
    H_ = json.loads((out / 'hosts.json').read_text())
    rows = [json.loads(line) for line in (out / 'rows.jsonl').read_text().splitlines()]
    value = {(r['setting'], r['config'], r['task_id']): r['value'] for r in rows}
    cpu = {(r['setting'], r['config'], r['task_id']): r['cpu_ns'] for r in rows}
    bad = [r for r in rows if r['status'] != 'VALID']
    rng_orders, rng_boot = random.Random(1414), random.Random(1415)
    summary = {'schema': 'genesis-b20rx3-capability-v1', 'settings': {}, 'non_valid_runs': len(bad),
               'non_valid_by_status': sorted({r['status'].split(':')[0] for r in bad}),
               'rule': {'budget_cpu_s': BUDGET, 'over_budget_factor': OVER, 'mue': MUE, 'share': SHARE, 'D': D, 'H': H}}
    for sid, domain, family, params in SETTINGS:
        s = H_[sid]
        names_all = [n for n, _, _ in configurations(domain)]
        names_menu = [n for n, _, _ in menu(domain)]
        groups = {n: g for n, g, _ in configurations(domain)}
        sel = [t['task_id'] for t in s['select']]
        held = [t['task_id'] for t in s['held_out']]
        if any((sid, n, h) not in value for n in names_all for h in sel + held):
            summary['settings'][sid] = {'status': 'INCOMPLETE'}
            continue
        v = {(n, h): value[(sid, n, h)] for n in names_all for h in sel + held}
        sel_total = {n: sum(v[(n, h)] for h in sel) for n in names_all}
        held_mean = {n: statistics.mean(v[(n, h)] for h in held) for n in names_all}
        cap = int(SHARE * len(names_menu) * D)
        k_fixed = cap // D

        def fixed(order):
            return P13._best(order[:k_fixed], sel_total)
        bf = [n for n in names_menu if groups[n] == 'B3'] + [n for n in names_menu if groups[n] == 'B1'] + \
             [n for n in names_menu if groups[n] == 'R4'] + [n for n in names_menu if groups[n] == 'V16']
        chosen = {'FIXED@CAP[registry]': fixed(names_menu), 'FIXED@CAP[baselines_first]': fixed(bf)}
        rand_menu, rand_all = [], []
        for _ in range(20):
            o = list(names_menu)
            rng_orders.shuffle(o)
            rand_menu.append(fixed(o))
            o = list(names_all)
            rng_orders.shuffle(o)
            rand_all.append(fixed(o))
        chosen['SH@CAP[menu]'], rungs_m, _ = P13.successive_halving(names_menu, sel, v, cap)
        chosen['SH@CAP[all]'], rungs_a, spent_a = P13.successive_halving(names_all, sel, v, cap)
        chosen['ORACLE[menu]'] = max(names_menu, key=lambda n: (held_mean[n], -names_all.index(n)))
        chosen['ORACLE[all]'] = max(names_all, key=lambda n: (held_mean[n], -names_all.index(n)))
        A, B = held[0::2], held[1::2]

        def pick(hs):
            return max(names_all, key=lambda n: (sum(v[(n, h)] for h in hs), -names_all.index(n)))
        oa, ob = pick(A), pick(B)
        means = {k: held_mean[c] for k, c in chosen.items()}
        means['RANDOM@CAP[menu]'] = statistics.mean(held_mean[c] for c in rand_menu)
        means['RANDOM@CAP[all]'] = statistics.mean(held_mean[c] for c in rand_all)
        means['ORACLE_CV[all]'] = (statistics.mean(v[(oa, h)] for h in B) + statistics.mean(v[(ob, h)] for h in A)) / 2
        means['BEST_OF[all]'] = statistics.mean(max(v[(n, h)] for n in names_all) for h in held)
        base_key = max(('FIXED@CAP[registry]', 'FIXED@CAP[baselines_first]', 'RANDOM@CAP[menu]', 'SH@CAP[menu]'),
                       key=lambda k: means[k])
        base = means[base_key]
        gap_dep = means['SH@CAP[all]'] - base
        gap_cap = means['ORACLE[all]'] - means['ORACLE[menu]']
        verdict = ('DEPLOYABLE_CAPABILITY_HEADROOM' if gap_dep >= MUE else
                   'CAPABILITY_HEADROOM' if gap_cap >= MUE else 'NO_CAPABILITY_HEADROOM')
        base_cfg = chosen[base_key] if base_key in chosen else chosen['FIXED@CAP[registry]']
        pair = lambda c: [v[(c, h)] - v[(base_cfg, h)] for h in held]  # noqa: E731
        summary['settings'][sid] = {
            'domain': domain, 'family': family, 'params': params, 'K_menu': len(names_menu), 'K_all': len(names_all),
            'cap_evaluations': cap, 'sh_all_rungs': rungs_a, 'sh_all_spent': spent_a, 'chosen': chosen,
            'held_out_mean': {k: round(x, 3) for k, x in means.items()}, 'base': base_key,
            'gap_deployable': round(gap_dep, 3), 'gap_capability': round(gap_cap, 3), 'verdict': verdict,
            'bootstrap90_vs_base_config': {'SH@CAP[all]': P13.bootstrap(pair(chosen['SH@CAP[all]']), rng_boot),
                                           'ORACLE[all]': P13.bootstrap(pair(chosen['ORACLE[all]']), rng_boot)},
            'config_held_out_mean': {n: round(held_mean[n], 3) for n in names_all},
            'config_mean_cpu_s': {n: round(statistics.mean(cpu[(sid, n, h)] for h in sel + held) / 1e9, 3)
                                  for n in names_all},
        }
    verdicts = {sid: s.get('verdict', s.get('status')) for sid, s in summary['settings'].items()}
    summary['verdicts'] = verdicts
    order = ('DEPLOYABLE_CAPABILITY_HEADROOM', 'CAPABILITY_HEADROOM', 'INCOMPLETE', 'NO_CAPABILITY_HEADROOM')
    summary['overall'] = next(x for x in order if x in verdicts.values() or x == order[-1])
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n')
    return summary


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    logf = (out / 'run.log').open('a')

    def log(msg):
        line = f'{time.strftime("%H:%M:%S")} {msg}'
        print(line, flush=True)
        logf.write(line + '\n')
        logf.flush()
    if '--summary' not in sys.argv:
        workers = int(sys.argv[sys.argv.index('--workers') + 1]) if '--workers' in sys.argv else 2
        run(out, workers, log)
    s = analyse(out)
    log(f'verdicts {s["verdicts"]}; overall {s["overall"]}')


if __name__ == '__main__':
    main()
