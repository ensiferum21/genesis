#!/usr/bin/env python3
"""F2: semantic checks of the transcribed Brankov-Hansen-Stevanovic bounds (engineering; not a study).

    taskset -c 1 python3 scripts/f2_bhs_transcription.py evidence/bhs_transcription_f2

Why. The sealed set (`genesis.conjecture.sealed`) is transcribed from later papers through a page-to-text tool,
because the 2006 text is not reachable here. A transcription error could turn a proved bound into a false one (and
then any study using it would be INVALID) or a refuted one into a true one. Textual agreement of two sources is the
sealing rule; these checks are a second, independent line of defence, and they decide nothing about Genesis.

For every bound: it parses in `conjecture.expr`'s grammar; its value at the regular point d = m = r (r = 1..6),
reported against 2r (mu of every r-regular bipartite graph); over every connected graph on 2 to 7 vertices (the
networkx atlas: 995 graphs), every violation of mu <= max f in floating point, each re-checked by the exact
certificate of `conjecture.verify` (a rational Rayleigh vector). Where a bound is undefined at some vertex or edge
(a negative radicand), the domain never takes the graph as a counterexample (conservative); the lenient reading
(undefined terms ignored in the maximum) is reported as a diagnostic. Expected: no exact violation of a proved or open
bound; for refuted bounds, a small exact counterexample where one exists (Taieb et al. report the path on 3
vertices for 48, 57 and 61). Data: only graphs this script enumerates; no study data.
"""
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from genesis.conjecture import expr as E  # noqa: E402
from genesis.conjecture import graphs as Gr  # noqa: E402
from genesis.conjecture import sealed as SD  # noqa: E402
from genesis.conjecture import verify as V  # noqa: E402

TOL = 1e-9


def atlas():
    import networkx as nx
    out = []
    for g in nx.graph_atlas_g():
        if g.number_of_nodes() >= 2 and nx.is_connected(g):
            out.append(Gr.normalise(g.number_of_nodes(), list(g.edges())))
    return out


def regular_values(ast, kind):
    vals = []
    for r in range(1, 7):
        env = {'d': r, 'm': r} if kind == 'vertex' else {'di': r, 'dj': r, 'mi': r, 'mj': r}
        v = E.evaluate(ast, env)
        vals.append(None if v is None else round(v / (2 * r), 12))
    return vals                                   # value / 2r


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    out = Path(argv[0])
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    graphs = atlas()
    spectra = {g: Gr.laplacian_top(*g) for g in graphs}
    rows = {}
    for k, (formula, tier, sources, note) in sorted(SD.BOUNDS.items()):
        kind, st = SD.kind(k), SD.status(k)
        ast = E.parse(formula, kind)
        float_viol, exact_viol, undefined, first, lenient = 0, 0, 0, None, 0
        for g in graphs:
            f = Gr.bound_value(ast, kind, *g)
            mu, vec = spectra[g]
            if f is None:
                undefined += 1
                vals = [v for v in (E.evaluate(ast, e) for e in Gr.envs(*g, kind)) if v is not None]
                if vals and mu > max(vals) + TOL:         # the lenient reading: undefined terms ignored
                    lenient += 1
                continue
            if mu > f + TOL:
                float_viol += 1
                cert = V.check(formula, kind, g[0], g[1], Gr.rational_vector(vec))
                if cert['verdict'] == 'REFUTED':
                    exact_viol += 1
                    if first is None:
                        first = {'graph6': Gr.graph6(*g), 'n': g[0], 'm': len(g[1]), 'mu': mu, 'bound': f,
                                 'certificate': cert}
        reg = regular_values(ast, kind)
        rows[k] = {'formula': E.render(ast), 'text': formula, 'kind': kind, 'tier': tier, 'sources': list(sources),
                   'note': note, 'status': st, 'regular_ratio': reg,
                   'tight_regular': all(x is not None and abs(x - 1) < 1e-9 for x in reg),
                   'graphs': len(graphs), 'undefined': undefined, 'float_violations': float_viol,
                   'exact_violations': exact_viol, 'smallest_exact_counterexample': first,
                   'lenient_violations_where_undefined': lenient}
    alarms = [k for k, r in rows.items() if r['status'] in ('proved', 'open') and r['exact_violations']]
    lenient_alarms = [k for k, r in rows.items() if r['status'] in ('proved', 'open')
                      and r['lenient_violations_where_undefined']]
    summary = {'schema': 'genesis-f2-bhs-transcription-v1', 'graphs': len(graphs), 'max_n': 7,
               'alarms_proved_or_open_violated': alarms,
               'lenient_reading_proved_or_open_violated': lenient_alarms,
               'tiers': {t: sorted(k for k, r in rows.items() if r['tier'] == t) for t in ('A1', 'A2', 'B', 'X')},
               'not_tight_regular': sorted(k for k, r in rows.items() if not r['tight_regular']),
               'refuted_with_small_counterexample': sorted(k for k, r in rows.items()
                                                            if r['status'].startswith('refuted')
                                                            and r['exact_violations']),
               'seconds': round(time.time() - t0, 1), 'rows': rows}
    (out / 'report.json').write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n')
    print(json.dumps({k: v for k, v in summary.items() if k != 'rows'}, indent=1))
    return 0 if not alarms else 1


if __name__ == '__main__':
    sys.exit(main())
