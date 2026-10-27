"""Statements about graph invariants as the Frontier sees them (research plane; the proving test's transfer family,
`docs/OMEGA_FRONTIER.md` §7b).

`InvariantDomain(posed)` is the conjecture domain (`domain.ConjectureDomain`) with a different objective, so that
the Frontier, its representations, its abstraction and its extracted procedures run on it unchanged:
  * problems: the posed statements by opaque id (`posed` is {id: text} in the language of `statement.py`; the
    statuses stay kernel side);
  * statement: 'invariant: <text>';
  * approaches: the same representations and methods, at sizes small enough for the exhaustive invariants
    (`DEFAULT_N`); a template abstracted here is searched only up to `max_n` (16) vertices;
  * step: one attack whose objective is `statement.Statement(text).score`, positive exactly when the statement is
    violated (exact verdict, float score). Artifacts are the conjecture domain's: fingerprint, signature, score,
    n, edges (the eigenvector there is unused here).
The kernel checks a claimed counterexample with its own transcription of the statement (`wowii.verifier`).
"""
from . import attack as AT
from . import domain as CD
from . import statement as ST

DEFAULT_N = (6, 8, 10, 12)
MAX_N = 16


class InvariantDomain(CD.ConjectureDomain):
    def __init__(self, posed, representations=('edges', 'tree', 'bounded', 'gamma'),
                 methods=('hill', 'anneal', 'evolution', 'gbfs', 'cem', 'nrpa'), n_values=DEFAULT_N, abstraction=True,
                 max_n=MAX_N):
        super().__init__(posed, representations, methods, n_values, abstraction)
        self.max_n = max_n
        self._objectives = {}

    def statement(self, pid):
        return 'invariant: ' + self.posed[pid]

    def objective(self, pid):
        if pid not in self._objectives:
            self._objectives[pid] = ST.Statement(self.posed[pid], max_n=self.max_n)
        return self._objectives[pid]

    def _runner(self, pid, d, seed, t):
        key = (pid, d['representation'], d['method'], d['params']['n'], seed)
        r = self._runners.get(key)
        if r is None or r.evals > t:
            rep = self._rep_for(d, max_n=self.max_n)
            r = AT.Runner(None, None, d['representation'], d['method'], d['params']['n'],
                          CD._h('attack', pid, d['representation'], d['method'], d['params']['n'], seed), rep=rep,
                          objective=self.objective(pid))
            self._runners[key] = r
        if r.evals < t:
            r.advance(int(t - r.evals))
        return r
