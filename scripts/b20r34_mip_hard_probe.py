#!/usr/bin/env python3
"""B20_R34: is there a triangle-free setting where an exact solver fails within the candidate's
budget, while the evaluator can still certify? (DEV probe for B20R33-OPEN-1, option 3)

    b20r34_mip_hard_probe.py OUT_DIR            run (resumable) and analyse
    b20r34_mip_hard_probe.py OUT_DIR --summary  analyse existing rows only

B20_R33 found that on the decided `e1b` family an exact MIP solver (HiGHS through the pinned
scipy) proves every optimum within 0.36 CPU s. Against it, neither frozen candidate can be "beyond
strong baselines". One option for the reviewer is a family where the exact solver does *not*
finish within the candidate's budget, while the evaluator's reference still certifies. The
evaluator certifies triangle-free hosts of at most 200 edges (`CERTIFICATE_MAX_EDGES`). This probe
maps that range. It changes no rule and no package. Everything below is fixed before running.

**Settings.** Triangle-free, inside the domain's family space (n ≤ 40) and chosen for 160–195
expected edges, near the certification bound:
  erdos            n30 p0.42, n34 p0.33, n37 p0.27, n40 p0.23
  planted_cluster  n36 p_in 0.6 p_out 0.15, n40 p_in 0.6 p_out 0.12, n40 p_in 0.8 p_out 0.06
8 DEV hosts per setting, generator seed 20263401 + 10 i, in this order. They exclude every
identity b20r24_repilots.exposure excludes: every graph host named under evidence/ and handoff/,
the regenerated E1 hosts, and the calibration hosts.

**Process.** One pinned CPU core, set before any library is imported, as in B20_R33.

**Per host:**
  mip        scipy.optimize.milp (HiGHS) at 2.0 s, exactly as B20_R33's mip_2.0 arm;
  candidate  the frozen E1b descriptor (`handoff/e1b/candidate_descriptor.json`), runc, 2.0 CPU s;
  baselines  the frozen E1b time-matched baselines, runc, 2.0 CPU s each; best_baseline is the
             per-host maximum;
  reference  discovery.obstruction.certify seeded with the best witness, 60 s (the e1-hard-v2
             certification limit). Hosts with more than 200 edges have no reference and count as
             uncertified.

**Per setting:**
  certified       share of hosts with lower == upper within 60 s;
  mip_suboptimal  share of certified hosts where the MIP's 2.0 s value is below the optimum;
  headroom        share of certified hosts where best_baseline is below the optimum;
  and the mean gaps to the optimum of the MIP, the candidate and best_baseline.

**Classification (fixed here):** a setting is MIP_HARD_CERTIFIABLE iff all three hold:
  * certified ≥ 0.9;
  * mip_suboptimal ≥ 0.25;
  * headroom ≥ 0.5.
The verdict is MIP_HARD_CERTIFIABLE_SETTINGS_FOUND, listing them, or
NO_MIP_HARD_CERTIFIABLE_SETTING.

Development look before preregistration: the builder ran this code path once on a B20_R33 host
(e1b planted_cluster, excluded here), with the reference at 20 s, to check the code. None of the
settings above was generated before the run.

A DEV probe on 8 hosts per setting. It is a map for a reviewer's decision, not a calibration under
any rule. Any setting it finds would still need a versioned family rule and a fresh calibration.
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

from genesis.common import code_identity, digest  # noqa: E402
from genesis.discovery import obstruction as O  # noqa: E402
from genesis.domains import ADAPTERS  # noqa: E402

import b20r11_e1_readiness as R11  # noqa: E402
import b20r23_e1b_readiness as RD  # noqa: E402
import b20r24_repilots as R24  # noqa: E402
import b20r33_strong_baseline_audit as R33  # noqa: E402

TF = RD.TF
SETTINGS = [('erdos', {'n': 30, 'p': 0.42}), ('erdos', {'n': 34, 'p': 0.33}), ('erdos', {'n': 37, 'p': 0.27}),
            ('erdos', {'n': 40, 'p': 0.23}),
            ('planted_cluster', {'n': 36, 'p_in': 0.6, 'p_out': 0.15}),
            ('planted_cluster', {'n': 40, 'p_in': 0.6, 'p_out': 0.12}),
            ('planted_cluster', {'n': 40, 'p_in': 0.8, 'p_out': 0.06})]
PER, SEED = 8, 20263401
BUDGET, REFERENCE_S = 2.0, 60
MAX_EDGES = 200


def arms():
    from genesis import candidates as C
    d = ROOT / 'handoff' / 'e1b'
    out = {'candidate': json.loads((d / 'candidate_descriptor.json').read_text())}
    out.update(sorted(json.loads((d / 'time_matched_baselines.json').read_text()).items()))
    for name, desc in out.items():
        if C.descriptor_problems(desc):
            raise RuntimeError(f'frozen E1b descriptor {name} does not rebuild')
    return out


def hosts(log):
    excluded, scan, _ = R24.exposure(log)
    seen, out = set(excluded), []
    for i, (family, params) in enumerate(SETTINGS):
        tasks, seen, _ = ADAPTERS[TF].generate(SEED + 10 * i, PER, 'DEV', family, params, excluded=seen)
        out += tasks
    if RD.identities(out) & set(excluded):
        raise RuntimeError('a generated host collides with a named host')
    return out, scan


def run_host(task, arm_descs):
    from genesis import candidates as C
    seed = int(digest({'pilot': 'b20r34', 'task': task.task_id})[:12], 16)
    res, best = {}, None
    for name, desc in arm_descs.items():
        r = C.run(task, desc, seed=seed, expected_id=desc['descriptor_id'], isolation='runc')
        ok = r['status'] == 'SUCCESS'
        res[name] = {'value': r['result']['value'] if ok else 0, 'status': r['status']}
        if ok and (best is None or r['result']['value'] > best[0]):
            best = (r['result']['value'], [tuple(e) for e in r['result']['selected']], name)
    m = R33.mip(task, BUDGET)
    res['mip'] = {k: m[k] for k in ('value', 'raw_value', 'cpu_s', 'wall_s', 'status', 'overrun', 'proved_optimal')}
    if m['value'] and (best is None or m['value'] > best[0]):
        best = (m['value'], m['selected'], 'mip')
    if len(task.edges) > MAX_EDGES:
        ref = {'status': 'NO_REFERENCE', 'reason': f'{len(task.edges)} edges > {MAX_EDGES}'}
        opt = None
    else:
        rec = O.certify(task, best[1] if best else [], seconds=REFERENCE_S)
        ref = {'lower': rec['lower'], 'upper': rec['upper'], 'method': rec['upper_evidence']['method'],
               'wall_s': rec['wall_s'], 'seeded_from': best and best[2]}
        opt = rec['lower'] if rec['lower'] == rec['upper'] and rec['wall_s'] <= REFERENCE_S else None
    return {'task_id': task.task_id, 'setting': task.family, 'n': task.n, 'edges': len(task.edges), 'arms': res,
            'reference': ref, 'optimum': opt}


def run(out, tasks, arm_descs, log):
    path = out / 'rows.jsonl'
    done = set()
    if path.exists():
        done = {json.loads(l)['task_id'] for l in path.read_text().splitlines() if l.strip()}
    t0 = time.monotonic()
    with path.open('a') as fh:
        for t in tasks:
            if t.task_id in done:
                continue
            r = run_host(t, arm_descs)
            fh.write(json.dumps(r, sort_keys=True) + '\n')
            fh.flush()
            log(f'{t.task_id} ({r["edges"]} edges): opt {r["optimum"]} '
                f'{ {k: a["value"] for k, a in r["arms"].items()} } [{time.monotonic() - t0:.0f}s]')


def classify(rows, base_names):
    bb = lambda r: max(r['arms'][k]['value'] for k in base_names)
    scored = [r for r in rows if r['optimum'] is not None]
    n, k = len(rows), len(scored)
    share = lambda f: round(sum(f(r) for r in scored) / k, 4) if k else None
    gap = lambda f: round(statistics.fmean(r['optimum'] - f(r) for r in scored), 4) if k else None
    out = {'hosts': n, 'edges_mean': round(statistics.fmean(r['edges'] for r in rows), 1),
           'over_edge_bound': sum(r['edges'] > MAX_EDGES for r in rows),
           'certified': round(k / n, 4), 'certified_hosts': k,
           'mip_suboptimal': share(lambda r: r['arms']['mip']['value'] < r['optimum']),
           'mip_proved_optimal': sum(r['arms']['mip']['proved_optimal'] for r in rows),
           'headroom': share(lambda r: bb(r) < r['optimum']),
           'gap_mip': gap(lambda r: r['arms']['mip']['value']), 'gap_candidate': gap(lambda r: r['arms']['candidate']['value']),
           'gap_best_baseline': gap(bb),
           'mip_cpu_s_max': max(r['arms']['mip']['cpu_s'] for r in rows)}
    out['class'] = ('MIP_HARD_CERTIFIABLE' if out['certified'] >= 0.9 and (out['mip_suboptimal'] or 0) >= 0.25
                    and (out['headroom'] or 0) >= 0.5 else 'NOT_MIP_HARD_CERTIFIABLE')
    return out


def analyse(out, tasks, scan, arm_descs):
    rows = [json.loads(l) for l in (out / 'rows.jsonl').read_text().splitlines() if l.strip()]
    if {r['task_id'] for r in rows} != {t.task_id for t in tasks}:
        raise RuntimeError('not every host has been run')
    base = [k for k in arm_descs if k != 'candidate']
    params = {t.family: p for t, (_, p) in zip(tasks[::PER], SETTINGS)}
    by = {}
    for r in rows:
        by.setdefault(r['setting'], []).append(r)
    settings = {s: dict(classify(rs, base), params=params.get(s)) for s, rs in by.items()}
    found = sorted(s for s, v in settings.items() if v['class'] == 'MIP_HARD_CERTIFIABLE')
    summary = {'schema': 'genesis-b20r34-mip-hard-probe-v1', 'seed': SEED, 'budget_s': BUDGET,
               'reference_s': REFERENCE_S, 'descriptors': {k: v['descriptor_id'] for k, v in arm_descs.items()},
               'settings': settings, 'found': found,
               'verdict': 'MIP_HARD_CERTIFIABLE_SETTINGS_FOUND' if found else 'NO_MIP_HARD_CERTIFIABLE_SETTING',
               'exposure_scan': scan, 'code_identity': code_identity(ROOT)['sha256'],
               'status': 'DEV probe for a reviewer decision (B20R33-OPEN-1); not a calibration; licenses no claim'}
    R11.dump(out / 'summary.json', summary)
    return summary


def main(argv=None):
    argv = argv or sys.argv[1:]
    out = Path(argv[0])
    out.mkdir(parents=True, exist_ok=True)
    cpu = R33.pinned_core()
    logf = (out / 'run.log').open('a')
    t0 = time.monotonic()

    def log(msg):
        line = f'[{time.monotonic() - t0:7.1f}s] {msg}'
        print(line, flush=True)
        logf.write(line + '\n')
        logf.flush()
    log(f'pinned to CPU {cpu}')
    arm_descs = arms()
    tasks, scan = hosts(log)
    R11.dump(out / 'hosts.json', {'seed': SEED, 'settings': [{'family': f, 'params': p} for f, p in SETTINGS],
                                  'tasks': [t.model_dump(mode='json') for t in tasks]})
    if '--summary' not in argv:
        run(out, tasks, arm_descs, log)
    s = analyse(out, tasks, scan, arm_descs)
    log(f'verdict {s["verdict"]}: ' + json.dumps({k: (v['class'], v['certified'], v['mip_suboptimal'], v['headroom'])
                                                  for k, v in s['settings'].items()}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
