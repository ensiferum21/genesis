"""B20_R65: why were rehearsal hosts unsupported? (statistician's brief, finding 5; diagnosis from committed evidence)

**Why.** The registered analysis excludes CONFIRM hosts whose optimum the reference cannot certify ("unsupported")
and is INVALID above 5%. The brief (B20_R61) noted that E1d's exclusions all fall in one stratum. If the reason a
host is unsupported correlates with the outcome, exclusion biases the estimate. This batch finds the reason for
every unsupported host in every same-operator rehearsal.

**Method.** For each rehearsal, read its own evidence file, the one that carries the CONFIRM hosts the custodian
drew. Then, for each unsupported task id, take that host (task ids are not unique across panels: a development look
in B20_R43 reused one), count its edges, and classify the reason:
  * SIZE_BOUND: more than `GraphHostAdapter.CERTIFICATE_MAX_EDGES` (200) host edges. The custody path refuses a
    certified reference for such a host (`supports(task, 'exact_reference')`) before any search. It depends on the
    host alone, so it is blind to both arms.
  * REFERENCE_LIMIT: within the bound, but the reference did not certify the optimum within its time.

The script also reports how many CONFIRM hosts per stratum exceed the bound, so the reader can see whether the
bound, not the reference, explains each exclusion. Nothing is re-run.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.domains import GraphHostAdapter  # noqa: E402

BOUND = GraphHostAdapter.CERTIFICATE_MAX_EDGES
REHEARSALS = (
    ('E1 (B20_R24)', 'evidence/rehearsal_rerun_b20r24/rehearsal_e1.json'),
    ('E1b (B20_R24)', 'evidence/rehearsal_rerun_b20r24/rehearsal_e1b_tf.json'),
    ('E1b-C4 (B20_R52)', 'evidence/e1b_c4_package_b20r52/rehearsal_summary.json'),
    ('E1d (B20_R43)', 'evidence/e1d_package_b20r43/rehearsal_summary.json'),
    ('E1d ablation (B20_R45)', 'evidence/e1d_ablation_rehearsal_b20r45/rehearsal_summary.json'),
)


def stratum(task_id):
    parts = task_id.split('-')
    return f'{parts[1]}:{parts[2]}'


def diagnose(rel):
    s = json.loads((ROOT / rel).read_text())
    hosts = {t['task_id']: t for t in s['confirm_hosts']}
    ar = s['receipt_payload']['analysis_result']
    if len(hosts) != len(s['confirm_hosts']) or len(hosts) != ar['tasks']:
        raise ValueError(f'{rel}: the CONFIRM hosts do not match the analysed tasks')
    out = []
    for u in ar['unsupported']:
        e = len(hosts[u]['edges'])
        out.append({'task_id': u, 'stratum': stratum(u), 'edges': e,
                    'reason': 'SIZE_BOUND' if e > BOUND else 'REFERENCE_LIMIT'})
    over = {}
    for t in hosts.values():
        if len(t['edges']) > BOUND:
            over[stratum(t['task_id'])] = over.get(stratum(t['task_id']), 0) + 1
    return {'tasks': ar['tasks'], 'unsupported': out, 'confirm_hosts_over_bound': dict(sorted(over.items())),
            'every_over_bound_host_is_unsupported': sum(over.values()) == sum(r['reason'] == 'SIZE_BOUND' for r in out),
            'max_edges': max(len(t['edges']) for t in hosts.values())}


def table():
    return {name: dict(diagnose(rel), evidence=rel) for name, rel in REHEARSALS}


def markdown():
    lines = ['| Rehearsal | CONFIRM hosts | Unsupported: task (edges) and reason | Hosts above 200 edges | All of them unsupported |',
             '|---|---|---|---|---|']
    for name, d in table().items():
        un = '; '.join(f"`{r['task_id']}` ({r['edges']}) {r['reason']}" for r in d['unsupported']) or 'none'
        over = ', '.join(f'{k}: {v}' for k, v in d['confirm_hosts_over_bound'].items()) or 'none'
        lines.append(f"| {name} | {d['tasks']} | {un} | {over} | {'yes' if d['every_over_bound_host_is_unsupported'] else 'no'} |")
    return '\n'.join(lines)


if __name__ == '__main__':
    print(markdown())
    print(json.dumps(table(), indent=1)[:3000])
