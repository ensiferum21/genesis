#!/usr/bin/env python3
"""CRPD-2b (B20 continuation): Lean-check the C4 pair-count bound and use it as a checked upper bound.

    b20r_pair_count.py OUT_DIR

Needs the revised formal workspace (toolchain/FORMAL_WORKSPACE.json with the Finset big-operator
roots). Steps:
  1. screen both statements (invention.pair_count) on small hosts, search with the builder-written
     recipes, accept through the sandboxed checker (allowed axioms only);
  2. assemble the theory package and replay it from its sources;
  3. certificate bundles v2 with the PAIR_COUNT_LEAN upper method on complete hosts K3..K7 and on
     random dense c4 hosts; each bundle replayed checker-only; the exact optimum is cross-checked
     by the exact producer and, where the bound is not tight, by a SAT/DRAT certificate.
Writes package.json, replay.json, certificates.json and bundles/ to OUT_DIR. Known results; the
statements and proofs are builder-written.
"""
import json
from pathlib import Path
import random
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from genesis.formal_research import loop as L  # noqa: E402
from genesis.formal_research import theory_package as TP  # noqa: E402
from genesis.graphs import exact_producer  # noqa: E402
from genesis.invention import pair_count as PC  # noqa: E402
from genesis.invention import soundness as SM  # noqa: E402
from genesis.models import GraphTask  # noqa: E402
from genesis.verification import certificates as CB  # noqa: E402


def hosts():
    out = []
    for n in range(3, 8):
        edges = tuple((u, v) for u in range(n) for v in range(u + 1, n))
        out.append(GraphTask(task_id=f'complete-k{n}', domain='c4_host_v2', n=n, edges=edges, family='complete',
                             split='DEV'))
    rng = random.Random(20261013)
    for i in range(4):
        n = rng.choice((7, 8))
        pairs = [(u, v) for u in range(n) for v in range(u + 1, n)]
        edges = tuple(sorted(e for e in pairs if rng.random() < 0.85))[:24]
        out.append(GraphTask(task_id=f'dense-{i}', domain='c4_host_v2', n=n, edges=tuple(sorted(edges)),
                             family='dense-erdos-p0.85', split='DEV'))
    return out


def main(argv=None):
    out = Path((argv or sys.argv[1:])[0])
    out.mkdir(parents=True, exist_ok=False)
    t0 = time.monotonic()
    log = lambda m: print(f'[{time.monotonic() - t0:7.1f}s] {m}', flush=True)
    state = L.prove_all(PC.conjectures(), base_modules=PC.base_modules(), conj_name=PC.CONJ_NAME,
                        proof_prefix=PC.PROOF_PREFIX, unfold=['G4.C4Free', 'G4.adj', 'G4.verts'],
                        extra_recipes=PC.recipes, log=log)
    statuses = {s['id']: s['status'] for s in state['statements']}
    if set(statuses.values()) != {'CHECKED'}:
        (out / 'state.json').write_text(json.dumps({'statements': state['statements'], 'attempts': state['attempts']},
                                                   indent=1, default=str, ensure_ascii=False) + '\n')
        log(f'not checked: {statuses}')
        return 1
    pkg, _ = L.assemble(state, name='C4 pair-count bound (CRPD-2b)', domain='c4_host_v2',
                        scope='every edge set S of ordered pairs u < v < n (the c4_host_v2 host contract)',
                        conventions=['known counting results; statements and proof recipes are builder-written',
                                     'adjacency is symmetric by definition (G4.adj)',
                                     'needs the revised workspace pin (Finset big operators)'])
    (out / 'package.json').write_text(json.dumps(pkg, indent=1, sort_keys=True, ensure_ascii=False) + '\n')
    rep = TP.replay(pkg)
    (out / 'replay.json').write_text(json.dumps(rep, indent=1, sort_keys=True, default=str) + '\n')
    log(f'statements {statuses}; package problems {PC.package_problems(pkg)}; replay {rep["verdict"]}')
    if rep['verdict'] != 'REPLAYED' or PC.package_problems(pkg):
        return 1
    rows = []
    for task in hosts():
        ex = exact_producer(task)
        bound = PC.quadratic_upper(task.n)
        bundle, blobs = CB.build_v2(task, witness=ex['selected'], lower=ex['value'],
                                    upper={'method': 'PAIR_COUNT_LEAN', 'package': pkg})
        h = CB.persist_dir(out / 'bundles', bundle, blobs)
        objects = out / 'bundles' / 'objects'
        r = CB.replay(bundle, lambda k: (objects / k).read_bytes())
        lo, up = SM.certificate_bound_modes(bundle, r)
        row = {'task_id': task.task_id, 'n': task.n, 'host_edges': len(task.edges), 'exact_optimum': ex['value'],
               'pair_count_bound': bound, 'bundle_sha256': h, 'recorded_status': bundle['status'],
               'replay': {k: r[k] for k in ('status', 'lower', 'upper', 'gap')}, 'replay_problems': r['problems'],
               'upper_mode': up['established'], 'optimum_licensed': not SM.optimum_problems(lo, up)}
        if bound > ex['value']:
            from genesis.verification.sat import certified_bounds
            sb = certified_bounds(task, seconds=60, start_witness=ex['selected'])
            row['sat_cross_check'] = {'status': sb['status'], 'upper': sb['upper'],
                                      'method': (sb.get('upper_certificate') or {}).get('method')}
        rows.append(row)
        log(f'{task.task_id}: n={task.n} m={len(task.edges)} optimum={ex["value"]} bound={bound} '
            f'replay={r["status"]} {r["problems"]}')
    summary = {'schema': 'genesis-pair-count-evidence-v1', 'package_sha256': pkg['package_sha256'],
               'checker_identity': PC.checker_identity(), 'statements': statuses,
               'axioms_used': pkg['assumptions']['axioms_used'], 'certificates': rows,
               'label': 'DEV fixtures; known results; builder-written statements and proofs'}
    (out / 'certificates.json').write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n')
    ok = all(r['replay']['status'] in ('OPTIMALITY_CHECKED', 'BOUNDS_CHECKED') for r in rows)
    log(f'certificates: {[(r["task_id"], r["replay"]["status"]) for r in rows]}')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
