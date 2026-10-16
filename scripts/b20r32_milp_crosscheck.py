#!/usr/bin/env python3
"""B20_R32, post hoc: cross-check the SAT/DRAT-certified optima of B20_R30 and B20_R32 with an
independent exact solver.

    b20r32_milp_crosscheck.py OUT_JSON

**Why, after the fact.** B20_R30 and B20_R32 drew their hosts from the same `e1b` settings.
Yet the share of hosts whose triangle-LP floor exceeds the certified optimum, so that the
evaluator needs an UNSAT proof, differed sharply: 18/90 in B20_R30 (planted 10/30) against 3/90
in B20_R32 (planted 0/30). One explanation would be an evaluator defect that certifies too low
an optimum through SAT. This check tests that explanation. It is not preregistered, and it
changes no verdict.

**What it does.** For every host whose certified upper bound came from SAT/DRAT, it solves the
integer program max Σ x_e, s.t. x(T) ≤ 2 for every host triangle T, x ∈ {0,1}, with HiGHS
through `scipy.optimize.milp` (scipy pinned in requirements.lock), with a 300 s limit. The
solution is re-checked by the domain checker. If its value exceeded a certified optimum, the
evaluator would be refuted. HiGHS's optimality claim carries no proof object; it is only a
cross-check. Wall time is recorded, with one solve at a time.
"""
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from genesis.common import canonical  # noqa: E402
from genesis.discovery.obstruction import triangles  # noqa: E402
from genesis.graphs import check_witness  # noqa: E402
from genesis.models import GraphTask  # noqa: E402

SOURCES = {
    'B20_R30': (ROOT / 'evidence' / 'certification_budget_b20r30',
                lambda r: (r['evaluator']['method'] == 'JOINT_SAT_DRAT', r['evaluator']['value'])),
    'B20_R32': (ROOT / 'evidence' / 'generated_certification_b20r32',
                lambda r: (r['a']['method'] == 'SAT_DRAT', r['a']['upper'])),
}


def solve(task, seconds=300):
    import numpy as np
    from scipy.optimize import Bounds, LinearConstraint, milp
    from scipy.sparse import lil_matrix
    E = [tuple(e) for e in task.edges]
    idx = {e: i for i, e in enumerate(E)}
    T = triangles(task)
    A = lil_matrix((max(1, len(T)), len(E)))
    for j, t in enumerate(T):
        for e in t:
            A[j, idx[e]] = 1
    t0 = time.monotonic()
    res = milp(-np.ones(len(E)), constraints=LinearConstraint(A.tocsr(), -np.inf, 2), integrality=np.ones(len(E)),
               bounds=Bounds(0, 1), options={'time_limit': seconds})
    wall = time.monotonic() - t0
    sel = [E[i] for i in range(len(E)) if res.x is not None and res.x[i] > 0.5]
    value = check_witness(task, sel)['value'] if res.x is not None else None
    return {'status': int(res.status), 'message': res.message, 'value': value,
            'dual_bound': None if getattr(res, 'mip_dual_bound', None) is None else round(-res.mip_dual_bound, 6),
            'wall_s': round(wall, 3)}


def main(argv=None):
    out = Path((argv or sys.argv[1:])[0])
    rows = []
    for batch, (d, pick) in SOURCES.items():
        tasks = {t['task_id']: GraphTask.model_validate_json(canonical(t))
                 for t in json.loads((d / 'hosts.json').read_text())['tasks']}
        for line in (d / 'rows.jsonl').read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            sat, claimed = pick(r)
            if not sat:
                continue
            m = solve(tasks[r['task_id']])
            rows.append({'batch': batch, 'task_id': r['task_id'], 'certified_optimum': claimed, 'milp': m,
                         'agrees': m['value'] == claimed and m['status'] == 0})
            print(r['task_id'], claimed, m, flush=True)
    summary = {'schema': 'genesis-b20r32-milp-crosscheck-v1', 'post_hoc': True, 'rows': rows,
               'hosts': len(rows), 'agree': sum(r['agrees'] for r in rows),
               'refuted': [r['task_id'] for r in rows if r['milp']['value'] is not None and
                           r['milp']['value'] > r['certified_optimum']],
               'milp_wall_s_max': max((r['milp']['wall_s'] for r in rows), default=None)}
    out.write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n')
    print(json.dumps({k: summary[k] for k in ('hosts', 'agree', 'refuted', 'milp_wall_s_max')}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
