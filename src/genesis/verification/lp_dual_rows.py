"""Exact checker for LP dual certificates over generated rows (B20_R32; trusted side, DEV only).

`verification.lp_dual` (v1) checks LP dual certificates whose rows are the host's motifs. This
module checks a second kind of certificate for triangle-free hosts. Its rows may also be copies
of *generated patterns*: inequalities "a triangle-free edge set has at most ex(F) edges on any copy
of F". Their validity is a Lean theorem in a theory package (B20_R31, `invention.cuts`). v1 and
its identity are unchanged. Nothing in the evaluator, the custodian or the certificate bundles
uses this module; wiring it in would be a separately reviewed trust-path change.

**Registry** (`registry_from_package`). Each pattern row comes from a CHECKED statement of a
theory package with intact hashes. The checks are:
  * the package's `GTDefs` source is the repository's trusted definitions
    (`triangle_theory.DEFS_SOURCE`);
  * its `PCDefs` source defines `PC.adj` exactly as ADJ_DEF says;
  * the statement's Lean text appears verbatim as a `def … : Prop :=` in the package's conjecture
    module, so the parsed text is the text that was checked;
  * the text has exactly the form

        ∀ (S : GT.Edges) (hS : GT.TriangleFree S) (hH : ∀ e ∈ S, e.1 < e.2) (v0 : ℕ) … (vk : ℕ),
          PC.adj S va vb + … ≤ ex

    with distinct pairs a < b that use every vertex 0..k.

Such a statement says: for every triangle-free edge set S in host form (each edge (u, v) with
u < v, as witnesses are), and for every assignment of host vertices to v0..vk, the adjacency sum is
at most ex. On an injective assignment that maps every pattern edge to a host edge, PC.adj S is
the indicator of that host edge in S, so the row Σ x_e ≤ ex over the copy holds for S.

**Certificate** (`check_certificate`). Rows are triangles of the host (rhs 2) or pattern copies
given by an injective vertex map (rhs ex(F), from the registry), each with a positive rational
weight, plus nonnegative slacks on host edges. The checker verifies, in exact arithmetic:
  * the task identity;
  * the registry digest named in the certificate;
  * every row and its right-hand side;
  * dual feasibility edge by edge;
  * the bound.
Weak duality then gives |S| ≤ floor(objective) for every triangle-free S. The checker imports no
optimisation library.
"""
from fractions import Fraction
import hashlib
import math
from pathlib import Path
import re

from ..common import digest

SCHEMA = 'genesis-lp-dual-rows-certificate-v1'
REGISTRY_SCHEMA = 'genesis-generated-rows-registry-v1'
ADJ_DEF = 'def adj (S : GT.Edges) (u v : ℕ) : ℕ := if (u, v) ∈ S ∨ (v, u) ∈ S then 1 else 0'
HEAD = '∀ (S : GT.Edges) (hS : GT.TriangleFree S) (hH : ∀ e ∈ S, e.1 < e.2) '


def checker_identity():
    return 'genesis.verification.lp_dual_rows@' + hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def parse_pattern_statement(lean):
    """(number of vertices, sorted edge list, ex) from a pattern statement, or None."""
    if not lean.startswith(HEAD):
        return None
    rest = lean[len(HEAD):]
    m = re.fullmatch(r'((?:\(v\d+ : ℕ\) )*\(v\d+ : ℕ\)), (.+) ≤ (\d+)', rest)
    if not m:
        return None
    binders = re.findall(r'\(v(\d+) : ℕ\)', m.group(1))
    k = len(binders)
    if binders != [str(i) for i in range(k)]:
        return None
    terms = m.group(2).split(' + ')
    edges = []
    for t in terms:
        tm = re.fullmatch(r'PC\.adj S v(\d+) v(\d+)', t)
        if not tm:
            return None
        a, b = int(tm.group(1)), int(tm.group(2))
        if not a < b < k:
            return None
        edges.append((a, b))
    if len(set(edges)) != len(edges) or {x for e in edges for x in e} != set(range(k)):
        return None
    return k, sorted(edges), int(m.group(3))


def registry_from_package(package, *, defs_source):
    """{'schema', 'package_sha256', 'patterns': {id: {'vertices', 'edges', 'ex', 'statement'}}}
    from a theory package whose hashes the caller has already checked
    (theory_package.integrity_problems). Raises ValueError when the definitions differ."""
    mods = {m['name']: m['source'] for m in package['modules']}
    if mods.get('GTDefs') != defs_source:
        raise ValueError('the package does not use the trusted GTDefs definitions')
    if ADJ_DEF not in mods.get('PCDefs', ''):
        raise ValueError('the package does not define PC.adj as 0/1 adjacency')
    conj = [s for n, s in mods.items() if n.endswith('Conj')]
    patterns = {}
    for s in package['statements']:
        if s.get('status') != 'CHECKED' or s.get('role') != 'pattern':
            continue
        if not any(f'def {s["id"]} : Prop := {s["lean"]}\n' in c for c in conj):
            raise ValueError(f'statement {s["id"]} is not the text of the checked conjecture')
        parsed = parse_pattern_statement(s['lean'])
        if parsed is None:
            raise ValueError(f'statement {s["id"]} is not a pattern bound')
        k, edges, ex = parsed
        patterns[s['id']] = {'vertices': k, 'edges': [list(e) for e in edges], 'ex': ex, 'statement': s['spec_const']}
    return {'schema': REGISTRY_SCHEMA, 'package_sha256': package['package_sha256'], 'patterns': patterns}


def check_certificate(task, cert, registry):
    """Independent exact check. Returns {'verdict': VALID | REJECTED, 'bound', 'reason'}."""
    def bad(reason):
        return {'verdict': 'REJECTED', 'bound': None, 'reason': reason}
    if not isinstance(cert, dict) or cert.get('schema') != SCHEMA:
        return bad('not a generated-rows LP dual certificate')
    if task.domain != 'triangle_free_host_v1':
        return bad('generated rows are defined for triangle-free hosts only')
    if cert.get('task_sha256') != digest(task.model_dump(mode='json')) or cert.get('domain') != task.domain:
        return bad('certificate names another task')
    if registry.get('schema') != REGISTRY_SCHEMA or cert.get('registry_sha256') != digest(registry):
        return bad('certificate names another registry')
    E = [tuple(e) for e in task.edges]
    Eset = set(E)
    cover = {e: Fraction(0) for e in E}
    total = Fraction(0)
    try:
        for q in cert['inequalities']:
            weight = Fraction(q['weight'])
            if weight <= 0:
                return bad('non-positive inequality weight')
            if q['kind'] == 'triangle':
                edges = [tuple(e) for e in q['edges']]
                vs = sorted({x for e in edges for x in e})
                if len(vs) != 3 or sorted(edges) != [(vs[0], vs[1]), (vs[0], vs[2]), (vs[1], vs[2])] or \
                        not set(edges) <= Eset:
                    return bad(f'row on {edges} is not a triangle of this host')
                rhs = 2
            elif q['kind'] == 'pattern':
                pat = registry['patterns'].get(q['pattern'])
                if pat is None:
                    return bad(f'unknown pattern {q["pattern"]!r}')
                phi = list(q['map'])
                if len(phi) != pat['vertices'] or len(set(phi)) != len(phi) or \
                        any(type(v) is not int for v in phi):
                    return bad('pattern map is not an injective vertex map of the right size')
                edges = [tuple(sorted((phi[a], phi[b]))) for a, b in pat['edges']]
                if not set(edges) <= Eset:
                    return bad('pattern map sends an edge outside this host')
                rhs = pat['ex']
            else:
                return bad(f'unknown row kind {q["kind"]!r}')
            if q['rhs'] != rhs:
                return bad('wrong right-hand side')
            for e in edges:
                cover[e] += weight
            total += weight * rhs
        for e, s in cert['slack']:
            e, s = tuple(e), Fraction(s)
            if e not in cover or s < 0:
                return bad('slack on a non-edge or negative slack')
            cover[e] += s
            total += s
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as exc:
        return bad(f'malformed certificate ({type(exc).__name__})')
    if any(v < 1 for v in cover.values()):
        return bad('dual infeasible: an edge is covered less than once')
    if Fraction(cert['objective']) != total or cert['bound'] != math.floor(total):
        return bad('objective or bound does not match the weights')
    return {'verdict': 'VALID', 'bound': math.floor(total), 'reason': None}


__all__ = ['SCHEMA', 'REGISTRY_SCHEMA', 'ADJ_DEF', 'check_certificate', 'registry_from_package',
           'parse_pattern_statement', 'checker_identity']
