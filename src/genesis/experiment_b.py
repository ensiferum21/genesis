"""Experiment B — Ghost Census kill gate (spec §19.2).

A preregistered family of first-order problems (algebraic theories, a
conjecture, and candidate lemmas that may be true or false) is attacked by
three arms under the same per-problem CPU budget, in randomized order:

  portfolio         conventional: finite-model search for a counterexample to the
                    conjecture, then E on axioms |- conjecture with the rest.
  lemmas_unfiltered prove every candidate lemma with E, then the conjecture from
                    axioms + proved lemmas.
  ghost_lemmas      Ghost Census: search countermodels of the conjecture and of each
                    candidate lemma first; lemmas with a validated ghost are dropped
                    without spending prover time; survivors are proved, then the goal.

Outcome states are kept distinct: PROVED (E claims Theorem; proof object stored,
not independently replayed), GHOST_FOUND (a finite countermodel to the goal,
independently re-checked), UNSETTLED (including saturation-based
"CounterSatisfiable" claims and resource outs), HARNESS_ERROR. A finite failure
to find a model is never reinterpreted as a consistency or truth proof.

The kill gate (preregistered): ghost_lemmas must settle at least `margin` more
problems than the better of the two baselines; otherwise the decision is KILL.
This runs on public DEV problems only; a sealed version needs the custodian.
"""
from itertools import combinations
from pathlib import Path
import random
import resource
import time

from pydantic import Field

from .common import atomic_write, canonical, code_identity, digest, utcnow
from .fol import parse, to_tptp
from .modelfind import find_model
from .models import StrictModel
from .store import Store
from .verification.eprover import prove

THEORIES = {
    'group': ['![X,Y,Z]: mul(mul(X,Y),Z) = mul(X,mul(Y,Z))', '![X]: mul(e,X) = X', '![X]: mul(inv(X),X) = e'],
    'monoid': ['![X,Y,Z]: mul(mul(X,Y),Z) = mul(X,mul(Y,Z))', '![X]: mul(e,X) = X', '![X]: mul(X,e) = X'],
    'band': ['![X,Y,Z]: mul(mul(X,Y),Z) = mul(X,mul(Y,Z))', '![X]: mul(X,X) = X'],
    'loop': ['![X]: mul(e,X) = X', '![X]: mul(X,e) = X', '![X,Y]: mul(X,ldiv(X,Y)) = Y',
             '![X,Y]: ldiv(X,mul(X,Y)) = Y'],
}
STATEMENTS = {
    'right_id': '![X]: mul(X,e) = X',
    'right_inv': '![X]: mul(X,inv(X)) = e',
    'comm': '![X,Y]: mul(X,Y) = mul(Y,X)',
    'idem': '![X]: mul(X,X) = X',
    'inv_inv': '![X]: inv(inv(X)) = X',
    'e_idem': 'mul(e,e) = e',
    'left_cancel': '![X,Y,Z]: (mul(X,Y) = mul(X,Z) => Y = Z)',
    'inv_mul': '![X,Y]: inv(mul(X,Y)) = mul(inv(Y),inv(X))',
    'rect_band': '![X,Y]: mul(mul(X,Y),X) = X',
    'assoc': '![X,Y,Z]: mul(mul(X,Y),Z) = mul(X,mul(Y,Z))',
    'unique_left_id': '![U]: ((![X]: mul(U,X) = X) => U = e)',
    'square_comm': '![X,Y]: mul(mul(X,X),Y) = mul(Y,mul(X,X))',
}
# Which statements make sense (use only the theory's symbols) per theory.
VOCAB = {'group': ['right_id', 'right_inv', 'comm', 'idem', 'inv_inv', 'e_idem', 'left_cancel', 'inv_mul',
                   'unique_left_id', 'square_comm'],
         'monoid': ['comm', 'idem', 'e_idem', 'left_cancel', 'unique_left_id', 'square_comm'],
         'band': ['comm', 'rect_band', 'square_comm'],
         'loop': ['comm', 'assoc', 'e_idem', 'left_cancel', 'unique_left_id', 'idem']}


class ExperimentBPrereg(StrictModel):
    schema_version: str = 'genesis-experiment-b-prereg-v1'
    seed: int = 20261014
    problems: int = Field(default=16, ge=2, le=200)
    lemmas_per_problem: int = Field(default=3, ge=1, le=6)
    budget_seconds: float = Field(default=12.0, gt=0, le=600)
    model_max_size: int = Field(default=6, ge=1, le=8)
    margin: int = Field(default=1, ge=0)
    arms: tuple[str, ...] = ('portfolio', 'lemmas_unfiltered', 'ghost_lemmas')
    family_digest: str = ''


def family(seed, count, lemmas_per_problem):
    rng = random.Random(seed)
    candidates = []
    for theory, vocab in THEORIES.items():
        for goal in VOCAB[theory]:
            others = [s for s in VOCAB[theory] if s != goal]
            for lemmas in combinations(others, min(lemmas_per_problem, len(others))):
                candidates.append({'theory': theory, 'goal': goal, 'lemmas': list(lemmas)})
    rng.shuffle(candidates)
    picked, seen = [], set()
    for c in candidates:
        key = (c['theory'], c['goal'])
        if key in seen:
            continue
        seen.add(key); picked.append(c)
        if len(picked) == count:
            break
    for i, p in enumerate(picked):
        p['problem_id'] = f'b{seed}-{i:03d}'
    return picked


def family_digest(problems):
    return digest([{k: p[k] for k in ('problem_id', 'theory', 'goal', 'lemmas')} for p in problems])


def _cpu():
    me = resource.getrusage(resource.RUSAGE_SELF); ch = resource.getrusage(resource.RUSAGE_CHILDREN)
    return me.ru_utime + me.ru_stime + ch.ru_utime + ch.ru_stime


class _Budget:
    def __init__(self, seconds):
        self.total = seconds; self.start = _cpu()

    def left(self):
        return self.total - (_cpu() - self.start)

    def slice(self, fraction, minimum=1):
        return max(minimum, min(self.left(), self.total * fraction))


def _ghost(axioms, negated, budget, prereg):
    model, record = find_model(axioms + [negated], max_size=prereg.model_max_size,
                               seconds=max(1, int(budget)))
    return model, record


def run_arm(arm, problem, prereg):
    axioms = [parse(a) for a in THEORIES[problem['theory']]]
    goal = parse(STATEMENTS[problem['goal']])
    lemmas = {name: parse(STATEMENTS[name]) for name in problem['lemmas']}
    budget = _Budget(prereg.budget_seconds)
    log = []
    try:
        if arm in ('portfolio', 'ghost_lemmas'):
            model, record = _ghost(axioms, ('not', goal), budget.slice(0.3), prereg)
            log.append({'step': 'goal_countermodel_search', **{k: record.get(k) for k in ('status', 'size')}})
            if record['status'] == 'HARNESS_ERROR':
                return {'status': 'HARNESS_ERROR', 'reason': record['reason'], 'log': log}
            if model is not None:
                return {'status': 'GHOST_FOUND', 'ghost': model.to_json(), 'log': log}
        usable = list(axioms)
        if arm in ('lemmas_unfiltered', 'ghost_lemmas'):
            for name, lemma in lemmas.items():
                if budget.left() <= 1:
                    break
                if arm == 'ghost_lemmas':
                    model, record = _ghost(axioms, ('not', lemma), budget.slice(0.1), prereg)
                    if model is not None:
                        log.append({'step': f'lemma_ghost:{name}', 'status': 'FALSE_LEMMA_DROPPED',
                                    'size': record['size']})
                        continue
                result = prove(axioms, lemma, seconds=budget.slice(0.15))
                log.append({'step': f'lemma_proof:{name}', 'status': result['status']})
                if result['status'] == 'THEOREM':
                    usable.append(lemma)
        if budget.left() >= 1:
            result = prove(usable, goal, seconds=max(1, budget.left()))
            log.append({'step': 'goal_proof', 'status': result['status'], 'lemmas_used': len(usable) - len(axioms)})
            if result['status'] == 'THEOREM':
                return {'status': 'PROVED', 'proof_object_sha256': digest(result['proof'] or ''),
                        'proof_replayed': False, 'lemmas_used': len(usable) - len(axioms), 'log': log}
            if result['status'] == 'COUNTERSATISFIABLE':
                return {'status': 'UNSETTLED', 'note': 'prover saturation claim; no exact countermodel', 'log': log}
        return {'status': 'UNSETTLED', 'log': log}
    except Exception as exc:  # harness failures are recorded, never counted as outcomes
        return {'status': 'HARNESS_ERROR', 'reason': f'{type(exc).__name__}: {exc}', 'log': log}


def run_experiment(root, prereg=None):
    prereg = prereg or ExperimentBPrereg()
    problems = family(prereg.seed, prereg.problems, prereg.lemmas_per_problem)
    prereg = prereg.model_copy(update={'family_digest': family_digest(problems)})
    root = Path(root)
    if root.exists() and any(root.iterdir()):
        raise FileExistsError('experiment destination must be empty')
    rng = random.Random(prereg.seed + 1)
    order = list(problems); rng.shuffle(order)
    with Store(root) as s:
        pid = digest(prereg.model_dump(mode='json'))
        s.save('experiment_b_prereg', pid, prereg.model_dump(mode='json'))
        s.save('experiment_b_family', prereg.family_digest, problems)
        s.set_state('source_hash', code_identity(Path(__file__).resolve().parents[2])['sha256'])
        rows = []
        for p in order:
            arms = list(prereg.arms); rng.shuffle(arms)
            for arm in arms:
                aid = s.start(f'expB-{p["problem_id"]}-{arm}', {'kind': 'experiment_b', 'arm': arm, 'problem': p,
                                                                'prereg': pid})
                c0 = _cpu(); w0 = time.monotonic()
                result = run_arm(arm, p, prereg)
                cpu = _cpu() - c0
                s.finish(aid, {'status': 'SUCCESS' if result['status'] != 'HARNESS_ERROR' else 'HARNESS_ERROR',
                               'outcome': result, 'cpu_seconds': round(cpu, 3),
                               'wall_seconds': round(time.monotonic() - w0, 3)})
                rows.append({'problem': p['problem_id'], 'theory': p['theory'], 'goal': p['goal'], 'arm': arm,
                             'status': result['status'], 'cpu_seconds': round(cpu, 3)})
        summary = summarize(prereg, rows)
        s.save('experiment_b_results', pid, summary)
        atomic_write(root / 'reports' / 'experiment_b.json', canonical(summary), overwrite=True)
        return summary


def summarize(prereg, rows):
    counts = {}
    for arm in prereg.arms:
        mine = [r for r in rows if r['arm'] == arm]
        counts[arm] = {s: sum(r['status'] == s for r in mine) for s in ('PROVED', 'GHOST_FOUND', 'UNSETTLED',
                                                                          'HARNESS_ERROR')}
        counts[arm]['settled'] = counts[arm]['PROVED'] + counts[arm]['GHOST_FOUND']
        counts[arm]['cpu_seconds'] = round(sum(r['cpu_seconds'] for r in mine), 2)
    baseline = max(counts[a]['settled'] for a in prereg.arms if a != 'ghost_lemmas')
    ghost = counts['ghost_lemmas']['settled']
    # Consistency: no problem may be PROVED by one arm and GHOST_FOUND by another.
    by_problem = {}
    for r in rows:
        by_problem.setdefault(r['problem'], set()).add(r['status'])
    contradictions = [p for p, st in by_problem.items() if {'PROVED', 'GHOST_FOUND'} <= st]
    decision = 'HARNESS_ERROR' if contradictions else ('CONTINUE' if ghost >= baseline + prereg.margin else 'KILL')
    return {'schema': 'genesis-experiment-b-results-v1', 'prereg': prereg.model_dump(mode='json'), 'rows': rows,
            'counts': counts, 'gate': {'ghost_settled': ghost, 'best_baseline_settled': baseline,
                                       'margin': prereg.margin, 'decision': decision},
            'contradictions': contradictions,
            'scope': 'public DEV algebra family; PROVED means E claimed Theorem (proof object not replayed)',
            'completed_utc': utcnow(), 'promotion_allowed': False}
