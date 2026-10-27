"""Procedures extracted from discoveries, and an inventor that reuses them (research plane; the proving test's parts
3-5, `docs/OMEGA_FRONTIER.md` §7b).

**Extraction** (`extract(engine, problem)`). The procedure behind the best verified result on a problem is
compiled from the engine's own records, not written by anyone:
  * if the discovering branch searched a representation the engine abstracted (`engine.invented`), the procedure is
        explore  the approaches whose branches converged on the abstracted structure, each with the share of the
                 budget it had used by then;
        converge on a structure reached by at least two independent approaches;
        abstract it into a representation (the domain's `abstract`);
        exploit  the new representation with the discovering branch's method and parameters;
  * otherwise it is a single exploit step with the discovering branch's approach.
A procedure refers to "the representation abstracted at its converge step", never to a problem or a template by
name, so it can run unchanged on another family (part 4). Its provenance (the statement digest of the problem, the
event indices) is kept with it.

**Reuse** (`ProcedurePolicy`, registered as the policy 'procedure'). It is the Frontier's policy plus a library of
procedures. On each problem without a discovery, up to a share `rho` of the compute spent goes to the library: the
procedure's explore approaches are opened (in the order recorded) and advanced to their recorded shares; when the
engine abstracts a new representation from a convergence on that problem, it is opened with the procedure's exploit
approach and advanced first. Everything else is the Frontier's policy. "The improved inventor" of part 5 is this
policy with the procedures extracted in part 3; its predecessor is the plain Frontier policy, at matched total
compute, with the cost of finding the procedures charged to the improved one.

This module registers the policy in `allocate.POLICIES` when imported; it does not change the pinned modules.
"""
import hashlib
import json

from . import allocate as AL
from . import direction as D


def _digest(x):
    return hashlib.sha256(json.dumps(x, sort_keys=True, default=str).encode()).hexdigest()


def extract(eng, problem):
    """The procedure behind the best verified result on `problem` (the last verified improvement), or None."""
    ev = next((e for e in reversed(eng.events) if e['kind'] == 'verified' and e['problem'] == problem), None)
    if ev is None:
        return None
    b = eng.branches[ev['branch']]
    d = b['direction']
    approach = {'representation': d['representation'], 'method': d['method'], 'params': dict(d['params'])}
    invented = {rep for _, rep in eng.invented}
    prov = {'statement': _digest(eng.domain.statement(problem)), 'verified_event': eng.events.index(ev),
            'spent': ev['spent']}
    if d['representation'] not in invented:
        return {'kind': 'procedure', 'version': 1, 'steps': [{'op': 'exploit', 'approach': approach,
                                                               'abstracted': False}], 'provenance': prov}
    ab = next((e for e in eng.events if e['kind'] == 'abstract' and e['result'] == d['representation']), None)
    if ab is None:
        return _derived(eng, d, approach, prov, invented)
    members = eng.clusters.members.get((ab['problem'], ab['fingerprint']), {})
    explore = []
    for (rep, method), ids in sorted(members.items()):
        bid = min(ids)
        br = eng.branches[bid]
        t_then = max((t for t in br['ts'] if t <= eng.budget), default=0.0)
        explore.append({'representation': rep, 'method': method, 'params': dict(br['direction']['params']),
                        'share': min(1.0, t_then / eng.budget)})
    exploit = {'method': d['method'], 'params': dict(d['params'])}
    prov.update(abstract_event=eng.events.index(ab), consilience=len(members))
    return {'kind': 'procedure', 'version': 1,
            'steps': [{'op': 'explore', 'approaches': explore}, {'op': 'converge', 'min_consilience': 2},
                      {'op': 'abstract'}, {'op': 'exploit', 'approach': exploit, 'abstracted': True}],
            'provenance': prov}


def _derived(eng, d, approach, prov, invented):
    """The procedure behind a discovery in a DERIVED representation: the lineage of derivations from a starting
    representation (the seeds the engine used, which reproduce the same operations), then the exploit step."""
    seeds, rep = [], d['representation']
    while rep in invented:
        dv = next((e for e in eng.events if e['kind'] == 'derive' and e['result'] == rep), None)
        if dv is None:
            break
        seeds.append(dv['seed'])
        rep = dv['representation']
    seeds.reverse()
    prov.update(derivations=len(seeds))
    return {'kind': 'procedure', 'version': 1,
            'steps': [{'op': 'derive', 'from': rep, 'seeds': seeds},
                      {'op': 'exploit', 'approach': {'method': d['method'], 'params': dict(d['params'])},
                       'abstracted': False, 'derived': True}],
            'provenance': prov}


class ProcedurePolicy(AL.FrontierPolicy):
    name = 'procedure'

    def __init__(self, params=None):
        params = dict(params or {})
        self.library = list(params.pop('procedures', []))
        self.rho = params.pop('rho', 0.5)
        super().__init__(params)
        self.proc_spent = 0.0
        self.assigned = {}                       # branch id -> share of the budget it may use under a procedure

    def to_json(self):
        d = super().to_json()
        d.update(proc_spent=self.proc_spent, assigned={str(k): v for k, v in self.assigned.items()})
        return d

    def load(self, data):
        super().load(data)
        self.proc_spent = data.get('proc_spent', 0.0)
        self.assigned = {int(k): v for k, v in data.get('assigned', {}).items()}

    def choose(self, eng):
        if self.library and self.proc_spent < self.rho * (eng.spent + eng.quantum):
            act = self._procedure_action(eng)
            if act is not None:
                self.proc_spent += eng.quantum
                return act
        return super().choose(eng)

    def _procedure_action(self, eng):
        for prob in eng.problem_order():
            if eng.best_verified.get(prob, 0.0) > 0:
                continue
            g = eng.grammar(prob)
            for proc in self.library:
                steps = proc['steps']
                exploit = steps[-1]
                if exploit.get('derived'):
                    act = self._derived_action(eng, prob, g, steps[0], exploit['approach'])
                    if act is not None:
                        return act
                    continue
                if exploit['abstracted']:
                    # 1. an abstraction from a convergence on this problem: open and push it first
                    for p, rep in eng.invented:
                        if p != prob:
                            continue
                        d = D.make(prob, rep, exploit['approach']['method'], exploit['approach']['params'],
                                   op='procedure')
                        act = self._open_or_advance(eng, d, g, 1.0)
                        if act is not None:
                            return act
                    # 2. the explore approaches, to their recorded shares
                    for a in steps[0]['approaches']:
                        d = D.make(prob, a['representation'], a['method'], a['params'], op='procedure')
                        act = self._open_or_advance(eng, d, g, max(a['share'], 2 * eng.quantum / eng.budget))
                        if act is not None:
                            return act
                else:
                    a = exploit['approach']
                    d = D.make(prob, a['representation'], a['method'], a['params'], op='procedure')
                    act = self._open_or_advance(eng, d, g, 0.25)
                    if act is not None:
                        return act
        return None

    def _derived_action(self, eng, prob, g, derive_step, approach):
        """Replay a procedure's derivations on `prob` (each seed in turn, from the starting representation), then open
        and advance the representation they give."""
        rep = derive_step['from']
        for seed in derive_step['seeds']:
            done = next((e for e in eng.events if e['kind'] == 'derive' and e['representation'] == rep
                         and e['seed'] == seed), None)
            if done is None:
                return ('derive', (prob, rep, approach['method'], approach['params'], seed))
            if done['result'] is None:
                return None
            rep = done['result']
        d = D.make(prob, rep, approach['method'], approach['params'], op='procedure')
        return self._open_or_advance(eng, d, eng.grammar(prob), 0.25)

    def _open_or_advance(self, eng, d, g, share):
        if not D.valid(d, g):
            return None
        key = D.descriptor(d)
        bid = next((b['id'] for b in eng.branches.values() if D.descriptor(b['direction']) == key), None)
        if bid is None:
            return ('open', d)
        b = eng.branches[bid]
        if b['t'] < share * eng.budget and not b['paused']:
            return ('advance', bid)
        return None


AL.POLICIES.setdefault('procedure', ProcedurePolicy)
