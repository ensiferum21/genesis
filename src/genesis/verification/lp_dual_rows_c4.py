"""Exact checker for LP dual certificates over generated C4 rows (B20_R47; trusted side, DEV only).

The C4-free counterpart of `verification.lp_dual_rows`. That module, and its identity, are unchanged. A
certificate here bounds the largest C4-free subgraph of a c4_host_v2 host. Its rows are 4-cycles of the
host (at most 3 of their 4 edges) or copies of generated C4 patterns: "a C4-free edge set has at most
ex(F) edges on any injective copy of F". Lean proves each pattern's validity in a theory package
(B20_R46, `invention.cuts_c4`). Nothing in the evaluator or the custodian uses this module.

**Registry** (`registry_from_package`). A pattern row comes only from a CHECKED statement of a theory
package with intact hashes. The checks are:
  * the package's `GTDefs` source is the trusted definitions (`triangle_theory.DEFS_SOURCE`);
  * its `G4Defs` source is the c4_host_v2 contract's (`representations.C4_SOURCE`);
  * its `P4Defs` source defines `P4.adj` exactly as ADJ_DEF says;
  * the statement's text appears verbatim as a `def … : Prop :=` in the package's conjecture module;
  * the text has exactly the form

        ∀ (S : GT.Edges) (hS : G4.C4Free S) (v0 : ℕ) … (vk : ℕ) (h_v0_v1 : v0 ≠ v1) … (h_v{k-1}_vk : … ≠ …),
          P4.adj S va vb + … ≤ ex

    with every pair i < j present, in order, and distinct edge pairs a < b that use every vertex.

Such a statement says: for every C4-free edge set S and every injective assignment of host vertices to
v0..vk, the adjacency sum is at most ex. On an injective map that sends every pattern edge to a host
edge, P4.adj S is the indicator of that host edge in S, so the row Σ x_e ≤ ex over the copy holds for S.

**Certificate** (`check_certificate`). Rows are 4-cycles of the host, given as a vertex cycle
[a, b, c, d] of distinct vertices whose four edges are host edges (rhs 3), or pattern copies given by an
injective vertex map (rhs ex(F), from the registry). Each row has a positive rational weight, and host
edges get nonnegative slacks. The checker verifies the following in exact arithmetic, with no
optimisation library:
  * the task identity and the registry digest;
  * every row and its right-hand side;
  * dual feasibility edge by edge;
  * the bound.
"""
from fractions import Fraction
import hashlib
import math
from pathlib import Path
import re

from ..common import digest

SCHEMA = 'genesis-lp-dual-rows-c4-certificate-v1'
REGISTRY_SCHEMA = 'genesis-generated-rows-c4-registry-v1'
DOMAIN = 'c4_host_v2'
ADJ_DEF = 'def adj (S : GT.Edges) (u v : ℕ) : ℕ := if (u, v) ∈ S ∨ (v, u) ∈ S then 1 else 0'
HEAD = '∀ (S : GT.Edges) (hS : G4.C4Free S) '


def checker_identity():
    return 'genesis.verification.lp_dual_rows_c4@' + hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def parse_pattern_statement(lean):
    """(number of vertices, sorted edge list, ex) from a C4 pattern statement, or None."""
    if not lean.startswith(HEAD):
        return None
    rest = lean[len(HEAD):]
    m = re.fullmatch(r'((?:\(v\d+ : ℕ\) )*\(v\d+ : ℕ\)) ((?:\(h_v\d+_v\d+ : v\d+ ≠ v\d+\) )*\(h_v\d+_v\d+ : v\d+ ≠ v\d+\)), '
                     r'(.+) ≤ (\d+)', rest)
    if not m:
        return None
    binders = re.findall(r'\(v(\d+) : ℕ\)', m.group(1))
    k = len(binders)
    if binders != [str(i) for i in range(k)]:
        return None
    hyps = re.findall(r'\(h_v(\d+)_v(\d+) : v(\d+) ≠ v(\d+)\)', m.group(2))
    want = [(i, j) for i in range(k) for j in range(i + 1, k)]
    if [(int(a), int(b)) for a, b, _, _ in hyps] != want or any((a, b) != (c, d) for a, b, c, d in hyps):
        return None
    edges = []
    for t in m.group(3).split(' + '):
        tm = re.fullmatch(r'P4\.adj S v(\d+) v(\d+)', t)
        if not tm:
            return None
        a, b = int(tm.group(1)), int(tm.group(2))
        if not a < b < k:
            return None
        edges.append((a, b))
    if len(set(edges)) != len(edges) or {x for e in edges for x in e} != set(range(k)):
        return None
    return k, sorted(edges), int(m.group(4))


def registry_from_package(package, *, defs_source, c4_source):
    """{'schema', 'package_sha256', 'patterns': {id: {'vertices', 'edges', 'ex', 'statement'}}} from a
    theory package whose hashes the caller has already checked. Raises ValueError when the definitions
    differ or a checked statement is not a C4 pattern bound."""
    mods = {m['name']: m['source'] for m in package['modules']}
    if mods.get('GTDefs') != defs_source:
        raise ValueError('the package does not use the trusted GTDefs definitions')
    if mods.get('G4Defs') != c4_source:
        raise ValueError('the package does not use the c4_host_v2 contract definitions (G4Defs)')
    if ADJ_DEF not in mods.get('P4Defs', '') or 'namespace P4' not in mods.get('P4Defs', ''):
        raise ValueError('the package does not define P4.adj as 0/1 adjacency')
    conj = [s for n, s in mods.items() if n.endswith('Conj')]
    patterns = {}
    for s in package['statements']:
        if s.get('status') != 'CHECKED' or s.get('role') != 'pattern':
            continue
        if not any(f'def {s["id"]} : Prop := {s["lean"]}\n' in c for c in conj):
            raise ValueError(f'statement {s["id"]} is not the text of the checked conjecture')
        parsed = parse_pattern_statement(s['lean'])
        if parsed is None:
            raise ValueError(f'statement {s["id"]} is not a C4 pattern bound')
        k, edges, ex = parsed
        patterns[s['id']] = {'vertices': k, 'edges': [list(e) for e in edges], 'ex': ex, 'statement': s['spec_const']}
    return {'schema': REGISTRY_SCHEMA, 'package_sha256': package['package_sha256'], 'patterns': patterns}


def check_certificate(task, cert, registry):
    """Independent exact check. Returns {'verdict': VALID | REJECTED, 'bound', 'reason'}."""
    def bad(reason):
        return {'verdict': 'REJECTED', 'bound': None, 'reason': reason}
    if not isinstance(cert, dict) or cert.get('schema') != SCHEMA:
        return bad('not a generated-rows C4 LP dual certificate')
    if task.domain != DOMAIN:
        return bad('generated C4 rows are defined for c4_host_v2 hosts only')
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
            if q['kind'] == 'cycle':
                cyc = list(q['cycle'])
                if len(cyc) != 4 or len(set(cyc)) != 4 or any(type(v) is not int for v in cyc):
                    return bad('a cycle row names four distinct vertices')
                edges = [tuple(sorted((cyc[i], cyc[(i + 1) % 4]))) for i in range(4)]
                if not set(edges) <= Eset:
                    return bad(f'row on {cyc} is not a 4-cycle of this host')
                rhs = 3
            elif q['kind'] == 'pattern':
                pat = registry['patterns'].get(q['pattern'])
                if pat is None:
                    return bad(f'unknown pattern {q["pattern"]!r}')
                phi = list(q['map'])
                if len(phi) != pat['vertices'] or len(set(phi)) != len(phi) or any(type(v) is not int for v in phi):
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


__all__ = ['SCHEMA', 'REGISTRY_SCHEMA', 'DOMAIN', 'ADJ_DEF', 'check_certificate', 'registry_from_package',
           'parse_pattern_statement', 'checker_identity']
