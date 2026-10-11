"""SAT-based finite model finder (Mace-style) for the FOF subset.

For domain size d, every function value f(a1..ak) is a one-hot Boolean vector
and every predicate atom a Boolean. Ground terms get memoized "term has value c"
variables defined by Tseitin equivalences; quantifiers are expanded over the
domain. CaDiCaL (pinned) searches; any model it returns is converted to tables
and re-checked by the independent evaluator in `fol.py` before use. A size-d
UNSAT answer only says "no model of size d" — it is never read as a proof.
"""
import math
import time
from itertools import product

from .fol import Model, check_model, signature
from .verification.sat import solve


class _CNF:
    def __init__(self):
        self.n = 0; self.clauses = []; self.true = self.var(); self.clauses.append([self.true])

    def var(self):
        self.n += 1
        return self.n

    def add(self, clause):
        self.clauses.append(list(clause))

    def AND(self, lits):
        lits = list(lits)
        if not lits:
            return self.true
        if len(lits) == 1:
            return lits[0]
        v = self.var()
        for l in lits:
            self.add([-v, l])
        self.add([v] + [-l for l in lits])
        return v

    def OR(self, lits):
        lits = list(lits)
        if not lits:
            return -self.true
        if len(lits) == 1:
            return lits[0]
        v = self.var()
        self.add([-v] + lits)
        for l in lits:
            self.add([v, -l])
        return v

    def dimacs(self):
        return ('p cnf %d %d\n' % (self.n, len(self.clauses)) +
                ''.join(' '.join(map(str, c)) + ' 0\n' for c in self.clauses)).encode()


def encode(formulas, size, sig):
    cnf = _CNF()
    fvar = {}   # (f, args, value) -> var
    pvar = {}   # (p, args) -> var
    for f, arity in sig['functions'].items():
        for args in product(range(size), repeat=arity):
            vs = [cnf.var() for _ in range(size)]
            for c, v in enumerate(vs):
                fvar[(f, args, c)] = v
            cnf.add(vs)
            for i in range(size):
                for j in range(i + 1, size):
                    cnf.add([-vs[i], -vs[j]])
    for p, arity in sig['predicates'].items():
        for args in product(range(size), repeat=arity):
            pvar[(p, args)] = cnf.var()
    # Least-number symmetry breaking for nullary functions (constants), in sorted order.
    consts = sorted(f for f, a in sig['functions'].items() if a == 0)
    for i, c in enumerate(consts):
        for value in range(i + 1, size):
            cnf.add([-fvar[(c, (), value)]])

    memo = {}

    def term_is(t, env, c):
        """Literal true iff ground term t (under env) evaluates to c."""
        if t[0] == 'var':
            return cnf.true if env[t[1]] == c else -cnf.true
        key = (t, tuple(sorted((k, v) for k, v in env.items() if k in _vars(t))), c)
        if key in memo:
            return memo[key]
        if not t[2]:
            lit = fvar[(t[1], (), c)]
        else:
            options = []
            for args in product(range(size), repeat=len(t[2])):
                parts = [term_is(a, env, v) for a, v in zip(t[2], args)]
                if any(p == -cnf.true for p in parts):
                    continue
                options.append(cnf.AND([p for p in parts if p != cnf.true] + [fvar[(t[1], args, c)]]))
            lit = cnf.OR(options)
        memo[key] = lit
        return lit

    def form(f, env):
        k = f[0]
        if k == 'const':
            return cnf.true if f[1] else -cnf.true
        if k == 'eq':
            return cnf.OR([cnf.AND([term_is(f[1], env, c), term_is(f[2], env, c)]) for c in range(size)])
        if k == 'pred':
            options = []
            for args in product(range(size), repeat=len(f[2])):
                parts = [term_is(a, env, v) for a, v in zip(f[2], args)]
                options.append(cnf.AND(parts + [pvar[(f[1], args)]]))
            return cnf.OR(options) if f[2] else pvar[(f[1], ())]
        if k == 'not':
            return -form(f[1], env)
        if k == 'and':
            return cnf.AND([form(f[1], env), form(f[2], env)])
        if k == 'or':
            return cnf.OR([form(f[1], env), form(f[2], env)])
        if k == 'imp':
            return cnf.OR([-form(f[1], env), form(f[2], env)])
        if k == 'iff':
            a, b = form(f[1], env), form(f[2], env)
            return cnf.AND([cnf.OR([-a, b]), cnf.OR([a, -b])])
        if k == 'all':
            return cnf.AND([form(f[2], {**env, f[1]: d}) for d in range(size)])
        if k == 'ex':
            return cnf.OR([form(f[2], {**env, f[1]: d}) for d in range(size)])
        raise ValueError(k)

    for f in formulas:
        cnf.add([form(f, {})])
    return cnf, fvar, pvar


_VAR_CACHE = {}


def _vars(t):
    if t in _VAR_CACHE:
        return _VAR_CACHE[t]
    if t[0] == 'var':
        out = {t[1]}
    else:
        out = set().union(*(_vars(a) for a in t[2])) if t[2] else set()
    _VAR_CACHE[t] = frozenset(out)
    return _VAR_CACHE[t]


def find_model(formulas, *, max_size=6, seconds=30, total_seconds=None):
    """Return (Model | None, record). The model is independently re-checked.
    `seconds` bounds each size; `total_seconds`, when given, bounds the whole search
    (wall clock of the solver calls), and an exhausted budget is reported UNKNOWN."""
    sig = signature(formulas)
    attempts = []
    start = time.monotonic()
    for size in range(1, max_size + 1):
        per = seconds
        if total_seconds is not None:
            # The solver's timeout has whole-second granularity, so a remaining fraction of
            # a second still gets one call (B19 fix: requiring a full second left starved
            # every size after the first under a one-second budget).
            remaining = total_seconds - (time.monotonic() - start)
            if remaining <= 0:
                return None, {'status': 'UNKNOWN', 'reason': 'budget exhausted', 'attempts': attempts}
            per = min(seconds, max(1, math.ceil(remaining)))
        cnf, fvar, pvar = encode(formulas, size, sig)
        result = solve(cnf.dimacs(), seconds=max(1, int(per)))
        attempts.append({'size': size, 'status': result['status'], 'vars': cnf.n, 'clauses': len(cnf.clauses),
                         'seconds': result['seconds']})
        if result['status'] == 'SAT':
            true = result['model']
            functions = {f: {} for f in sig['functions']}
            for (f, args, c), v in fvar.items():
                if v in true:
                    functions[f][args] = c
            predicates = {p: {args for (q, args), v in pvar.items() if q == p and v in true}
                          for p in sig['predicates']}
            model = Model(size, functions, predicates)
            ok, why = check_model(model, formulas, sig)
            if not ok:
                return None, {'status': 'HARNESS_ERROR', 'reason': f'SAT model failed independent check: {why}',
                              'attempts': attempts}
            return model, {'status': 'MODEL_FOUND', 'size': size, 'attempts': attempts}
        if result['status'] == 'UNKNOWN':
            return None, {'status': 'UNKNOWN', 'attempts': attempts}
    return None, {'status': 'NO_MODEL_UP_TO_SIZE', 'max_size': max_size, 'attempts': attempts}
