"""Patch synthesis (research plane; `docs/OMEGA_SELF_REPAIR.md` §2.4). No language model: candidates come from edit
operators over the repairable file, applied as **line-preserving text edits** (a statement's lines, or an expression's
columns), so that a patch changes only what it must.

**The operators**, each a small, general program transformation:
  * statements: swap two neighbours, move one up to three places, delete one;
  * expressions: flip a comparison within its family (<, <=, >, >=; ==, !=; in, not in; is, is not), flip + and -,
    move an integer by one, flip a boolean, swap min and max or any and all, add or remove a copy (`list(x)`), add or
    remove the index of `pop`;
  * **homologous recombination**: a statement transplanted from a sibling method of the same class into the suspected
    method, where every name it uses is defined (in nature, a damaged strand is repaired from its intact homologue);
  * **law restoration**: when a conservation law (`probe`) breaks first in a method, statements that restore it are
    inserted after the statements of that method which change the law's quantity: for "X is None or X == f(Y)",
    `self.X = None` after each change to Y (invalidation); for "set(A) == set(B)", the paired change to B after each
    change to A.

**The search** is clonal selection with annealing, after the adaptive immune system and statistical physics:
  * every candidate (an antibody) has an energy (lower is better): failing the reproducer, weighted by how early it
    fails (a candidate that gets further is closer: the energy landscape is graded, not flat); failing the trials
    that failed before; failing visible tests; breaking a conserved law; and its size (Occam);
  * **negative selection**: a candidate that changes the behaviour of a trial that passed before is near-eliminated
    (it attacks "self"), the analogue of the thymus removing self-reactive cells;
  * the first repertoire is every single edit at the suspected lines and methods, ordered by the obstacle model's
    posterior and the law-restoring edits first; the best are cloned in proportion to their rank and hypermutated
    (one more edit), and a clone replaces its parent if its energy is lower, or with probability exp(-dE / T) at a
    temperature T that cools each generation;
  * the search stops at the first generation that holds a candidate passing everything it can see, and returns the
    smallest such patch; or when its evaluation budget is spent.
What the search can see is the job's own failure and trials, the visible tests and the mined laws; never the
verifier's hidden tests or fresh seeds."""
import ast
import math
import random

COMPARE_FAMILIES = ((ast.Lt, ast.LtE, ast.Gt, ast.GtE), (ast.Eq, ast.NotEq), (ast.In, ast.NotIn), (ast.Is, ast.IsNot))
OP_TEXT = {ast.Lt: '<', ast.LtE: '<=', ast.Gt: '>', ast.GtE: '>=', ast.Eq: '==', ast.NotEq: '!=', ast.In: 'in',
           ast.NotIn: 'not in', ast.Is: 'is', ast.IsNot: 'is not'}
NAME_SWAPS = {'min': 'max', 'max': 'min', 'any': 'all', 'all': 'any'}
PAIR_OPS = {  # a change to A, the paired change to B by B's kind
    'set': {'append': 'add', 'add': 'add', 'remove': 'discard', 'discard': 'discard', 'pop': 'discard'},
    'list': {'append': 'append', 'add': 'append', 'remove': 'remove', 'discard': 'remove'},
}
MUTATORS = ('append', 'add', 'remove', 'discard', 'pop', 'clear', 'extend', 'insert', 'update', 'popitem',
            'move_to_end', 'setdefault')


# ------------------------------------------------------------------------------------------------- text editing

def _lines(src):
    return src.split('\n')


def _stmt_block(lines, node):
    return lines[node.lineno - 1:node.end_lineno]


def _indent(line):
    return line[:len(line) - len(line.lstrip())]


def _bodies(tree):
    """Every statement list with the function it belongs to: [(function name, body list)]."""
    out = []

    def walk(node, func):
        for field in ('body', 'orelse', 'finalbody'):
            body = getattr(node, field, None)
            if isinstance(body, list) and body and isinstance(body[0], ast.stmt):
                out.append((func, body))
                for st in body:
                    f = st.name if isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef)) else func
                    walk(st, f)
        for h in getattr(node, 'handlers', []) or []:
            out.append((func, h.body))
            for st in h.body:
                walk(st, func)
    walk(tree, None)
    return out


def _replace_cols(src, node, text):
    if node.lineno != node.end_lineno:
        return None
    lines = _lines(src)
    ln = lines[node.lineno - 1]
    lines[node.lineno - 1] = ln[:node.col_offset] + text + ln[node.end_col_offset:]
    return '\n'.join(lines)


def _seg(src, node):
    return ast.get_source_segment(src, node)


def swap(src, a, b):
    lines = _lines(src)
    A, B = _stmt_block(lines, a), _stmt_block(lines, b)
    mid = lines[a.end_lineno:b.lineno - 1]
    return '\n'.join(lines[:a.lineno - 1] + B + mid + A + lines[b.end_lineno:])


def delete(src, node, body):
    lines = _lines(src)
    if len(body) == 1:
        return '\n'.join(lines[:node.lineno - 1] + [_indent(lines[node.lineno - 1]) + 'pass'] + lines[node.end_lineno:])
    return '\n'.join(lines[:node.lineno - 1] + lines[node.end_lineno:])


def insert_after(src, node, text):
    lines = _lines(src)
    ind = _indent(lines[node.lineno - 1])
    return '\n'.join(lines[:node.end_lineno] + [ind + text] + lines[node.end_lineno:])


def insert_before(src, node, text):
    lines = _lines(src)
    ind = _indent(lines[node.lineno - 1])
    return '\n'.join(lines[:node.lineno - 1] + [ind + text] + lines[node.lineno - 1:])


# ------------------------------------------------------------------------------------------------- operators

def _in_focus(node, focus_lines):
    if not hasattr(node, 'lineno'):
        return False
    return focus_lines is None or any(node.lineno <= ln <= node.end_lineno for ln in focus_lines)


def local_edits(src, focus_lines=None, focus_funcs=None):
    """Every single edit of the local operators at the focus (lines, or functions; None = everywhere)."""
    tree = ast.parse(src)
    out = []

    def ok_func(f):
        return focus_funcs is None or f in focus_funcs

    for func, body in _bodies(tree):
        if not ok_func(func):
            continue
        for i, st in enumerate(body):
            if isinstance(st, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
                continue
            if not _in_focus(st, focus_lines):
                continue
            for j in range(i + 1, min(len(body), i + 4)):
                if isinstance(body[j], (ast.FunctionDef, ast.ClassDef)):
                    break
                new = src
                for k in range(i, j):          # move statement i down to j by neighbour swaps
                    t = ast.parse(new)
                    b = next(bb for ff, bb in _bodies(t) if ff == func and bb[0].lineno == body[0].lineno)
                    new = swap(new, b[k], b[k + 1])
                out.append((f'move {func}:{st.lineno} down {j - i}', new))
            out.append((f'delete {func}:{st.lineno}', delete(src, st, body)))
    for node in ast.walk(tree):
        if not _in_focus(node, focus_lines):
            continue
        func = _func_of(tree, node)
        if not ok_func(func):
            continue
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            fam = next((f for f in COMPARE_FAMILIES if type(node.ops[0]) in f), None)
            for op in fam or ():
                if op is type(node.ops[0]):
                    continue
                left, right = _seg(src, node.left), _seg(src, node.comparators[0])
                if left is None or right is None:
                    continue
                new = _replace_cols(src, node, f'{left} {OP_TEXT[op]} {right}')
                if new:
                    out.append((f'compare {func}:{node.lineno} -> {OP_TEXT[op]}', new))
        elif isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub)):
            left, right = _seg(src, node.left), _seg(src, node.right)
            op = '-' if isinstance(node.op, ast.Add) else '+'
            new = _replace_cols(src, node, f'{left} {op} {right}') if left and right else None
            if new:
                out.append((f'arith {func}:{node.lineno} -> {op}', new))
        elif isinstance(node, ast.Constant) and isinstance(node.value, bool):
            new = _replace_cols(src, node, str(not node.value))
            if new:
                out.append((f'bool {func}:{node.lineno}', new))
        elif isinstance(node, ast.Constant) and isinstance(node.value, int) and abs(node.value) <= 2:
            for d in (-1, 1):
                new = _replace_cols(src, node, str(node.value + d))
                if new:
                    out.append((f'int {func}:{node.lineno} {node.value}->{node.value + d}', new))
        elif isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Name) and f.id in NAME_SWAPS:
                new = _replace_cols(src, f, NAME_SWAPS[f.id])
                if new:
                    out.append((f'name {func}:{node.lineno} {f.id}->{NAME_SWAPS[f.id]}', new))
            if isinstance(f, ast.Name) and f.id in ('list', 'dict', 'set') and len(node.args) == 1:
                inner = _seg(src, node.args[0])
                new = _replace_cols(src, node, inner) if inner else None
                if new:
                    out.append((f'uncopy {func}:{node.lineno}', new))
            if isinstance(f, ast.Attribute) and f.attr == 'pop':
                target = _seg(src, f)
                if not node.args:
                    for a in ('0', '-1'):
                        new = _replace_cols(src, node, f'{target}({a})')
                        if new:
                            out.append((f'pop {func}:{node.lineno} ({a})', new))
                elif len(node.args) == 1 and isinstance(node.args[0], ast.Constant):
                    new = _replace_cols(src, node, f'{target}()')
                    if new:
                        out.append((f'pop {func}:{node.lineno} ()', new))
    for node in ast.walk(tree):                   # add a copy where a container is iterated, returned or stored
        if not _in_focus(node, focus_lines):
            continue
        func = _func_of(tree, node)
        if not ok_func(func):
            continue
        targets = []
        if isinstance(node, ast.For):
            targets.append(node.iter)
        elif isinstance(node, (ast.Return, ast.Assign)) and node.value is not None:
            targets.append(node.value)
        elif isinstance(node, ast.Dict):
            targets.extend(v for v in node.values if v is not None)
        for t in targets:
            if isinstance(t, (ast.Name, ast.Attribute, ast.Subscript)):
                seg = _seg(src, t)
                new = _replace_cols(src, t, f'list({seg})') if seg else None
                if new:
                    out.append((f'copy {func}:{t.lineno}', new))
    return _dedupe(src, out)


def _func_of(tree, node):
    best = None
    for f in ast.walk(tree):
        if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)) and f.lineno <= node.lineno <= f.end_lineno:
            if best is None or f.lineno > best.lineno:
                best = f
    return best.name if best else None


def _dedupe(src, out):
    seen, res = {src}, []
    for name, new in out:
        if new is None or new in seen:
            continue
        try:
            ast.parse(new)
        except SyntaxError:
            continue
        seen.add(new)
        res.append((name, new))
    return res


def _methods(tree):
    out = {}
    for c in ast.walk(tree):
        if isinstance(c, ast.ClassDef):
            for f in c.body:
                if isinstance(f, ast.FunctionDef):
                    out[f.name] = f
    return out


def _names_used(node):
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}


def _defined_before(func, pos_line):
    names = {a.arg for a in func.args.args} | {a.arg for a in func.args.kwonlyargs}
    for n in ast.walk(func):
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store) and n.lineno < pos_line:
            names.add(n.id)
    return names


def transplants(src, focus_funcs):
    """Homologous recombination: simple statements of sibling methods inserted into the focus methods."""
    import builtins
    tree = ast.parse(src)
    methods = _methods(tree)
    donors = []
    for name, f in methods.items():
        for st in ast.walk(f):
            if isinstance(st, (ast.Expr, ast.Assign, ast.AugAssign)) and st.lineno == st.end_lineno:
                if isinstance(st, ast.Expr) and not isinstance(st.value, ast.Call):
                    continue
                donors.append((name, st, _seg(src, st)))
    out = []
    for fname in focus_funcs or ():
        f = methods.get(fname)
        if f is None:
            continue
        own = {_seg(src, st) for st in ast.walk(f) if isinstance(st, ast.stmt)}
        for _, body in _bodies(f):
            for st in body:
                for dname, d, text in donors:
                    if dname == fname or text in own:
                        continue
                    for where, pos in (('after', st), ('before', st)):
                        line = pos.end_lineno + 1 if where == 'after' else pos.lineno
                        if not _names_used(d) <= (_defined_before(f, line) | set(dir(builtins))):
                            continue
                        new = insert_after(src, pos, text) if where == 'after' else insert_before(src, pos, text)
                        out.append((f'transplant {text!r} from {dname} {where} {fname}:{pos.lineno}', new))
    return _dedupe(src, out)


def law_repairs(src, method, law):
    """Statements restoring a broken conservation law, after the changes to its quantity in `method`."""
    tree = ast.parse(src)
    f = _methods(tree).get(method)
    if f is None or law is None:
        return []
    out = []
    changes = []                        # (statement, attribute changed, mutator, argument text)
    for st in ast.walk(f):
        if isinstance(st, ast.Expr) and isinstance(st.value, ast.Call) and isinstance(st.value.func, ast.Attribute):
            tgt = st.value.func.value
            if isinstance(tgt, ast.Attribute) and isinstance(tgt.value, ast.Name) and tgt.value.id == 'self' \
                    and st.value.func.attr in MUTATORS:
                arg = _seg(src, st.value.args[0]) if st.value.args else None
                changes.append((st, tgt.attr, st.value.func.attr, arg))
        elif isinstance(st, (ast.Assign, ast.AugAssign)):
            for t in (st.targets if isinstance(st, ast.Assign) else [st.target]):
                base = t.value if isinstance(t, ast.Subscript) else t
                if isinstance(base, ast.Attribute) and isinstance(base.value, ast.Name) and base.value.id == 'self':
                    changes.append((st, base.attr, 'assign', None))
        elif isinstance(st, ast.Assign) and isinstance(st.value, ast.Call):
            pass
    for st in ast.walk(f):                 # v = self.Y.pop() is a change to Y too
        if isinstance(st, ast.Assign) and isinstance(st.value, ast.Call) and isinstance(st.value.func, ast.Attribute):
            tgt = st.value.func.value
            if isinstance(tgt, ast.Attribute) and isinstance(tgt.value, ast.Name) and tgt.value.id == 'self' \
                    and st.value.func.attr in MUTATORS:
                changes.append((st, tgt.attr, st.value.func.attr, None))
    if ' is None or ' in law:                                       # coherence: X is None or X == f(Y)
        x = law.split(' is None')[0]
        y = law.split('(')[-1].rstrip(')')
        for st, attr, _, _ in changes:
            if attr == y:
                out.append((f'restore {law!r}: invalidate {x} after {method}:{st.lineno}',
                            insert_after(src, st, f'self.{x} = None')))
    elif law.startswith('set(') or law.startswith('len('):        # pairing: set(A) == set(B)
        a = law.split('(')[1].split(')')[0]
        b = law.split('(')[-1].rstrip(')').rstrip(')')
        kinds = _kinds(tree)
        for st, attr, mut, arg in changes:
            if arg is None or attr not in (a, b):
                continue
            other = b if attr == a else a
            op = PAIR_OPS.get(kinds.get(other, ''), {}).get(mut)
            if op:
                out.append((f'restore {law!r}: self.{other}.{op}({arg}) after {method}:{st.lineno}',
                            insert_after(src, st, f'self.{other}.{op}({arg})')))
    return _dedupe(src, out)


# ------------------------------------------------------------------------------------------------- inventions
# Operators added after B20_R180, each from a class of obstacle that no earlier operator could reach (a statement
# with no homologue to transplant). Each is a general structural principle, not a pattern of one defect.

class _Rename(ast.NodeTransformer):
    def __init__(self, mapping):
        self.mapping = mapping

    def visit_Name(self, node):
        if node.id in self.mapping:
            return ast.copy_location(ast.Name(id=self.mapping[node.id], ctx=node.ctx), node)
        return node


def _symmetric_pairs(f):
    """Pairs of a method's arguments it treats as interchangeable: both index the same container somewhere in it."""
    args = [a.arg for a in f.args.args if a.arg != 'self']
    by_container = {}
    for n in ast.walk(f):
        if isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Name) and n.slice.id in args:
            by_container.setdefault(ast.dump(n.value), set()).add(n.slice.id)
    pairs = set()
    for names in by_container.values():
        names = sorted(names)
        for i, x in enumerate(names):
            for y in names[i + 1:]:
                pairs.add((x, y))
    return sorted(pairs)


def mirrors(src, focus_funcs=None):
    """**Symmetry completion** (physics: a law that holds for i holds for its mirror image j). In a method whose
    arguments a and b index the same container (a swap, a pair), a simple statement that mentions a but not b and has
    no mirror image in the method gets one: the statement with a and b exchanged, inserted after it. A broken
    symmetry (an index updated for one side of a swap only) is repaired by restoring it."""
    tree = ast.parse(src)
    out = []
    for name, f in _methods(tree).items():
        if focus_funcs is not None and name not in focus_funcs:
            continue
        for a, b in _symmetric_pairs(f):
            own = {ast.dump(st) for st in ast.walk(f) if isinstance(st, ast.stmt)}
            for st in ast.walk(f):
                if not isinstance(st, (ast.Assign, ast.AugAssign, ast.Expr)) or st.lineno != st.end_lineno:
                    continue
                names = {n.id for n in ast.walk(st) if isinstance(n, ast.Name)}
                if (a in names) == (b in names):
                    continue
                m = _Rename({a: b, b: a}).visit(ast.parse(_seg(src, st)).body[0])
                if ast.dump(m) in own:
                    continue
                text = ast.unparse(m)
                out.append((f'mirror {name}:{st.lineno} ({a}<->{b})', insert_after(src, st, text)))
    return _dedupe(src, out)


def orphans(src, focus_funcs=None):
    """**Vestigial organs** (biology: an organ that no longer has a function points at a lost pathway). A private
    method that takes no argument but `self` and that nothing in the class calls any more gets a call restored, at
    the start or the end of each other method (but `__init__`)."""
    tree = ast.parse(src)
    methods = _methods(tree)
    called = {n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
              and isinstance(n.func.value, ast.Name) and n.func.value.id == 'self'}
    lost = [m for m, f in methods.items() if m.startswith('_') and not m.startswith('__') and m not in called
            and [a.arg for a in f.args.args] == ['self']]
    out = []
    for m in lost:
        for name, f in methods.items():
            if name in (m, '__init__') or (focus_funcs is not None and name not in focus_funcs):
                continue
            first, last = f.body[0], f.body[-1]
            if isinstance(first, ast.Expr) and isinstance(getattr(first, 'value', None), ast.Constant):
                first = f.body[1] if len(f.body) > 1 else first
            out.append((f'orphan call self.{m}() at the start of {name}', insert_before(src, first, f'self.{m}()')))
            if isinstance(last, ast.Return):
                out.append((f'orphan call self.{m}() before the return of {name}', insert_before(src, last, f'self.{m}()')))
            else:
                out.append((f'orphan call self.{m}() at the end of {name}', insert_after(src, last, f'self.{m}()')))
    return _dedupe(src, out)


def _clocks(tree):
    """Attributes that only ever grow by an argument: `self.P += x` (a clock, a position, a counter of time)."""
    grow = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.AugAssign) and isinstance(n.op, ast.Add) and isinstance(n.target, ast.Attribute) \
                and isinstance(n.target.value, ast.Name) and n.target.value.id == 'self' \
                and isinstance(n.value, ast.Name):
            grow[n.target.attr] = True
    return sorted(grow)


def offsets(src, focus_funcs=None):
    """**Dimensional analysis** (physics: a point in time is a duration measured from an origin). Where an attribute
    that is a clock (`clocks`) is compared with values elsewhere, a duration stored or returned without the clock has
    the wrong dimension: each `self.X` read in a statement of the focus (X not itself a clock) is offered as
    `self.P + self.X`, and an existing `self.P + E` as `E` (the converse)."""
    tree = ast.parse(src)
    clocks = _clocks(tree)
    if not clocks:
        return []
    out = []
    for name, f in _methods(tree).items():
        if name == '__init__' or (focus_funcs is not None and name not in focus_funcs):
            continue
        for st in ast.walk(f):
            if not isinstance(st, (ast.Assign, ast.Return, ast.Expr)) or st.lineno != st.end_lineno:
                continue
            value = st.value
            if value is None:
                continue
            for n in ast.walk(value):
                if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == 'self' \
                        and isinstance(n.ctx, ast.Load) and n.attr not in clocks \
                        and not any(isinstance(p, ast.Call) and p.func is n for p in ast.walk(value)):
                    for c in clocks:
                        out.append((f'offset {name}:{st.lineno} self.{n.attr} -> self.{c} + self.{n.attr}',
                                    _replace_cols(src, n, f'self.{c} + self.{n.attr}')))
                if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add) and isinstance(n.left, ast.Attribute) \
                        and n.left.attr in clocks:
                    out.append((f'offset {name}:{st.lineno} drop self.{n.left.attr} +',
                                _replace_cols(src, n, _seg(src, n.right))))
    return _dedupe(src, out)


EMPTY = ('{}', '[]', 'set()', 'dict()', 'list()', 'OrderedDict()', '0', 'None')


def annihilates(src, patch):
    """How many statements the patch adds outside `__init__` that reset an attribute to an empty or zero value
    (`self.X = {}`, `[]`, `set()`, `0`, `None`, or `self.X.clear()`) where X is not a cache the component itself
    resets that way somewhere outside `__init__` already."""
    def resets(text):
        tree = ast.parse(text)
        out = []
        for name, f in _methods(tree).items():
            if name == '__init__':
                continue
            for st in ast.walk(f):
                if isinstance(st, ast.Assign) and len(st.targets) == 1 and isinstance(st.targets[0], ast.Attribute) \
                        and ast.unparse(st.value) in EMPTY:
                    out.append(st.targets[0].attr)
                elif isinstance(st, ast.Expr) and isinstance(st.value, ast.Call) \
                        and isinstance(st.value.func, ast.Attribute) and st.value.func.attr == 'clear' \
                        and isinstance(st.value.func.value, ast.Attribute):
                    out.append(st.value.func.value.attr)
        return out
    before, after = resets(src), resets(patch)
    return sum(1 for x in set(after) if after.count(x) > before.count(x) and x not in before)


def inventions(src, focus_funcs=None):
    return mirrors(src, focus_funcs) + orphans(src, focus_funcs) + offsets(src, focus_funcs)


def _kinds(tree):
    """The kind of each attribute initialised in __init__ (set, list, dict)."""
    out = {}
    init = _methods(tree).get('__init__')
    for st in ast.walk(init) if init else []:
        if isinstance(st, ast.Assign):
            for t in st.targets:
                if isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id == 'self':
                    v = st.value
                    if isinstance(v, ast.Call) and isinstance(v.func, ast.Name):
                        out[t.attr] = v.func.id
                    elif isinstance(v, ast.List):
                        out[t.attr] = 'list'
                    elif isinstance(v, ast.Dict):
                        out[t.attr] = 'dict'
                    elif isinstance(v, ast.Set):
                        out[t.attr] = 'set'
    return out


def changed_lines(a, b):
    import difflib
    return sum(1 for x in difflib.unified_diff(a.split('\n'), b.split('\n'), lineterm='', n=0)
               if x[:1] in '+-' and not x.startswith(('+++', '---')))


# ------------------------------------------------------------------------------------------------- the search

class Search:
    """Clonal selection with annealing over candidate sources. `evaluate(src) -> (energy, solved)`."""

    def __init__(self, base, evaluate, budget=400, seed=0, generations=8, temperature=20.0, cooling=0.8):
        self.base, self.evaluate, self.budget = base, evaluate, budget
        self.rng = random.Random(seed)
        self.generations, self.T, self.cooling = generations, temperature, cooling
        self.evals = 0
        self.first_solution = None          # the evaluation at which the first candidate passed everything visible
        self.seen = {}
        self.history = []

    def score(self, name, src):
        if src in self.seen:
            return self.seen[src]
        if self.evals >= self.budget:
            return None
        self.evals += 1
        e, solved = self.evaluate(src)
        if solved and self.first_solution is None:
            self.first_solution = self.evals
        e += 0.5 * changed_lines(self.base, src)
        self.seen[src] = (e, solved, name)
        return self.seen[src]

    def run(self, repertoire, mutate):
        """repertoire: [(name, src)] in priority order; mutate(src, rng) -> (name, src) or None. Returns the
        solutions found (smallest first) and the search record."""
        pop = []
        for name, src in repertoire:
            r = self.score(name, src)
            if r is None:
                break
            pop.append((r[0], name, src, r[1]))
        solutions = [p for p in pop if p[3]]
        gen = 0
        while not solutions and gen < self.generations and self.evals < self.budget and pop:
            gen += 1
            pop.sort(key=lambda p: p[0])
            elite = pop[:6]
            new_pop = list(elite)
            for rank, (e, name, src, _) in enumerate(elite):
                clones = max(1, 6 // (rank + 1))
                for _ in range(clones):
                    m = mutate(src, self.rng)
                    if m is None:
                        continue
                    mname, msrc = m
                    r = self.score(f'{name} + {mname}', msrc)
                    if r is None:
                        break
                    ce = r[0]
                    if r[1]:
                        solutions.append((ce, f'{name} + {mname}', msrc, True))
                    if ce < e or self.rng.random() < math.exp(-(ce - e) / max(self.T, 1e-6)):
                        new_pop.append((ce, f'{name} + {mname}', msrc, r[1]))
            pop = new_pop
            self.T *= self.cooling
            self.history.append({'generation': gen, 'best': round(min(p[0] for p in pop), 3), 'evals': self.evals})
        solutions.sort(key=lambda p: (changed_lines(self.base, p[2]), p[0]))
        return solutions, {'evaluations': self.evals, 'first_solution': self.first_solution, 'generations': gen,
                           'history': self.history}
