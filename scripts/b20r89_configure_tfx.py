#!/usr/bin/env python3
"""B20_R89: the system configures its own engine: a racing search over `tfx-v1`'s operators (DEV, preregistered)

    taskset -c 0 python3 scripts/b20r89_configure_tfx.py OUT_DIR      run alone (resumable)

**Why.** Daniel asked for a solver that beats the most tuned solvers there are, inspired by nature and physics, and
earlier asked that the system find things itself. The strongest MaxSAT solvers were tuned by their authors, often
with automatic configurators (irace, SMAC). `tfx-v1` (B20_R88) carries operators from physics (simulated bifurcation,
three-body mean-field annealing, parallel tempering), biology (crossover, ant-colony memory) and the independent-set
literature ((1,2)-swaps, path relinking, restarts); which run, and how, is data. Here the system chooses, by racing
configurations on fresh training hosts, as an automatic algorithm configurator does (successive halving, Jamieson
and Talwalkar 2016; racing, Birattari et al. 2002, irace, López-Ibáñez et al. 2016). The builder fixes the space, the
budget and the rule, and does not choose.

**Design (fixed before running).**
  * **Configurations:** 126 drawn uniformly from `tfx-v1`'s SPACE (20 keys; seed 20268902), plus two disclosed
    entrants: DEFAULT (the builder's first design) and DEV_PICK (DEFAULT with ws 2 and K 8: B20_R88's best
    development-look variant, on B20_R76's hosts). 128 in all, indexed in that order.
  * **Training hosts:** planted_cluster (p_in 0.8, p_out 0.06), 32 fresh DEV hosts at n63, seed 20268901, excluding
    every identity `b20r24_repilots.exposure` excludes (all earlier studies' hosts).
  * **Targets:** per host, the best of DEFAULT at 5 s (two seeds) and DeepDist (`maxsat-anytime-v1`) at 5 s (one
    seed), computed first. A configuration may exceed a target; its gap is then negative.
  * **Score of a configuration on (host, seed):** the mean over budgets (0.02, 0.05, 0.1, 0.25) CPU s of
    (target − value). (0.02 s, below B20_R90's ladder, separates configurations that all reach the targets at
    0.05 s; in a toy smoke run on dev-only hosts many tied at zero.)
    The race calls the pinned `tfx-v1` binary directly, pinned to one core (the sandboxed kind runs the same binary;
    B20_R90 judges the frozen configuration in runc). Run seeds are derived from (configuration, host, seed, budget).
  * **Successive halving** (lower mean score is better; ties by index): round 0, all 128 on hosts 0–3, seeds 0–1;
    keep 64. Round 1: add hosts 4–7; keep 32. Round 2: add hosts 8–15; keep 16. Round 3: add hosts 16–31; keep 8.
    Round 4: add seeds 2–3 on all 32 hosts; keep 4. **Frozen:** the lowest mean over all its evaluations among those
    4. About 1,400 CPU s of runs plus 480 s of targets.
  * **Output:** `config.json` (the frozen configuration, valid under `tfx-v1`), `race.jsonl` (every evaluation),
    `hosts.json`, `targets.json`, `summary.json` (each round's survivors and means, and which operators the frozen
    configuration uses).

**Expectation, stated before running.** From B20_R88's looks on other hosts: the frozen configuration will use cut
descent warm starts, a population of 8 or more, and probably no simulated bifurcation (it cost time at these
budgets); the pheromone memory will not survive; crossover and parallel tempering are open. DEV_PICK is likely among
the last 8; DEFAULT likely not.

**What it decides.** Only `tfx-v1`'s configuration for B20_R90. **Status.** A DEV diagnostic; licenses nothing.
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

from genesis.candidate_kinds import maxsat as MS, tfx as T  # noqa: E402
from genesis.common import canonical, code_identity, digest  # noqa: E402
from genesis.models import CandidateGraph, GraphTask  # noqa: E402

import b20r11_e1_readiness as R11  # noqa: E402
import b20r23_e1b_readiness as RD  # noqa: E402
import b20r24_repilots as R24  # noqa: E402
import b20r33_strong_baseline_audit as R33  # noqa: E402
import b20r64_e1d_scaling as R64  # noqa: E402

TF = RD.TF
HOST_SEED, CONFIG_SEED, HOSTS, N = 20268901, 20268902, 32, 63
P_IN, P_OUT = 0.8, 0.06
DRAWN = 126
BUDGETS = (0.02, 0.05, 0.1, 0.25)
TARGET_S = 5.0
DEV_PICK = dict(T.DEFAULT, ws=2, K=8)
# (hosts in play, seeds in play, survivors kept) per round
ROUNDS = ((4, 2, 64), (8, 2, 32), (16, 2, 16), (32, 2, 8), (32, 4, 4))


def configurations():
    rng = random.Random(CONFIG_SEED)
    drawn = [{k: rng.choice(v) for k, v in T.SPACE.items()} for _ in range(DRAWN)]
    out = drawn + [dict(T.DEFAULT), dict(DEV_PICK)]
    for c in out:
        if T.check_config(c):
            raise RuntimeError(T.check_config(c))
    return out


def hosts(out, log, excluded):
    path = out / 'hosts.json'
    if path.exists():
        log('hosts reloaded from hosts.json')
        return [GraphTask.model_validate_json(canonical(t)) for t in json.loads(path.read_text())['tasks']]
    tasks, _ = R64.generate_beyond_space(HOST_SEED, HOSTS, 'DEV', {'n': N, 'p_in': P_IN, 'p_out': P_OUT}, set(excluded))
    if len(tasks) != HOSTS or RD.identities(tasks) & set(excluded):
        raise RuntimeError('host drawing failed or collides with an excluded identity')
    R11.dump(path, {'seed': HOST_SEED, 'count': HOSTS, 'n': N, 'params': {'p_in': P_IN, 'p_out': P_OUT},
                    'role': 'B20_R89 training hosts', 'tasks': [t.model_dump(mode='json') for t in tasks]})
    return tasks


def run_tfx(task, config, budget, seed):
    """The pinned binary, directly; the best value, its edge set re-checked here."""
    E = [tuple(e) for e in task.edges]
    text = f'{task.n} {len(E)} {seed % (1 << 62)} {budget * 1000:.3f}\n' + ''.join(f'{u} {v}\n' for u, v in E)
    r = subprocess.run([T.BINARY, *T.arguments(config)], input=text, capture_output=True, text=True,
                       timeout=budget + 5)
    line = [l for l in r.stdout.splitlines() if l.startswith('v ')]
    if r.returncode or len(line) != 1:
        raise RuntimeError(f'tfx failed: {r.returncode} {r.stdout[-200:]} {r.stderr[-200:]}')
    chosen = [E[i] for i, b in enumerate(line[0][2:]) if b == '1']
    nb = [0] * task.n
    for u, v in chosen:
        nb[u] |= 1 << v
        nb[v] |= 1 << u
    if any(nb[u] & nb[v] for u, v in chosen):
        raise RuntimeError('tfx returned a triangle')
    return len(chosen)


def seed_of(*parts):
    return int(digest({'study': 'b20r89', 'parts': list(parts)})[:12], 16)


def targets(out, log, tasks):
    path = out / 'targets.json'
    if path.exists():
        return json.loads(path.read_text())['targets']
    tg = {}
    for t in tasks:
        vals = [run_tfx(t, T.DEFAULT, TARGET_S, seed_of('target', t.task_id, s)) for s in range(2)]
        dd = MS.solve(CandidateGraph(domain=TF, n=t.n, edges=t.edges), {'solver': 'deepdist', 'cpu_seconds': TARGET_S},
                      TARGET_S, seed_of('target-deepdist', t.task_id))['value']
        tg[t.task_id] = max(vals + [dd])
        log(f'target {t.task_id[-4:]} ({len(t.edges)} edges): {tg[t.task_id]} (tfx {vals}, deepdist {dd})')
    R11.dump(path, {'targets': tg, 'tfx_seconds': TARGET_S, 'deepdist_seconds': TARGET_S,
                    'deepdist_sha256': MS.binary_digest(MS.SOLVERS['deepdist']['binary'])})
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
    log(f'pinned to CPU {cpu}; tfx sha256 {T.binary_digest()[:16]} (pinned {T.BINARY_SHA256[:16]})')
    if T.binary_digest() != T.BINARY_SHA256:
        raise SystemExit('the tfx binary is not the pinned build')
    configs = configurations()
    excluded, scan, _ = R24.exposure(log)
    tasks = hosts(out, log, excluded)
    tg = targets(out, log, tasks)
    path = out / 'race.jsonl'
    scores = {}                                        # (config, host, seed) -> score
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
                        vals = [run_tfx(task, configs[c], b, seed_of(c, task.task_id, s, b)) for b in BUDGETS]
                        sc = statistics.mean(tg[task.task_id] - v for v in vals)
                        scores[(c, h, s)] = sc
                        fh.write(json.dumps({'config': c, 'host': h, 'seed': s, 'values': vals, 'score': sc}) + '\n')
                        fh.flush()
            mean = {c: statistics.mean(scores[(c, h, s)] for h in range(nh) for s in range(ns)) for c in alive}
            alive = sorted(alive, key=lambda c: (mean[c], c))[:keep]
            rounds.append({'round': ri, 'hosts': nh, 'seeds': ns, 'kept': alive,
                           'means': {str(c): round(mean[c], 4) for c in sorted(mean, key=lambda c: (mean[c], c))}})
            log(f'round {ri} ({nh} hosts x {ns} seeds): kept {len(alive)}; best '
                + ', '.join(f'#{c} {mean[c]:.3f}' for c in alive[:6]))
    final = {c: statistics.mean(v for (cc, h, s), v in scores.items() if cc == c) for c in alive}
    winner = min(alive, key=lambda c: (final[c], c))
    config = configs[winner]
    if T.check_config(config):
        raise RuntimeError('the frozen configuration is not valid')
    R11.dump(out / 'config.json', {'config': config, 'index': winner, 'final_mean_gap': round(final[winner], 4),
                                   'is_default': winner == DRAWN, 'is_dev_pick': winner == DRAWN + 1})
    uses = {'simulated_bifurcation': bool(config['ws'] & 1), 'cut_descent': bool(config['ws'] & 2),
            'mean_field_annealing': bool(config['ws'] & 4), 'parallel_tempering': config['acc'] == 1,
            'crossover': config['cross'] > 0, 'ant_colony_memory': config['rho'] > 0 and config['pherw'] > 0,
            'path_relinking': config['relink'] > 0, 'restarts': config['restart'] > 0}
    summary = {'schema': 'genesis-b20r89-configure-tfx-v1', 'frozen': config, 'frozen_index': winner,
               'frozen_final_mean_gap': round(final[winner], 4), 'operators_used': uses,
               'final_four': {str(c): {'mean_gap': round(final[c], 4), 'config': configs[c]} for c in alive},
               'rounds': rounds, 'entrants': {'drawn': DRAWN, 'default_index': DRAWN, 'dev_pick_index': DRAWN + 1},
               'budgets': list(BUDGETS), 'seeds': {'hosts': HOST_SEED, 'configs': CONFIG_SEED},
               'tfx_sha256': T.BINARY_SHA256, 'evaluations': len(scores), 'exposure_scan': scan,
               'code_identity': code_identity(ROOT)['sha256'],
               'status': 'DEV configuration search; licenses nothing; decides only the configuration for B20_R90'}
    R11.dump(out / 'summary.json', summary)
    log(f'frozen #{winner} (mean gap {final[winner]:.4f}): {json.dumps(config, sort_keys=True)}; uses {uses}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
