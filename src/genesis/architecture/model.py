"""The architecture model (`docs/OMEGA_ARCHITECTURE_INVENTION.md` §3; ARA-1): what the system can actually do, from
executed probes, and what it has measured, from recorded verdicts. Rebuilt from scratch on each call, so it cannot
drift from the code.

* **Capabilities**: every operator of the graph library is probed on a small fixture (a view over the probe graphs
  with a deterministic objective), and its postcondition checked; status OBSERVED_OK, FAILED (with the violation)
  or UNPROBED. A capability whose probe fails is FAILED even though its name is registered (a test plants a broken
  implementation through `impl`).
* **Evidence**: every finished direction of `research_queue.json` with its outcome, grouped by research line; a
  **failure pattern** is a run of negative outcomes within a line, and lines the queue marked stagnant.
* **Assumptions**: the registry of `assumptions`.
"""
import json
from pathlib import Path

from ..senses import graph as SG
from . import assumptions as AS
from . import graph as G
from . import policies as PO
from . import rewrite as R

ROOT = Path(__file__).resolve().parents[3]


class FixtureView:
    """Probe graphs with a deterministic objective: option 1 is best above the median mean degree, option 0 below,
    option 2 is worth half everywhere; no noise."""

    def __init__(self):
        gs = R.probes()
        self._g = {'dev_a': gs, 'dev_b': gs}
        d = [SG.evaluate(['mean_n', 'deg'], g) for g in gs]
        cut = sorted(d)[len(d) // 2]
        self._side = [int(x > cut) for x in d]
        self.K, self.units, self.budget = 3, 0, 500.0

    def graphs(self, split):
        return self._g[split]

    def size(self, split):
        return len(self._g[split])

    def evaluate(self, split, i, c, r):
        self.units += 1
        return 0.5 if c == 2 else float(c == self._side[i])


def _fixture_ag(policy='threshold', search='exhaustive', evaluator='paired', sense=('mean_n', 'deg')):
    pp = {'n_cuts': 1} if policy == 'threshold' else ({'k': 3} if policy == 'knn' else {})
    nodes = {'s1': G.node('Sense', 'expr', {'expr': list(sense)}), 's2': G.node('Sense', 'expr', {'expr': 'n'}),
             'feat': G.node('Features', 'stack'), 'pol': G.node('Policy', policy, pp),
             'ev': G.node('Evaluator', evaluator, {'repeats': 1}), 'search': G.node('Search', search, {'steps': 40}),
             'out': G.node('Output', 'reattempt', kernel=True)}
    edges = [['s1', 'feat', 'senses'], ['s2', 'feat', 'senses'], ['feat', 'search', 'features'],
             ['pol', 'search', 'family'], ['ev', 'search', 'scheme'], ['search', 'out', 'policy']]
    return G.make(nodes, edges, 500.0, {'search': 0.9})


def _value(policy, view):
    ch = G.choose(policy, view.graphs('dev_a'))
    if any(c not in range(view.K) for c in ch):
        return None
    return sum(view.evaluate('dev_a', i, c, 0) for i, c in enumerate(ch)) / len(ch)


def probe(role, op, impl=None):
    """(status, violation) of one operator on the fixture. `impl` may replace library functions (tests)."""
    impl = impl or {}
    apply_ = impl.get('apply', PO.apply)
    view = FixtureView()
    try:
        if role == 'Sense':
            vals = G.column(['mean_n', 'deg'] if op == 'expr' else ['sub_s', ['mean_n', 'deg'], 'n'], view.graphs('dev_a'))
            ok = len(vals) == view.size('dev_a') and all(v == v for v in vals)
            return ('OBSERVED_OK', None) if ok else ('FAILED', 'non-finite or missing values')
        if role == 'Features' or role == 'Output':
            r = G.execute(_fixture_ag(), view)
            ok = r['policy']['senses'] == [['mean_n', 'deg'], 'n']
            return ('OBSERVED_OK', None) if ok else ('FAILED', 'features out of order')
        if role == 'Policy':
            r = G.execute(_fixture_ag(policy=op), view)
            ch = apply_(op, r['policy']['params'], [[SG.evaluate(e, g) for e in r['policy']['senses']]
                                                   for g in view.graphs('dev_a')]) if r['policy']['params'] else None
            if ch is None or any(c not in range(view.K) for c in ch):
                return 'FAILED', 'a choice outside the option set'
            v = sum(view.evaluate('dev_a', i, c, 0) for i, c in enumerate(ch)) / len(ch)
            return ('OBSERVED_OK', None) if v >= 0.5 - 1e-9 else ('FAILED', f'worse than the best single option ({v})')
        if role == 'Evaluator':
            r = G.execute(_fixture_ag(evaluator=op), view)
            v = _value(r['policy'], view)
            return ('OBSERVED_OK', None) if v is not None and v >= 0.5 - 1e-9 else ('FAILED', 'search misled')
        if role == 'Search':
            r = G.execute(_fixture_ag(search=op), view)
            v = _value(r['policy'], view)
            return ('OBSERVED_OK', None) if v is not None and v >= 0.5 - 1e-9 else ('FAILED', 'below its start')
    except Exception as e:                 # a probe that raises is a failed capability, recorded with the reason
        return 'FAILED', f'{type(e).__name__}: {e}'
    return 'UNPROBED', None


def capabilities(lib=G.LIB, impl=None):
    return {f'{role}.{op}': dict(zip(('status', 'violation'), probe(role, op, impl)))
            for role in sorted(lib) for op in sorted(lib[role])}


def evidence(root=ROOT):
    q = json.loads((Path(root) / 'research_queue.json').read_text())
    lines = {}
    for name, ln in q['lines'].items():
        outs = ln.get('outcomes', [])
        run, worst = 0, 0
        for _, _, pos in outs:
            run = 0 if pos else run + 1
            worst = max(worst, run)
        lines[name] = {'outcomes': [[i, o[:120], p] for i, o, p in outs], 'negative_run': run,
                       'longest_negative_run': worst, 'stagnant': ln.get('stagnant', False),
                       'diagnosis': ln.get('diagnosis')}
    patterns = [{'line': k, 'negative_run': v['negative_run'], 'stagnant': v['stagnant']}
                for k, v in sorted(lines.items()) if v['negative_run'] >= 2 or v['stagnant']]
    return {'lines': lines, 'failure_patterns': patterns}


def build(root=ROOT, ag=None, impl=None):
    return {'schema': 'genesis-architecture-model-v1', 'library': G.library_version(),
            'capabilities': capabilities(impl=impl), 'evidence': evidence(root), 'assumptions': AS.registry(ag)}


__all__ = ['FixtureView', 'probe', 'capabilities', 'evidence', 'build']
