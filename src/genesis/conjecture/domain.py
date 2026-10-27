"""The conjecture domain as the Frontier sees it (research plane; F2, `docs/OMEGA_FRONTIER.md` §5, §8).

`ConjectureDomain(posed)` offers the public calls the Frontier's manifest allows (`frontier.manifest.PUBLIC`):
  * problems: the posed bounds, by opaque id (`posed` is {id: (formula, kind)}, from a study; the statuses stay
    kernel side);
  * statement: 'kind: formula' (public content: the engine orders and seeds problems by its digest);
  * approaches: representations x methods x n (the starting set has no quotient, partition, blow-up or symmetry
    concept, §7b);
  * step: advances one attack (`attack.Runner`) by `quantum` evaluations. The curve point is the best score so
    far (exact, monotone). The artifact is the step's best graph when it improved: its fingerprint (a
    Weisfeiler-Leman hash), its signature (the sorted degree sequence), its score, and a certificate candidate
    (n, edges, a rational vector) for the kernel to check;
  * abstract and successors: none yet. Genesis's abstraction over Gamma programs comes with the library learner's
    adapter, and its own conjectures in F5.
Runners are cached and rebuilt by replay when a resumed engine asks for a position the cache does not hold (attacks
are deterministic in their seed).
"""
import hashlib

from . import attack as AT

DEFAULT_N = (8, 12, 16, 20, 28)


def _h(*parts):
    return int(hashlib.sha256(repr(parts).encode()).hexdigest()[:12], 16)


class ConjectureDomain:
    def __init__(self, posed, representations=('edges', 'tree', 'bounded', 'gamma'),
                 methods=('hill', 'anneal', 'evolution', 'gbfs', 'cem', 'nrpa'), n_values=DEFAULT_N):
        self.posed = dict(posed)
        self.representations, self.methods, self.n_values = tuple(representations), tuple(methods), tuple(n_values)
        self._runners = {}

    def problems(self):
        return sorted(self.posed)

    def statement(self, pid):
        formula, kind = self.posed[pid]
        return f'{kind}: {formula}'

    def approaches(self, pid):
        return {'representation': list(self.representations), 'method': list(self.methods),
                'params': {'n': list(self.n_values)}}

    def neighbours(self, pid):
        return [p for p in self.problems() if p != pid]

    def _runner(self, pid, d, seed, t):
        key = (pid, d['representation'], d['method'], d['params']['n'], seed)
        r = self._runners.get(key)
        if r is None or r.evals > t:
            formula, kind = self.posed[pid]
            r = AT.Runner(formula, kind, d['representation'], d['method'], d['params']['n'],
                          _h('attack', pid, d['representation'], d['method'], d['params']['n'], seed))
            self._runners[key] = r
        if r.evals < t:
            r.advance(int(t - r.evals))                       # replay to the requested position
        return r

    def step(self, pid, d, seed, t, quantum):
        r = self._runner(pid, d, seed, t)
        improved = r.advance(int(quantum))
        pts = [(t + quantum, r.best if r.best > -1e300 else -1.0)]
        if not improved or r.best_A is None:
            return pts, []
        import warnings
        import networkx as nx
        A = r.best_A
        G = nx.from_numpy_array(A)
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')                  # networkx 3.5 changed unlabelled hashes; ours are new
            fp = nx.weisfeiler_lehman_graph_hash(G, iterations=4)
        n, edges, x = AT.certificate(A)
        art = {'problem': pid, 'fingerprint': fp,
               'signature': ','.join(map(str, sorted(int(v) for v in A.sum(axis=1)))), 'score': float(r.best),
               'n': n, 'edges': [list(e) for e in edges], 'x': [str(v) for v in x]}
        return pts, [art]

    def abstract(self, pid, fingerprint):
        return None

    def successors(self, pid, artifact):
        return []

