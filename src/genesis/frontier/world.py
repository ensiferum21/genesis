"""The planted world: the Frontier's calibration domain (KERNEL SIDE; F1, `docs/OMEGA_FRONTIER.md` §4.7). It is to
the Frontier what the Limitation Zoo is to ARA: every hidden curve, attractor and successor is a key only this
module holds, and nothing measured in it is evidence about real problems.

**Problems** have public statements (random tokens) and opaque ids. Each problem's grammar of approaches is a set of
representations, a set of methods and one parameter `p` with three values. Each (problem, representation, method,
p) has a hidden curve

    f(t) = C * (1 - exp(-(t / tau)^k))        (true quality of the branch's incumbent after compute t)

of a planted type:

| type | C | tau | k |
|---|---|---|---|
| dead | 0-0.05 | any | 1 |
| decoy | 0.20-0.35 | 5-15 | 1 (an early rise to a low plateau: the B20_R148 trap) |
| vein | 0.45-0.75 | 50-200 | 1 |
| slow | 0.75-1.0 | 0.25-0.6 of the world's horizon | 2.5 (flat early) |
| recombination vein | 0.9-1.0 for ONE (representation, method) pair whose parts are dead or decoys elsewhere | 80-200 | 1 |

`p` scales C by 0.9, 1.0 or 1.1. Observations are f(t) + N(0, sigma). A step returns observations and artifacts:
with probability rising with f/C_max, an artifact from one of the problem's hidden attractors (true clusters,
reached by every representation with C > 0.3), otherwise a spurious one (unique). `verify(problem, artifact)` returns
the artifact's true value (the curve at its creation), noise free.

**Abstraction** (`abstract(problem, fingerprint)`): when the engine asks about a TRUE attractor, the world unlocks a
new representation for that problem (`rep*<k>`) whose curves are veins with C 1.05-1.2 times the problem's best
planted ceiling (the planted version of "discovering a useful new representation"); about a spurious cluster it
answers None. **Successors** (`successors(problem, artifact)`): an artifact of true value at least 0.5 on a problem
with a successor reveals it: a new problem whose best ceiling is 1.2-1.5 times its parent's (branching out pays), up
to depth 2. **Null world**: every C is 0, nothing can be abstracted, no successor exists.

Determinism: everything is a function of (world seed, problem, direction, branch seed, t), so a branch is resumable
from (direction, seed, t) alone, and two engines evaluating the same thing see the same numbers. An artifact carries
its origin and a token (a keyed hash of the origin): `verify` recomputes the true value from the origin and refuses
a forged token, so a resumed world needs no memory of past steps.
"""
import hashlib
import json
import math
import random

REPS = ('r0', 'r1', 'r2', 'r3')
METHODS = ('m0', 'm1', 'm2', 'm3')
P_VALUES = (0, 1, 2)
P_SCALE = (0.9, 1.0, 1.1)
TYPES = (('dead', 0.45), ('decoy', 0.25), ('vein', 0.17), ('slow', 0.13))


def _h(*parts):
    return int(hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()[:15], 16)


class PlantedWorld:
    def __init__(self, seed, problems=4, horizon=20000, sigma=0.02, null=False, successors=True, recomb=True):
        self.seed, self.horizon, self.sigma, self.null = seed, horizon, sigma, null
        rng = random.Random(_h('world', seed))
        self._problems = {}
        self._order = []
        for i in range(problems):
            self._add_problem(rng, depth=0, parent=None, recomb=recomb, allow_successor=successors)
        self.verify_calls = 0
        self.abstractions = {}

    # ------------------------------------------------------------------------------------------- the hidden world
    def _add_problem(self, rng, depth, parent, recomb, allow_successor, boost=1.0):
        pid = f'P{_h(self.seed, "pid", len(self._problems)) % 10 ** 8:08d}'
        statement = f'S{_h(self.seed, "statement", pid) % 10 ** 10:010d}'
        curves = {}
        for r in REPS:
            for m in METHODS:
                kind = rng.choices([t for t, _ in TYPES], [w for _, w in TYPES])[0]
                curves[(r, m)] = self._curve(rng, kind, boost)
        if recomb and not self.null and rng.random() < 0.75:
            r, m = rng.choice(REPS), rng.choice(METHODS)
            for rr in REPS:
                for mm in METHODS:
                    if (rr == r) != (mm == m):                     # the pair's parts are poor elsewhere
                        curves[(rr, mm)] = self._curve(rng, rng.choice(('dead', 'decoy')), boost)
            curves[(r, m)] = {'kind': 'recomb', 'C': rng.uniform(0.9, 1.0) * boost, 'tau': rng.uniform(80, 200),
                              'k': 1.0}
        if self.null:
            curves = {key: {'kind': 'dead', 'C': 0.0, 'tau': 50.0, 'k': 1.0} for key in curves}
        attractors = [f'A{_h(self.seed, pid, "attr", j) % 10 ** 9:09d}' for j in range(3)]
        self._problems[pid] = {'statement': statement, 'curves': curves, 'attractors': attractors, 'depth': depth,
                               'parent': parent, 'reps': list(REPS), 'successor': None, 'revealed': False,
                               'cmax': max(c['C'] for c in curves.values())}
        if allow_successor and not self.null and depth < 2 and rng.random() < 0.5:
            self._problems[pid]['successor_boost'] = rng.uniform(1.2, 1.5)
        self._order.append(pid)
        return pid

    def _curve(self, rng, kind, boost=1.0):
        if kind == 'dead':
            return {'kind': kind, 'C': rng.uniform(0, 0.05) * boost, 'tau': rng.uniform(20, 200), 'k': 1.0}
        if kind == 'decoy':
            return {'kind': kind, 'C': rng.uniform(0.2, 0.35) * boost, 'tau': rng.uniform(5, 15), 'k': 1.0}
        if kind == 'vein':
            return {'kind': kind, 'C': rng.uniform(0.45, 0.75) * boost, 'tau': rng.uniform(50, 200), 'k': 1.0}
        return {'kind': 'slow', 'C': rng.uniform(0.75, 1.0) * boost,
                'tau': rng.uniform(0.25, 0.6) * self.horizon / 8, 'k': 2.5}

    def _f(self, pid, direction, t):
        c = self._problems[pid]['curves'][(direction['representation'], direction['method'])]
        C = c['C'] * P_SCALE[direction['params'].get('p', 1)]
        return C * (1 - math.exp(-(max(t, 0.0) / c['tau']) ** c['k']))

    # ------------------------------------------------------------------------------------------- the public API
    def problems(self):
        """The problems posed so far (initial ones and revealed successors), as opaque ids."""
        return [p for p in self._order if self._problems[p]['parent'] is None or self._problems[p]['revealed']]

    def statement(self, pid):
        return self._problems[pid]['statement']

    def approaches(self, pid):
        return {'representation': list(self._problems[pid]['reps']), 'method': list(METHODS),
                'params': {'p': list(P_VALUES)}}

    def neighbours(self, pid):
        return [p for p in self.problems() if p != pid]

    def step(self, pid, direction, seed, t, quantum):
        """Advance a branch from compute t by `quantum`: (points [(t, y)], artifacts)."""
        rng = random.Random(_h(self.seed, pid, direction['representation'], direction['method'],
                               direction['params'], seed, round(t, 6)))
        prob = self._problems[pid]
        t1 = t + quantum
        f = self._f(pid, direction, t1)
        y = f + rng.gauss(0, self.sigma)
        c = prob['curves'][(direction['representation'], direction['method'])]
        if c['C'] > 0.3 and rng.random() < min(0.9, f / max(prob['cmax'], 1e-9)):
            j = REPS.index(direction['representation']) % len(prob['attractors']) \
                if direction['representation'] in REPS else 0
            fp = prob['attractors'][j]
        else:
            fp = f'X{rng.getrandbits(48):012x}'                     # spurious: never seen twice
        origin = {'representation': direction['representation'], 'method': direction['method'],
                  'params': dict(direction['params']), 'seed': seed, 't': t1}
        art = {'fingerprint': fp, 'signature': fp[:4], 'problem': pid, 'score': y, 'origin': origin,
               'token': self._token(pid, fp, origin)}
        return [(t1, y)], [art]

    def _token(self, pid, fp, origin):
        return f'{_h(self.seed, "token", pid, fp, origin):x}'

    def verify(self, pid, artifact):
        """KERNEL: the artifact's true value (noise free), or 0.0 for an unknown or foreign artifact."""
        self.verify_calls += 1
        if artifact.get('problem') != pid:
            return 0.0
        return self.verify_value(artifact)

    def abstract(self, pid, fingerprint):
        """A new representation if `fingerprint` is one of the problem's true attractors, else None."""
        prob = self._problems[pid]
        if self.null or fingerprint not in prob['attractors']:
            return None
        key = (pid, fingerprint)
        if key in self.abstractions:
            return self.abstractions[key]
        rng = random.Random(_h(self.seed, 'abstract', pid, fingerprint))
        name = f'rep*{len([k for k in self.abstractions if k[0] == pid])}'
        for m in METHODS:
            prob['curves'][(name, m)] = {'kind': 'invented', 'C': prob['cmax'] * rng.uniform(1.05, 1.2),
                                         'tau': rng.uniform(60, 180), 'k': 1.0}
        prob['reps'].append(name)
        self.abstractions[key] = name
        return name

    def successors(self, pid, artifact):
        prob = self._problems[pid]
        if 'successor_boost' not in prob or self.verify_value(artifact) < 0.5:
            return []
        if prob['successor'] is None:
            rng = random.Random(_h(self.seed, 'successor', pid))
            child = self._add_problem(rng, prob['depth'] + 1, pid, recomb=True, allow_successor=True,
                                      boost=prob['successor_boost'] * max(prob['cmax'], 0.5) / 0.75)
            prob['successor'] = child
        self._problems[prob['successor']]['revealed'] = True
        return [prob['successor']]

    def verify_value(self, artifact):
        """KERNEL: the true value of an artifact this world issued (0.0 for a forged or unknown one): the curve at its
        creation, recomputed from its origin, which the token authenticates."""
        o, pid = artifact.get('origin'), artifact.get('problem')
        if not o or pid not in self._problems or artifact.get('token') != self._token(pid, artifact.get('fingerprint'), o):
            return 0.0
        if (o['representation'], o['method']) not in self._problems[pid]['curves']:
            return 0.0
        return float(self._f(pid, o, o['t']))

    # ------------------------------------------------------------------------------------------- the judge's view
    def oracle(self, budget):
        """KERNEL: a reference value at `budget`: per initial problem, its best planted curve given an equal share of
        the budget (no successors, no abstraction): what a perfectly informed single choice would reach."""
        roots = [p for p in self._order if self._problems[p]['parent'] is None]
        share = budget / max(1, len(roots))
        total = 0.0
        for p in roots:
            best = 0.0
            for (r, m), c in self._problems[p]['curves'].items():
                if r not in REPS:
                    continue
                for v in P_VALUES:
                    best = max(best, self._f(p, {'representation': r, 'method': m, 'params': {'p': v}}, share))
            total += best
        return total

    def keys(self):
        """KERNEL: the hidden types, for analysis only."""
        return {p: {f'{r}|{m}': c['kind'] for (r, m), c in self._problems[p]['curves'].items()}
                for p in self._order}
