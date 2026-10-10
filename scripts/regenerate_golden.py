#!/usr/bin/env python3
"""Regenerate the baseline-regression golden file (spec §38).

Run only after a reviewed, deliberate change to a baseline solver or exact
checker; commit the new file together with the adjudication note it prints.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.research import make_panel          # noqa: E402
from genesis.dsl import baseline_programs, solve  # noqa: E402
from genesis.graphs import certified_optimum      # noqa: E402


def compute():
    rows = []
    for domain in ('c4_host_v2', 'triangle_free_host_v1'):
        tasks, _ = make_panel(424242, 6, domain, 'DEV')
        for t in tasks:
            row = {'task': t.model_dump(mode='json'), 'optimum': certified_optimum(t)['value']}
            for name, prog in baseline_programs().items():
                r = solve(t, prog, 60, 7)
                row[name] = {'value': r['value'], 'queries': r['queries'], 'selected': [list(e) for e in r['selected']]}
            rows.append(row)
    return {'schema': 'genesis-baseline-golden-v1', 'seed': 424242, 'query_budget': 60, 'solver_seed': 7, 'rows': rows}


if __name__ == '__main__':
    out = ROOT / 'tests_genesis' / 'golden' / 'baselines.json'
    out.write_text(json.dumps(compute(), indent=1, sort_keys=True) + '\n')
    print(f'wrote {out}; record why the baseline changed in docs/BATCH_LOG.md before committing')
