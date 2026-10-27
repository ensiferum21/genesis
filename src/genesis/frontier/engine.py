"""The Frontier engine: the divergent-convergent research cycle (research plane; F1, `docs/OMEGA_FRONTIER.md` §4.6).

`Frontier(manifest, policy, seed, params, abstraction, branch_out).run(max_steps)` spends the manifest's budget:
  1. the policy chooses: advance a branch, or open a direction (`allocate.py`);
  2. a step: `domain.step(problem, direction, seed, t, quantum)` gives observations and artifacts (cost: quantum);
  3. verification: an artifact whose internal score beats the best verified value on its problem by `margin` is
     sent to the kernel through `manifest.verify` (cost: verify_cost each); the engine never sees how;
  4. record: the best verified value per problem; a verified improvement asks the domain for successors (new
     problems a result reveals: branching out);
  5. convergence: artifacts are clustered (`converge.Clusters`); a cluster reached by two independent approaches is
     abstracted (`domain.abstract`) when abstraction is on, and an invented representation enters the grammar;
     a policy may also ask the domain to derive a representation from a leading branch's (`domain.derive`, an
     operator acting on the representation's own operations), which enters the grammar the same way;
  6. repeat until the budget is spent.
Problems are ordered by the digest of their public statement, and every random draw comes from the engine's seeded
generator, so renaming problems leaves every decision unchanged (the relabelling audit, §3.3). The state is saved as
JSON (`save`, `load`); a resumed engine replays the domain's mutations (abstractions, revealed successors) in order
and reaches the same result as an uninterrupted one. Every decision is logged.
"""
import hashlib
import json
from pathlib import Path
import random

from . import allocate as AL
from . import converge as CG
from . import direction as D

ENGINE_DEFAULTS = {'margin': 0.0}


def _digest(*parts):
    return hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()


class Frontier:
    def __init__(self, manifest, policy='frontier', seed=0, params=None, abstraction=None, branch_out=None,
                 policy_params=None):
        self.m = manifest
        self.domain = manifest.domain
        self.budget, self.quantum, self.verify_cost = manifest.budget, manifest.quantum, manifest.verify_cost
        self.params = dict(ENGINE_DEFAULTS, **(params or {}))
        self.policy_name = policy
        self.policy = AL.POLICIES[policy](policy_params)
        self.abstraction = (policy == 'frontier') if abstraction is None else abstraction
        self.branch_out = (policy == 'frontier') if branch_out is None else branch_out
        self.seed = seed
        self.rng = random.Random(_digest('frontier', seed))
        self.spent, self.step_count, self.verify_calls = 0, 0, 0
        self.branches, self.archive, self.tried = {}, [], set()
        self.best_verified, self.best_artifact = {}, {}
        self.clusters = CG.Clusters()
        self.abstracted, self.invented = [], []          # [(problem, fingerprint)], [(problem, representation)]
        self.revealed = []                               # [(problem, artifact)] in order
        self.known = set(self.domain.problems())
        self.events = []
        self.curve = []                                  # [(spent, total verified value)]

    # ------------------------------------------------------------------------------------------------ helpers
    def seed_for(self, *parts):
        return int(_digest(self.seed, *parts)[:12], 16)

    def log(self, kind, **kw):
        self.events.append(dict(kw, kind=kind, step=self.step_count, spent=self.spent))

    def problem_order(self):
        if not self.branch_out:
            ps = [p for p in self.domain.problems() if p in self.initial]
        else:
            ps = list(self.domain.problems())
        return sorted(ps, key=lambda p: _digest(self.domain.statement(p)))

    def grammar(self, problem):
        return self.domain.approaches(problem)

    def best_branch(self, problem):
        brs = [b for b in self.branches.values() if b['direction']['problem'] == problem and b['ys']]
        return max(brs, key=lambda b: (AL.level(b), -b['id'])) if brs else None

    def best_branch_overall(self):
        brs = [b for b in self.branches.values() if b['ys']]
        return max(brs, key=lambda b: (AL.level(b), -b['id'])) if brs else None

    def total(self):
        return sum(self.best_verified.values())

    # ------------------------------------------------------------------------------------------------ actions
    def open(self, d):
        bid = len(self.branches)
        self.branches[bid] = {'id': bid, 'direction': d, 'seed': self.seed_for('branch', bid), 't': 0.0, 'ts': [],
                              'ys': [], 'paused': False}
        self.archive.append(d)
        self.tried.add(D.descriptor(d))
        self.log('open', branch=bid, op=d['op'], direction=D.descriptor(d))
        if hasattr(self.policy, 'opened'):
            self.policy.opened(bid)
        return bid

    def derive(self, problem, representation, seed=None):
        """Ask the domain for a representation derived from `representation` (with the engine's next seed, or a
        procedure's recorded one); logged and replayed on resume."""
        if seed is None:
            seed = self.seed_for('derive', sum(1 for e in self.events if e['kind'] == 'derive'))
        new = self.domain.derive(problem, representation, seed)
        self.log('derive', problem=problem, representation=representation, seed=seed, result=new)
        if new is not None and (problem, new) not in self.invented:
            self.invented.append((problem, new))
        return new

    def advance(self, bid):
        b = self.branches[bid]
        d = b['direction']
        pts, arts = self.domain.step(d['problem'], d, b['seed'], b['t'], self.quantum)
        self.spent += self.quantum
        for t, y in pts:
            b['t'], b['ts'], b['ys'] = t, b['ts'] + [t], b['ys'] + [y]
        improved = False
        for a in arts:
            p = a['problem']
            con = self.clusters.add(p, a['fingerprint'], d, bid)
            if a['score'] > self.best_verified.get(p, 0.0) + self.params['margin'] \
                    and self.spent + self.verify_cost <= self.budget:
                self.spent += self.verify_cost
                self.verify_calls += 1
                v = float(self.m.verify(p, a))
                if v > self.best_verified.get(p, 0.0):
                    self.best_verified[p] = v
                    self.best_artifact[p] = a
                    improved = True
                    self.log('verified', branch=bid, problem=p, value=round(v, 9))
                    if self.branch_out:
                        for q in self.domain.successors(p, a):
                            if q not in self.known:
                                self.known.add(q)
                                self.revealed.append((p, a))
                                self.log('revealed', problem=q, by=p)
            if self.abstraction and con >= 2 and (p, a['fingerprint']) not in self.abstracted:
                self.abstracted.append((p, a['fingerprint']))
                rep = self.domain.abstract(p, a['fingerprint'])
                self.log('abstract', problem=p, fingerprint=a['fingerprint'], result=rep)
                if rep is not None:
                    self.invented.append((p, rep))
        return improved

    # ------------------------------------------------------------------------------------------------ the cycle
    def run(self, max_steps=None):
        """Spend the budget; 'done', or 'paused' after max_steps steps (resume with `save`/`load`)."""
        if not hasattr(self, 'initial'):
            self.initial = set(self.domain.problems())
        n = 0
        while self.spent + self.quantum <= self.budget:
            if max_steps is not None and n >= max_steps:
                return 'paused'
            action, arg = self.policy.choose(self)
            if action == 'derive':
                prob, rep, method, params = arg[:4]
                new = self.derive(prob, rep, arg[4] if len(arg) > 4 else None)
                d = D.make(prob, new, method, params, op='derive') if new is not None else None
                if d is None or D.descriptor(d) in self.tried or not D.valid(d, self.grammar(prob)):
                    d = D.imagine(self.grammar(prob), prob, self.rng, self.archive, 8)
                action, arg = 'open', d
            if action == 'open':
                bid = self.open(arg)
                improved = self.advance(bid)
            else:
                improved = self.advance(arg)
            self.step_count += 1
            n += 1
            self.policy.observe(self, improved)
            self.curve.append((self.spent, self.total()))
        return 'done'

    # ------------------------------------------------------------------------------------------------ state
    def summary(self):
        return {'policy': self.policy_name, 'seed': self.seed, 'spent': self.spent, 'steps': self.step_count,
                'verify_calls': self.verify_calls, 'total': self.total(),
                'best_verified': {p: v for p, v in sorted(self.best_verified.items())},
                'branches': len(self.branches), 'abstracted': len(self.abstracted), 'invented': list(self.invented),
                'revealed': len(self.revealed), 'manifest': self.m.digest({'policy': self.policy_name,
                                                                         'params': self.params})}

    def save(self, path):
        state = {'policy_name': self.policy_name, 'policy': self.policy.to_json(), 'seed': self.seed,
                 'rng': [self.rng.getstate()[0], list(self.rng.getstate()[1]), self.rng.getstate()[2]],
                 'spent': self.spent, 'step_count': self.step_count, 'verify_calls': self.verify_calls,
                 'branches': {str(k): v for k, v in self.branches.items()}, 'archive': self.archive,
                 'best_verified': self.best_verified, 'best_artifact': self.best_artifact,
                 'clusters': self.clusters.to_json(), 'abstracted': self.abstracted, 'invented': self.invented,
                 'revealed': self.revealed, 'known': sorted(self.known), 'initial': sorted(self.initial),
                 'events': self.events, 'curve': self.curve, 'params': self.params,
                 'abstraction': self.abstraction, 'branch_out': self.branch_out}
        Path(path).write_text(json.dumps(state, sort_keys=True, default=list))

    @classmethod
    def load(cls, path, manifest, policy_params=None):
        s = json.loads(Path(path).read_text())
        eng = cls(manifest, s['policy_name'], s['seed'], s['params'], s['abstraction'], s['branch_out'],
                  policy_params)
        eng.policy.load(s['policy'])
        eng.rng.setstate((s['rng'][0], tuple(s['rng'][1]), s['rng'][2]))
        eng.spent, eng.step_count, eng.verify_calls = s['spent'], s['step_count'], s['verify_calls']
        eng.branches = {int(k): v for k, v in s['branches'].items()}
        for b in eng.branches.values():
            b['direction']['params'] = dict(b['direction']['params'])
        eng.archive = s['archive']
        eng.tried = {D.descriptor(d) for d in eng.archive}
        eng.best_verified, eng.best_artifact = s['best_verified'], s['best_artifact']
        eng.clusters = CG.Clusters.from_json(s['clusters'])
        eng.abstracted = [tuple(x) for x in s['abstracted']]
        eng.invented = [tuple(x) for x in s['invented']]
        eng.revealed = [tuple(x) for x in s['revealed']]
        eng.initial = set(s['initial'])
        eng.events, eng.curve = s['events'], [tuple(x) for x in s['curve']]
        # replay the domain's mutations in the order they happened
        for kind_ev in s['events']:
            if kind_ev['kind'] == 'abstract':
                eng.domain.abstract(kind_ev['problem'], kind_ev['fingerprint'])
            elif kind_ev['kind'] == 'derive':
                eng.domain.derive(kind_ev['problem'], kind_ev['representation'], kind_ev['seed'])
            elif kind_ev['kind'] == 'revealed':
                p = kind_ev['by']
                eng.domain.successors(p, eng._artifact_for_reveal(p, kind_ev))
        eng.known = set(s['known'])
        return eng

    def _artifact_for_reveal(self, problem, ev):
        for p, art in self.revealed:
            if p == problem:
                return art
        return {'problem': problem}
