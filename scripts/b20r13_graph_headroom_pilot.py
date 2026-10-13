#!/usr/bin/env python3
"""B20_R13 design pilot (DEV): does graph construction leave room for a better improver (GV4)?

    b20r13_graph_headroom_pilot.py OUT_DIR [--workers N]     run (resumable) and summarise
    b20r13_graph_headroom_pilot.py OUT_DIR --summary         summarise existing rows only

A design diagnostic, not a study: it licenses no claim. The user chose graph construction as the GV4
domain on 13 Oct 2026, after three pilots found no research-policy headroom on the equational domain
(B20R9-OPEN-1). Here an *improver* is a research process that spends DEV evaluations choosing a solver
configuration; its output is the chosen configuration, scored on held-out DEV hosts. The question is
whether the choice matters enough that one improver could beat another at the same research budget.

Solver space (fixed here; every configuration gets the same 0.5 CPU s of search per host and the E1
profile's 1000 oracle queries per DSL restart, so cost is matched by construction):
  * R4   represent-and-repair with each representation licensed on the domain (cross_2, ordered_2,
         adjacent_2, adjacent_3 on triangle_free_host_v1; none is licensed on c4_host_v2);
  * B3   the three conventional DSL baselines, time-matched (dsl-time-matched-v1 semantics);
  * B1   low_cycle with exchange, time-matched (the adaptive proposer's fixed extra point);
  * V16  16 grammar points drawn once with random.Random(1313) from the propose() grammar
         (weights in [-3, 3]^4, rounds in {2, 4, 8, 32}, exchange, componentwise), time-matched.
  Registry order: R4, B3, B1, V16. Runs are in-process (no sandbox; this is a design pilot) and every
  witness is re-checked by both graph checkers; an invalid witness scores 0.

Host settings (fixed here; generator seeds 20261301 + 10 i for selection hosts and 20261302 + 10 i for
held-out hosts; triangle-free n = 22 excludes every E1 host the builder has generated):
  S1 tf  erdos n22 p0.35  (the adopted calibration, the E1 family)   S5 tf  erdos n40 p0.35
  S2 tf  erdos n30 p0.30                                             S6 c4  erdos n20 p0.25 (adopted)
  S3 tf  erdos n40 p0.20                                             S7 c4  erdos n30 p0.20
  S4 tf  planted_cluster n30 p_in0.6 p_out0.2
  Per setting: D = 10 selection hosts (what an improver may evaluate on) and H = 16 held-out hosts.

Improvers, research budget CAP = 0.25 x (K configurations x D hosts) evaluations (the B20 share rule):
  FIXED@CAP[order]  evaluate the first floor(CAP / D) configurations of `order` on all D hosts and keep
                    the best by selection total; orders: 'registry' and 'baselines_first'
                    (B3, B1, R4, V16);
  RANDOM@CAP        the same with a uniformly random order; reported as the mean over 20 orders
                    (random.Random(1314));
  SH@CAP            successive halving (eta = 2): all K on the first host, the better half on the first
                    two, then four, ..., stopping before the next rung would exceed CAP; keeps the best
                    by mean on the hosts of its last rung (ties: registry order). A deployable improver;
  EXHAUST           every configuration on all D hosts (4 x CAP), best by selection total.
References (not improvers):
  ORACLE            the configuration with the best held-out total (optimistic: chosen with the answers);
  ORACLE_CV         choose on half the held-out hosts and score on the other half, both ways, averaged;
  BEST_OF           per-host maximum over all configurations (a ceiling, s14.3).

Verdict per setting (fixed here; means are edges per held-out host; BASE = max(FIXED@CAP[registry],
FIXED@CAP[baselines_first], RANDOM@CAP)):
  DEPLOYABLE_HEADROOM  SH@CAP - BASE >= 0.5
  HEADROOM             otherwise ORACLE - BASE >= 0.5
  NO_HEADROOM          otherwise
0.5 edges per host is E1's minimum useful effect. Seven settings and 16 held-out hosts make a positive
setting a lead for a fresh DEV replication with new seeds, not a finding. Paired bootstrap 90% intervals
(2000 resamples, random.Random(1315)) are reported as diagnostics. Every host is written to OUT_DIR, so
later studies count it as exposed.
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

from genesis import calibration as CAL  # noqa: E402
from genesis.common import canonical, digest  # noqa: E402
from genesis.domains import ADAPTERS  # noqa: E402
from genesis.dsl import baseline_programs, solve  # noqa: E402
from genesis.graphs import check_witness  # noqa: E402
from genesis.models import GraphTask, SolverProgram  # noqa: E402

TF, C4 = 'triangle_free_host_v1', 'c4_host_v2'
SETTINGS = [
    ('S1', TF, 'erdos', {'n': 22, 'p': 0.35}),
    ('S2', TF, 'erdos', {'n': 30, 'p': 0.3}),
    ('S3', TF, 'erdos', {'n': 40, 'p': 0.2}),
    ('S4', TF, 'planted_cluster', {'n': 30, 'p_in': 0.6, 'p_out': 0.2}),
    ('S5', TF, 'erdos', {'n': 40, 'p': 0.35}),
    ('S6', C4, 'erdos', {'n': 20, 'p': 0.25}),
    ('S7', C4, 'erdos', {'n': 30, 'p': 0.2}),
]
D, H = 10, 16
SEARCH_S, QUERIES = 0.5, 1000
SHARE, MUE = 0.25, 0.5
REPS = ('cross_2', 'ordered_2', 'adjacent_2', 'adjacent_3')


# ------------------------------------------------------------------ the solver space

def grammar_points():
    rng, out = random.Random(1313), []
    fixed = set(baseline_programs().values()) | {SolverProgram(weights=(0, 0, 0, 1), rounds=32, exchange=True)}
    while len(out) < 16:
        p = SolverProgram(weights=tuple(rng.randint(-3, 3) for _ in range(4)), rounds=rng.choice((2, 4, 8, 32)),
                          exchange=rng.choice((False, True)), componentwise=rng.choice((False, True)))
        if p not in fixed and p not in out:
            out.append(p)
    return out


def configurations(domain):
    """Registry order: R4, B3, B1, V16. Each entry is (name, group, spec)."""
    out = []
    if domain == TF:
        out += [(r, 'R4', {'representation': r}) for r in REPS]
    out += [(f'{n}_tm', 'B3', {'program': p.model_dump(mode='json')}) for n, p in sorted(baseline_programs().items())]
    out.append(('low_cycle_exchange_tm', 'B1',
                {'program': SolverProgram(weights=(0, 0, 0, 1), rounds=32, exchange=True).model_dump(mode='json')}))
    out += [(f'v{i:02}_tm', 'V16', {'program': p.model_dump(mode='json')}) for i, p in enumerate(grammar_points())]
    return out


def run_config(task, spec, seed):
    """One configuration on one host, in this process. Mirrors the custody kinds' child code:
    represent-and-repair-v1 (candidates._child) and dsl-time-matched-v1's restart loop."""
    start = time.process_time_ns()
    if 'representation' in spec:
        from genesis.invention import representations as R
        rep = next(r for r in R.proposals() if r['id'] == spec['representation'])
        out = R.represent_and_repair(task.n, task.edges, rep, R.tf_add_ok, cpu_seconds=SEARCH_S, seed=seed)
        witness, extra = out['witness'], {'rounds': out['rounds']}
    else:
        program = SolverProgram.model_validate_json(canonical(spec['program']))
        budget_ns, best, k = int(SEARCH_S * 1e9), None, 0
        while best is None or time.process_time_ns() - start < budget_ns:
            o = solve(task, program, QUERIES, (seed + 1_000_003 * k) % (1 << 62))
            if best is None or o['value'] > best['value']:
                best = o
            k += 1
        witness, extra = best['selected'], {'restarts': k}
    cpu_ns = time.process_time_ns() - start
    try:
        value = check_witness(task, [tuple(e) for e in witness])['value']
        status = 'VALID'
    except (ValueError, RuntimeError) as exc:
        value, status = 0, f'INVALID: {exc}'
    return {'value': value, 'status': status, 'cpu_ns': cpu_ns, **extra}


# ------------------------------------------------------------------ hosts

# E1 host lists (B20_R11 / B20_R12 constants, reproduced here so this pilot runs without them).
B19_SEED, B19_TASKS = 20261026, 60
R11_PILOT_SEED, R11_PILOT_TASKS = 20261113, 30
R12_PILOT_SEED, R12_PILOT_TASKS = 20261204, 30


def e1_exposure():
    """Canonical identities of every E1 host the builder generated that can still be named.

    Restored on 13 Oct 2026 after a workspace loss. The original version (lost commit 810c39e)
    called b20r12_e1_redesign; this one computes the same deterministic lists directly: the B19
    pilot, the B20_R11 pilot, the B20_R11 rehearsal hosts (handoff/e1/exposure_hosts_to_exclude.json,
    byte-identical to B20_R11) and the B20_R12 pilot. The B20_R12 SELECT-rehearsal hosts were drawn
    from os.urandom in the lost run and cannot be named; they are not excluded here, and the redo of
    B20_R12 must exclude this pilot's hosts instead. Every other rule below is unchanged."""
    record = CAL.load(TF, ROOT)
    _, seen = CAL.calibrated_panel(record, B19_SEED, B19_TASKS, 'DEV')
    _, seen2 = CAL.calibrated_panel(record, R11_PILOT_SEED, R11_PILOT_TASKS, 'DEV', excluded=seen)
    seen = set(seen) | set(seen2)
    a = ADAPTERS[TF]
    for t in json.loads((ROOT / 'handoff/e1/exposure_hosts_to_exclude.json').read_text())['b20r11_rehearsal']:
        ident = a.exposure_identity(GraphTask.model_validate_json(canonical(t)))
        if isinstance(ident, dict):
            seen.add(ident['canonical'])
    _, seen = CAL.calibrated_panel(record, R12_PILOT_SEED, R12_PILOT_TASKS, 'DEV', excluded=seen)
    return set(seen)


def hosts():
    out, e1 = {}, None
    for i, (sid, domain, family, params) in enumerate(SETTINGS):
        excluded = set()
        if domain == TF and family == 'erdos' and params == {'n': 22, 'p': 0.35}:
            e1 = e1 if e1 is not None else e1_exposure()
            excluded = set(e1)
        a = ADAPTERS[domain]
        sel, seen, g1 = a.generate(20261301 + 10 * i, D, 'DEV', family, params, excluded=excluded)
        held, _, g2 = a.generate(20261302 + 10 * i, H, 'DEV', family, params, excluded=seen)
        out[sid] = {'domain': domain, 'family': family, 'params': params, 'select': sel, 'held_out': held,
                    'generator': {'select': g1, 'held_out': g2}, 'e1_hosts_excluded': len(excluded)}
    return out


# ------------------------------------------------------------------ running

def _job(args):
    sid, role, task_raw, name, spec = args
    task = GraphTask.model_validate_json(canonical(task_raw))
    seed = int(digest({'pilot': 'b20r13', 'task': task.task_id})[:12], 16)
    r = run_config(task, spec, seed)
    return {'setting': sid, 'role': role, 'task_id': task.task_id, 'config': name, **r}


def run(out, workers, log):
    H_ = hosts()
    tasks_dump = {sid: {k: ([t.model_dump(mode='json') for t in v] if k in ('select', 'held_out') else v)
                        for k, v in s.items()} for sid, s in H_.items()}
    (out / 'hosts.json').write_text(json.dumps(tasks_dump, indent=1, sort_keys=True) + '\n')
    space = {d: [{'name': n, 'group': g, 'spec': s} for n, g, s in configurations(d)] for d in (TF, C4)}
    (out / 'solver_space.json').write_text(json.dumps(space, indent=1, sort_keys=True) + '\n')
    rows_path = out / 'rows.jsonl'
    done = set()
    if rows_path.exists():
        for line in rows_path.read_text().splitlines():
            r = json.loads(line)
            done.add((r['setting'], r['task_id'], r['config']))
    jobs = []
    for sid, s in H_.items():
        for role in ('select', 'held_out'):
            for t in s[role]:
                for name, _, spec in configurations(s['domain']):
                    if (sid, t.task_id, name) not in done:
                        jobs.append((sid, role, t.model_dump(mode='json'), name, spec))
    log(f'{len(done)} rows on disk, {len(jobs)} to run with {workers} workers')
    t0 = time.time()
    with rows_path.open('a') as fh, get_context('fork').Pool(workers) as pool:
        for k, r in enumerate(pool.imap_unordered(_job, jobs, chunksize=4), 1):
            fh.write(json.dumps(r, sort_keys=True) + '\n')
            fh.flush()
            if k % 100 == 0 or k == len(jobs):
                log(f'{k}/{len(jobs)} runs, {time.time() - t0:.0f} s')


# ------------------------------------------------------------------ analysis

def _best(names, totals):
    order = {n: i for i, n in enumerate(names)}
    return max(names, key=lambda n: (totals[n], -order[n]))


def successive_halving(names, select_ids, value, cap):
    """eta = 2; rung r: the surviving configurations on the first 2^r selection hosts."""
    alive, t, spent, seen = list(names), 1, 0, set()
    rungs = []
    order = {n: i for i, n in enumerate(names)}
    while True:
        cost = sum(1 for n in alive for h in select_ids[:t] if (n, h) not in seen)
        if spent + cost > cap:
            break
        for n in alive:
            for h in select_ids[:t]:
                seen.add((n, h))
        spent += cost
        means = {n: statistics.mean(value[(n, h)] for h in select_ids[:t]) for n in alive}
        rungs.append({'configs': len(alive), 'hosts': t, 'spent': spent})
        last = (alive, means)
        if len(alive) == 1 or t >= len(select_ids):
            break
        alive = sorted(alive, key=lambda n: (-means[n], order[n]))[:math.ceil(len(alive) / 2)]
        t = min(2 * t, len(select_ids))
    alive, means = last
    return max(alive, key=lambda n: (means[n], -order[n])), rungs, spent


def bootstrap(diffs, rng, n=2000):
    if not diffs:
        return None
    means = sorted(statistics.mean(rng.choice(diffs) for _ in diffs) for _ in range(n))
    return [round(means[int(0.05 * n)], 3), round(means[int(0.95 * n) - 1], 3)]


def analyse(out):
    H_ = json.loads((out / 'hosts.json').read_text())
    rows = [json.loads(line) for line in (out / 'rows.jsonl').read_text().splitlines()]
    value = {(r['setting'], r['config'], r['task_id']): r['value'] for r in rows}
    cpu = {(r['setting'], r['config'], r['task_id']): r['cpu_ns'] for r in rows}
    invalid = [r for r in rows if r['status'] != 'VALID']
    rng_orders, rng_boot = random.Random(1314), random.Random(1315)
    summary = {'schema': 'genesis-b20r13-graph-headroom-v1', 'settings': {}, 'invalid_witnesses': len(invalid),
               'rule': {'mue': MUE, 'share': SHARE, 'D': D, 'H': H, 'search_seconds': SEARCH_S, 'queries': QUERIES}}
    for sid, domain, family, params in SETTINGS:
        s = H_[sid]
        names = [n for n, _, _ in configurations(domain)]
        groups = {n: g for n, g, _ in configurations(domain)}
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

        def fixed(order):
            first = order[:k_fixed]
            return _best(first, sel_total)

        reg = names
        bf = [n for n in names if groups[n] == 'B3'] + [n for n in names if groups[n] == 'B1'] + \
             [n for n in names if groups[n] == 'R4'] + [n for n in names if groups[n] == 'V16']
        chosen = {'FIXED@CAP[registry]': fixed(reg), 'FIXED@CAP[baselines_first]': fixed(bf)}
        rand_choices = []
        for _ in range(20):
            o = list(names)
            rng_orders.shuffle(o)
            rand_choices.append(fixed(o))
        sh, rungs, spent = successive_halving(names, sel, v, cap)
        chosen['SH@CAP'] = sh
        chosen['EXHAUST'] = _best(names, sel_total)
        chosen['ORACLE'] = max(names, key=lambda n: (held_mean[n], -names.index(n)))
        A, B = held[0::2], held[1::2]

        def pick(hs):
            return max(names, key=lambda n: (sum(v[(n, h)] for h in hs), -names.index(n)))
        oa, ob = pick(A), pick(B)
        oracle_cv = (statistics.mean(v[(oa, h)] for h in B) + statistics.mean(v[(ob, h)] for h in A)) / 2
        means = {k: held_mean[c] for k, c in chosen.items()}
        means['RANDOM@CAP'] = statistics.mean(held_mean[c] for c in rand_choices)
        means['ORACLE_CV'] = oracle_cv
        means['BEST_OF'] = statistics.mean(max(v[(n, h)] for n in names) for h in held)
        base_key = max(('FIXED@CAP[registry]', 'FIXED@CAP[baselines_first]', 'RANDOM@CAP'), key=lambda k: means[k])
        base = means[base_key]
        gap_sh, gap_or = means['SH@CAP'] - base, means['ORACLE'] - base
        verdict = 'DEPLOYABLE_HEADROOM' if gap_sh >= MUE else 'HEADROOM' if gap_or >= MUE else 'NO_HEADROOM'
        # paired intervals against the better fixed order (RANDOM@CAP is a mixture, so it has no per-host pairing)
        fixed_best = max(('FIXED@CAP[registry]', 'FIXED@CAP[baselines_first]'), key=lambda k: means[k])
        pair = lambda c: [v[(c, h)] - v[(chosen[fixed_best], h)] for h in held]  # noqa: E731
        ratio = {n: statistics.mean(cpu[(sid, n, h)] for h in sel + held) / 1e9 for n in names}
        summary['settings'][sid] = {
            'domain': domain, 'family': family, 'params': params, 'K': len(names), 'cap_evaluations': cap,
            'fixed_configs_within_cap': k_fixed, 'sh_rungs': rungs, 'sh_spent': spent,
            'chosen': chosen, 'random_choices': rand_choices, 'held_out_mean': {k: round(x, 3) for k, x in means.items()},
            'base': base_key, 'gap_sh': round(gap_sh, 3), 'gap_oracle': round(gap_or, 3),
            'gap_oracle_cv': round(oracle_cv - base, 3), 'verdict': verdict,
            'bootstrap90_vs_better_fixed_order': {'SH@CAP': bootstrap(pair(chosen['SH@CAP']), rng_boot),
                                                  'ORACLE': bootstrap(pair(chosen['ORACLE']), rng_boot)},
            'config_held_out_mean': {n: round(held_mean[n], 3) for n in names},
            'config_selection_mean': {n: round(sel_total[n] / D, 3) for n in names},
            'config_mean_cpu_s': {n: round(x, 3) for n, x in ratio.items()},
            'selection_vs_held_out_rank_corr': _spearman([sel_total[n] for n in names], [held_mean[n] for n in names]),
        }
    verdicts = {sid: s.get('verdict', s.get('status')) for sid, s in summary['settings'].items()}
    summary['verdicts'] = verdicts
    summary['overall'] = ('DEPLOYABLE_HEADROOM' if 'DEPLOYABLE_HEADROOM' in verdicts.values() else
                          'HEADROOM' if 'HEADROOM' in verdicts.values() else
                          'INCOMPLETE' if 'INCOMPLETE' in verdicts.values() else 'NO_HEADROOM')
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n')
    return summary


def _spearman(a, b):
    def ranks(x):
        order = sorted(range(len(x)), key=lambda i: x[i])
        r = [0.0] * len(x)
        i = 0
        while i < len(x):
            j = i
            while j + 1 < len(x) and x[order[j + 1]] == x[order[i]]:
                j += 1
            for k in range(i, j + 1):
                r[order[k]] = (i + j) / 2
            i = j + 1
        return r
    ra, rb = ranks(a), ranks(b)
    ma, mb = statistics.mean(ra), statistics.mean(rb)
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    den = math.sqrt(sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb))
    return round(num / den, 3) if den else None


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
