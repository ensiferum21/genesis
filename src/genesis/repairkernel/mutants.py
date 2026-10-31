"""Random defects by mutation (kernel side; for SR-2c, `docs/OMEGA_RULE_INVENTION.md` §6).

B20_R182's held-out catalogue was written by the author of the repair grammar, who knew which classes the loop had
missed; several of its defects fell in classes the grammar has productions for. A catalogue that tests whether Genesis
can invent what is missing must not be chosen by that author. This module draws defects the way mutation testing does
(DeMillo, Lipton and Sayward 1978; Offutt's sufficient operators; Just et al. 2014: detectable mutants stand in for
real faults): every way one of a small set of operators changes one place in a component's methods is enumerated, the
list is shuffled with a fixed seed, and the first mutants that are *real obstacles* are kept, in that order:
  * the source parses and the kernel's static guard accepts it (it only re-arranges the component's own tokens);
  * it is not the source of any defect of the four hand-written catalogues (those are development data);
  * every job of the study's seeds is interrupted by it (it is detectable by the job's own checks);
  * the independent verifier rejects it, and accepts the correct source on the same job.

The operators (one change each, in a method other than `__init__`):
  * 'delete': a simple statement (assignment, augmented assignment, call, deletion) removed, its block kept non-empty;
  * 'arith': `+` and `-` exchanged (binary or augmented);
  * 'compare': `<`/`<=`, `>`/`>=`, `==`/`!=`, `in`/`not in` exchanged;
  * 'constant': an integer constant c made c + 1 or c - 1;
  * 'swap': the two arguments of a two-argument call exchanged;
  * 'attribute': `self.a` read or written in place of `self.b`, both attributes holding the same kind of value;
  * 'call': `max`/`min`, `add`/`discard`, `append`/`remove` exchanged.
The selection uses nothing but these rules, the seed and the components; the mutants are written once to a sealed
catalogue (`defects5.py`) by `scripts/b20r184_make_mutant_catalogue.py`, before any code that is to repair them."""
import ast
import random

OPERATORS = ('delete', 'arith', 'compare', 'constant', 'swap', 'attribute', 'call')
COMPARE = {ast.Lt: ('<', '<='), ast.LtE: ('<=', '<'), ast.Gt: ('>', '>='), ast.GtE: ('>=', '>'),
           ast.Eq: ('==', '!='), ast.NotEq: ('!=', '=='), ast.In: (' in ', ' not in '), ast.NotIn: (' not in ', ' in ')}
CALLS = {'max': 'min', 'min': 'max', 'add': 'discard', 'discard': 'add', 'append': 'remove', 'remove': 'append'}
SIMPLE = (ast.Assign, ast.AugAssign, ast.Expr, ast.Delete)


def _kinds(tree):
    kinds = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Attribute) \
                and isinstance(n.targets[0].value, ast.Name) and n.targets[0].value.id == 'self':
            v = n.value
            k = ('dict' if isinstance(v, ast.Dict) else 'list' if isinstance(v, ast.List) else
                 'set' if isinstance(v, ast.Call) and getattr(v.func, 'id', '') == 'set' else
                 'int' if isinstance(v, ast.Constant) and type(v.value) is int else None)
            if k:
                kinds.setdefault(n.targets[0].attr, k)
    return kinds


def _offset(lines, lineno, col):
    return sum(len(x) + 1 for x in lines[:lineno - 1]) + col


def _span(src, lines, node):
    return _offset(lines, node.lineno, node.col_offset), _offset(lines, node.end_lineno, node.end_col_offset)


def _methods(tree):
    for c in ast.walk(tree):
        if isinstance(c, ast.ClassDef):
            for f in c.body:
                if isinstance(f, ast.FunctionDef) and f.name != '__init__':
                    yield f


def _blocks(f):
    for n in ast.walk(f):
        for field in ('body', 'orelse'):
            b = getattr(n, field, None)
            if isinstance(b, list) and b and isinstance(b[0], ast.stmt):
                yield b


def enumerate_mutants(target, src):
    """Every single-place mutant of the component's methods: [(operator, description, mutant source)], in source
    order, duplicates (the same mutant source) removed."""
    tree = ast.parse(src)
    lines = src.split('\n')
    kinds = _kinds(tree)
    out = []

    def sub(a, b, text, op, what):
        out.append((op, what, src[:a] + text + src[b:]))

    for f in _methods(tree):
        doc = f.body[0] if isinstance(f.body[0], ast.Expr) and isinstance(f.body[0].value, ast.Constant) else None
        for body in _blocks(f):
            for st in body:
                if st is doc or not isinstance(st, SIMPLE) or len(body) < 2:
                    continue
                if isinstance(st, ast.Expr) and not isinstance(st.value, ast.Call):
                    continue
                a = _offset(lines, st.lineno, 0)
                b = _offset(lines, st.end_lineno + 1, 0) if st.end_lineno < len(lines) else len(src)
                sub(a, b, '', 'delete', f'{f.name}:{st.lineno} delete {ast.unparse(st)!r}')
        for n in ast.walk(f):
            if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Sub)) and n.lineno == n.end_lineno:
                a = _offset(lines, n.left.end_lineno, n.left.end_col_offset)
                b = _offset(lines, n.right.lineno, n.right.col_offset)
                mid = src[a:b]
                o, p = ('+', '-') if isinstance(n.op, ast.Add) else ('-', '+')
                if mid.count(o) == 1:
                    sub(a, b, mid.replace(o, p), 'arith', f'{f.name}:{n.lineno} {o} -> {p} in {ast.unparse(n)!r}')
            if isinstance(n, ast.AugAssign) and isinstance(n.op, (ast.Add, ast.Sub)) and n.lineno == n.end_lineno:
                a = _offset(lines, n.target.end_lineno, n.target.end_col_offset)
                b = _offset(lines, n.value.lineno, n.value.col_offset)
                mid = src[a:b]
                o, p = ('+=', '-=') if isinstance(n.op, ast.Add) else ('-=', '+=')
                if mid.count(o) == 1:
                    sub(a, b, mid.replace(o, p), 'arith', f'{f.name}:{n.lineno} {o} -> {p} in {ast.unparse(n)!r}')
            if isinstance(n, ast.Compare) and len(n.ops) == 1 and type(n.ops[0]) in COMPARE and n.lineno == n.end_lineno:
                a = _offset(lines, n.left.end_lineno, n.left.end_col_offset)
                b = _offset(lines, n.comparators[0].lineno, n.comparators[0].col_offset)
                mid = src[a:b]
                o, p = COMPARE[type(n.ops[0])]
                if mid.strip() == o.strip():
                    new = mid.replace(o.strip(), p.strip())
                    sub(a, b, new, 'compare', f'{f.name}:{n.lineno} {o.strip()} -> {p.strip()} in {ast.unparse(n)!r}')
            if isinstance(n, ast.Constant) and type(n.value) is int and n.lineno == n.end_lineno:
                a, b = _span(src, lines, n)
                if src[a:b] == repr(n.value):
                    for v in (n.value + 1, n.value - 1):
                        sub(a, b, repr(v), 'constant', f'{f.name}:{n.lineno} {n.value} -> {v}')
            if isinstance(n, ast.Call) and len(n.args) == 2 and not n.keywords and n.lineno == n.end_lineno:
                x, y = n.args
                if all(isinstance(z, (ast.Name, ast.Attribute, ast.Constant)) for z in (x, y)):
                    (a1, b1), (a2, b2) = _span(src, lines, x), _span(src, lines, y)
                    tx, ty = src[a1:b1], src[a2:b2]
                    if tx != ty:
                        out.append(('swap', f'{f.name}:{n.lineno} swap {ast.unparse(n)!r}',
                                    src[:a1] + ty + src[b1:a2] + tx + src[b2:]))
            if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == 'self' \
                    and n.attr in kinds and n.lineno == n.end_lineno:
                a, b = _span(src, lines, n)
                for other in sorted(kinds):
                    if other != n.attr and kinds[other] == kinds[n.attr]:
                        sub(a, b, f'self.{other}', 'attribute', f'{f.name}:{n.lineno} self.{n.attr} -> self.{other}')
            if isinstance(n, ast.Call):
                fn = n.func
                name = fn.id if isinstance(fn, ast.Name) else fn.attr if isinstance(fn, ast.Attribute) else None
                if name in CALLS and fn.lineno == fn.end_lineno:
                    a, b = _span(src, lines, fn)
                    text = src[a:b]
                    if text.endswith(name):
                        sub(a, b, text[:-len(name)] + CALLS[name], 'call', f'{f.name}:{n.lineno} {name} -> {CALLS[name]}')
    seen, res = {src}, []
    for op, what, m in out:
        if m in seen:
            continue
        try:
            ast.parse(m)
        except SyntaxError:
            continue
        seen.add(m)
        res.append((op, what, m))
    return res


def as_defect(src, mutant):
    """The mutant as a catalogue entry's ('old', 'new'): the smallest window of whole lines around the change whose
    old text occurs once in the source."""
    a, b = src.split('\n'), mutant.split('\n')
    i = 0
    while i < min(len(a), len(b)) and a[i] == b[i]:
        i += 1
    j = 0
    while j < min(len(a), len(b)) - i and a[-1 - j] == b[-1 - j]:
        j += 1
    lo, hi_a, hi_b = i, len(a) - j, len(b) - j
    while True:
        old, new = '\n'.join(a[lo:hi_a]), '\n'.join(b[lo:hi_b])
        if old and src.count(old) == 1 and src.replace(old, new) == mutant:
            return old, new
        if lo > 0:
            lo -= 1
        elif hi_a < len(a):
            hi_a += 1
            hi_b += 1
        else:
            raise ValueError('no unique window')


def shuffled(sources, seed):
    """Every mutant of every component, as (target, operator, description, source), shuffled with `seed`."""
    allm = [(t, op, what, m) for t in sorted(sources) for op, what, m in enumerate_mutants(t, sources[t])]
    random.Random(seed).shuffle(allm)
    return allm
