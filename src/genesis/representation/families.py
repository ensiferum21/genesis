"""Problem families given only as constraints on values, for reductions Genesis synthesises itself (representation
language, stage C; directive items 4 and 6).

The builder writes, per family: a generator, the constraints as **predicates** (which assignments a constraint
allows, nothing about how to encode them), an independent checker, and the natural MaxSAT encoding the specialists
use. The builder writes **no** QUBO, penalty or reduction. Genesis turns each family into one BQP by synthesising and
verifying the gadgets its relations need (`gadgets`, `library`), and parks what it cannot synthesise.

Families (all on literals of n Boolean variables; m constraints of arity 3 drawn uniformly, signs at random):
  * `one_in_three`: exactly one literal true (1-in-3 SAT; Schaefer 1978);
  * `nae3`: not all three literals equal (NAE-3SAT);
  * `xor3`: an odd number of the three literals true (XOR-3SAT, as a Max-CSP);
  * `max3sat`: at least one literal true.
Each is a weighted Max-CSP (every constraint weight 1): the score is the number of satisfied constraints, maximised.
"""
import random

from .relations import Relation, clause, exactly, nae, parity

FAMILIES = ('one_in_three', 'nae3', 'xor3', 'max3sat')
BASE = {'one_in_three': exactly(3, 1), 'nae3': nae(3), 'xor3': parity(3, 1), 'max3sat': clause([True, True, True])}


def generate(family, seed, params):
    """{'n', 'constraints': [[l1, l2, l3]]} with literals +/-(i + 1)."""
    if family not in FAMILIES:
        raise ValueError(f'unknown family {family!r}')
    rng = random.Random(f'repr-family|{family}|{seed}|{sorted(params.items())}')
    n, m = params['n'], params['m']
    cons = []
    for _ in range(m):
        vs = rng.sample(range(1, n + 1), 3)
        cons.append([v * rng.choice((1, -1)) for v in vs])
    return {'family': family, 'n': n, 'constraints': cons}


def relation_of(family, lits):
    """The family's relation on the constraint's three variables, with the literals' signs applied."""
    flips = sum(1 << j for j, l in enumerate(lits) if l < 0)
    return BASE[family].transform([0, 1, 2], flips)


def spec(inst):
    """The instance as a constraint problem for `compile` (Max-CSP)."""
    cons = [{'relation': relation_of(inst['family'], c).to_json(), 'vars': [abs(l) - 1 for l in c], 'weight': 1}
            for c in inst['constraints']]
    return {'n': inst['n'], 'constraints': cons, 'objective': None}


def satisfied(family, lits, x):
    vals = [x[abs(l) - 1] == (1 if l > 0 else 0) for l in lits]
    t = sum(vals)
    if family == 'one_in_three':
        return t == 1
    if family == 'nae3':
        return 0 < t < 3
    if family == 'xor3':
        return t % 2 == 1
    if family == 'max3sat':
        return t >= 1
    raise ValueError(family)


def check(inst, x):
    """(valid, satisfied constraints): the family's own checker, from the instance alone (not from any encoding)."""
    if len(x) < inst['n'] or any(v not in (0, 1) for v in x[:inst['n']]):
        return False, None
    return True, sum(satisfied(inst['family'], c, x) for c in inst['constraints'])


def wcnf(inst):
    """The natural weighted partial MaxSAT encoding (the specialists' input): soft clauses only, one group per
    constraint, a constraint's clauses each weighted 1 where a violated constraint violates exactly one of them
    (nae3, xor3, max3sat); 1-in-3 SAT uses an at-least-one clause and three at-most-one clauses, each weight 1, so its
    cost counts violated clauses, not constraints (the solver's score is re-checked by `check`)."""
    soft = []
    for a, b, c in inst['constraints']:
        if inst['family'] == 'max3sat':
            soft.append([a, b, c])
        elif inst['family'] == 'nae3':
            soft += [[a, b, c], [-a, -b, -c]]
        elif inst['family'] == 'xor3':
            soft += [[a, b, c], [a, -b, -c], [-a, b, -c], [-a, -b, c]]
        elif inst['family'] == 'one_in_three':
            soft += [[a, b, c], [-a, -b], [-a, -c], [-b, -c]]
    return {'n_vars': inst['n'], 'hard': [], 'soft': [[1, cl] for cl in soft]}


__all__ = ['FAMILIES', 'BASE', 'generate', 'relation_of', 'spec', 'satisfied', 'check', 'wcnf', 'Relation']
