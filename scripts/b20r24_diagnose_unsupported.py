#!/usr/bin/env python3
"""B20_R24 diagnosis: why the custodian marked rehearsal CONFIRM hosts UNSUPPORTED.

    PYTHONPATH=src python3 scripts/b20r24_diagnose_unsupported.py   (from the repository root)

For each unsupported host of evidence/repilots_b20r24/rehearsal_<key>.json: the graph adapter reference the
custodian used (SAT-only, default 600 s) and obstruction.certify (exact LP dual, then SAT/DRAT; 120 s, unseeded).
Output: evidence/repilots_b20r24/diagnosis_unsupported.log. A diagnosis, not a study.
"""
import json, sys, time
from genesis.models import GraphTask
from genesis.common import canonical
from genesis.domains import ADAPTERS
from genesis.discovery import obstruction as O
for key in ('e1', 'e1b_tf'):
    r = json.load(open(f'evidence/repilots_b20r24/rehearsal_{key}.json'))
    bad = set(r['receipt_payload']['analysis_result']['unsupported'])
    for t in r['confirm_hosts']:
        if t['task_id'] not in bad: continue
        g = GraphTask.model_validate_json(canonical(t))
        t0 = time.monotonic(); ref = ADAPTERS[g.domain].reference(g)
        a = time.monotonic() - t0
        t0 = time.monotonic(); c = O.certify(g, [], seconds=120)
        print(key, g.task_id, len(g.edges), 'adapter:', getattr(ref, 'reason', None) or ref.get('status'), round(a, 1), 's | certify:', c['lower'], c['upper'], c['upper_evidence']['method'], round(time.monotonic() - t0, 1), 's', flush=True)
