"""Genesis growing its own repair space (research plane; SR-2c, `docs/OMEGA_RULE_INVENTION.md` §6).

**A transformation** maps a statement the component already has (the *donor*) to a repair: a few leaf substitutions,
abstracted by role, and where the image goes. A transformation is a production of candidate patches, kept as data in
the research plane's vault directory (`transforms.jsonl`), never code the builder writes.

Leaves (`leaves`): bare names ('name'), called functions ('func'), the component's attributes `self.a` ('attr'),
methods and fields of other values ('meth'), operators ('op'), constants ('const'). Substitutions (`abstract_subs`):
  ('swap', kind)        two leaves of the kind exchanged everywhere in the statement (`adj[u].add(v)` -> `adj[v].add(u)`)
  ('rename', kind)      one leaf put for another in scope: another local of the method, another attribute holding the
                        same kind of value
  ('map', kind, a, b)   a concrete partner: `discard` for `add`, `Sub` for `Add`, `min` for `max`
  ('shift', d)          an integer constant made c + d
  ('any', kind)         the generalisation of 'map' and 'shift': any partner of the same family (an operator's
                        siblings, the methods and functions the component uses, a constant one larger or smaller)
Edits: 'after' and 'before' (the image inserted next to its donor), 'replace' (the image in the donor's place; for a
compound statement, its header), 'transplant' (the image of a donor of another method inserted in a suspected method,
at its start or after one of its statements).

**Where transformations come from.**
  1. `lift`: from a verified repair, the donor is the statement of the component with the same syntax tree as the
     repaired statement and the fewest differing leaves (the replaced statement itself for a replacement; for an
     insertion, the statement it follows, else the nearest of its method, else one of another method); the leaves that
     differ give the substitutions (at most two).
  2. `derive` (the inventor improving how it invents): from the admitted transformations, without new repairs: the
     *inverse* (b for a from a for b; a shift of -d from d), the *transfer* to another edit, the *composition* of two
     (at most two substitutions), the *generalisation* of a concrete partner to any partner of its family. These are
     the group operations on the set of symmetries. A `Deriver` keeps a Beta posterior per derivation operator
     (admitted against tested-and-not-admitted), and derived candidates are tried in that order: the inventor learns
     which ways of inventing work.
  3. Admission: as for rules (`invent.Library`): only a verified repair of an obstacle of another family admits a
     transformation; one whose patch the verifier rejects, with no admission, is rejected."""
import ast
import copy
import json
from pathlib import Path

from . import invent as IV

MAX_SUBS = 2
CAP = 60                                                    # images per (transformation, donor)
PRIOR = (1.0, 1.0)
DERIVATIONS = ('invert', 'transfer', 'compose', 'generalise')
EDITS = ('after', 'before', 'replace', 'transplant')
FAMILIES = (('Add', 'Sub', 'Mult', 'Div', 'FloorDiv', 'Mod'), ('Lt', 'LtE', 'Gt', 'GtE', 'Eq', 'NotEq'),
            ('In', 'NotIn'), ('Is', 'IsNot'), ('And', 'Or'), ('USub', 'UAdd'))
SIMPLE = (ast.Assign, ast.AugAssign, ast.Expr, ast.Delete, ast.Return)


# ------------------------------------------------------------------------------------------------- leaves
def _walk(node):
    yield node
    for _, v in ast.iter_fields(node):
        if isinstance(v, ast.AST):
            yield from _walk(v)
        elif isinstance(v, list):
            for x in v:
                if isinstance(x, ast.AST):
                    yield from _walk(x)


def leaves(node):
    """[(i, field, index, kind, value)] in a fixed order; i is the node's position in `_walk(node)`."""
    nodes = list(_walk(node))
    funcs = {id(n.func) for n in nodes if isinstance(n, ast.Call)}
    out = []
    for i, n in enumerate(nodes):
        if isinstance(n, ast.Name):
            if n.id != 'self':
                out.append((i, 'id', None, 'func' if id(n) in funcs else 'name', n.id))
        elif isinstance(n, ast.Attribute):
            own = isinstance(n.value, ast.Name) and n.value.id == 'self' and id(n) not in funcs
            out.append((i, 'attr', None, 'attr' if own else 'meth', n.attr))
        elif isinstance(n, (ast.BinOp, ast.AugAssign, ast.UnaryOp, ast.BoolOp)):
            out.append((i, 'op', None, 'op', type(n.op).__name__))
        elif isinstance(n, ast.Compare):
            for j, o in enumerate(n.ops):
                out.append((i, 'ops', j, 'op', type(o).__name__))
        elif isinstance(n, ast.Constant) and not (isinstance(n.value, (str, bytes)) and len(n.value) >= 40):
            out.append((i, 'value', None, 'const', n.value))
    return out


def skeleton(node):
    """The syntax tree with every leaf blanked: two statements are comparable when their skeletons are equal."""
    c = copy.deepcopy(node)
    nodes = list(_walk(c))
    for i, field, j, kind, _ in leaves(c):
        n = nodes[i]
        if kind == 'op':
            fam = _family(type(n.ops[j] if j is not None else n.op).__name__)
            blank = getattr(ast, fam[0])()
            if j is None:
                n.op = blank
            else:
                n.ops[j] = blank
        elif field == 'value':
            n.value = 0
        else:
            setattr(n, field, '_')
    return ast.dump(c, annotate_fields=False, include_attributes=False)


def _family(op):
    return next((f for f in FAMILIES if op in f), (op,))


def _set(node, slot, value):
    c = copy.deepcopy(node)
    i, field, j, kind, _ = slot
    n = list(_walk(c))[i]
    if kind == 'op':
        if j is None:
            n.op = getattr(ast, value)()
        else:
            n.ops[j] = getattr(ast, value)()
    else:
        setattr(n, field, value)
    return c


def _map_values(node, kind, mapping):
    """Every leaf of the kind whose value is a key of mapping (equal and of the same type) put to its image, at once."""
    c = copy.deepcopy(node)
    nodes = list(_walk(c))
    for i, field, j, k, v in leaves(c):
        if k != kind:
            continue
        hit = next((m for m in mapping if m == v and type(m) is type(v)), _NONE)
        if hit is not _NONE:
            setattr(nodes[i], field, mapping[hit])
    return c


_NONE = object()


# ------------------------------------------------------------------------------------------------- substitutions
def diff(donor, repaired):
    """[(kind, donor value, repaired value)] for comparable statements, else None."""
    if skeleton(donor) != skeleton(repaired):
        return None
    a, b = leaves(donor), leaves(repaired)
    if len(a) != len(b):
        return None
    return [(x[3], x[4], y[4]) for x, y in zip(a, b) if x[4] != y[4] or type(x[4]) is not type(y[4])]


def abstract_subs(changes):
    """The substitutions (sorted, at most MAX_SUBS) that explain the changes, or None."""
    subs, used = [], set()
    for i, (k, a, b) in enumerate(changes):
        if i in used:
            continue
        j = next((j for j, (k2, a2, b2) in enumerate(changes) if j > i and j not in used and k2 == k and a2 == b
                  and b2 == a), None)
        if j is not None:
            used |= {i, j}
            subs.append(('swap', k))
            for m, (k3, a3, b3) in enumerate(changes):         # every other occurrence of the same exchange
                if (k3, {a3, b3}) == (k, {a, b}):
                    used.add(m)
    for i, (k, a, b) in enumerate(changes):
        if i in used:
            continue
        if k in ('name', 'attr'):
            s = ('rename', k)
        elif k == 'const' and type(a) is int and type(b) is int:
            s = ('shift', b - a)
        else:
            s = ('map', k, a, b)
        subs.append(s)
    subs = sorted(set(subs), key=repr)
    return tuple(subs) if 0 < len(subs) <= MAX_SUBS else None


def _context(src):
    voc = IV.vocabulary(src)
    tree = ast.parse(src)
    meths = sorted({n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)
                    and not (isinstance(n.value, ast.Name) and n.value.id == 'self')} | set(voc['called']))
    funcs = sorted({n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)})
    return {'kinds': voc['kinds'], 'meths': meths, 'funcs': funcs}


def _apply_sub(node, s, ctx, locals_):
    L = leaves(node)
    out = []
    if s[0] == 'swap':
        vals = sorted({v for *_, k, v in L if k == s[1]}, key=repr)
        for x in range(len(vals)):
            for y in range(x + 1, len(vals)):
                out.append(_map_values(node, s[1], {vals[x]: vals[y], vals[y]: vals[x]}))
    elif s[0] == 'rename':
        vals = sorted({v for *_, k, v in L if k == s[1]}, key=repr)
        for v in vals:
            if s[1] == 'name':
                pool = [w for w in locals_ if w not in vals]
            else:
                kind = ctx['kinds'].get(v)
                pool = [w for w, k in sorted(ctx['kinds'].items()) if kind and k == kind and w not in vals]
            out += [_map_values(node, s[1], {v: w}) for w in pool]
    elif s[0] == 'shift':
        out += [_set(node, sl, sl[4] + s[1]) for sl in L if sl[3] == 'const' and type(sl[4]) is int]
    elif s[0] == 'map':
        out += [_set(node, sl, s[3]) for sl in L if sl[3] == s[1] and sl[4] == s[2]]
    elif s[0] == 'any':
        for sl in L:
            if sl[3] != s[1]:
                continue
            if s[1] == 'op':
                pool = [o for o in _family(sl[4]) if o != sl[4]]
            elif s[1] == 'const':
                pool = [sl[4] + 1, sl[4] - 1] if type(sl[4]) is int else []
            elif s[1] == 'meth':
                pool = [m for m in ctx['meths'] if m != sl[4]]
            elif s[1] == 'func':
                pool = [f for f in ctx['funcs'] if f != sl[4]]
            else:
                pool = []
            out += [_set(node, sl, w) for w in pool]
    return out


def images(node, subs, ctx, locals_, cap=CAP):
    """Every way to apply all the substitutions to node (distinct, at most cap)."""
    res = [node]
    for s in subs:
        res = [m for n in res for m in _apply_sub(n, s, ctx, locals_)][:cap * 4]
    seen, out = set(), []
    for m in res:
        try:
            t = ast.unparse(m)
        except Exception:                                       # an operator put where it does not parse
            continue
        if t not in seen and t != ast.unparse(node):
            seen.add(t)
            out.append(m)
    return out[:cap]


# ------------------------------------------------------------------------------------------------- application
def _donors(f):
    """The statements of method f a transformation can start from: (node to transform, statement, compound)."""
    out = []
    for st in IV._statements(f):
        if isinstance(st, SIMPLE) and st.lineno == st.end_lineno:
            if isinstance(st, ast.Expr) and not isinstance(st.value, ast.Call):
                continue
            out.append((st, st, False))
        elif isinstance(st, (ast.If, ast.While)) and st.test.lineno == st.lineno == st.test.end_lineno:
            out.append((st.test, st, True))
    return out


def _insert_before(src, node, text):
    lines = src.split('\n')
    first = lines[node.lineno - 1]
    ind = first[:len(first) - len(first.lstrip())]
    return '\n'.join(lines[:node.lineno - 1] + [ind + ln for ln in text.split('\n')] + lines[node.lineno - 1:])


def _header(src, st, test):
    lines = src.split('\n')
    first = lines[st.lineno - 1]
    ind = first[:len(first) - len(first.lstrip())]
    kw = 'if' if isinstance(st, ast.If) else 'while'
    if not first.strip().startswith(kw + ' '):
        return None
    lines[st.lineno - 1] = f'{ind}{kw} {ast.unparse(test)}:'
    return '\n'.join(lines)


def apply_transform(t, src, focus_funcs=None):
    """The candidate patches the transformation makes on src: [(name, source)]."""
    tree = ast.parse(src)
    lines = src.split('\n')
    ctx = _context(src)
    methods = {n: f for n, f in IV._methods(tree).items() if n != '__init__'}
    subs = [tuple(s) for s in t['subs']]
    out, seen = [], {src}
    for fname, f in methods.items():
        if focus_funcs is not None and fname not in focus_funcs:
            continue
        own = {ln.strip() for ln in lines[f.lineno - 1:f.end_lineno]}
        loc = IV._locals(f)
        if t['edit'] in ('after', 'before', 'replace'):
            for node, st, compound in _donors(f):
                if t['edit'] in ('after', 'before') and (compound or isinstance(st, ast.Return)):
                    continue
                for m in images(node, subs, ctx, loc):
                    if t['edit'] in ('after', 'before'):
                        text = ast.unparse(m)
                        if text in own:
                            continue                                # the method already does it
                        cand = (IV._insert_after if t['edit'] == 'after' else _insert_before)(src, st, text)
                    elif compound:
                        cand = _header(src, st, m)
                    else:
                        cand = IV._replace(src, st, ast.unparse(m))
                    if cand and cand not in seen:
                        seen.add(cand)
                        out.append((f"transform {t['id']} {t['edit']} {fname}:{st.lineno}", cand))
        else:                                                       # transplant: a donor of another method
            anchors = [st for node, st, compound in _donors(f) if not isinstance(st, ast.Return)]   # after an if: its end
            body = [x for x in f.body if not (isinstance(x, ast.Expr) and isinstance(x.value, ast.Constant))]
            for gname, g in methods.items():
                if gname == fname:
                    continue
                for node, st, compound in _donors(g):
                    if compound or isinstance(st, ast.Return):
                        continue
                    for m in images(node, subs, ctx, loc):
                        text = ast.unparse(m)
                        if text in own or not set(_names(m)) <= set(loc) | {'self'}:
                            continue                                # it must make sense in the new method
                        places = [(f'{fname}:start', _insert_before(src, body[0], text))] if body else []
                        places += [(f'{fname}:{a.lineno}', IV._insert_after(src, a, text)) for a in anchors]
                        for where, cand in places:
                            if cand not in seen:
                                seen.add(cand)
                                out.append((f"transform {t['id']} transplant {gname}->{where}", cand))
    res = []
    for n, s in out:
        try:
            ast.parse(s)
        except SyntaxError:
            continue
        res.append((n, s))
    return res


def _names(node):
    """The bare names a statement reads or writes, builtins aside."""
    return [n.id for n in ast.walk(node) if isinstance(n, ast.Name) and n.id not in IV.BUILTINS]


# ------------------------------------------------------------------------------------------------- lifting
def _parse_line(text):
    """A statement, or a compound statement's header as (test expression, kind), from one line of text."""
    try:
        body = ast.parse(text).body
        return body[0] if len(body) == 1 else None
    except SyntaxError:
        pass
    if text.endswith(':'):
        try:
            st = ast.parse(text + '\n    pass').body[0]
        except SyntaxError:
            return None
        if isinstance(st, (ast.If, ast.While)):
            return st.test
    return None


def lift(src0, patch, provenance):
    """The transformations a verified patch shows: [transformation] (at most one per edit), with provenance."""
    e = IV._edit(src0, patch)
    if e is None:
        return []
    kind, anchor_text, text = e
    new = _parse_line(text) if '\n' not in text else None
    if new is None:
        return []
    found = []
    if kind == 'replace':
        old = _parse_line(anchor_text)
        ch = diff(old, new) if old is not None and type(old) is type(new) else None
        subs = abstract_subs(ch) if ch else None
        if subs:
            found.append(('replace', subs, anchor_text))
    else:
        tree = ast.parse(src0)
        methods = {n: f for n, f in IV._methods(tree).items() if n != '__init__'}
        lines = src0.split('\n')
        a, b = lines, patch.split('\n')
        at = next(i for i in range(len(a)) if a[i] != b[i])            # the inserted text starts at line at + 1
        nxt = next((s for f in methods.values() for s in IV._statements(f) if s.lineno == at + 1), None)
        home = next((n for n, f in methods.items() if any(lines[s.lineno - 1].strip() == anchor_text
                                                           for s in IV._statements(f))), None)
        best = None
        for fname, f in methods.items():
            for node, st, compound in _donors(f):
                if compound:
                    continue
                ch = diff(st, new)
                subs = abstract_subs(ch) if ch else None
                if not subs:
                    continue
                is_anchor = lines[st.lineno - 1].strip() == anchor_text
                if st is nxt:
                    edit = 'before'
                    is_anchor = True
                elif is_anchor:
                    edit = 'after'
                elif fname == home:
                    continue                                    # same method, not adjacent: not this language
                else:
                    edit = 'transplant'
                rank = (len(ch), 0 if is_anchor else 1, 0 if fname == home else 1)
                if best is None or rank < best[0]:
                    best = (rank, edit, subs, lines[st.lineno - 1].strip())
        if best:
            found.append((best[1], best[2], best[3]))
    out = []
    for edit, subs, donor in found:
        out.append({'id': f"{provenance.get('episode', 'x')}:{edit}:{_subs_text(subs)}", 'edit': edit,
                    'subs': [list(s) for s in subs], 'generation': provenance.get('generation', 1),
                    'derived': None, 'example': {'donor': donor, 'new': text}, 'provenance': provenance,
                    'status': 'candidate', 'tested': 0, 'admitted_by': [], 'successes': 0, 'failures': 0})
    return out


def _subs_text(subs):
    return '+'.join('-'.join(str(x) for x in s) for s in subs)


def key(t):
    return (t['edit'], tuple(tuple(s) for s in t['subs']))


# ------------------------------------------------------------------------------------------------- derivation
def _invert(s):
    if s[0] == 'map':
        return ('map', s[1], s[3], s[2])
    if s[0] == 'shift':
        return ('shift', -s[1])
    return None


def _generalise(s):
    if s[0] == 'map' and s[1] in ('op', 'meth', 'func'):
        return ('any', s[1])
    if s[0] == 'shift' and abs(s[1]) == 1:
        return ('any', 'const')
    return None


def derive(admitted, generation=2):
    """Candidate transformations derived from the admitted ones by the four operators: [transformation]."""
    out = []

    def new(edit, subs, op, parents):
        subs = tuple(sorted(set(tuple(s) for s in subs), key=repr))
        if not subs or len(subs) > MAX_SUBS:
            return
        prov = {'episode': f'derive-{op}', 'family': None, 'derived_from_families':
                sorted({p['provenance'].get('family') or '' for p in parents}), 'generation': generation}
        out.append({'id': f"g{generation}-{op}:{edit}:{_subs_text(subs)}", 'edit': edit,
                    'subs': [list(s) for s in subs], 'generation': generation,
                    'derived': {'op': op, 'from': [p['id'] for p in parents]}, 'example': None, 'provenance': prov,
                    'status': 'candidate', 'tested': 0, 'admitted_by': [], 'successes': 0, 'failures': 0})
    for t in admitted:
        subs = [tuple(s) for s in t['subs']]
        inv = [_invert(s) or s for s in subs]
        if inv != subs:
            new(t['edit'], inv, 'invert', [t])
        for e in EDITS:
            if e != t['edit']:
                new(e, subs, 'transfer', [t])
        gen = [_generalise(s) or s for s in subs]
        if gen != subs:
            new(t['edit'], gen, 'generalise', [t])
    for i, a in enumerate(admitted):
        for b in admitted[i + 1:]:
            if a['edit'] == b['edit']:
                new(a['edit'], [tuple(s) for s in a['subs']] + [tuple(s) for s in b['subs']], 'compose', [a, b])
    seen, res = {key(t) for t in admitted}, []
    for t in out:
        if key(t) not in seen:
            seen.add(key(t))
            res.append(t)
    return res


# ------------------------------------------------------------------------------------------------- the stores
class Transforms(IV.Library):
    """Transformations with provenance and outcomes (`transforms.jsonl`); admission as for rules, except that a
    derived transformation (no family of its own) is admitted by a verified repair of any family its parents did not
    come from."""

    def add(self, ts):
        have = {key(t) for t in self.rules}
        new = []
        for t in ts:
            if key(t) not in have:
                have.add(key(t))
                new.append(t)
        self.rules += new
        self.save()
        return new

    def candidates(self, family=None):
        return [t for t in self.rules if t['status'] == 'candidate' and t['provenance'].get('family') != family
                and family not in t['provenance'].get('derived_from_families', [])]

    def record(self, tid, verified, family, false_repair=False):
        t = self.get(tid)
        if t is None:
            return
        own = {t['provenance'].get('family')} | set(t['provenance'].get('derived_from_families', []))
        t['tested'] += 1
        if verified:
            t['successes'] += 1
            if family not in own:
                t['admitted_by'].append(family)
                t['status'] = 'admitted'
        else:
            t['failures'] += 1
            if false_repair and t['status'] == 'candidate' and not t['admitted_by']:
                t['status'] = 'rejected'
        self.save()


class Deriver:
    """The inventor's beliefs about its derivation operators (`deriver.json`): a Beta posterior per operator, a
    derived transformation admitted against one tested and not admitted. Derived candidates are tried in that order,
    then by how few candidates they make (minimum description length)."""

    def __init__(self, path):
        self.path = Path(path) if path else None
        self.beliefs = {op: list(PRIOR) for op in DERIVATIONS + ('lifted',)}
        if self.path and self.path.exists():
            self.beliefs.update(json.loads(self.path.read_text()))

    def save(self):
        if self.path:
            self.path.write_text(json.dumps(self.beliefs, indent=1))

    def mean(self, op):
        a, b = self.beliefs[op]
        return a / (a + b)

    def op_of(self, t):
        return (t.get('derived') or {}).get('op', 'lifted')

    def order(self, ts, src, focus_funcs=None):
        scored = []
        for t in ts:
            n = len(apply_transform(t, src, focus_funcs))
            if n:
                scored.append((-self.mean(self.op_of(t)), n, t['id'], t))
        return [t for *_, t in sorted(scored, key=lambda x: x[:3])]

    def learn(self, t, admitted):
        op = self.op_of(t)
        a, b = self.beliefs[op]
        self.beliefs[op] = [a + 1, b] if admitted else [a, b + 1]
        self.save()
