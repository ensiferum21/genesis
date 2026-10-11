"""Ghost Census beyond the small development family (roadmap W16): a DEV diagnostic.

B13's Experiment B (B11 code, `genesis.experiment_b`) reported KILL on its small DEV
family: every arm settled almost everything, so lemma selection could not matter. That
result is preserved. Before any sealed evaluation is spent, this diagnostic asks, on a
harder DEV family, whether the mechanism, the budget allocation or the family can
plausibly give a benefit. It is not a sealed study and supports no efficacy claim.

Family. Ten equational theories (groups and two group varieties, lattices and
distributive lattices, rings and Boolean rings, quasigroups, Moufang loops and
Huntington's axioms for Boolean algebra) with named statements in their vocabulary. Each
(theory, statement) pair is labelled first, independently of the arms:
  TRUE     E (strategy schedule) claims Theorem at the labelling budget, and the proof
           object is replayed step by step in Lean (`formal_research.fof_lean`);
  TRUE_UNCHECKED  E claims Theorem but the Lean replay did not go through;
  FALSE    a finite countermodel, re-checked by the independent evaluator;
  UNKNOWN  neither.
A problem is a theory, a goal and three candidate lemmas from the same pool.

Arms, all under the same per-problem CPU budget, in randomized order:
  portfolio_auto     B11's portfolio: countermodel search, then E --auto;
  portfolio          the strongest baseline: countermodel search, then E's strategy
                     schedule;
  lemmas_unfiltered  prove every candidate lemma, then the goal with the proved lemmas;
  ghost_lemmas       B11's Ghost Census allocation: countermodels for the goal and for each
                     lemma first, drop lemmas with a validated ghost, prove the rest;
  ghost_lemmas_lean  the same mechanism with a leaner allocation (less ghost search);
  oracle_lemmas      diagnostic only, not a competitor: the lemmas labelled TRUE are given
                     to E free of charge. It bounds what any lemma-selection arm can gain.

Outcomes: PROVED (E's claim), PROVED_CHECKED (the proof object, and the proofs of the
lemmas it used, replayed in Lean and bound to the trusted statement), GHOST_FOUND,
UNSETTLED, HARNESS_ERROR. Lean replay is the evaluator's cost, recorded separately and
not charged to an arm.

The decision rule is fixed in `PLAN` before the run and stored with the results.
"""
import math
import random
import resource
import time

from ..common import digest
from ..fol import evaluate, parse, signature, to_tptp, Model
from ..modelfind import find_model
from ..formal_research import fof_lean as F
from ..verification.eprover import prove

GROUP = ['![X,Y,Z]: mul(mul(X,Y),Z) = mul(X,mul(Y,Z))', '![X]: mul(e,X) = X', '![X]: mul(inv(X),X) = e']
LATTICE = ['![X,Y]: meet(X,Y) = meet(Y,X)', '![X,Y]: join(X,Y) = join(Y,X)',
           '![X,Y,Z]: meet(meet(X,Y),Z) = meet(X,meet(Y,Z))', '![X,Y,Z]: join(join(X,Y),Z) = join(X,join(Y,Z))',
           '![X,Y]: meet(X,join(X,Y)) = X', '![X,Y]: join(X,meet(X,Y)) = X']
RING = ['![X,Y,Z]: plus(plus(X,Y),Z) = plus(X,plus(Y,Z))', '![X,Y]: plus(X,Y) = plus(Y,X)',
        '![X]: plus(zero,X) = X', '![X]: plus(X,neg(X)) = zero',
        '![X,Y,Z]: times(times(X,Y),Z) = times(X,times(Y,Z))',
        '![X,Y,Z]: times(X,plus(Y,Z)) = plus(times(X,Y),times(X,Z))',
        '![X,Y,Z]: times(plus(X,Y),Z) = plus(times(X,Z),times(Y,Z))']
QUASIGROUP = ['![X,Y]: mul(X,ldiv(X,Y)) = Y', '![X,Y]: ldiv(X,mul(X,Y)) = Y', '![X,Y]: mul(rdiv(X,Y),Y) = X',
              '![X,Y]: rdiv(mul(X,Y),Y) = X']
THEORIES = {
    'group': GROUP,
    'group_sq': GROUP + ['![X,Y]: mul(mul(X,Y),mul(X,Y)) = mul(mul(X,X),mul(Y,Y))'],
    'group_exp2': GROUP + ['![X]: mul(X,X) = e'],
    'lattice': LATTICE,
    'dist_lattice': LATTICE + ['![X,Y,Z]: meet(X,join(Y,Z)) = join(meet(X,Y),meet(X,Z))'],
    'ring': RING,
    'boolean_ring': RING + ['![X]: times(X,X) = X'],
    'quasigroup': QUASIGROUP,
    'moufang': ['![X]: mul(e,X) = X', '![X]: mul(X,e) = X'] + QUASIGROUP +
               ['![X,Y,Z]: mul(mul(Z,X),mul(Y,Z)) = mul(mul(Z,mul(X,Y)),Z)'],
    'huntington': ['![X,Y]: plus(X,Y) = plus(Y,X)', '![X,Y,Z]: plus(plus(X,Y),Z) = plus(X,plus(Y,Z))',
                   '![X,Y]: plus(n(plus(n(X),Y)),n(plus(n(X),n(Y)))) = X'],
}
STATEMENTS = {
    # groups (mul, e, inv)
    'right_id': '![X]: mul(X,e) = X',
    'right_inv': '![X]: mul(X,inv(X)) = e',
    'comm': '![X,Y]: mul(X,Y) = mul(Y,X)',
    'inv_inv': '![X]: inv(inv(X)) = X',
    'left_cancel': '![X,Y,Z]: (mul(X,Y) = mul(X,Z) => Y = Z)',
    'right_cancel': '![X,Y,Z]: (mul(Y,X) = mul(Z,X) => Y = Z)',
    'inv_mul': '![X,Y]: inv(mul(X,Y)) = mul(inv(Y),inv(X))',
    'unique_left_id': '![U]: ((![X]: mul(U,X) = X) => U = e)',
    'idem': '![X]: mul(X,X) = X',
    'inv_e': 'inv(e) = e',
    'self_inverse': '![X]: inv(X) = X',
    'inv_comm': '![X,Y]: mul(inv(X),inv(Y)) = mul(inv(Y),inv(X))',
    'sq_e_unique': '![X]: (mul(X,X) = X => X = e)',
    'sq_central': '![X,Y]: mul(mul(X,X),Y) = mul(Y,mul(X,X))',
    # loops and quasigroups (mul, ldiv, rdiv, e)
    'assoc': '![X,Y,Z]: mul(mul(X,Y),Z) = mul(X,mul(Y,Z))',
    'flexible': '![X,Y]: mul(mul(X,Y),X) = mul(X,mul(Y,X))',
    'left_alt': '![X,Y]: mul(X,mul(X,Y)) = mul(mul(X,X),Y)',
    'right_alt': '![X,Y]: mul(mul(Y,X),X) = mul(Y,mul(X,X))',
    'ldiv_self': '![X,Y]: ldiv(X,X) = ldiv(Y,Y)',
    'moufang_right': '![X,Y,Z]: mul(mul(mul(X,Y),Z),Y) = mul(X,mul(Y,mul(Z,Y)))',
    'ldiv_e': '![X]: ldiv(X,X) = e',
    # lattices (meet, join)
    'meet_idem': '![X]: meet(X,X) = X',
    'join_idem': '![X]: join(X,X) = X',
    'order_dual': '![X,Y]: (meet(X,Y) = X <=> join(X,Y) = Y)',
    'distrib': '![X,Y,Z]: meet(X,join(Y,Z)) = join(meet(X,Y),meet(X,Z))',
    'distrib_dual': '![X,Y,Z]: join(X,meet(Y,Z)) = meet(join(X,Y),join(X,Z))',
    'modular': '![X,Y,Z]: (meet(X,Z) = X => meet(join(X,Y),Z) = join(X,meet(Y,Z)))',
    'cancel': '![X,Y,Z]: ((meet(X,Z) = meet(Y,Z) & join(X,Z) = join(Y,Z)) => X = Y)',
    'meet_is_join': '![X,Y]: meet(X,Y) = join(X,Y)',
    'chain': '![X,Y]: (meet(X,Y) = X | meet(X,Y) = Y)',
    # rings (plus, zero, neg, times)
    'char2': '![X]: plus(X,X) = zero',
    'times_comm': '![X,Y]: times(X,Y) = times(Y,X)',
    'neg_self': '![X]: neg(X) = X',
    'times_zero': '![X]: times(X,zero) = zero',
    'zero_times': '![X]: times(zero,X) = zero',
    'plus_cancel': '![X,Y,Z]: (plus(X,Y) = plus(X,Z) => Y = Z)',
    'neg_neg': '![X]: neg(neg(X)) = X',
    'neg_times': '![X,Y]: times(neg(X),Y) = neg(times(X,Y))',
    'anti_comm': '![X,Y]: plus(times(X,Y),times(Y,X)) = zero',
    'no_nilpotent': '![X]: (times(X,X) = zero => X = zero)',
    'times_idem': '![X]: times(X,X) = X',
    # Boolean algebra after Huntington (plus, n)
    'h_idem': '![X]: plus(X,X) = X',
    'h_double_neg': '![X]: n(n(X)) = X',
    'h_complement': '![X,Y]: plus(X,n(X)) = plus(Y,n(Y))',
    'h_neg_fix': '![X]: n(X) = X',
    'h_de_morgan_wrong': '![X,Y]: n(plus(X,Y)) = plus(n(X),n(Y))',
}

PLAN = {
    'schema': 'genesis-ghost-census-v2-diagnostic-plan',
    'split': 'DEV',
    'seed': 20261024,
    'budgets_cpu_s': [2.0, 8.0],
    'label_budget': {'prove_cpu_s': 30, 'ghost_max_size': 6, 'ghost_total_s': 20},
    'lemmas_per_problem': 3,
    'arms': ['portfolio_auto', 'portfolio', 'lemmas_unfiltered', 'ghost_lemmas', 'ghost_lemmas_lean',
             'oracle_lemmas'],
    'competitors': ['portfolio_auto', 'portfolio', 'lemmas_unfiltered', 'ghost_lemmas', 'ghost_lemmas_lean'],
    'baselines': ['portfolio_auto', 'portfolio', 'lemmas_unfiltered'],
    'mechanism_arms': ['ghost_lemmas', 'ghost_lemmas_lean'],
    'diagnostic_only': ['oracle_lemmas'],
    'settled_means': 'PROVED (E claim) or GHOST_FOUND; the checked count is reported alongside',
    'margin_rule': 'margin = max(1, ceil(0.05 * problems))',
    'decision_rule': [
        'HARNESS_ERROR if any problem is PROVED by one arm and GHOST_FOUND by another, or contradicts its label',
        'RETIRE_NO_HEADROOM if at every budget oracle_lemmas settles fewer than best_baseline + margin',
        'PLAUSIBLE_BENEFIT if at the larger budget some mechanism arm settles at least best_baseline + margin',
        'RETIRE_MECHANISM_GAP otherwise (headroom exists, the Ghost Census arms do not capture it)'],
    'consequence': {
        'RETIRE_NO_HEADROOM': 'retire the Ghost Census branch for this scope (equational theories, these budgets)',
        'RETIRE_MECHANISM_GAP': 'retire this mechanism design for this scope; record redesign directions',
        'PLAUSIBLE_BENEFIT': 'freeze the arm and design a sealed, custodian-run study (not run by the builder)'},
    'not_claimed': 'no efficacy claim; DEV diagnostic only; a sealed study needs the independent custodian',
}


def pools():
    """Statements in each theory's vocabulary that are not among its axioms."""
    out = {}
    for th, axioms in THEORIES.items():
        sig = signature([parse(a) for a in axioms])['functions']
        ax = {to_tptp(parse(a)) for a in axioms}
        mine = []
        for name, text in STATEMENTS.items():
            f = parse(text)
            fs = signature([f])['functions']
            if set(fs) <= set(sig) and all(sig[k] == v for k, v in fs.items()) and to_tptp(f) not in ax:
                mine.append(name)
        out[th] = mine
    return out


def _cpu():
    me = resource.getrusage(resource.RUSAGE_SELF); ch = resource.getrusage(resource.RUSAGE_CHILDREN)
    return me.ru_utime + me.ru_stime + ch.ru_utime + ch.ru_stime


class Budget:
    def __init__(self, seconds):
        self.total = seconds; self.start = _cpu()

    def used(self):
        return _cpu() - self.start

    def left(self):
        return self.total - self.used()

    def slice(self, fraction, minimum=1.0):
        return max(minimum, min(self.left(), self.total * fraction))


def _prove(axioms, goal, seconds, mode):
    return prove(axioms, goal, seconds=max(1, int(math.ceil(seconds))), mode=mode)


def _ghost(axioms, negated, seconds, max_size):
    return find_model(axioms + [negated], max_size=max_size, seconds=max(1, int(seconds)),
                      total_seconds=max(1.0, seconds))


# ---------------------------------------------------------------- labelling

def label(theory, name, *, plan=PLAN, cache=None):
    axioms = [parse(a) for a in THEORIES[theory]]
    goal = parse(STATEMENTS[name])
    lb = plan['label_budget']
    c0 = _cpu()
    model, rec = _ghost(axioms, ('not', goal), lb['ghost_total_s'], lb['ghost_max_size'])
    if model is not None:
        return {'label': 'FALSE', 'ghost_size': rec['size'], 'ghost': model.to_json(),
                'cpu_s': round(_cpu() - c0, 3)}
    r = _prove(axioms, goal, lb['prove_cpu_s'], 'schedule')
    out = {'e_status': r['status'], 'e_seconds': r['seconds'], 'ghost_search': rec['status']}
    if r['status'] == 'THEOREM' and r['proof']:
        rp = F.replay(f'label-{theory}-{name}', axioms, goal, r['proof'], cache=cache)
        out.update(label='TRUE' if rp['status'] == 'THEOREM_CHECKED' else 'TRUE_UNCHECKED',
                   proof=r['proof'], replay={k: rp.get(k) for k in ('status', 'reason', 'steps', 'hinted_steps',
                                                                    'errors', 'proof_module_sha256')})
    else:
        out['label'] = 'UNKNOWN'
    out['cpu_s'] = round(_cpu() - c0, 3)
    return out


def family(labels, seed, lemmas_per_problem=3):
    """Every (theory, goal) pair; three candidate lemmas from the same pool, including a
    true and a false one when the pool has them (so that lemma selection can matter)."""
    rng = random.Random(seed)
    problems = []
    for th, names in pools().items():
        for goal in names:
            others = [s for s in names if s != goal]
            true = [s for s in others if labels[(th, s)]['label'] == 'TRUE']
            false = [s for s in others if labels[(th, s)]['label'] == 'FALSE']
            pick = []
            if true:
                pick.append(rng.choice(true))
            if false:
                pick.append(rng.choice(false))
            rest = [s for s in others if s not in pick]
            rng.shuffle(rest)
            pick += rest[:max(0, lemmas_per_problem - len(pick))]
            problems.append({'theory': th, 'goal': goal, 'lemmas': sorted(pick[:lemmas_per_problem])})
    rng.shuffle(problems)
    for i, p in enumerate(problems):
        p['problem_id'] = f'gc{seed}-{i:03d}'
    return problems


# ---------------------------------------------------------------- arms

ALLOCATION = {'ghost_lemmas': {'goal_ghost': 0.3, 'lemma_ghost': 0.1, 'lemma_prove': 0.15},
              'ghost_lemmas_lean': {'goal_ghost': 0.15, 'lemma_ghost': 0.05, 'lemma_prove': 0.1},
              'lemmas_unfiltered': {'lemma_prove': 0.15}}


def run_arm(arm, problem, budget_s, labels, *, max_size=6):
    th = problem['theory']
    axioms = [parse(a) for a in THEORIES[th]]
    goal = parse(STATEMENTS[problem['goal']])
    lemmas = {n: parse(STATEMENTS[n]) for n in problem['lemmas']}
    mode = 'auto' if arm == 'portfolio_auto' else 'schedule'
    b = Budget(budget_s)
    log = []
    try:
        if arm in ('portfolio_auto', 'portfolio', 'ghost_lemmas', 'ghost_lemmas_lean', 'oracle_lemmas'):
            frac = ALLOCATION.get(arm, {}).get('goal_ghost', 0.3)
            model, rec = _ghost(axioms, ('not', goal), b.slice(frac), max_size)
            log.append({'step': 'goal_ghost', 'status': rec['status'], 'size': rec.get('size'),
                        'cpu_s': round(b.used(), 3)})
            if rec['status'] == 'HARNESS_ERROR':
                return {'status': 'HARNESS_ERROR', 'reason': rec.get('reason'), 'log': log}
            if model is not None:
                return {'status': 'GHOST_FOUND', 'ghost': model.to_json(), 'log': log}
        usable, used = list(axioms), []
        if arm == 'oracle_lemmas':
            for n in problem['lemmas']:
                if labels[(th, n)]['label'] == 'TRUE':
                    usable.append(lemmas[n]); used.append((n, labels[(th, n)]['proof']))
            log.append({'step': 'oracle', 'lemmas_given': [n for n, _ in used]})
        if arm in ALLOCATION:
            alloc = ALLOCATION[arm]
            for n in problem['lemmas']:
                if b.left() <= 1:
                    break
                if 'lemma_ghost' in alloc:
                    model, rec = _ghost(axioms, ('not', lemmas[n]), b.slice(alloc['lemma_ghost']), max_size)
                    if model is not None:
                        log.append({'step': f'lemma_ghost:{n}', 'status': 'FALSE_LEMMA_DROPPED',
                                    'size': rec['size'], 'cpu_s': round(b.used(), 3)})
                        continue
                c0 = _cpu()
                r = _prove(axioms, lemmas[n], b.slice(alloc['lemma_prove']), mode)
                log.append({'step': f'lemma_proof:{n}', 'status': r['status'], 'cpu_s': round(_cpu() - c0, 3),
                            'label': labels[(th, n)]['label']})
                if r['status'] == 'THEOREM' and r['proof']:
                    usable.append(lemmas[n]); used.append((n, r['proof']))
        if b.left() >= 1:
            r = _prove(usable, goal, b.left(), mode)
            log.append({'step': 'goal_proof', 'status': r['status'], 'lemmas_used': [n for n, _ in used],
                        'cpu_s': round(b.used(), 3)})
            if r['status'] == 'THEOREM' and r['proof']:
                return {'status': 'PROVED', 'proof': r['proof'], 'lemma_proofs': used, 'log': log}
        return {'status': 'UNSETTLED', 'log': log}
    except Exception as exc:          # harness failures are recorded, never counted as outcomes
        return {'status': 'HARNESS_ERROR', 'reason': f'{type(exc).__name__}: {exc}', 'log': log}


def replay_outcome(problem, result, *, cache=None):
    """Lean replay of a PROVED outcome together with the proofs of the lemmas it used."""
    th = problem['theory']
    axioms = [parse(a) for a in THEORIES[th]]
    goal = parse(STATEMENTS[problem['goal']])
    lemmas = [(parse(STATEMENTS[n]), proof) for n, proof in result['lemma_proofs']]
    key = digest({'p': problem['problem_id'], 'g': result['proof'], 'l': [p for _, p in lemmas]})
    return F.replay(f'gc-{key[:16]}', axioms, goal, result['proof'], lemmas=lemmas, cache=cache)


# ---------------------------------------------------------------- analysis

def summarize(plan, problems, rows, labels):
    out = {'budgets': {}}
    n = len(problems)
    margin = max(1, math.ceil(0.05 * n))
    contradictions = []
    for p in problems:
        st = {r['status'] for r in rows if r['problem'] == p['problem_id']}
        lab = labels[(p['theory'], p['goal'])]['label']
        if {'PROVED', 'GHOST_FOUND'} <= st or ('PROVED' in st and lab == 'FALSE') or \
                ('GHOST_FOUND' in st and lab in ('TRUE', 'TRUE_UNCHECKED')):
            contradictions.append(p['problem_id'])
    for bud in plan['budgets_cpu_s']:
        mine = [r for r in rows if r['budget'] == bud]
        counts = {}
        for arm in plan['arms']:
            rs = [r for r in mine if r['arm'] == arm]
            c = {s: sum(r['status'] == s for r in rs) for s in ('PROVED', 'GHOST_FOUND', 'UNSETTLED', 'HARNESS_ERROR')}
            c['settled'] = c['PROVED'] + c['GHOST_FOUND']
            c['proved_checked'] = sum(r.get('replay') == 'THEOREM_CHECKED' for r in rs)
            c['settled_checked'] = c['proved_checked'] + c['GHOST_FOUND']
            c['cpu_s'] = round(sum(r['cpu_s'] for r in rs), 2)
            counts[arm] = c
        best = max(counts[a]['settled'] for a in plan['baselines'])
        best_arm = max(plan['baselines'], key=lambda a: (counts[a]['settled'], a))
        unsettled_by_best = sorted({r['problem'] for r in mine if r['arm'] == best_arm and
                                    r['status'] not in ('PROVED', 'GHOST_FOUND')})
        waste = sum(s['cpu_s'] for r in mine if r['arm'] == 'lemmas_unfiltered'
                    for s in r['log'] if s['step'].startswith('lemma_proof:') and s.get('label') == 'FALSE')
        dropped = sum(1 for r in mine if r['arm'] == 'ghost_lemmas'
                      for s in r['log'] if s.get('status') == 'FALSE_LEMMA_DROPPED')
        out['budgets'][str(bud)] = {
            'counts': counts, 'best_baseline': best_arm, 'best_baseline_settled': best,
            'headroom_problems': len(unsettled_by_best), 'headroom_fraction': round(len(unsettled_by_best) / n, 3),
            'oracle_gain': counts['oracle_lemmas']['settled'] - best,
            'oracle_gain_on_headroom': sum(1 for r in mine if r['arm'] == 'oracle_lemmas' and
                                           r['problem'] in unsettled_by_best and
                                           r['status'] in ('PROVED', 'GHOST_FOUND')),
            'mechanism_gain': {a: counts[a]['settled'] - best for a in plan['mechanism_arms']},
            'unfiltered_cpu_on_false_lemmas_s': round(waste, 2),
            'ghost_lemmas_false_lemmas_dropped': dropped}
    big = str(max(plan['budgets_cpu_s']))
    if contradictions:
        decision = 'HARNESS_ERROR'
    elif all(v['oracle_gain'] < margin for v in out['budgets'].values()):
        decision = 'RETIRE_NO_HEADROOM'
    elif max(out['budgets'][big]['mechanism_gain'].values()) >= margin:
        decision = 'PLAUSIBLE_BENEFIT'
    else:
        decision = 'RETIRE_MECHANISM_GAP'
    out.update(problems=n, margin=margin, contradictions=contradictions, decision=decision,
               consequence=plan['consequence'].get(decision))
    return out


# ---------------------------------------------------------------- faithfulness of the translation

def random_model(sig, size, rng):
    from itertools import product
    fns = {f: {args: rng.randrange(size) for args in product(range(size), repeat=a)}
           for f, a in sig['functions'].items()}
    return Model(size, fns, {})


def translation_checks(seed, per_statement=2, size=2):
    """(items, module source): Lean's `decide` must agree with `fol.evaluate` on random
    finite tables for every family formula (axioms and statements)."""
    rng = random.Random(seed)
    formulas = sorted({t for ax in THEORIES.values() for t in ax} | set(STATEMENTS.values()))
    items = []
    for text in formulas:
        f = parse(text)
        sig = signature([f])
        for _ in range(per_statement):
            m = random_model(sig, size, rng)
            items.append((f, m, evaluate(f, m)))
    return items, F.truth_table_module('GCTruth', items)


__all__ = ['THEORIES', 'STATEMENTS', 'PLAN', 'pools', 'label', 'family', 'run_arm', 'replay_outcome', 'summarize',
           'translation_checks']
