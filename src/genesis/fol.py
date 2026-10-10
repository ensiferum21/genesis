"""First-order logic subset (TPTP FOF style) with an independent finite-model evaluator.

Syntax accepted (one formula per item):
    ![X,Y]: phi   ?[X]: phi   ~phi   phi & psi   phi | psi   phi => psi   phi <=> psi
    s = t   s != t   p(t1,...)   f(t1,...)   constants and Variables (Uppercase)
Terms are function applications over constants/variables; predicates are
lowercase applications in formula position. `$true` / `$false` are allowed.

`evaluate(formula, model)` decides truth in a finite structure directly by
recursion over the syntax. It shares no code with the SAT encoding in
`modelfind.py`, so a countermodel found by the SAT route is re-checked here
independently before it is ever reported as a ghost.
"""
from dataclasses import dataclass
from itertools import product
import re

_TOKEN = re.compile(r"\s*(<=>|=>|!=|\$true|\$false|[A-Za-z_][A-Za-z0-9_]*|[!?~&|=(),:\[\]])")


class ParseError(ValueError):
    pass


def tokenize(text):
    pos, out = 0, []
    while pos < len(text):
        m = _TOKEN.match(text, pos)
        if not m or m.end() == pos:
            if text[pos:].strip() == '':
                break
            raise ParseError(f'unexpected input at {text[pos:pos + 20]!r}')
        out.append(m.group(1)); pos = m.end()
    return out


class _Parser:
    def __init__(self, text):
        self.t = tokenize(text); self.i = 0

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else None

    def take(self, expected=None):
        tok = self.peek()
        if tok is None or (expected and tok != expected):
            raise ParseError(f'expected {expected or "token"}, got {tok!r}')
        self.i += 1
        return tok

    def formula(self):
        left = self.binary()
        if self.peek() in ('=>', '<=>'):
            op = self.take(); right = self.formula()
            return ('imp' if op == '=>' else 'iff', left, right)
        return left

    def binary(self):
        left = self.unary()
        while self.peek() in ('&', '|'):
            op = self.take(); right = self.unary()
            left = ('and' if op == '&' else 'or', left, right)
        return left

    def unary(self):
        tok = self.peek()
        if tok == '~':
            self.take(); return ('not', self.unary())
        if tok in ('!', '?'):
            self.take(); self.take('[')
            names = [self.take()]
            while self.peek() == ',':
                self.take(); names.append(self.take())
            self.take(']'); self.take(':')
            body = self.unary()
            for name in reversed(names):
                if not name[0].isupper():
                    raise ParseError('quantified variables must be uppercase')
                body = ('all' if tok == '!' else 'ex', name, body)
            return body
        if tok == '(':
            self.take(); f = self.formula(); self.take(')'); return f
        if tok in ('$true', '$false'):
            self.take(); return ('const', tok == '$true')
        left = self.term()
        if self.peek() in ('=', '!='):
            op = self.take(); right = self.term()
            atom = ('eq', left, right)
            return atom if op == '=' else ('not', atom)
        if left[0] == 'var':
            raise ParseError('a variable is not a formula')
        return ('pred', left[1], left[2])

    def term(self):
        name = self.take()
        if not re.match(r'[A-Za-z_]', name):
            raise ParseError(f'bad term start {name!r}')
        if name[0].isupper():
            return ('var', name)
        args = []
        if self.peek() == '(':
            self.take(); args.append(self.term())
            while self.peek() == ',':
                self.take(); args.append(self.term())
            self.take(')')
        return ('fn', name, tuple(args))


def parse(text):
    p = _Parser(text)
    f = p.formula()
    if p.peek() is not None:
        raise ParseError(f'trailing input {p.peek()!r}')
    return f


def signature(formulas):
    """{'functions': {name: arity}, 'predicates': {name: arity}} with consistency checks."""
    fns, preds = {}, {}

    def term(t):
        if t[0] == 'fn':
            if fns.setdefault(t[1], len(t[2])) != len(t[2]):
                raise ParseError(f'inconsistent arity for {t[1]}')
            for a in t[2]:
                term(a)

    def form(f):
        k = f[0]
        if k == 'eq':
            term(f[1]); term(f[2])
        elif k == 'pred':
            if preds.setdefault(f[1], len(f[2])) != len(f[2]):
                raise ParseError(f'inconsistent arity for {f[1]}')
            for a in f[2]:
                term(a)
        elif k in ('and', 'or', 'imp', 'iff'):
            form(f[1]); form(f[2])
        elif k == 'not':
            form(f[1])
        elif k in ('all', 'ex'):
            form(f[2])
    for f in formulas:
        form(f)
    if set(fns) & set(preds):
        raise ParseError('a symbol is used both as function and predicate')
    return {'functions': fns, 'predicates': preds}


def free_vars(f, bound=frozenset()):
    k = f[0]
    if k == 'var':
        return set() if f[1] in bound else {f[1]}
    if k == 'fn':
        return set().union(*(free_vars(a, bound) for a in f[2])) if f[2] else set()
    if k == 'eq':
        return free_vars(f[1], bound) | free_vars(f[2], bound)
    if k == 'pred':
        return set().union(*(free_vars(a, bound) for a in f[2])) if f[2] else set()
    if k == 'not':
        return free_vars(f[1], bound)
    if k in ('and', 'or', 'imp', 'iff'):
        return free_vars(f[1], bound) | free_vars(f[2], bound)
    if k in ('all', 'ex'):
        return free_vars(f[2], bound | {f[1]})
    return set()


@dataclass
class Model:
    size: int
    functions: dict      # name -> {args tuple: value}
    predicates: dict     # name -> set of true args tuples

    def to_json(self):
        return {'size': self.size,
                'functions': {f: sorted([list(k), v] for k, v in t.items()) for f, t in sorted(self.functions.items())},
                'predicates': {p: sorted(list(k) for k in t) for p, t in sorted(self.predicates.items())}}


def _term_value(t, model, env):
    if t[0] == 'var':
        return env[t[1]]
    args = tuple(_term_value(a, model, env) for a in t[2])
    table = model.functions[t[1]]
    if args not in table:
        raise ValueError(f'function {t[1]} undefined at {args}')
    return table[args]


def evaluate(f, model, env=None):
    env = env or {}
    k = f[0]
    if k == 'const':
        return f[1]
    if k == 'eq':
        return _term_value(f[1], model, env) == _term_value(f[2], model, env)
    if k == 'pred':
        return tuple(_term_value(a, model, env) for a in f[2]) in model.predicates.get(f[1], set())
    if k == 'not':
        return not evaluate(f[1], model, env)
    if k == 'and':
        return evaluate(f[1], model, env) and evaluate(f[2], model, env)
    if k == 'or':
        return evaluate(f[1], model, env) or evaluate(f[2], model, env)
    if k == 'imp':
        return (not evaluate(f[1], model, env)) or evaluate(f[2], model, env)
    if k == 'iff':
        return evaluate(f[1], model, env) == evaluate(f[2], model, env)
    if k == 'all':
        return all(evaluate(f[2], model, {**env, f[1]: d}) for d in range(model.size))
    if k == 'ex':
        return any(evaluate(f[2], model, {**env, f[1]: d}) for d in range(model.size))
    raise ValueError(f'unknown node {k}')


def check_model(model, formulas, sig):
    """Independent validation that `model` is total on the signature and satisfies `formulas`."""
    for name, arity in sig['functions'].items():
        table = model.functions.get(name)
        if table is None or set(table) != set(product(range(model.size), repeat=arity)):
            return False, f'function {name} is not total on the domain'
        if any(not 0 <= v < model.size for v in table.values()):
            return False, f'function {name} leaves the domain'
    for i, f in enumerate(formulas):
        if free_vars(f):
            return False, f'formula {i} has free variables'
        if not evaluate(f, model):
            return False, f'formula {i} is false in the model'
    return True, None


def to_tptp(f):
    k = f[0]
    if k == 'var':
        return f[1]
    if k == 'fn':
        return f[1] + ('(' + ','.join(to_tptp(a) for a in f[2]) + ')' if f[2] else '')
    if k == 'const':
        return '$true' if f[1] else '$false'
    if k == 'eq':
        return f'{to_tptp(f[1])} = {to_tptp(f[2])}'
    if k == 'pred':
        return f[1] + ('(' + ','.join(to_tptp(a) for a in f[2]) + ')' if f[2] else '')
    if k == 'not':
        return f'~({to_tptp(f[1])})'
    sym = {'and': '&', 'or': '|', 'imp': '=>', 'iff': '<=>'}
    if k in sym:
        return f'({to_tptp(f[1])} {sym[k]} {to_tptp(f[2])})'
    if k in ('all', 'ex'):
        return f"{'!' if k == 'all' else '?'}[{f[1]}]: ({to_tptp(f[2])})"
    raise ValueError(k)
