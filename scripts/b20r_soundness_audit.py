#!/usr/bin/env python3
"""CRPD-1 audit: the soundness mode of every existing Genesis abstraction artifact.

    b20r_soundness_audit.py OUT_JSON

Derives modes from recorded, checked evidence only (no prover, no producer):
  * B18 representation decoders, per domain (invention_b18/representations/package.json);
  * B18 world transports (invention_b18/worlds/package.json);
  * B20_R1 joint-certification bounds, from a checker-only replay of every bundle
    (obstruction_custody_b20r/);
  * learned or tuned guidance (research policies, macros, curricula, retrieval, market
    estimates), which is HEURISTIC by construction.
The output says what each artifact licenses (lift a positive result, refute, prune, bound,
or only order search). It does not promote anything.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from genesis.invention import soundness as S  # noqa: E402
from genesis.verification import certificates as CB  # noqa: E402


def licensed(rec):
    return sorted(u for u in S.USES if not S.problems(rec, u))


def main(argv=None):
    out_path = Path((argv or sys.argv[1:])[0])
    ev = ROOT / 'evidence'
    rows = []
    reps = json.loads((ev / 'invention_b18' / 'representations' / 'package.json').read_text())
    for (rid, dom), rec in sorted(S.representation_modes(reps).items()):
        rows.append({'artifact': f'representation {rid}', 'scope': dom, 'mode': rec['established'],
                     'requested': rec['requested'], 'obligations': rec['obligations'], 'licenses': licensed(rec),
                     'source': 'evidence/invention_b18/representations/package.json'})
    worlds = json.loads((ev / 'invention_b18' / 'worlds' / 'package.json').read_text())['verdict']
    for d in worlds['transports']:
        rec = S.transport_mode(d, worlds['worlds'])
        rows.append({'artifact': f'transport {d["from"]} -> {d["to"]}', 'scope': rec['scope'],
                     'mode': rec['established'], 'requested': rec['requested'], 'obligations': rec['obligations'],
                     'b18_verdict': d['verdict'], 'licenses': licensed(rec),
                     'source': 'evidence/invention_b18/worlds/package.json'})
    d = ev / 'obstruction_custody_b20r'
    optima = 0
    with CB.checker_only():
        for b in sorted((d / 'bundles').glob('*.json')):
            bundle = json.loads(b.read_bytes())
            r = CB.replay(bundle, lambda h: (d / 'objects' / h).read_bytes())
            lo, up = S.certificate_bound_modes(bundle, r)
            ok = not S.optimum_problems(lo, up)
            optima += ok
            rows.append({'artifact': f'certificate bundle {b.stem[:16]}', 'scope': bundle['problem']['task']['task_id'],
                         'mode': 'BOUND', 'lower': lo['established'], 'upper': up['established'],
                         'upper_method': bundle['upper']['method'], 'optimum_licensed': ok,
                         'source': 'evidence/obstruction_custody_b20r'})
    for comp in S.HEURISTIC_COMPONENTS:
        rec = S.heuristic(comp)
        rows.append({'artifact': comp, 'scope': 'search guidance', 'mode': rec['established'],
                     'licenses': licensed(rec), 'source': 'by construction'})
    counts = {}
    for r in rows:
        counts[r['mode']] = counts.get(r['mode'], 0) + 1
    report = {'schema': 'genesis-soundness-audit-v1', 'module': 'genesis.invention.soundness',
              'counts': dict(sorted(counts.items())), 'optima_licensed': optima, 'rows': rows,
              'note': 'modes derived from recorded checked evidence; HEURISTIC and REJECTED never admit a proof'}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=1, sort_keys=True) + '\n')
    print(json.dumps({'counts': report['counts'], 'optima_licensed': optima}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
