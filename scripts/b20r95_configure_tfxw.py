#!/usr/bin/env python3
"""B20_R95: the system configures its large-graph engine: a racing search over `tfxw-v1`'s operators on hosts with
128 and 256 vertices, by quality at equal time (DEV, preregistered)

    taskset -c 0 python3 scripts/b20r95_configure_tfxw.py OUT_DIR      run alone (resumable)

**Why.** B20_R93's adaptation cell, reading every study, proposes moving to instances no method solves to the optimum
within the budget and comparing the values found at equal time (SATURATION, SIZE_CAP: chronic). B20_R94 built the
domain and `tfxw-v1`, tfx-v1's search scaled past 64 vertices with one new choice (kpick). B20_R89's configuration was
chosen by time to target at n = 63 and under 0.25 s; on larger hosts and longer budgets the right operators may
differ (B20_R92 could not show any of them helping at n = 63). As in B20_R89, the system chooses by racing on fresh
training hosts (successive halving; Jamieson and Talwalkar 2016; racing, Birattari et al. 2002); the builder fixes the
space, the budget and the rule.

**Design (fixed before running).**
  * **Configurations:** 62 drawn uniformly from `tfxw-v1`'s SPACE (21 keys; seed 20269502), plus two disclosed
    entrants: B20_R89's frozen configuration with kpick 1 (tfx-v1's search as judged in B20_R90 and B20_R92) and
    `tfxw-v1`'s DEFAULT (the builder's first design, kpick 1). 64 in all, indexed in that order.
  * **Training hosts** (domain `triangle_free_large_v1`, seed 20269501): four cells, planted_cluster (p_in 0.8,
    p_out 0.06) and G(n, 0.5), each at n = 128 and n = 256; four hosts per cell, 16 in all, ordered so that every
    four consecutive hosts cover the four cells. Excluded: every large-domain host recorded in earlier evidence (none
    before this study; the n <= 63 hosts cannot coincide with them).
  * **Targets:** per host, the best value of B20_R89's configuration at 10 s (two seeds) and of PASMaxSAT-c and
    DeepDist (`maxsat-anytime-large-v1`, which gives each its whole budget after encoding) at 10 s (one seed each),
    computed first.
  * **Score of a configuration on (host, seed):** the mean over budgets (1, 5) CPU s of the MaxSAT Evaluation 2026
    anytime score against the target, (target cost + 1) / (cost + 1), cost = host edges − value (above 1 if it beats
    the target; `genesis.anytime`'s formula). Higher is better. The race calls the pinned `tfxw-v1` binary directly,
    pinned to one core (the sandboxed kind runs the same binary); run seeds derive from (configuration, host, seed,
    budget); every edge set is re-checked.
  * **Successive halving** (higher mean is better; ties by index): round 0, all 64 on hosts 0-3, seed 0; keep 16.
    Round 1: hosts 0-7; keep 8. Round 2: hosts 0-15, seeds 0-1; keep 4. Round 3: hosts 0-15, seeds 0-2; the frozen
    configuration is the best mean over all its evaluations among those four. About 3,500 CPU s of runs and 640 s of
    targets.
  * **Output:** `config.json`, `race.jsonl` (every evaluation), `hosts.json`, `targets.json`, `summary.json` (each
    round's survivors and means; which operators the frozen configuration uses; B20_R89's configuration's rank).

**Expectation, stated before running.** B20_R89's configuration is unlikely to win: it was chosen for time to target
under 0.25 s. On larger hosts within seconds, restarts and crossover (each rebuilds a member) and a large population
cost more; the frozen configuration will likely use cut descent warm starts, a population of 2-8, kpick above 1, and no
mean-field annealing. Simulated bifurcation, parallel tempering and crossover are open. DEFAULT likely does not reach
the last four.

**What it decides.** Only `tfxw-v1`'s configuration for the large-graph head-to-head. **Status.** A DEV diagnostic;
licenses nothing.
"""
import json
from pathlib import Path
import random
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))

from genesis import domains as DM  # noqa: E402
from genesis.candidate_kinds import maxsat_large as ML, tfxw as TW  # noqa: E402
from genesis.common import canonical, code_identity, digest  # noqa: E402
from genesis.models_large import LargeCandidateGraph, LargeGraphTask  # noqa: E402

import b20r11_e1_readiness as R11  # noqa: E402
import b20r33_strong_baseline_audit as R33  # noqa: E402

LARGE = 'triangle_free_large_v1'
HOST_SEED, CONFIG_SEED = 20269501, 20269502
CELLS = (('planted_cluster', {'n': 128, 'p_in': 0.8, 'p_out': 0.06}), ('erdos', {'n': 128, 'p': 0.5}),
         ('planted_cluster', {'n': 256, 'p_in': 0.8, 'p_out': 0.06}), ('erdos', {'n': 256, 'p': 0.5}))
PER_CELL = 4
DRAWN = 62
BUDGETS = (1.0, 5.0)
TARGET_S = 10.0
TARGET_CHAMPIONS = ('pasmaxsat-c', 'deepdist')
R89_CONFIG = ROOT / 'evidence' / 'configure_tfx_b20r89' / 'config.json'
# (hosts in play, seeds in play, survivors kept) per round
ROUNDS = ((4, 1, 16), (8, 1, 8), (16, 2, 4), (16, 3, 4))


def r89_config():
    return dict(json.loads(R89_CONFIG.read_text())['config'], kpick=1)


def configurations():
    rng = random.Random(CONFIG_SEED)
    drawn = [{k: rng.choice(v) for k, v in TW.SPACE.items()} for _ in range(DRAWN)]
    out = drawn + [r89_config(), dict(TW.DEFAULT)]
    for c in out:
        if TW.check_config(c):
            raise RuntimeError(TW.check_config(c))
    return out


def large_exposure(root):
    """Identities of every large-domain host recorded under evidence/ (hosts.json files with large tasks)."""
    a = DM.adapter(LARGE)
    seen = set()
    for p in sorted(Path(root, 'evidence').glob('*/hosts.json')):
        try:
            data = json.loads(p.read_text())
        except ValueError:
            continue
        for t in data.get('tasks', []) if isinstance(data, dict) else []:
            if isinstance(t, dict) and t.get('domain') == LARGE:
                seen.add(a.exposure_identity(LargeGraphTask.model_validate_json(canonical(t)))['canonical'])
    return seen


def hosts(out, log, excluded):
    path = out / 'hosts.json'
    if path.exists():
        log('hosts reloaded from hosts.json')
        return [LargeGraphTask.model_validate_json(canonical(t)) for t in json.loads(path.read_text())['tasks']]
    a = DM.adapter(LARGE)
    by_cell, seen = [], set(excluded)
    for ci, (fam, params) in enumerate(CELLS):
        tasks, seen, _ = a.generate(HOST_SEED + ci, PER_CELL, 'DEV', fam, params, excluded=seen)
        by_cell.append(tasks)
    order = [by_cell[c][i] for i in range(PER_CELL) for c in range(len(CELLS))]
    R11.dump(path, {'seed': HOST_SEED, 'cells': [[f, p] for f, p in CELLS], 'per_cell': PER_CELL,
                    'role': 'B20_R95 training hosts', 'tasks': [t.model_dump(mode='json') for t in order]})
    return order


def check(task, chosen):
    nb = [0] * task.n
    host = set(task.edges)
    for u, v in chosen:
        if (u, v) not in host:
            raise RuntimeError('an edge outside the host')
        nb[u] |= 1 << v
        nb[v] |= 1 << u
    if any(nb[u] & nb[v] for u, v in chosen):
        raise RuntimeError('a triangle')
    return len(chosen)


def run_tfxw(task, config, budget, seed):
    E = [tuple(e) for e in task.edges]
    text = f'{task.n} {len(E)} {seed % (1 << 62)} {budget * 1000:.3f}\n' + ''.join(f'{u} {v}\n' for u, v in E)
    r = subprocess.run([TW.BINARY, *[f'{k}={config[k]}' for k in sorted(config)]], input=text, capture_output=True,
                       text=True, timeout=budget + 30)
    line = [l for l in r.stdout.splitlines() if l.startswith('v ')]
    if r.returncode or len(line) != 1 or len(line[0]) != 2 + len(E):
        raise RuntimeError(f'tfxw failed: {r.returncode} {r.stdout[-200:]} {r.stderr[-200:]}')
    return check(task, [E[i] for i, b in enumerate(line[0][2:]) if b == '1'])


def seed_of(*parts):
    return int(digest({'study': 'b20r95', 'parts': list(parts)})[:12], 16)


def score(task, target, value):
    m = len(task.edges)
    return (m - target + 1) / (m - value + 1)


def targets(out, log, tasks):
    path = out / 'targets.json'
    if path.exists():
        return json.loads(path.read_text())['targets']
    tg, detail = {}, {}
    cfg = r89_config()
    for t in tasks:
        vals = {f'tfxw-r89-s{s}': run_tfxw(t, cfg, TARGET_S, seed_of('target', t.task_id, s)) for s in range(2)}
        view = LargeCandidateGraph(n=t.n, edges=t.edges)
        for c in TARGET_CHAMPIONS:
            r = ML.solve(view, {'solver': c, 'cpu_seconds': TARGET_S}, TARGET_S + ML.ENCODING_ALLOWANCE_S,
                         seed_of('target', c, t.task_id))
            vals[c] = check(t, [tuple(e) for e in r['selected']])
        tg[t.task_id] = max(vals.values())
        detail[t.task_id] = vals
        log(f'target {t.task_id} ({t.n} vertices, {len(t.edges)} edges): {tg[t.task_id]} {vals}')
    R11.dump(path, {'targets': tg, 'detail': detail, 'seconds': TARGET_S, 'champions': list(TARGET_CHAMPIONS),
                    'tfxw_sha256': TW.BINARY_SHA256})
    return tg


def main(argv=None):
    argv = argv or sys.argv[1:]
    out = Path(argv[0])
    out.mkdir(parents=True, exist_ok=True)
    cpu = R33.pinned_core()
    logf = (out / 'run.log').open('a')
    t0 = time.monotonic()

    def log(m):
        line = f'[{time.monotonic() - t0:7.1f}s] {m}'
        print(line, flush=True)
        logf.write(line + '\n')
        logf.flush()
    log(f'pinned to CPU {cpu}; tfxw sha256 {TW.binary_digest()[:16]} (pinned {TW.BINARY_SHA256[:16]})')
    if TW.binary_digest() != TW.BINARY_SHA256:
        raise SystemExit('the tfxw binary is not the pinned build')
    for c in TARGET_CHAMPIONS:
        why = ML.check_parameters(LARGE, {'solver': c, 'cpu_seconds': TARGET_S})
        if why:
            raise SystemExit(why)
    configs = configurations()
    excluded = large_exposure(ROOT)
    log(f'large-domain exposure: {len(excluded)} identities')
    tasks = hosts(out, log, excluded)
    tg = targets(out, log, tasks)
    path = out / 'race.jsonl'
    scores = {}
    if path.exists():
        for l in path.read_text().splitlines():
            if l.strip():
                r = json.loads(l)
                scores[(r['config'], r['host'], r['seed'])] = r['score']
    alive = list(range(len(configs)))
    rounds = []
    with path.open('a') as fh:
        for ri, (nh, ns, keep) in enumerate(ROUNDS):
            for c in alive:
                for h in range(nh):
                    for s in range(ns):
                        if (c, h, s) in scores:
                            continue
                        task = tasks[h]
                        vals = [run_tfxw(task, configs[c], b, seed_of(c, task.task_id, s, b)) for b in BUDGETS]
                        sc = statistics.mean(score(task, tg[task.task_id], v) for v in vals)
                        scores[(c, h, s)] = sc
                        fh.write(json.dumps({'config': c, 'host': h, 'seed': s, 'values': vals, 'score': sc}) + '\n')
                        fh.flush()
            mean = {c: statistics.mean(scores[(c, h, s)] for h in range(nh) for s in range(ns)) for c in alive}
            alive = sorted(alive, key=lambda c: (-mean[c], c))[:keep]
            rounds.append({'round': ri, 'hosts': nh, 'seeds': ns, 'kept': alive,
                           'means': {str(c): round(mean[c], 6) for c in sorted(mean, key=lambda c: (-mean[c], c))}})
            log(f'round {ri} ({nh} hosts x {ns} seeds): kept {len(alive)}; best '
                + ', '.join(f'#{c} {mean[c]:.5f}' for c in alive[:6]))
    final = {c: statistics.mean(v for (cc, h, s), v in scores.items() if cc == c) for c in alive}
    winner = max(alive, key=lambda c: (final[c], -c))
    config = configs[winner]
    if TW.check_config(config):
        raise RuntimeError('the frozen configuration is not valid')
    R11.dump(out / 'config.json', {'config': config, 'index': winner, 'final_mean_score': round(final[winner], 6),
                                   'is_r89': winner == DRAWN, 'is_default': winner == DRAWN + 1})
    uses = {'simulated_bifurcation': bool(config['ws'] & 1), 'cut_descent': bool(config['ws'] & 2),
            'mean_field_annealing': bool(config['ws'] & 4), 'parallel_tempering': config['acc'] == 1,
            'crossover': config['cross'] > 0, 'ant_colony_memory': config['rho'] > 0 and config['pherw'] > 0,
            'path_relinking': config['relink'] > 0, 'restarts': config['restart'] > 0,
            'least_tight_kicks': config['kpick'] > 1}
    r0 = rounds[0]['means']
    summary = {'schema': 'genesis-b20r95-configure-tfxw-v1', 'frozen': config, 'frozen_index': winner,
               'frozen_final_mean_score': round(final[winner], 6), 'operators_used': uses,
               'final_four': {str(c): {'mean_score': round(final[c], 6), 'config': configs[c]} for c in alive},
               'r89_rank_in_round_0': sorted(r0, key=lambda k: -r0[k]).index(str(DRAWN)) + 1,
               'default_rank_in_round_0': sorted(r0, key=lambda k: -r0[k]).index(str(DRAWN + 1)) + 1,
               'rounds': rounds, 'entrants': {'drawn': DRAWN, 'r89_index': DRAWN, 'default_index': DRAWN + 1},
               'budgets': list(BUDGETS), 'seeds': {'hosts': HOST_SEED, 'configs': CONFIG_SEED},
               'tfxw_sha256': TW.BINARY_SHA256, 'evaluations': len(scores),
               'code_identity': code_identity(ROOT)['sha256'],
               'status': 'DEV configuration search; licenses nothing; decides only the configuration of tfxw-v1'}
    R11.dump(out / 'summary.json', summary)
    log(f'frozen #{winner} (mean score {final[winner]:.5f}): {json.dumps(config, sort_keys=True)}; uses {uses}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
