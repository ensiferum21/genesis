"""Genesis inventing its own repair rules (research plane; `docs/OMEGA_RULE_INVENTION.md`).

**A rule** is a transformation with holes. Its *pattern* is the shape of one statement of the component with some
classes of identifier replaced by metavariables; its *template* is the statement(s) to insert after a match (kind
'insert') or to put in its place (kind 'replace'), sharing the metavariables. Rules are data (JSON lines in the
research plane's own vault directory), never code the builder writes.

**Where rules come from.**
  1. `dream_edits`: when no rule solves an obstacle, a deeper search over a *grammar of statements* built from the
     component's own vocabulary (its attributes by the kind of value they hold, the suspected methods' arguments and
     locals, its private methods): increments and decrements, updates of indexed entries, calls of container methods
     on indexed values, `setdefault` insertions, deletions (also of entries left empty), calls of private methods,
     invalidations, and the flip of every augmented assignment to its sibling operator. The "dream" happens offline,
     at a budget several times the normal one (physics: exploring the landscape at high temperature).
  2. `abstract`: a repair the verifier accepted is lifted into rules by **anti-unification** (Plotkin 1970: the least
     general generalisation): the statement before the edit (the anchor) and the new statement are rewritten with
     each identifier class at a chosen *level* (LEVELS: keep everything; abstract the bare names; the names and the
     attributes; also the operations on values, such as `add` or `discard`; and the constants too) replaced by metavariables, consistently between pattern and template. At the
     last level, 'free', an attribute the template names and the pattern does not becomes a *free* metavariable,
     bound when the rule is applied to every attribute of the target that holds the same kind of value (a dict, a
     set, a counter): the rule "after writing one map, write the inverse into another map" rather than "after
     writing `fwd`, write `back`". The levels are the lattice from the concrete patch (it matches only where it was
     found) to the most general rule.
  3. Admission (the kernel decides, the inventor counts): a candidate rule is admitted to the library only when a
     patch it produced on an obstacle of *another family* (another defect, usually another component) was accepted
     by the independent verifier. Its record keeps the provenance and a Beta posterior of its success.

**Improving the inventor.** `Inventor` keeps a Beta posterior per level: admitted against tested-and-not-admitted.
Candidate rules are tried in probes in the order of their level's posterior mean (then by how few candidates they
produce: minimum description length), so the levels that produced rules that transferred are tried first next time."""
import ast
import builtins
import copy
import json
from pathlib import Path

LEVELS = ('concrete', 'names', 'names+attrs', 'names+attrs+ops', 'names+attrs+ops+consts', 'free')
ABSTRACT = {'concrete': set(), 'names': {'name'}, 'names+attrs': {'name', 'attr'},
            'names+attrs+ops': {'name', 'attr', 'op'}, 'names+attrs+ops+consts': {'name', 'attr', 'op', 'const'},
            'free': {'name', 'attr', 'op', 'const'}}
FREE_CAP = 12
FLIP = {ast.Add: ast.Sub, ast.Sub: ast.Add, ast.Mult: ast.Div, ast.Div: ast.Mult}
CONTAINER_CALLS = ('add', 'discard', 'append', 'remove')
PRIOR = (1.0, 1.0)
BUILTINS = frozenset(dir(builtins))


# ------------------------------------------------------------------------------------------------- vocabulary
def _methods(tree):
    out = {}
    for c in ast.walk(tree):
        if isinstance(c, ast.ClassDef):
            for f in c.body:
                if isinstance(f, ast.FunctionDef):
                    out[f.name] = f
    return out


def vocabulary(src):
    """The component's attributes by the kind of value they hold, and its private methods that take only `self`."""
    tree = ast.parse(src)
    kinds = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Attribute) \
                and isinstance(n.targets[0].value, ast.Name) and n.targets[0].value.id == 'self':
            v = n.value
            k = ('dict' if isinstance(v, ast.Dict) else 'list' if isinstance(v, ast.List) else
                 'set' if isinstance(v, ast.Call) and getattr(v.func, 'id', '') == 'set' else
                 'int' if isinstance(v, ast.Constant) and isinstance(v.value, int) and not isinstance(v.value, bool)
                 else 'none' if isinstance(v, ast.Constant) and v.value is None else None)
            if k and n.targets[0].attr not in kinds:
                kinds[n.targets[0].attr] = k
    values = {}                                  # dict attribute -> kind of its values ('set', 'list', 'int')
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
            base = n.func.value
            if isinstance(base, ast.Subscript) and isinstance(base.value, ast.Attribute) \
                    and n.func.attr in CONTAINER_CALLS:
                values[base.value.attr] = 'set' if n.func.attr in ('add', 'discard') else 'list'
            if n.func.attr == 'setdefault' and isinstance(base, ast.Attribute) and len(n.args) == 2:
                d = n.args[1]
                if isinstance(d, ast.Call) and getattr(d.func, 'id', '') == 'set':
                    values[base.attr] = 'set'
                elif isinstance(d, ast.List):
                    values[base.attr] = 'list'
        if isinstance(n, (ast.AugAssign, ast.Assign)):
            t = n.target if isinstance(n, ast.AugAssign) else n.targets[0]
            if isinstance(t, ast.Subscript) and isinstance(t.value, ast.Attribute) and isinstance(n, ast.AugAssign):
                values.setdefault(t.value.attr, 'int')
    called = {n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
    methods = _methods(tree)
    private = [m for m, f in methods.items() if m.startswith('_') and not m.startswith('__')
               and [a.arg for a in f.args.args] == ['self']]
    return {'kinds': kinds, 'values': values, 'private': private, 'called': called}


def _locals(f):
    names = [a.arg for a in f.args.args if a.arg != 'self']
    for n in ast.walk(f):
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store) and n.id not in names:
            names.append(n.id)
    return names


# ------------------------------------------------------------------------------------------------- the dream
def _insert_after(src, node, text):
    lines = src.split('\n')
    first = lines[node.lineno - 1]
    ind = first[:len(first) - len(first.lstrip())]
    block = [ind + ln for ln in text.split('\n')]
    return '\n'.join(lines[:node.end_lineno] + block + lines[node.end_lineno:])


def _replace(src, node, text):
    lines = src.split('\n')
    first = lines[node.lineno - 1]
    ind = first[:len(first) - len(first.lstrip())]
    return '\n'.join(lines[:node.lineno - 1] + [ind + ln for ln in text.split('\n')] + lines[node.end_lineno:])


def _statements(f):
    out = []
    for n in ast.walk(f):
        for field in ('body', 'orelse'):
            body = getattr(n, field, None)
            if isinstance(body, list):
                out += [s for s in body if isinstance(s, ast.stmt) and not isinstance(s, ast.FunctionDef)]
    return sorted(out, key=lambda s: s.lineno)


def grammar(src, f, voc):
    """The statements the grammar can build in method f from the component's vocabulary."""
    names = _locals(f)
    out = []
    for a, k in sorted(voc['kinds'].items()):
        if k == 'int':
            for y in names + ['1']:
                out += [f'self.{a} += {y}', f'self.{a} -= {y}']
        if k == 'none':
            out.append(f'self.{a} = None')
        if k == 'dict':
            vk = voc['values'].get(a)
            for x in names:
                out += [f'del self.{a}[{x}]', f'if not self.{a}[{x}]:\n    del self.{a}[{x}]']
                for y in names + ['1']:
                    if y == x:
                        continue
                    if vk == 'int':
                        out += [f'self.{a}[{x}] += {y}', f'self.{a}[{x}] -= {y}']
                    if vk in ('set', 'list'):
                        for m in (('add', 'discard') if vk == 'set' else ('append', 'remove')):
                            out.append(f'self.{a}[{x}].{m}({y})')
                        out.append(f'self.{a}.setdefault({x}, {"set()" if vk == "set" else "[]"}).'
                                   f'{"add" if vk == "set" else "append"}({y})')
                    if vk is None:
                        out.append(f'self.{a}[{x}] = {y}')
    for m in voc['private']:
        if m != f.name:
            out.append(f'self.{m}()')
    return list(dict.fromkeys(out))


PRODUCTIONS = ('flip', 'delete-empty', 'delete', 'setdefault', 'container-call', 'indexed-counter', 'counter',
               'invalidate', 'private-call', 'assign')


def production(name):
    """The grammar production a dream edit came from."""
    if name.startswith('dream flip'):
        return 'flip'
    text = name.split("'")[1] if "'" in name else ''
    if text.startswith('if not '):
        return 'delete-empty'
    if text.startswith('del '):
        return 'delete'
    if '.setdefault(' in text:
        return 'setdefault'
    if text.endswith('()') and text.startswith('self._'):
        return 'private-call'
    if text.endswith('= None'):
        return 'invalidate'
    if '+=' in text or '-=' in text:
        return 'indexed-counter' if '[' in text.split('=')[0] else 'counter'
    if '(' in text:
        return 'container-call'
    return 'assign'


def dream_edits(src, focus_funcs=None):
    """Every grammar statement inserted after every statement (or at the start) of the focus methods, and every
    augmented assignment flipped to its sibling operator: [(name, source)]."""
    tree = ast.parse(src)
    voc = vocabulary(src)
    out = []
    for name, f in _methods(tree).items():
        if name == '__init__' or (focus_funcs is not None and name not in focus_funcs):
            continue
        stmts = _statements(f)
        doc = isinstance(f.body[0], ast.Expr) and isinstance(getattr(f.body[0], 'value', None), ast.Constant)
        anchors = stmts if not doc else [s for s in stmts if s is not f.body[0]]
        for text in grammar(src, f, voc):
            for st in anchors:
                if isinstance(st, ast.Return):
                    continue
                if isinstance(st, (ast.If, ast.For, ast.While, ast.With)):
                    continue                        # after a compound statement: its last inner statement is anchor
                out.append((f'dream insert {text.splitlines()[0]!r} after {name}:{st.lineno}',
                            _insert_after(src, st, text)))
        for st in stmts:
            if isinstance(st, ast.AugAssign) and type(st.op) in FLIP and st.lineno == st.end_lineno:
                new = copy.deepcopy(st)
                new.op = FLIP[type(st.op)]()
                out.append((f'dream flip {name}:{st.lineno}', _replace(src, st, ast.unparse(new))))
    seen, res = {src}, []
    for n, s in out:
        if s in seen:
            continue
        try:
            ast.parse(s)
        except SyntaxError:
            continue
        seen.add(s)
        res.append((n, s))
    return res


# ------------------------------------------------------------------------------------------------- abstraction
class _Lift(ast.NodeTransformer):
    """Replace identifiers of the abstracted classes by metavariables, consistently through `table`."""

    def __init__(self, classes, table):
        self.classes, self.table = classes, table

    def _meta(self, cls, value):
        key = (cls, repr(value))
        if key not in self.table:
            self.table[key] = f'__m{len(self.table)}__'
        return self.table[key]

    def visit_Name(self, node):
        if 'name' in self.classes and node.id != 'self' and node.id not in BUILTINS:
            return ast.copy_location(ast.Name(id=self._meta('name', node.id), ctx=node.ctx), node)
        return node

    def visit_Attribute(self, node):
        self.generic_visit(node)
        if isinstance(node.value, ast.Name) and node.value.id == 'self':
            if 'attr' in self.classes:
                node.attr = self._meta('attr', node.attr)
        elif 'op' in self.classes and not node.attr.startswith('__'):
            node.attr = self._meta('op', node.attr)      # the operation on a value: add, discard, pop, setdefault
        return node

    def visit_Constant(self, node):
        if 'const' in self.classes and isinstance(node.value, int) and not isinstance(node.value, bool):
            return ast.copy_location(ast.Name(id=self._meta('const', node.value), ctx=ast.Load()), node)
        return node


def shape(stmt_text, level, table=None):
    """(the statement's shape with the level's identifiers lifted, the table metavariable -> value)."""
    table = {} if table is None else table
    tree = ast.parse(stmt_text)
    lifted = _Lift(ABSTRACT[level], table).visit(tree)
    return ast.dump(lifted, annotate_fields=False), table


def _edit(src0, patch):
    """('insert', anchor text, new text) or ('replace', old text, new text) for a patch, or None."""
    a, b = src0.split('\n'), patch.split('\n')
    i = 0
    while i < min(len(a), len(b)) and a[i] == b[i]:
        i += 1
    j = 0
    while j < min(len(a), len(b)) - i and a[-1 - j] == b[-1 - j]:
        j += 1
    old, new = a[i:len(a) - j], b[i:len(b) - j]
    ded = [ln.strip() for ln in new]
    if not new:
        return None
    if not old:                                                  # an insertion after line i-1
        tree = ast.parse(src0)
        anchor = next((s for s in sorted((n for n in ast.walk(tree) if isinstance(n, ast.stmt)
                                           and not isinstance(n, (ast.FunctionDef, ast.ClassDef))),
                                          key=lambda n: -n.lineno) if s.end_lineno == i), None)
        if anchor is None or anchor.lineno != anchor.end_lineno:
            return None
        ind = len(new[0]) - len(new[0].lstrip())
        text = '\n'.join(ln[ind:] for ln in new)
        try:
            ast.parse(text)
        except SyntaxError:
            return None
        return ('insert', a[anchor.lineno - 1].strip(), text)
    if len(old) == 1 and len(new) == 1:
        return ('replace', old[0].strip(), ded[0])
    return None


def abstract(src0, patch, provenance):
    """The candidate rules (one per level) of a verified patch, most concrete first."""
    e = _edit(src0, patch)
    if e is None:
        return []
    kind, anchor, text = e
    try:
        ast.parse(anchor)
        ast.parse(text)
    except SyntaxError:
        return []                       # a compound statement's header: not a rule of this language (yet)
    out = []
    for level in LEVELS:
        table = {}
        pat, table = shape(anchor, level, table)
        templ_tree = _Lift(ABSTRACT[level], table).visit(ast.parse(text))
        free = [k for k in table if k[1] not in _identifiers_text(anchor, k[0])]
        free_kinds = {}
        if free:
            if level != 'free' or any(cls != 'attr' for cls, _ in free):
                continue                # a template metavariable the pattern does not bind: not applicable
            kinds = vocabulary(src0)['kinds']
            free_kinds = {table[k]: kinds.get(ast.literal_eval(k[1])) for k in free}
            if None in free_kinds.values():
                continue
        elif level == 'free':
            continue                    # the same rule as the level below
        out.append({'kind': kind, 'level': level, 'pattern': pat, 'template': ast.unparse(templ_tree),
                    'free': free_kinds,
                    'metas': {v: list(k) for k, v in table.items()}, 'example': {'anchor': anchor, 'new': text},
                    'provenance': provenance, 'status': 'candidate', 'tested': 0, 'admitted_by': [],
                    'successes': 0, 'failures': 0})
    seen, res = set(), []
    for r in out:
        key = (r['kind'], r['pattern'], r['template'])
        if key not in seen:
            seen.add(key)
            res.append(r)
    for k, r in enumerate(res):
        r['id'] = f"{provenance.get('episode', 'x')}#{k}:{r['level']}"
    return res


def _identifiers_text(text, cls):
    vals = set()
    for n in ast.walk(ast.parse(text)):
        if cls == 'name' and isinstance(n, ast.Name):
            vals.add(repr(n.id))
        elif cls in ('attr', 'op') and isinstance(n, ast.Attribute):
            vals.add(repr(n.attr))
        elif cls == 'const' and isinstance(n, ast.Constant):
            vals.add(repr(n.value))
    return vals


class _Bind(ast.NodeTransformer):
    def __init__(self, binding):
        self.binding = binding

    def visit_Name(self, node):
        if node.id in self.binding:
            cls, value = self.binding[node.id]
            if cls == 'const':
                return ast.copy_location(ast.Constant(value=value), node)
            return ast.copy_location(ast.Name(id=value, ctx=node.ctx), node)
        return node

    def visit_Attribute(self, node):
        self.generic_visit(node)
        if node.attr in self.binding:
            node.attr = self.binding[node.attr][1]
        return node



def apply_rule(rule, src):
    """The candidate patches the rule makes on src: [(name, source)]."""
    tree = ast.parse(src)
    lines = src.split('\n')
    funcs = [g for g in ast.walk(tree) if isinstance(g, ast.FunctionDef)]
    out = []
    for n in ast.walk(tree):
        if not isinstance(n, ast.stmt) or isinstance(n, (ast.FunctionDef, ast.ClassDef)) or n.lineno != n.end_lineno:
            continue
        text = lines[n.lineno - 1].strip()
        try:
            pat, table = shape(text, rule['level'])
        except SyntaxError:
            continue
        if pat != rule['pattern']:
            continue
        binding = {}
        for (cls, rv), meta in table.items():
            binding[meta] = (cls, ast.literal_eval(rv))
        choices = [{}]
        free = rule.get('free') or {}
        if free:
            kinds = vocabulary(src)['kinds']
            bound = {v for c, v in binding.values() if c == 'attr'}
            choices = []
            for meta, kind in sorted(free.items()):
                opts = [a for a, k in sorted(kinds.items()) if k == kind and a not in bound]
                choices = [dict(c, **{meta: ('attr', a)}) for c in (choices or [{}]) for a in opts][:FREE_CAP]
        f = next((g for g in funcs if g.lineno <= n.lineno <= g.end_lineno), None)
        own = {ln.strip() for ln in lines[f.lineno - 1:f.end_lineno]} if f else set()
        for extra in choices:
            new = ast.unparse(_Bind(dict(binding, **extra)).visit(ast.parse(rule['template'])))
            if rule['kind'] == 'insert' and all(ln.strip() in own for ln in new.split('\n')):
                continue                            # the method already does it
            cand = _insert_after(src, n, new) if rule['kind'] == 'insert' else _replace(src, n, new)
            if cand != src:
                out.append((f"rule {rule['id']} at {n.lineno}", cand))
    return out


# ------------------------------------------------------------------------------------------------- the library
class Library:
    """Rules with provenance and outcomes, in the research plane's vault directory (JSON lines, rewritten whole)."""

    def __init__(self, path):
        self.path = Path(path) if path else None
        self.rules = []
        if self.path and self.path.exists():
            self.rules = [json.loads(x) for x in self.path.read_text().splitlines() if x.strip()]

    def save(self):
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(''.join(json.dumps(r) + '\n' for r in self.rules))

    def add(self, rules):
        have = {(r['kind'], r['pattern'], r['template']) for r in self.rules}
        new = [r for r in rules if (r['kind'], r['pattern'], r['template']) not in have]
        self.rules += new
        self.save()
        return new

    def get(self, rid):
        return next((r for r in self.rules if r['id'] == rid), None)

    def posterior(self, r):
        a, b = PRIOR
        return (a + r['successes']) / (a + b + r['successes'] + r['failures'])

    def admitted(self):
        return sorted((r for r in self.rules if r['status'] == 'admitted'), key=lambda r: -self.posterior(r))

    def candidates(self, family=None):
        return [r for r in self.rules if r['status'] == 'candidate' and r['provenance'].get('family') != family]

    def record(self, rid, verified, family, false_repair=False):
        r = self.get(rid)
        if r is None:
            return
        r['tested'] += 1
        if verified:
            r['successes'] += 1
            if family != r['provenance'].get('family'):
                r['admitted_by'].append(family)
                r['status'] = 'admitted'
        else:
            r['failures'] += 1
            if false_repair and r['status'] == 'candidate' and not r['admitted_by']:
                r['status'] = 'rejected'
        self.save()


class Inventor:
    """The inventor's beliefs about its own choices (`inventor.json`): a Beta posterior per generalisation level
    (admitted against tested and not admitted), and one per grammar production (a dream's verified repair against
    none). Probes try the believed levels first; dreams try the believed productions first: the inventor learns where
    to look as it goes."""

    def __init__(self, path):
        self.path = Path(path) if path else None
        self.beliefs = {lv: [1.0, 1.0] for lv in LEVELS}
        self.productions = {pr: [1.0, 1.0] for pr in PRODUCTIONS}
        if self.path and self.path.exists():
            data = json.loads(self.path.read_text())
            self.beliefs.update(data.get('levels', data if 'levels' not in data and 'productions' not in data else {}))
            self.productions.update(data.get('productions', {}))

    def save(self):
        if self.path:
            self.path.write_text(json.dumps({'levels': self.beliefs, 'productions': self.productions}, indent=1))

    def production_mean(self, pr):
        a, b = self.productions[pr]
        return a / (a + b)

    def order_dream(self, edits):
        """Dream edits with the believed productions first (stable within a production)."""
        return sorted(edits, key=lambda e: -self.production_mean(production(e[0])))

    def learn_production(self, pr, repaired):
        a, b = self.productions[pr]
        self.productions[pr] = [a + 1, b] if repaired else [a, b + 1]
        self.save()

    def mean(self, level):
        a, b = self.beliefs[level]
        return a / (a + b)

    def order(self, rules, src):
        """Candidate rules in the order to try them: the level's posterior mean first, then the fewest candidates
        (minimum description length: a rule that proposes little and repairs is worth more)."""
        scored = []
        for r in rules:
            n = len(apply_rule(r, src))
            if n:
                scored.append((-self.mean(r['level']), n, r['id'], r))
        return [r for *_, r in sorted(scored, key=lambda x: x[:3])]

    def learn(self, level, admitted):
        a, b = self.beliefs[level]
        self.beliefs[level] = [a + 1, b] if admitted else [a, b + 1]
        self.save()
