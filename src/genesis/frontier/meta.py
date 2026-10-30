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
`SuiteMetaDomain` is the repair of B20R163-META (`docs/BLOCKING_DEFECTS.md`): one meta-task over several training
worlds, the run's spend split evenly among them, and nothing returned once every member has spent its inner budget.
A study pairs it with an outer policy that compares branches at equal spend ('halving').
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


class SuiteMetaDomain(MetaDomain):
    """Configurations compared on several training worlds at once (the repair of B20R163-META).

    The study poses meta-tasks whose factories return a list of fresh inner Manifests, one per training world:
    `factory(run_key)` -> [Manifest, ...], the same worlds for every configuration. An inner run is one engine per
    member, each with its own seed (from the run key and the member's index). `step(task, d, seed, t, quantum)`
    advances every member to (t + quantum) / n_members inner units, so a branch's t is its run's total inner spend;
    the curve point is the mean over members of each engine's verified total per initial problem, and the artifact
    carries it as its score with the members' spends. Branches at the same t are therefore compared at the same
    spend on the same worlds. Once every member has spent its inner budget, step returns no point and no artifact
    (the branch's t stops growing; the outer engine still charges its quantum, so a study sizes the outer budget to
    the outer policy's schedule). `quantum` must be a multiple of the number of members.

    In `MetaDomain` (F6) a finished inner run kept returning points, and the best artifact compared configurations
    at whatever spends the outer engine had given them; the outer Frontier policy gave its first branch most of the
    compute, so the first configuration opened was promoted (B20R163-META)."""

    def _inner(self, task, d, seed, t):
        key = run_key(task, d, seed)
        got = self._runs.get(key)
        if got is None or self._pos.get(key, 0.0) > t:         # a resumed outer engine asks for an earlier position
            ms = self.posed[task](key)
            engines = [EN.Frontier(m, d['representation'], seed=int(_digest(key, i)[:12], 16),
                                   policy_params=dict(d['params'])) for i, m in enumerate(ms)]
            got = (engines, [max(1, len(m.domain.problems())) for m in ms])
            self._runs[key] = got
        engines, ks = got
        for eng in engines:
            self._advance(eng, t / len(engines))
        self._pos[key] = t
        return key, engines, ks

    def __init__(self, posed, policies=('frontier',), grid=None):
        super().__init__(posed, policies=policies, grid=grid)
        self._pos = {}                                    # run key -> the outer position it was last advanced to

    @staticmethod
    def _score(engines, ks):
        return sum(eng.total() / k for eng, k in zip(engines, ks)) / len(engines)

    def statement(self, task):
        if task not in self._statements:
            ms = self.posed[task]('statement')
            stmts = sorted(sorted(m.domain.statement(p) for p in m.domain.problems()) for m in ms)
            self._statements[task] = 'meta: ' + _digest(stmts)[:32]
        return self._statements[task]

    def step(self, task, d, seed, t, quantum):
        key, engines, ks = self._inner(task, d, seed, t)
        if quantum % len(engines):
            raise ValueError('the outer quantum must be a multiple of the number of members')
        if all(eng.spent + eng.quantum > eng.budget for eng in engines):
            return [], []
        before = self._score(engines, ks)
        for eng in engines:
            self._advance(eng, (t + quantum) / len(engines))
        self._pos[key] = t + quantum
        score = self._score(engines, ks)
        pts = [(t + quantum, score)]
        if score <= before:
            return pts, []
        solved = sorted((i, p) for i, eng in enumerate(engines) for p, v in eng.best_verified.items() if v >= 0.5)
        art = {'problem': task, 'fingerprint': _digest('solved', solved)[:16], 'score': float(score), 'run': key,
               'config': {'policy': d['representation'], 'params': dict(d['params'])},
               'inner_spent': [eng.spent for eng in engines]}
        return pts, [art]

    def inner_compute(self):
        return sum(eng.spent for engines, _ in self._runs.values() for eng in engines)


def halving_bracket(pool, eta, rung):
    """One bracket of `allocate.HalvingPolicy(pool, eta, rung)`: its stages [(live branches, quanta each)], the
    quanta it spends in all, and the quanta its final survivor has had. The engine advances a branch once when it
    opens it, so the first stage gives each branch rung + 1 quanta. A study sizes the outer budget to one bracket,
    so that no outer quantum is spent on a second."""
    stages, n, r = [(pool, rung + 1)], max(1, pool // eta), rung * eta
    while pool > 1:
        stages.append((n, r))
        if n == 1:
            break
        n, r = max(1, n // eta), r * eta
    return {'stages': stages, 'quanta': sum(n * r for n, r in stages), 'final': sum(r for _, r in stages)}
