"""Fault-tolerant reasoning and expert interaction (roadmap W23), DEV only.

Heterogeneous routes for one claim, "equation e holds in system S":
  decider       exact evaluation in the generating algebra (or free-group reduction);
  prover        E's claim, with its proof object;
  kernel        Lean replay of that proof object, bound to a statement generated from
                the claim (never from the proof);
  countermodel  the finite model finder, its model re-checked by the independent
                evaluator.
The routes share no code: the decider never sees a proof, the kernel never trusts the
prover, and countermodels are re-evaluated independently.

`diagnose` turns route outcomes into a verdict. Acceptance requires the kernel, so a
prover fault can never be accepted, and a disagreement is always reported with the
routes that disagree; it is never resolved by majority. Faults can be injected into
proofs, statements, the decider and the claim itself (`inject`), to measure detection
and false acceptance.

Expert questions. When the routes leave a decision open (for example, the prover gave up
and no countermodel was found), a question is raised with its cost and provenance and
charged to an intervention budget. In this DEV harness the answers come from a SIMULATED
expert: the decider, flipped with a declared error rate. This is labelled everywhere it
appears. A real expert's effect remains to be measured.
"""
import random

from ..common import digest
from ..fol import check_model, signature
from ..modelfind import find_model
from ..verification.eprover import prove
from . import equational as Q

VERDICTS = ('ACCEPTED', 'REJECTED_FALSE', 'UNVERIFIED', 'DISAGREEMENT')


def routes(system, eq, *, proof=None, prove_s=2, model_size=4, model_s=5, decider=None, kernel=True):
    """Outcomes of every route for one claim. `proof` (optional) is a proof object
    offered by someone else; otherwise E is asked. `decider` overrides the decider
    (fault injection)."""
    from ..formal_research import fof_lean as F
    spec = Q.SYSTEMS[system]
    ax = Q.axioms(system)
    out = {'claim': Q.text(eq)}
    out['decider'] = bool(decider(eq) if decider else Q.holds(eq, spec['decider']))
    if proof is None:
        r = prove(ax, Q.closed(eq), seconds=prove_s)
        proof = r['proof'] if r['status'] == 'THEOREM' else None
        out['prover'] = r['status']
    else:
        out['prover'] = 'OFFERED'
    if proof is not None and kernel:
        rec = F.replay(f'w23-{digest({"c": out["claim"], "p": proof})[:12]}', ax, Q.closed(eq), proof)
        out['kernel'] = rec['status']
    else:
        out['kernel'] = 'NO_PROOF'
    model, rec = find_model(ax + [('not', Q.closed(eq))], max_size=model_size, seconds=model_s, total_seconds=model_s)
    if model is not None:
        ok, _ = check_model(model, ax + [('not', Q.closed(eq))], signature(ax + [Q.closed(eq)]))
        out['countermodel'] = 'FOUND' if ok else 'INVALID'
    else:
        out['countermodel'] = 'NONE_UP_TO_SIZE' if rec['status'] == 'NO_MODEL_UP_TO_SIZE' else 'UNKNOWN'
    return out


def diagnose(r):
    """Verdict and the disagreeing routes. Acceptance needs THEOREM_CHECKED."""
    says_true = []
    says_false = []
    if r['decider']:
        says_true.append('decider')
    else:
        says_false.append('decider')
    if r['kernel'] == 'THEOREM_CHECKED':
        says_true.append('kernel')
    if r['prover'] == 'THEOREM':
        says_true.append('prover')
    if r['countermodel'] == 'FOUND':
        says_false.append('countermodel')
    if says_true and says_false:
        # a kernel-checked proof and a validated countermodel cannot both be right
        if 'kernel' in says_true and 'countermodel' in says_false:
            culprit = 'the axiom translation or the evaluator'
        elif 'kernel' in says_true:
            culprit = 'decider'
        elif 'countermodel' in says_false:
            culprit = 'prover' if 'prover' in says_true else 'decider'
        else:
            culprit = 'prover or decider (no independent route settles it)'
        return {'verdict': 'DISAGREEMENT', 'true': says_true, 'false': says_false, 'suspect': culprit}
    if 'kernel' in says_true:
        return {'verdict': 'ACCEPTED', 'true': says_true, 'false': []}
    if says_false:
        return {'verdict': 'REJECTED_FALSE', 'true': [], 'false': says_false}
    return {'verdict': 'UNVERIFIED', 'true': says_true, 'false': []}


def corrupt_proof(proof, rng):
    """Flip one equation literal (= <-> !=) in a derived clause of a TSTP proof object.
    Input lines are left alone: the replay rebuilds inputs from the trusted statement."""
    lines = proof.splitlines()
    idx = [i for i, l in enumerate(lines) if l.startswith('cnf(') and ', plain, (' in l and 'file(' not in l
           and '=' in l[l.index(', plain, ('):]]
    if not idx:
        return None
    i = rng.choice(idx)
    l = lines[i]
    a = l.index(', plain, (') + len(', plain, (')
    eqpos = l.index('=', a)
    if l[eqpos - 1] == '!':
        lines[i] = l[:eqpos - 1] + '=' + l[eqpos + 1:]
    else:
        lines[i] = l[:eqpos] + '!=' + l[eqpos + 1:]
    return '\n'.join(lines)


def inject(kind, item, pool, rng):
    """One faulty claim. Returns (eq, proof, decider override, truth)."""
    eq, proof = item['eq'], item['proof']
    if kind == 'corrupt_proof':
        return eq, corrupt_proof(proof, rng), None, True
    if kind == 'swapped_proof':
        other = rng.choice([x for x in pool if x['eq'] != eq])
        return eq, other['proof'], None, True
    if kind == 'false_claim_with_proof':
        f = item['false_eq']
        return f, proof, None, False
    if kind == 'decider_flip':
        return eq, proof, (lambda e: not Q.holds(e, item['decider'])), True
    raise ValueError(kind)


# ---------------------------------------------------------------- expert questions

def question(claim, reason, *, cost=1.0):
    return {'question': f'Is "{claim}" true in this system?', 'claim': claim, 'reason': reason, 'cost': cost,
            'provenance': {'raised_by': 'faults.routes/diagnose', 'claim_sha256': digest({'c': claim})},
            'status': 'OPEN', 'answer': None, 'answered_by': None}


class SimulatedExpert:
    """SIMULATED: answers from the decider, flipped with probability `error_rate`. Used only
    to exercise the interface and the intervention budget; not evidence about real experts."""
    label = 'SIMULATED_EXPERT'

    def __init__(self, system, error_rate, seed):
        self.system, self.error, self.rng = system, error_rate, random.Random(seed)

    def answer(self, q, eq):
        truth = Q.holds(eq, Q.SYSTEMS[self.system]['decider'])
        ans = truth if self.rng.random() >= self.error else not truth
        return dict(q, status='ANSWERED', answer=ans, answered_by=self.label)


__all__ = ['routes', 'diagnose', 'inject', 'corrupt_proof', 'question', 'SimulatedExpert', 'VERDICTS']
