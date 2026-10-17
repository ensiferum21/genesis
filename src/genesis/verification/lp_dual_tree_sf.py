"""Exact checker for branch-and-bound certificates over generated sum-free rows (B20_R56; trusted side, DEV only).

The sum-free counterpart of `verification.lp_dual_tree_c4` (B20_R48), which is unchanged. A certificate bounds the
largest sum-free subset of a sumfree_host_v1 host (a finite set of positive integers) by U.

**Hosts.** A task is a plain record {'domain': 'sumfree_host_v1', 'task_id', 'elements': sorted distinct positive
integers}; certificates name it by `common.digest`. A set S is sum-free when no a + b (a = b allowed) of S lies in S.

**Rows.** Each row bounds |S ∩ R| for every sum-free S over a set R of host elements:
  * schur [a, b, c]: a < b, a + b = c, all in the host; rhs 2 (all three would give a + b = c inside S);
  * double [a, c]: a + a = c, both in the host; rhs 1;
  * pattern: a copy of a registry pattern given by a map [y0, …, yk-1] of distinct host elements that satisfies
    every relation v_i + v_j = v_l of the pattern's Lean statement; rhs ex(P). The Lean statement (B20_R55, CHECKED)
    says that for every sum-free S and all values satisfying those relations, Σ_i ind(S, v_i) <= ex(P); with
    distinct values that sum is |S ∩ R|.

**Registry** (`registry_from_package`). A pattern row comes only from a CHECKED statement of a theory package with
intact hashes (checked by the caller) whose `SFDefs` source is the trusted sum-free contract
(`invention.cuts_sf.SOURCE`), whose statement text appears verbatim as a `def … : Prop :=` in its conjecture module,
and whose text has exactly the form

    ∀ (S : Finset ℕ) (hS : SF.SumFree S) (v0 : ℕ) … (vk : ℕ) (r0 : va + vb = vc) … (rt : …),
      SF.ind S v0 + … + SF.ind S vk ≤ ex

with the binders v0..vk in order, relations r0..rt in order over those variables, and every variable summed once
in order.

**Tree.** Each internal node branches on one host element x not yet fixed: `zero` fixes x out, `one` fixes x in.
A leaf is either
  * dual: rows with positive rational weights and nonnegative slacks on the free elements; a row's effective rhs is
    rhs − |row ∩ F1| >= 0, every free element is covered at least once, and the leaf bound |F1| + ⌊Σ weight ×
    effective rhs + Σ slack⌋ is at most U; or
  * infeasible: one row with |row ∩ F1| > rhs.

**Soundness.** Take any sum-free S ⊆ host. Follow the tree, going to `one` at an element of S and to `zero`
otherwise; the leaf reached has F1 ⊆ S and F0 ∩ S = ∅. Every row holds for S, so no S reaches an infeasible leaf,
and at a dual leaf weak LP duality gives |S ∩ free| <= the dual objective, so |S| <= the leaf bound <= U.

The checker uses exact arithmetic and no optimisation library. Nothing in the evaluator or the custodian uses it.
"""
from fractions import Fraction
import hashlib
import math
from pathlib import Path
import re

from ..common import digest

SCHEMA = 'genesis-lp-dual-tree-sumfree-certificate-v1'
REGISTRY_SCHEMA = 'genesis-generated-rows-sumfree-registry-v1'
DOMAIN = 'sumfree_host_v1'
HEAD = '∀ (S : Finset ℕ) (hS : SF.SumFree S) '
MAX_NODES = 2_000_000


def checker_identity():
    return 'genesis.verification.lp_dual_tree_sf@' + hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def task_problems(task):
    if not isinstance(task, dict) or task.get('domain') != DOMAIN:
        return ['not a sumfree_host_v1 task']
    el = task.get('elements')
    if not isinstance(el, list) or any(type(x) is not int or x < 1 for x in el) or el != sorted(set(el)):
        return ['host elements are not sorted distinct positive integers']
    return []


def parse_pattern_statement(lean):
    """(k, relations [(a, b, c)], ex) from a sum-free pattern statement, or None."""
    if not lean.startswith(HEAD):
        return None
    m = re.fullmatch(r'((?:\(v\d+ : ℕ\) )*\(v\d+ : ℕ\)) ((?:\(r\d+ : v\d+ \+ v\d+ = v\d+\) )*\(r\d+ : v\d+ \+ v\d+ = v\d+\)), '
                     r'(.+) ≤ (\d+)', lean[len(HEAD):])
    if not m:
        return None
    binders = re.findall(r'\(v(\d+) : ℕ\)', m.group(1))
    k = len(binders)
    if binders != [str(i) for i in range(k)]:
        return None
    rels = re.findall(r'\(r(\d+) : v(\d+) \+ v(\d+) = v(\d+)\)', m.group(2))
    if [int(t) for t, *_ in rels] != list(range(len(rels))):
        return None
    relations = [(int(a), int(b), int(c)) for _, a, b, c in rels]
    if any(not (x < k) for r in relations for x in r):
        return None
    if m.group(3) != ' + '.join(f'SF.ind S v{i}' for i in range(k)):
        return None
    return k, relations, int(m.group(4))


def registry_from_package(package, *, sf_source):
    """{'schema', 'package_sha256', 'patterns': {id: {'k', 'relations', 'ex', 'statement'}}} from a theory package
    whose hashes the caller has already checked. Raises ValueError when the definitions differ or a checked pattern
    statement is not a sum-free pattern bound."""
    mods = {m['name']: m['source'] for m in package['modules']}
    if mods.get('SFDefs') != sf_source:
        raise ValueError('the package does not use the trusted sum-free contract (SFDefs)')
    conj = [s for n, s in mods.items() if n.endswith('Conj')]
    patterns = {}
    for s in package['statements']:
        if s.get('status') != 'CHECKED' or s.get('role') != 'pattern':
            continue
        if not any(f'def {s["id"]} : Prop := {s["lean"]}\n' in c for c in conj):
            raise ValueError(f'statement {s["id"]} is not the text of the checked conjecture')
        parsed = parse_pattern_statement(s['lean'])
        if parsed is None:
            raise ValueError(f'statement {s["id"]} is not a sum-free pattern bound')
        k, relations, ex = parsed
        patterns[s['id']] = {'k': k, 'relations': [list(r) for r in relations], 'ex': ex,
                             'statement': s['spec_const']}
    return {'schema': REGISTRY_SCHEMA, 'package_sha256': package['package_sha256'], 'patterns': patterns}


class Bad(Exception):
    pass


def row_elements(q, registry, host):
    """(element list, rhs) of a row, or Bad."""
    kind = q.get('kind')
    if kind == 'schur':
        t = list(q.get('triple', ()))
        if len(t) != 3 or any(type(x) is not int for x in t) or not (t[0] < t[1] and t[0] + t[1] == t[2]):
            raise Bad('a schur row names a < b with a + b = c')
        els, rhs = t, 2
    elif kind == 'double':
        t = list(q.get('pair', ()))
        if len(t) != 2 or any(type(x) is not int for x in t) or t[0] + t[0] != t[1] or t[0] < 1:
            raise Bad('a double row names a with a + a = c')
        els, rhs = t, 1
    elif kind == 'pattern':
        pat = registry['patterns'].get(q.get('pattern'))
        if pat is None:
            raise Bad(f'unknown pattern {q.get("pattern")!r}')
        phi = list(q.get('map', ()))
        if len(phi) != pat['k'] or len(set(phi)) != len(phi) or any(type(v) is not int for v in phi):
            raise Bad('pattern map is not an injective map of the right size')
        if any(phi[a] + phi[b] != phi[c] for a, b, c in pat['relations']):
            raise Bad('pattern map violates a relation of the pattern')
        els, rhs = phi, pat['ex']
    else:
        raise Bad(f'unknown row kind {kind!r}')
    if not set(els) <= host:
        raise Bad('row names an element outside this host')
    if q.get('rhs') != rhs:
        raise Bad('wrong right-hand side')
    return els, rhs


def _leaf(leaf, registry, E, host, F0, F1, upper):
    if not isinstance(leaf, dict):
        raise Bad('a leaf is an object')
    if leaf.get('kind') == 'infeasible':
        els, rhs = row_elements(leaf.get('row') or {}, registry, host)
        if sum(1 for x in els if x in F1) <= rhs:
            raise Bad('an infeasible leaf names a row its fixed-in elements do not overfill')
        return
    if leaf.get('kind') != 'dual':
        raise Bad(f'unknown leaf kind {leaf.get("kind")!r}')
    cover = {x: Fraction(0) for x in E if x not in F0 and x not in F1}
    total = Fraction(0)
    for q in leaf.get('inequalities', ()):
        weight = Fraction(q['weight'])
        if weight <= 0:
            raise Bad('non-positive inequality weight')
        els, rhs = row_elements(q, registry, host)
        eff = rhs - sum(1 for x in els if x in F1)
        if eff < 0:
            raise Bad('a dual leaf uses a row its fixed-in elements overfill')
        for x in els:
            if x in cover:
                cover[x] += weight
        total += weight * eff
    for x, s in leaf.get('slack', ()):
        s = Fraction(s)
        if type(x) is not int or x not in cover or s < 0:
            raise Bad('slack on a fixed or non-host element, or negative slack')
        cover[x] += s
        total += s
    if any(v < 1 for v in cover.values()):
        raise Bad('dual infeasible at a leaf: a free element is covered less than once')
    if len(F1) + math.floor(total) > upper:
        raise Bad(f'a leaf bound {len(F1) + math.floor(total)} exceeds the claimed upper bound {upper}')


def check_certificate(task, cert, registry):
    """Independent exact check. Returns {'verdict': VALID | REJECTED, 'bound', 'reason', 'leaves'}."""
    def bad(reason):
        return {'verdict': 'REJECTED', 'bound': None, 'reason': reason, 'leaves': None}
    if task_problems(task):
        return bad(task_problems(task)[0])
    if not isinstance(cert, dict) or cert.get('schema') != SCHEMA:
        return bad('not a sum-free branch-and-bound certificate')
    if cert.get('task_sha256') != digest(task) or cert.get('domain') != DOMAIN:
        return bad('certificate names another task')
    if registry.get('schema') != REGISTRY_SCHEMA or cert.get('registry_sha256') != digest(registry):
        return bad('certificate names another registry')
    upper = cert.get('upper')
    if type(upper) is not int or upper < 0:
        return bad('the claimed upper bound is not a nonnegative integer')
    E = list(task['elements'])
    host = set(E)
    stack = [(cert.get('tree'), frozenset(), frozenset())]
    nodes = leaves = 0
    try:
        while stack:
            node, F0, F1 = stack.pop()
            nodes += 1
            if nodes > MAX_NODES:
                return bad('tree too large')
            if not isinstance(node, dict):
                return bad('a tree node is an object')
            if 'leaf' in node:
                _leaf(node['leaf'], registry, E, host, F0, F1, upper)
                leaves += 1
                continue
            x = node.get('branch')
            if type(x) is not int or x not in host or x in F0 or x in F1:
                return bad('a branch names a fixed or non-host element')
            if 'zero' not in node or 'one' not in node:
                return bad('a branch node lacks a child')
            stack.append((node['zero'], F0 | {x}, F1))
            stack.append((node['one'], F0, F1 | {x}))
    except Bad as exc:
        return bad(str(exc))
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as exc:
        return bad(f'malformed certificate ({type(exc).__name__})')
    return {'verdict': 'VALID', 'bound': upper, 'reason': None, 'leaves': leaves}


def check_witness(task, witness):
    """The value of a claimed sum-free subset of the host, or ValueError."""
    if task_problems(task):
        raise ValueError(task_problems(task)[0])
    w = sorted(set(witness))
    if len(w) != len(witness) or not set(w) <= set(task['elements']):
        raise ValueError('witness is not a set of host elements')
    s = set(w)
    if any(a + b in s for a in s for b in s):
        raise ValueError('witness is not sum-free')
    return len(w)


__all__ = ['SCHEMA', 'REGISTRY_SCHEMA', 'DOMAIN', 'check_certificate', 'registry_from_package',
           'parse_pattern_statement', 'checker_identity', 'row_elements', 'task_problems', 'check_witness']
