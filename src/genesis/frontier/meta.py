"""The engine adapting itself (research plane; F6, `docs/OMEGA_FRONTIER.md` §4.8).

The Frontier's own configuration is a research object. `MetaDomain` presents engine configurations as directions
over meta-tasks, so that the same Frontier can search them:
  * problems: meta-tasks by opaque id. A study (kernel side) poses each as a factory: `factory(run_key)` returns a
    fresh inner `Manifest` (a domain and its kernel verifier, at an inner budget the study fixes). The inner domain
    stays behind the manifest, as for any engine;
  * statement: 'meta: ' and the digest of the inner domain's public problem statements;
  * approaches: representation = the inner allocation policy (`allocate.POLICIES`), method 'run', and the policy's
    parameters on a grid (`GRID`);
  * step(task, d, seed, t, quantum): runs an inner Frontier with the configuration on a fresh manifest, `quantum`
    inner compute units further; the curve point is the inner engine's total verified value per initial problem.
    When it improved, the artifact carries the configuration, the inner run's key and its score. The kernel's meta
    verifier (the study's) answers from its own record of what the inner verifier confirmed for that run; the
    research plane never sees how;
  * abstract: None (no abstraction at this level yet); successors: none.
Inner engines are kept live and rebuilt by replay when a resumed outer engine asks for an earlier position (inner
runs are deterministic in their seed). The total compute of a meta-search is the sum of its inner compute
(`inner_compute`: an inner run may pass its quantum by the cost of the verifications in its last step), which a
study charges to whatever configuration it promotes (§4.8: promoted only by the kernel on held-out tasks, at matched
total compute with the meta-search counted).
"""
import hashlib
import json

from . import allocate as AL
from . import engine as EN

GRID = {'eps': [0.1, 0.25, 0.4], 'lam_lp': [0.0, 1.0, 3.0], 'lam_con': [0.0, 0.02, 0.1], 'k_imagine': [1, 8, 32],
        'patience_quanta': [2, 4, 8], 'stall': [20, 40, 80]}
DEFAULT = {'eps': 0.25, 'lam_lp': 1.0, 'lam_con': 0.02, 'k_imagine': 8, 'patience_quanta': 4, 'stall': 40}


def _digest(*parts):
    return hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()


def run_key(task, direction, seed):
    """The inner run's key: a function of the meta-task, the configuration and the branch seed only."""
    return _digest('meta-run', task, direction['representation'], direction['method'],
                   sorted(direction['params'].items()), seed)[:24]


class MetaDomain:
    def __init__(self, posed, policies=('frontier',), grid=None):
        self.posed = dict(posed)
        self.policies = tuple(p for p in policies if p in AL.POLICIES)
        self.grid = {k: list(v) for k, v in (grid or GRID).items()}
        self._runs = {}                                   # run key -> (inner engine, number of initial problems)
        self._statements = {}

    def problems(self):
        return sorted(self.posed)

    def statement(self, task):
        if task not in self._statements:
            m = self.posed[task]('statement')
            stmts = sorted(m.domain.statement(p) for p in m.domain.problems())
            self._statements[task] = 'meta: ' + _digest(stmts)[:32]
        return self._statements[task]

    def approaches(self, task):
        return {'representation': list(self.policies), 'method': ['run'], 'params': self.grid}

    def neighbours(self, task):
        return [p for p in self.problems() if p != task]

    def _inner(self, task, d, seed, t):
        key = run_key(task, d, seed)
        got = self._runs.get(key)
        if got is None or got[0].spent > t:
            m = self.posed[task](key)
            eng = EN.Frontier(m, d['representation'], seed=int(key[:12], 16), policy_params=dict(d['params']))
            got = (eng, max(1, len(m.domain.problems())))
            self._runs[key] = got
        eng, k = got
        self._advance(eng, t)
        return key, eng, k

    @staticmethod
    def _advance(eng, target):
        while eng.spent < target and eng.spent + eng.quantum <= eng.budget:
            if eng.run(max_steps=1) == 'done':
                break

    def step(self, task, d, seed, t, quantum):
        key, eng, k = self._inner(task, d, seed, t)
        before = eng.total() / k
        self._advance(eng, t + quantum)
        score = eng.total() / k
        pts = [(t + quantum, score)]
        if score <= before:
            return pts, []
        solved = sorted(p for p, v in eng.best_verified.items() if v >= 0.5)     # what the configuration reached
        art = {'problem': task, 'fingerprint': _digest('solved', solved)[:16], 'score': float(score),
               'run': key, 'config': {'policy': d['representation'], 'params': dict(d['params'])},
               'inner_spent': eng.spent}
        return pts, [art]

    def inner_compute(self):
        """The meta-search's true compute: what every inner run has spent (including its verifications), each run
        counted once however often it was replayed."""
        return sum(eng.spent for eng, _ in self._runs.values())

    def abstract(self, task, fingerprint):
        return None

    def successors(self, task, artifact):
        return []
