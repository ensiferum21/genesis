#!/usr/bin/env python3
"""B20_RX5 design pilot (DEV): proposal headroom over a pipeline grammar (GV4 capability design, step 1).

    b20rx5_proposal_pilot.py OUT_DIR [--workers N]     run (resumable) and summarise
    b20rx5_proposal_pilot.py OUT_DIR --summary         summarise existing rows only

handoff/gv4/README.md (DRAFT) proposes a GV4 study in which improvers *construct* solver pipelines
from a typed component grammar. Before such a study is worth designing, this pilot asks whether
the way pipelines are proposed matters at all: if a fixed enumeration or random sampling of the
grammar already finds near-best pipelines within the research budget, a learned improver has
nothing to win. B20_RX3/RX3b suggested it might matter (random proposals did not reliably find the
good methods; successive halving did), but there the method set was hand-picked.

Fixed before running.

Grammar (data only; components are trusted code in discovery/construct.py and the menu modules):
  pipeline = (init, frac, finish); the init runs for frac x B, the finisher for the rest of B
  init     triangle-free: rep:cross_2, rep:adjacent_2, rep:adjacent_3, rep:ordered_2,
                          menu:multistart_tm, menu:low_cycle_tm, lp_greedy, random_greedy
           C4:            menu:multistart_tm, menu:low_cycle_tm, menu:exchange_tm, lp_greedy, random_greedy
  frac     1.0 (finish none), or 0.5 / 0.25 with finish sat_climb or lp_restarts
  -> 5 pipelines per init: 40 on triangle-free hosts, 25 on C4 hosts
  registry order: inits as listed; per init (1.0, none), (0.5, sat), (0.5, lp), (0.25, sat), (0.25, lp)
Budget: B = 2.0 CPU s per host per pipeline, children included; a run over 1.25 B scores 0.
Settings: the B20_RX3 families with fresh seeds 20261701 + 10 i (selection) and 20261702 + 10 i
(held-out); every RX3 and RX3b host is excluded. D = 10, H = 16.
Proposers, all with research budget CAP = 0.25 x K x D evaluations:
  FIXED_ENUM   the first floor(CAP / D) pipelines of the registry order on all D hosts, best total
  RANDOM       the same with a random order (mean over 20 orders, random.Random(1514))
  SH           successive halving over the grammar (an adaptive research process)
References: ORACLE (best held-out mean), ORACLE_CV, BEST_OF.
Verdict per setting (MUE = 0.5 edges per held-out host):
  SIMPLE = max(FIXED_ENUM, RANDOM)
  ADAPTIVE_HEADROOM       SH - SIMPLE >= MUE
  ORACLE_ONLY_HEADROOM    otherwise ORACLE - max(SIMPLE, SH) >= MUE
  NO_PROPOSAL_HEADROOM    otherwise
A design diagnostic, not a study; it licenses no claim.
"""
import json
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
import b20rx3_capability_pilot as P3  # noqa: E402
from genesis.common import canonical, digest  # noqa: E402
from genesis.domains import ADAPTERS  # noqa: E402
from genesis.graphs import check_witness  # noqa: E402
from genesis.models import GraphTask  # noqa: E402

TF, C4 = P13.TF, P13.C4
SETTINGS = P3.SETTINGS
D, H = 10, 16
BUDGET, OVER, SHARE, MUE = 2.0, 1.25, 0.25, 0.5
INITS = {TF: ['rep:cross_2', 'rep:adjacent_2', 'rep:adjacent_3', 'rep:ordered_2', 'menu:multistart_tm',
              'menu:low_cycle_tm', 'lp_greedy', 'random_greedy'],
         C4: ['menu:multistart_tm', 'menu:low_cycle_tm', 'menu:exchange_tm', 'lp_greedy', 'random_greedy']}
SHAPES = [(1.0, 'none'), (0.5, 'sat_climb'), (0.5, 'lp_restarts'), (0.25, 'sat_climb'), (0.25, 'lp_restarts')]


def grammar(domain):
    return [f'{i}|{f}|{fin}' for i in INITS[domain] for f, fin in SHAPES]


def run_pipeline(task, pipe, seed):
    from genesis.discovery import construct as K
    init, frac, finish = pipe.split('|')
    frac = float(frac)
    b = K.Budget(BUDGET)
    stage = frac * BUDGET
    if init.startswith('rep:'):
        w = P3._menu_witness(task, {'representation': init[4:]}, seed, stage)
    elif init.startswith('menu:'):
        spec = next(s for n, _, s in P13.configurations(task.domain) if n == init[5:])
        w = P3._menu_witness(task, spec, seed, stage)
    elif init == 'lp_greedy':
        w = K.lp_greedy(task, K.Budget(stage), seed)['witness']
    elif init == 'random_greedy':
        rng, sb, w = random.Random(seed), K.Budget(stage), ()
        order = list(range(len(task.edges)))
        while True:
            rng.shuffle(order)
            g = K.greedy(task, order)
            if len(g) > len(w):
                w = g
            if sb.left() <= 0:
                break
    else:
        raise ValueError(init)
    extra = {}
    if finish == 'sat_climb':
        r = K.sat_climb(task, w, b)
        w, extra = r['witness'], {'stop': r['stop'], 'sat_calls': r['sat_calls']}
    elif finish == 'lp_restarts':
        if b.left() > 0:
            w2 = K.lp_greedy(task, b, seed + 1)['witness']
            w = w2 if len(w2) > len(w) else w
    return w, b.used(), extra


def _job(args):
    sid, role, task_raw, pipe = args
    task = GraphTask.model_validate_json(canonical(task_raw))
    seed = int(digest({'pilot': 'b20rx5', 'task': task.task_id})[:12], 16)
    w, cpu, extra = run_pipeline(task, pipe, seed)
    try:
        value, status = check_witness(task, [tuple(e) for e in w])['value'], 'VALID'
    except (ValueError, RuntimeError) as exc:
        value, status = 0, f'INVALID: {exc}'
    if cpu > OVER * BUDGET:
        value, status = 0, f'OVER_BUDGET: {cpu:.2f} s'
    return {'setting': sid, 'role': role, 'task_id': task.task_id, 'config': pipe, 'value': value, 'status': status,
            'cpu_ns': int(cpu * 1e9), **extra}


def hosts():
    out = {}
    for i, (sid, domain, family, params) in enumerate(SETTINGS):
        a = ADAPTERS[domain]
        excluded = P3._first_run_hosts(domain, family, params, i)
        _, seen_b, _ = a.generate(P3.REPLICATION_SEED_BASE + 10 * i, D, 'DEV', family, params, excluded=excluded)
        excluded |= set(seen_b)
        _, seen_b, _ = a.generate(P3.REPLICATION_SEED_BASE + 1 + 10 * i, H, 'DEV', family, params, excluded=excluded)
        excluded |= set(seen_b)
        sel, seen, g1 = a.generate(20261701 + 10 * i, D, 'DEV', family, params, excluded=excluded)
        held, _, g2 = a.generate(20261702 + 10 * i, H, 'DEV', family, params, excluded=set(seen) | excluded)
        out[sid] = {'domain': domain, 'family': family, 'params': params, 'select': sel, 'held_out': held,
                    'generator': {'select': g1, 'held_out': g2}}
    return out


def run(out, workers, log):
    H_ = hosts()
    (out / 'hosts.json').write_text(json.dumps(
        {sid: {k: ([t.model_dump(mode='json') for t in v] if k in ('select', 'held_out') else v) for k, v in s.items()}
         for sid, s in H_.items()}, indent=1, sort_keys=True) + '\n')
    (out / 'grammar.json').write_text(json.dumps({d: grammar(d) for d in (TF, C4)}, indent=1) + '\n')
    rows_path = out / 'rows.jsonl'
    done = set()
    if rows_path.exists():
        for line in rows_path.read_text().splitlines():
            r = json.loads(line)
            done.add((r['setting'], r['task_id'], r['config']))
    jobs = [(sid, role, t.model_dump(mode='json'), p) for sid, s in H_.items() for role in ('select', 'held_out')
            for t in s[role] for p in grammar(s['domain']) if (sid, t.task_id, p) not in done]
    log(f'{len(done)} rows on disk, {len(jobs)} to run with {workers} workers')
    t0 = time.time()
    with rows_path.open('a') as fh, get_context('fork').Pool(workers, initializer=P3._init) as pool:
        for k, r in enumerate(pool.imap_unordered(_job, jobs, chunksize=2), 1):
            fh.write(json.dumps(r, sort_keys=True) + '\n')
            fh.flush()
            if k % 100 == 0 or k == len(jobs):
                log(f'{k}/{len(jobs)} runs, {time.time() - t0:.0f} s')


def analyse(out):
    H_ = json.loads((out / 'hosts.json').read_text())
    rows = [json.loads(line) for line in (out / 'rows.jsonl').read_text().splitlines()]
    value = {(r['setting'], r['config'], r['task_id']): r['value'] for r in rows}
    bad = [r for r in rows if r['status'] != 'VALID']
    rng_orders, rng_boot = random.Random(1514), random.Random(1515)
    summary = {'schema': 'genesis-b20rx5-proposal-v1', 'settings': {}, 'non_valid_runs': len(bad),
               'rule': {'budget_cpu_s': BUDGET, 'over_budget_factor': OVER, 'mue': MUE, 'share': SHARE, 'D': D, 'H': H}}
    for sid, domain, family, params in SETTINGS:
        s = H_[sid]
        names = grammar(domain)
        sel = [t['task_id'] for t in s['select']]
        held = [t['task_id'] for t in s['held_out']]
        if any((sid, n, h) not in value for n in names for h in sel + held):
            summary['settings'][sid] = {'status': 'INCOMPLETE'}
            continue
        v = {(n, h): value[(sid, n, h)] for n in names for h in sel + held}
        sel_total = {n: sum(v[(n, h)] for h in sel) for n in names}
        held_mean = {n: statistics.mean(v[(n, h)] for h in held) for n in names}
        cap = int(SHARE * len(names) * D)
        k_fixed = cap // D
        chosen = {'FIXED_ENUM': P13._best(names[:k_fixed], sel_total)}
        rand = []
        for _ in range(20):
            o = list(names)
            rng_orders.shuffle(o)
            rand.append(P13._best(o[:k_fixed], sel_total))
        chosen['SH'], rungs, spent = P13.successive_halving(names, sel, v, cap)
        chosen['ORACLE'] = max(names, key=lambda n: (held_mean[n], -names.index(n)))
        A, B = held[0::2], held[1::2]

        def pick(hs):
            return max(names, key=lambda n: (sum(v[(n, h)] for h in hs), -names.index(n)))
        oa, ob = pick(A), pick(B)
        means = {k: held_mean[c] for k, c in chosen.items()}
        means['RANDOM'] = statistics.mean(held_mean[c] for c in rand)
        means['ORACLE_CV'] = (statistics.mean(v[(oa, h)] for h in B) + statistics.mean(v[(ob, h)] for h in A)) / 2
        means['BEST_OF'] = statistics.mean(max(v[(n, h)] for n in names) for h in held)
        simple = max(means['FIXED_ENUM'], means['RANDOM'])
        gap_ad = means['SH'] - simple
        gap_or = means['ORACLE'] - max(simple, means['SH'])
        verdict = ('ADAPTIVE_HEADROOM' if gap_ad >= MUE else 'ORACLE_ONLY_HEADROOM' if gap_or >= MUE
                   else 'NO_PROPOSAL_HEADROOM')
        fixed_cfg = chosen['FIXED_ENUM']
        pair = lambda c: [v[(c, h)] - v[(fixed_cfg, h)] for h in held]  # noqa: E731
        good = [n for n in names if held_mean[n] >= means['ORACLE'] - MUE]
        summary['settings'][sid] = {
            'domain': domain, 'family': family, 'params': params, 'K': len(names), 'cap_evaluations': cap,
            'sh_rungs': rungs, 'sh_spent': spent, 'chosen': chosen, 'random_choices': rand,
            'held_out_mean': {k: round(x, 3) for k, x in means.items()},
            'gap_adaptive': round(gap_ad, 3), 'gap_oracle_beyond': round(gap_or, 3), 'verdict': verdict,
            'pipelines_within_mue_of_oracle': len(good),
            'bootstrap90_vs_fixed_enum': {'SH': P13.bootstrap(pair(chosen['SH']), rng_boot),
                                          'ORACLE': P13.bootstrap(pair(chosen['ORACLE']), rng_boot)},
            'pipeline_held_out_mean': {n: round(held_mean[n], 3) for n in names},
        }
    summary['verdicts'] = {sid: s.get('verdict', s.get('status')) for sid, s in summary['settings'].items()}
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
    log(f'verdicts {s["verdicts"]}')


if __name__ == '__main__':
    main()
