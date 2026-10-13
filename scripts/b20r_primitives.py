#!/usr/bin/env python3
"""W22 DEV comparison: the builder's starting derived primitives under the committed VERDICT_RULE.

    b20r_primitives.py OUT_DIR

Conformance hosts: every graph on 4 vertices (64) plus DEV hosts (seed 2026101301). Comparison hosts:
fresh DEV hosts (seed 2026101302) from the same families, never used for conformance. The rule
(primitives.VERDICT_RULE) was committed with the module before this script ran. CPU timings are this
host's; the verdicts are design diagnostics for the representation language, not research results.
There is no DEV trace corpus of MRDL expressions yet, so proposal by trace mining is not exercised
here (it is tested on a fixture).
"""
from itertools import combinations, product
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from genesis import primitives as P  # noqa: E402
from genesis.domains import ADAPTERS  # noqa: E402
from genesis.models import GraphTask  # noqa: E402

FAMILIES = [('c4_host_v2', {'n': 6, 'p': 0.5}), ('c4_host_v2', {'n': 10, 'p': 0.4}), ('c4_host_v2', {'n': 24, 'p': 0.3}),
            ('c4_host_v2', {'n': 40, 'p': 0.3}), ('triangle_free_host_v1', {'n': 8, 'p': 0.5}),
            ('triangle_free_host_v1', {'n': 20, 'p': 0.35}), ('triangle_free_host_v1', {'n': 40, 'p': 0.3})]


def dev_hosts(seed, per=4):
    out = []
    for i, (dom, params) in enumerate(FAMILIES):
        ts, _, _ = ADAPTERS[dom].generate(seed + 10 * i, per, 'DEV', 'erdos', params)
        out += ts
    return out


def small_hosts():
    pairs = list(combinations(range(4), 2))
    return [GraphTask(task_id=f'all4-{i:02}', domain='c4_host_v2', n=4, edges=tuple(p for p, b in zip(pairs, bits) if b),
                      family='all-graphs-n4') for i, bits in enumerate(product((0, 1), repeat=len(pairs)))]


def main(argv=None):
    out = Path((argv or sys.argv[1:])[0])
    out.mkdir(parents=True, exist_ok=False)
    reg = P.starting_registry()
    conf_hosts = small_hosts() + dev_hosts(2026101301)
    fresh = dev_hosts(2026101302)
    seen = {(t.n, t.edges) for t in conf_hosts}
    fresh = [t for t in fresh if (t.n, t.edges) not in seen]
    summary = {'schema': 'genesis-primitive-comparison-v1', 'registry': reg.identity(),
               'cognitive_kernel': P.cognitive_kernel(reg), 'rule': P.VERDICT_RULE,
               'conformance_hosts': len(conf_hosts), 'fresh_hosts': len(fresh), 'primitives': {},
               'label': 'DEV design diagnostic; builder-written primitives; host-dependent CPU timings'}
    conf_all, cmp_all = {}, {}
    for name in reg.contracts:
        conf = P.conformance(name, reg, conf_hosts)
        cmp_ = P.compare(name, reg, conf, fresh)
        conf_all[name], cmp_all[name] = conf, cmp_
        summary['primitives'][name] = {
            'conformance': conf['verdict'], 'conformance_beyond_language_bounds': conf['beyond_language_bounds'],
            'verdict': cmp_['verdict'], 'incumbent_cpu_ns': cmp_['incumbent_cpu_ns'],
            'native_cpu_ns_with_conformance': cmp_['native_cpu_ns_with_conformance'],
            'fresh_not_expandable': sum(1 for r in cmp_['rows'] if r['reference_error'])}
        print(name, summary['primitives'][name], flush=True)
    (out / 'registry.json').write_text(json.dumps(reg.record(), indent=1, sort_keys=True) + '\n')
    (out / 'conformance.json').write_text(json.dumps(conf_all, indent=1, sort_keys=True) + '\n')
    (out / 'comparison.json').write_text(json.dumps(cmp_all, indent=1, sort_keys=True) + '\n')
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
