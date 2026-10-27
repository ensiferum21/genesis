"""A small, safe expression language for graph bounds (research plane; F2, `docs/OMEGA_FRONTIER.md` §5).

Grammar (no `eval`, no names beyond the declared variables):

    expr    := term (('+' | '-') term)*
    term    := power (('*' | '/') power)*
    power   := unary ('^' INT)?            integer exponents only; roots are functions
    unary   := '-' unary | atom
    atom    := NUMBER | VAR | FUNC '(' expr ')' | '(' expr ')'
    FUNC    := sqrt | root4                 root4(x) = x^(1/4)

Variables: a vertex bound uses `d`, `m` (the vertex's degree and the average degree of its neighbours); an edge
bound uses `di`, `dj`, `mi`, `mj`. Numbers are integers or decimals (read exactly as fractions).

Two evaluators:
  * `evaluate(ast, env)`: floats, for search; a negative radicand or a zero divisor gives None (undefined);
  * `enclose(ast, env, bits)`: exact rational intervals [lo, hi] containing the true value, for verification:
    +, -, *, / and integer powers are exact interval operations on `fractions.Fraction`; sqrt and root4 are
    enclosed by integer square roots at a resolution of 2^-bits, so the true value always lies in the interval.
    A radicand whose interval is entirely negative, or a divisor interval containing 0, gives None (undefined, or
    not decidable at this resolution: the caller may retry with more bits).
A bound's value at a graph is the maximum over its vertices (or edges); if it is undefined anywhere the graph is
never taken as a counterexample (conservative).
"""
from fractions import Fraction
import math
import re

VERTEX_VARS = ('d', 'm')
EDGE_VARS = ('di', 'dj', 'mi', 'mj')
FUNCS = ('sqrt', 'root4')
_TOKEN = re.compile(r'\s*(?:(\d+(?:\.\d+)?)|([A-Za-z_][A-Za-z0-9_]*)|(\S))')


def tokens(text):
    out, pos = [], 0
    text = text.strip()
    while pos < len(text):
        mt = _TOKEN.match(text, pos)
        if not mt or mt.end() == pos:
            raise ValueError(f'cannot read {text[pos:]!r}')
        num, name, sym = mt.groups()
        if num is not None:
            out.append(('num', num))
        elif name is not None:
            out.append(('name', name))
        elif sym in '+-*/^()':
            out.append(('sym', sym))
        else:
            raise ValueError(f'unexpected {sym!r}')
        pos = mt.end()
    return out


class _Parser:
    def __init__(self, toks, variables):
        self.t, self.i, self.vars = toks, 0, variables

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else (None, None)

    def take(self, kind=None, value=None):
        k, v = self.peek()
        if k is None or (kind and k != kind) or (value is not None and v != value):
            raise ValueError(f'expected {value or kind} at token {self.i}, found {v!r}')
        self.i += 1
        return v

    def expr(self):
        node = self.term()
        while self.peek() in (('sym', '+'), ('sym', '-')):
            op = self.take()
            node = (op, node, self.term())
        return node

    def term(self):
        node = self.power()
        while self.peek() in (('sym', '*'), ('sym', '/')):
            op = self.take()
            node = (op, node, self.power())
        return node

    def power(self):
        node = self.unary()
        if self.peek() == ('sym', '^'):
            self.take()
            neg = False
            if self.peek() == ('sym', '-'):
                self.take()
                neg = True
            k, v = self.peek()
            if k != 'num' or '.' in v:
                raise ValueError('exponents must be integers (use sqrt or root4 for roots)')
            self.take()
            node = ('^', node, -int(v) if neg else int(v))
        return node

    def unary(self):
        if self.peek() == ('sym', '-'):
            self.take()
            return ('neg', self.unary())
        return self.atom()

    def atom(self):
        k, v = self.peek()
        if k == 'num':
            self.take()
            return ('num', Fraction(v))
        if k == 'name':
            self.take()
            if v in FUNCS:
                self.take('sym', '(')
                inner = self.expr()
                self.take('sym', ')')
                return (v, inner)
            if v not in self.vars:
                raise ValueError(f'unknown variable {v!r} (allowed: {self.vars})')
            return ('var', v)
        if (k, v) == ('sym', '('):
            self.take()
            inner = self.expr()
            self.take('sym', ')')
            return inner
        raise ValueError(f'unexpected {v!r}')


def parse(text, kind):
    """The AST of a bound's right-hand side; kind 'vertex' or 'edge'."""
    variables = {'vertex': VERTEX_VARS, 'edge': EDGE_VARS}[kind]
    p = _Parser(tokens(text), variables)
    node = p.expr()
    if p.i != len(p.t):
        raise ValueError(f'trailing input at token {p.i}')
    return node


def variables_of(node):
    if node[0] == 'var':
        return {node[1]}
    if node[0] == 'num':
        return set()
    if node[0] in ('neg', 'sqrt', 'root4'):
        return variables_of(node[1])
    if node[0] == '^':
        return variables_of(node[1])
    return variables_of(node[1]) | variables_of(node[2])


def render(node):
    """A canonical text (fully parenthesised): equal ASTs render equally."""
    k = node[0]
    if k == 'num':
        return str(node[1])
    if k == 'var':
        return node[1]
    if k == 'neg':
        return f'(-{render(node[1])})'
    if k in FUNCS:
        return f'{k}({render(node[1])})'
    if k == '^':
        return f'({render(node[1])}^{node[2]})'
    return f'({render(node[1])}{k}{render(node[2])})'


# ------------------------------------------------------------------------------------------------- floats

def evaluate(node, env):
    """Float value, or None where undefined."""
    k = node[0]
    if k == 'num':
        return float(node[1])
    if k == 'var':
        return float(env[node[1]])
    if k == 'neg':
        x = evaluate(node[1], env)
        return None if x is None else -x
    if k in FUNCS:
        x = evaluate(node[1], env)
        if x is None or x < 0:
            return None
        return math.sqrt(x) if k == 'sqrt' else math.sqrt(math.sqrt(x))
    if k == '^':
        x = evaluate(node[1], env)
        if x is None or (x == 0 and node[2] < 0):
            return None
        return x ** node[2]
    a, b = evaluate(node[1], env), evaluate(node[2], env)
    if a is None or b is None:
        return None
    if k == '+':
        return a + b
    if k == '-':
        return a - b
    if k == '*':
        return a * b
    if b == 0:
        return None
    return a / b


# ---------------------------------------------------------------------------------------- exact intervals

def _sqrt_lo(x, bits):
    """A rational <= sqrt(x) within 2^-bits (x a nonnegative Fraction)."""
    scale = 1 << (2 * bits)
    return Fraction(math.isqrt((x.numerator * scale) // x.denominator), 1 << bits)


def _sqrt_hi(x, bits):
    """A rational >= sqrt(x) within 2^-bits."""
    scale = 1 << (2 * bits)
    n = -((-x.numerator * scale) // x.denominator)          # ceil(x * 4^bits)
    r = math.isqrt(n)
    if r * r < n:
        r += 1
    return Fraction(r, 1 << bits)


def _mul(a, b):
    ps = (a[0] * b[0], a[0] * b[1], a[1] * b[0], a[1] * b[1])
    return (min(ps), max(ps))


def _pow(a, k):
    if k == 0:
        return (Fraction(1), Fraction(1))
    if k < 0:
        inv = _inv(a)
        return None if inv is None else _pow(inv, -k)
    lo, hi = a
    if k % 2 == 1 or lo >= 0:
        return (lo ** k, hi ** k) if lo >= 0 or k % 2 == 1 else None
    if hi <= 0:
        return (hi ** k, lo ** k)
    return (Fraction(0), max(lo ** k, hi ** k))


def _inv(a):
    if a[0] <= 0 <= a[1]:
        return None
    return (1 / a[1], 1 / a[0])


def enclose(node, env, bits=64):
    """An exact rational interval (lo, hi) containing the value, or None (undefined or undecidable here)."""
    k = node[0]
    if k == 'num':
        return (node[1], node[1])
    if k == 'var':
        x = Fraction(env[node[1]])
        return (x, x)
    if k == 'neg':
        x = enclose(node[1], env, bits)
        return None if x is None else (-x[1], -x[0])
    if k in FUNCS:
        x = enclose(node[1], env, bits)
        if x is None or x[1] < 0:
            return None
        lo = max(x[0], Fraction(0))
        if x[0] < 0:
            return None                 # straddles 0: not decidable at this resolution
        r = (_sqrt_lo(lo, bits), _sqrt_hi(x[1], bits))
        if k == 'root4':
            r = (_sqrt_lo(r[0], bits), _sqrt_hi(r[1], bits))
        return r
    if k == '^':
        x = enclose(node[1], env, bits)
        return None if x is None else _pow(x, node[2])
    a, b = enclose(node[1], env, bits), enclose(node[2], env, bits)
    if a is None or b is None:
        return None
    if k == '+':
        return (a[0] + b[0], a[1] + b[1])
    if k == '-':
        return (a[0] - b[1], a[1] - b[0])
    if k == '*':
        return _mul(a, b)
    inv = _inv(b)
    return None if inv is None else _mul(a, inv)


# ------------------------------------------------------------------------------------------- numpy (search)

def compile_numpy(node):
    """A function of numpy arrays (one per variable) giving the elementwise value; NaN where undefined. For search
    only: verification uses `enclose`."""
    import numpy as np

    def build(n):
        k = n[0]
        if k == 'num':
            v = float(n[1])
            return lambda env: v
        if k == 'var':
            name = n[1]
            return lambda env: env[name]
        if k == 'neg':
            f = build(n[1])
            return lambda env: -f(env)
        if k == 'sqrt':
            f = build(n[1])
            return lambda env: np.sqrt(np.where(f(env) >= 0, f(env), np.nan))
        if k == 'root4':
            f = build(n[1])
            return lambda env: np.sqrt(np.sqrt(np.where(f(env) >= 0, f(env), np.nan)))
        if k == '^':
            f, e = build(n[1]), n[2]
            if e >= 0:
                return lambda env: f(env) ** e
            return lambda env: np.where(f(env) != 0, 1.0 / np.where(f(env) != 0, f(env), 1.0) ** (-e), np.nan)
        a, b = build(n[1]), build(n[2])
        if k == '+':
            return lambda env: a(env) + b(env)
        if k == '-':
            return lambda env: a(env) - b(env)
        if k == '*':
            return lambda env: a(env) * b(env)
        return lambda env: np.where(b(env) != 0, a(env) / np.where(b(env) != 0, b(env), 1.0), np.nan)
    f = build(node)

    def run(env):
        with np.errstate(invalid='ignore', divide='ignore', over='ignore'):
            out = f(env)
        return out
    return run
