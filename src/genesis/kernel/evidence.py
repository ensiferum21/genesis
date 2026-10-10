"""Evidence DAG, epistemic effects, trust graph, claim promotion and revocation.

Spec anchors: §3.1-3.2 (release gate, trust root, CIRCULAR_JUSTIFICATION),
§4.3 (epistemic type and effect system), §7 (orthogonal evidence axes),
§15.1 (trust tower), §26.2 (evidence promotion), §37.3 (transitive invalidation).
Roadmap W02: R-01 (signed evidence bound to the claim) and R-02 (effective
revocation everywhere).

Everything is stored as immutable Store entities; revocations and promotion
decisions are appended, never edited. No stored level is authoritative:
`levels()` re-derives the effective level of every axis from the immutable
evidence graph, the current revocations and the current trust registry, and
every consumer (reports, index, release export, bundle verification) uses it.
`recorded_levels()` is the historical record of what was granted.

Externally signed kinds are interpreted only by `kernel.receipts` (shared with
the phase machine, release preflight and the custodian). The role that may sign
a kind is fixed in trusted code; wrapper fields such as `verdict` or a claimed
signing role are ignored for those kinds.
"""
from collections import Counter
from enum import Enum

from .. import eligibility
from ..common import digest, utcnow
from . import receipts as R
from .roles import load_role_registry


class Effect(str, Enum):
    USES_DEV_DATA = 'USES_DEV_DATA'
    TOUCHED_SEALED_SET = 'TOUCHED_SEALED_SET'
    APPROXIMATE = 'APPROXIMATE'
    SELF_JUDGED = 'SELF_JUDGED'
    NONDETERMINISTIC = 'NONDETERMINISTIC'
    HUMAN_INTERVENTION = 'HUMAN_INTERVENTION'
    MANUAL_INTERVENTION = 'MANUAL_INTERVENTION'
    EXTERNAL_SOURCE = 'EXTERNAL_SOURCE'
    HYPOTHETICAL = 'HYPOTHETICAL'
    UNCHECKED_PROPOSAL = 'UNCHECKED_PROPOSAL'
    INTERVENTION_CANDIDATE = 'INTERVENTION_CANDIDATE'
    UNKNOWN_TYPE = 'UNKNOWN_TYPE'
    CONTAMINATED = 'CONTAMINATED'


# Effects that taint downstream artifacts until resolved (§4.3).
SPECULATIVE = {Effect.HYPOTHETICAL, Effect.UNCHECKED_PROPOSAL, Effect.INTERVENTION_CANDIDATE, Effect.UNKNOWN_TYPE}
CONTAMINATING = {Effect.TOUCHED_SEALED_SET, Effect.CONTAMINATED}
CHECK_KINDS = {'witness_check', 'exact_check', 'formal_check', 'bound_state', 'sealed_evaluation',
               'sealed_transfer_evaluation', 'sealed_improver_evaluation', 'sealed_generation_evaluation',
               'ablation', 'placebo', 'internal_replication', 'external_reproduction',
               'external_priority_adjudication', 'priority_check'}
PASSING = ('VALID', 'SUPPORTED', 'PASS')

AXES = {
    'math': ['UNCHECKED', 'EXECUTABLE', 'WITNESS_VALID', 'FINITE_CERTIFIED', 'THEOREM_CHECKED', 'OPTIMALITY_CHECKED'],
    'utility': ['NOT_TESTED', 'DEV_ONLY', 'CONFIRMED_SAME_DOMAIN', 'CONFIRMED_TRANSFER'],
    'causality': ['NOT_TESTED', 'CORRELATED', 'ABLATION_SUPPORTED', 'PLACEBO_CONTROLLED'],
    'improver': ['NOT_TESTED', 'SAME_DOMAIN_CONFIRMED', 'CROSS_DOMAIN_CONFIRMED', 'MULTIGEN_CONFIRMED'],
    'novelty': ['UNKNOWN', 'REDISCOVERY', 'VARIANT', 'CANDIDATE_NOVEL', 'EXTERNALLY_CHECKED_NOVEL'],
    'replication': ['NONE', 'INTERNAL_INDEPENDENT', 'EXTERNAL_REPRODUCTION'],
}
FLOOR = {axis: levels[0] for axis, levels in AXES.items()}
# Negative / non-ordinal math outcomes are recorded, never "promoted to".
MATH_TERMINAL = {'REJECTED', 'UNSETTLED', 'CHECKER_ERROR'}

CONFIRMATION = {('utility', 'CONFIRMED_SAME_DOMAIN'), ('utility', 'CONFIRMED_TRANSFER'),
                ('improver', 'SAME_DOMAIN_CONFIRMED'), ('improver', 'CROSS_DOMAIN_CONFIRMED'),
                ('improver', 'MULTIGEN_CONFIRMED'), ('replication', 'EXTERNAL_REPRODUCTION'),
                ('novelty', 'EXTERNALLY_CHECKED_NOVEL')}

# Artifact kinds whose presence (validly checked) licenses a level.
REQUIRED_EVIDENCE = {
    ('math', 'EXECUTABLE'): [('execution_receipt', 1)],
    ('math', 'WITNESS_VALID'): [('witness_check', 1)],
    ('math', 'FINITE_CERTIFIED'): [('exact_check', 2)],          # two independent exact checkers
    ('math', 'THEOREM_CHECKED'): [('formal_check', 1)],
    ('math', 'OPTIMALITY_CHECKED'): [('bound_state', 1)],
    ('utility', 'DEV_ONLY'): [('dev_comparison', 1)],
    ('utility', 'CONFIRMED_SAME_DOMAIN'): [('sealed_evaluation', 1)],
    ('utility', 'CONFIRMED_TRANSFER'): [('sealed_transfer_evaluation', 1)],
    ('causality', 'CORRELATED'): [('dev_comparison', 1)],
    ('causality', 'ABLATION_SUPPORTED'): [('ablation', 1)],
    ('causality', 'PLACEBO_CONTROLLED'): [('ablation', 1), ('placebo', 1)],
    ('improver', 'SAME_DOMAIN_CONFIRMED'): [('sealed_improver_evaluation', 1)],
    ('improver', 'CROSS_DOMAIN_CONFIRMED'): [('sealed_improver_evaluation', 2)],
    ('improver', 'MULTIGEN_CONFIRMED'): [('sealed_generation_evaluation', 3)],
    ('novelty', 'REDISCOVERY'): [('priority_check', 1)],
    ('novelty', 'VARIANT'): [('priority_check', 1)],
    ('novelty', 'CANDIDATE_NOVEL'): [('priority_check', 1)],
    ('novelty', 'EXTERNALLY_CHECKED_NOVEL'): [('external_priority_adjudication', 1)],
    ('replication', 'INTERNAL_INDEPENDENT'): [('internal_replication', 1)],
    ('replication', 'EXTERNAL_REPRODUCTION'): [('external_reproduction', 1)],
}
# Kinds whose meaning comes only from an envelope signed by a registry role (kernel.receipts).
EXTERNALLY_SIGNED = set(R.KIND_ROLES) - {'preregistration_anchor'}
SIGNED_KINDS = set(R.KIND_ROLES)


class PromotionRejected(Exception):
    pass


def _norm_effects(effects):
    out = set()
    for e in effects:
        out.add(Effect(e))  # raises ValueError on unknown effect names: no typo can bypass the gate
    return out


class _Context:
    """Per-decision cache: registry, verified signed nodes, revocations."""

    def __init__(self, kernel):
        self.k = kernel
        self._registry = None
        self._opened = {}

    def registry(self):
        if self._registry is None:
            self._registry = self.k._registry()
        return self._registry

    def opened(self, nid, kind):
        """(payload or None, problems, envelope) for a signed node, verified once."""
        if nid not in self._opened:
            reg, problems, _ = self.registry()
            wrapper = self.k.s.get(self.k.node(nid)['payload_hash'])
            envelope = wrapper.get('envelope') if isinstance(wrapper, dict) else None
            if reg is None:
                self._opened[nid] = (None, ['no externally controlled role registry: ' + '; '.join(problems)],
                                     envelope)
            else:
                payload, why = R.open_signed(wrapper, kind, reg['pins'], revoked_keys=self.k.revoked_keys())
                self._opened[nid] = (payload, why, envelope)
        return self._opened[nid]


class EvidenceKernel:
    """Single-writer evidence ledger on top of a genesis Store.

    Production construction reads role pins only from an externally controlled
    trust root (`kernel.roles`). `with_fixture_registry` is a test seam: its
    decisions are stamped `registry: FIXTURE`, and release export, preflight
    and bundle verification build their own trust-root kernel, so fixture
    grants never survive into an accepted path.
    """

    def __init__(self, store, *, anchors=None, trust_root=None):
        self.s = store
        # identity -> description of externally anchored verifiers (pinned binaries, signed roles).
        self.anchors = dict(anchors or {})
        self._trust_root = trust_root
        self._fixture = None

    @classmethod
    def with_fixture_registry(cls, store, registry, *, anchors=None):
        k = cls(store, anchors=anchors)
        k._fixture = {'pins': dict(registry['pins'])}
        return k

    def _registry(self):
        if self._fixture is not None:
            return self._fixture, [], 'FIXTURE'
        reg, reasons = load_role_registry(self._trust_root)
        return reg, reasons, (reg['root_key_sha256'] if reg else None)

    # ---------- recording ----------
    def record(self, kind, payload, *, parents=(), effects=(), route, source_hash, verdict=None,
               verifier=None, scope=None):
        """Record an immutable artifact node. Returns its content-derived id."""
        for p in parents:
            if self.s.state(f'evnode:{p}') is None:
                raise ValueError(f'unknown parent artifact {p}')
        node = {'schema': 'genesis-evidence-node-v1', 'kind': kind, 'payload_hash': self.s.put(payload),
                'parents': sorted(set(parents)), 'effects': sorted(e.value for e in _norm_effects(effects)),
                'route': route, 'source_hash': source_hash, 'verdict': verdict, 'verifier': verifier,
                'scope': scope}
        nid = digest(node)
        self.s.save('evidence_node', nid, node)
        if self.s.state(f'evnode:{nid}') is None:
            self.s.set_state(f'evnode:{nid}', node)
        return nid

    def record_signed(self, kind, envelope, *, parents=(), route, source_hash, effects=()):
        """Record a signed envelope as a bare wrapper node (no unsigned verdict or role)."""
        if kind not in SIGNED_KINDS:
            raise ValueError(f'{kind} is not a signed evidence kind')
        return self.record(kind, R.wrap(envelope), parents=parents, route=route, source_hash=source_hash,
                           effects=effects)

    def node(self, nid):
        node = self.s.state(f'evnode:{nid}')
        if node is None:
            raise KeyError(nid)
        return node

    def payload(self, nid):
        return self.s.get(self.node(nid)['payload_hash'])

    def register_verifier(self, identity, implementation_hash, *, validated_by=(), generated=False):
        """A verifier is itself an artifact; `validated_by` are receipts from other verifiers."""
        return self.record('verifier', {'identity': identity, 'implementation_hash': implementation_hash,
                                        'generated': generated},
                           parents=validated_by, route='genesis.kernel', source_hash=implementation_hash,
                           verifier=identity)

    # ---------- derived facts ----------
    def closure(self, ids):
        seen, stack = set(), list(ids)
        while stack:
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x)
            stack.extend(self.node(x)['parents'])
        return seen

    def effects(self, nid, _memo=None, *, resolved=frozenset()):
        """Effective effects: own effects plus inherited ones (§4.3).

        A passing local check node resolves speculative taint from what it
        checked. A signed node resolves it only when `resolved` says it was
        verified and supportive for the decision at hand; its unsigned wrapper
        verdict never does. Contamination, approximation and self-judgement
        are never resolved by checking.
        """
        memo = {} if _memo is None else _memo
        if nid in memo:
            return memo[nid]
        node = self.node(nid)
        inherited = set()
        for p in node['parents']:
            inherited |= self.effects(p, memo, resolved=resolved)
        if node['kind'] in SIGNED_KINDS:
            if nid in resolved:
                inherited -= SPECULATIVE
        elif node['kind'] in CHECK_KINDS and node['verdict'] in PASSING:
            inherited -= SPECULATIVE
        memo[nid] = inherited | _norm_effects(node['effects'])
        return memo[nid]

    # ---------- revocation ----------
    def _revocation(self, target_type, target, reason, actor):
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError('revocation needs a reason')
        record = {'target_type': target_type, 'artifact': target, 'reason': reason, 'actor': actor, 'at': utcnow()}
        self.s.save('evidence_revocation', digest(record), record)
        key = {'node': 'evrevoked', 'key': 'evrevoked_keys', 'evaluation': 'evrevoked_evaluations'}[target_type]
        revoked = set(self.s.state(key, []))
        revoked.add(target)
        self.s.set_state(key, sorted(revoked))
        return record

    def revoke(self, nid, reason, actor):
        """Revoke an artifact node (a dependency, an ancestor, a verifier registration, an imported capability)."""
        self.node(nid)
        return self._revocation('node', nid, reason, actor)

    def revoke_key(self, public_key_b64, reason, actor):
        """Signing-key compromise: receipts that verify only under this key stop counting."""
        return self._revocation('key', public_key_b64, reason, actor)

    def revoke_evaluation(self, identity, reason, actor):
        """Retire one evaluation (panel commitment + raw root) wherever its receipt appears."""
        if not R.hex64(identity):
            raise ValueError('evaluation identity')
        return self._revocation('evaluation', identity, reason, actor)

    def revoked_keys(self):
        return set(self.s.state('evrevoked_keys', []))

    def revocations(self):
        out = []
        for (h,) in self.s.db.execute("SELECT object_hash FROM entities WHERE kind='evidence_revocation' ORDER BY id"):
            out.append(self.s.get(h))
        return sorted(out, key=lambda r: (r['at'], r['artifact']))

    def revocation_head(self):
        return digest({'nodes': self.s.state('evrevoked', []), 'keys': self.s.state('evrevoked_keys', []),
                       'evaluations': self.s.state('evrevoked_evaluations', [])})

    def revoked_ancestors(self, nid):
        revoked = set(self.s.state('evrevoked', []))
        return sorted(self.closure([nid]) & revoked)

    def _registrations(self, identity):
        return [nid for nid in self._all_nodes() if self.node(nid)['kind'] == 'verifier'
                and self.node(nid)['verifier'] == identity]

    def revoked_verifiers(self):
        revoked = set(self.s.state('evrevoked', []))
        by_identity = {}
        for nid in self._all_nodes():
            n = self.node(nid)
            if n['kind'] == 'verifier':
                by_identity.setdefault(n['verifier'], []).append(nid)
        return {i for i, regs in by_identity.items() if regs and all(r in revoked for r in regs)}

    def verifier_trust(self, verifier_identity):
        """ANCHORED, CIRCULAR_JUSTIFICATION, UNANCHORED, REVOKED or UNREGISTERED (§3.2)."""
        revoked = set(self.s.state('evrevoked', []))
        regs = self._registrations(verifier_identity)
        if not regs:
            return 'UNREGISTERED'
        if all(r in revoked for r in regs):
            return 'REVOKED'
        visiting, done = set(), {}

        def walk(identity):
            if identity in done:
                return done[identity]
            if identity in visiting:
                return 'CIRCULAR_JUSTIFICATION'
            visiting.add(identity)
            result = 'UNANCHORED'
            for vn in self._registrations(identity):
                if vn in revoked:
                    continue
                v = self.node(vn)
                if self.s.get(v['payload_hash'])['implementation_hash'] in self.anchors or identity in self.anchors:
                    result = 'ANCHORED'
                    break
                statuses = []
                for receipt in v['parents']:
                    if receipt in revoked:
                        continue
                    checker = self.node(receipt)['verifier']
                    if checker == identity:
                        statuses.append('CIRCULAR_JUSTIFICATION')  # self-validation
                    else:
                        statuses.append(walk(checker))
                if 'ANCHORED' in statuses:
                    result = 'ANCHORED'
                    break
                if 'CIRCULAR_JUSTIFICATION' in statuses:
                    result = 'CIRCULAR_JUSTIFICATION'
            visiting.discard(identity)
            done[identity] = result
            return result

        return walk(verifier_identity)

    def _all_nodes(self):
        return [key for (key,) in self.s.db.execute("SELECT id FROM entities WHERE kind='evidence_node'")]

    # ---------- claims ----------
    def create_claim(self, claim_id, statement, scope, dependencies, *, binding=None):
        """Immutable claim. `binding` (kernel.receipts.CLAIM_BINDING) is required for
        any confirmation-level promotion; build it with receipts.binding_from_requests."""
        for d in dependencies:
            self.node(d)
        claim = {'claim_id': claim_id, 'statement': statement, 'scope': scope, 'dependencies': sorted(dependencies)}
        if binding is not None:
            problems = R.check_binding(binding)
            if problems:
                raise ValueError('claim binding: ' + '; '.join(problems))
            claim['binding'] = binding
        self.s.save('claim', claim_id, claim)  # raises if the identity is reused with other content
        if self.s.state(f'claimlevels:{claim_id}') is None:
            self.s.set_state(f'claimlevels:{claim_id}', dict(FLOOR))
        return claim

    def claim(self, claim_id):
        return self.s.get(self._entity('claim', claim_id))

    def claim_ids(self):
        return [cid for (cid,) in self.s.db.execute("SELECT id FROM entities WHERE kind='claim' ORDER BY id")]

    def _entity(self, kind, key):
        row = self.s.db.execute('SELECT object_hash FROM entities WHERE kind=? AND id=?', (kind, key)).fetchone()
        if row is None:
            raise KeyError(f'{kind}:{key}')
        return row[0]

    def recorded_levels(self, claim_id):
        """Historical: levels as granted, ignoring later revocation or trust changes."""
        levels = self.s.state(f'claimlevels:{claim_id}')
        if levels is None:
            raise KeyError(claim_id)
        return levels

    def promotion_history(self, claim_id):
        hist = self.s.state(f'claimpromotions:{claim_id}')
        if hist is None:  # stores written before B14: fall back to the recorded levels
            rec = self.recorded_levels(claim_id)
            hist = [{'axis': a, 'level': lvl, 'decision': None} for a, lvl in rec.items()
                    if a in AXES and lvl != FLOOR[a]]
        return hist

    def levels(self, claim_id, _ctx=None):
        """Effective levels, re-derived now. Revoked dependencies, revoked verifiers,
        revoked evaluations or keys, and an unavailable trust registry all lower them."""
        self.recorded_levels(claim_id)
        if self.invalidation(claim_id):
            return dict(FLOOR) | {'invalidated': True}
        ctx = _ctx or _Context(self)
        claim = self.claim(claim_id)
        history = self.promotion_history(claim_id)
        out = {}
        for axis in AXES:
            granted = sorted({h['level'] for h in history if h['axis'] == axis}, key=AXES[axis].index, reverse=True)
            out[axis] = next((lvl for lvl in granted if not self._licensing(claim, axis, lvl, ctx)[0]), FLOOR[axis])
        return out

    def invalidation(self, claim_id):
        """Whole-claim invalidations: revoked ancestors, revoked verifiers, revoked evaluations."""
        claim = self.claim(claim_id)
        deps = self.closure(claim['dependencies'])
        revoked = set(self.s.state('evrevoked', []))
        hits = set(deps & revoked)
        dead_verifiers = self.revoked_verifiers()
        dead_evaluations = set(self.s.state('evrevoked_evaluations', []))
        for d in deps:
            n = self.node(d)
            if n['verifier'] in dead_verifiers and n['kind'] != 'verifier':
                hits.add(f'verifier:{n["verifier"]}')
            if n['kind'] in SIGNED_KINDS and dead_evaluations:
                inner = R.unwrap_unverified(self.s.get(n['payload_hash']))
                if inner and inner.get('panel_commitment') is not None and 'raw_evidence_root' in inner:
                    ident = R.evaluation_identity(inner)
                    if ident in dead_evaluations:
                        hits.add(f'evaluation:{ident}')
        return sorted(hits)

    def promote(self, claim_id, axis, level):
        """Grant `level` on `axis` only if the dependency closure licenses it (§26.2).

        Returns the decision record; raises PromotionRejected with every reason.
        """
        if axis not in AXES:
            raise PromotionRejected(['unknown evidence axis'])
        if level not in AXES[axis]:
            raise PromotionRejected([f'{level} is not a promotable {axis} state'])
        claim = self.claim(claim_id)
        ctx = _Context(self)
        current = self.levels(claim_id, ctx)
        reasons = []
        if current.get('invalidated'):
            reasons.append('claim has a revoked dependency: ' + ', '.join(self.invalidation(claim_id)[:3]))
        elif AXES[axis].index(level) <= AXES[axis].index(current[axis]):
            reasons.append(f'{axis} already at {current[axis]}')
        lic, used = self._licensing(claim, axis, level, ctx)
        reasons += lic
        if reasons:
            self.s.event('PROMOTION_REJECTED', {'claim': claim_id, 'axis': axis, 'level': level, 'reasons': reasons})
            raise PromotionRejected(reasons)
        deps = self.closure(claim['dependencies'])
        _, _, registry_source = ctx.registry() if (axis, level) in CONFIRMATION else (None, None, None)
        decision = {'claim': claim_id, 'axis': axis, 'level': level, 'dependencies': sorted(deps),
                    'effects': sorted(e.value for e in used['effects']), 'evidence_used': sorted(used['nodes']),
                    'evaluations': sorted(used['evaluations']), 'registry': registry_source,
                    'revocation_context': self.revocation_head(), 'at': utcnow()}
        did = digest(decision)
        self.s.save('promotion', did, decision)
        history = list(self.s.state(f'claimpromotions:{claim_id}') or [])
        history.append({'axis': axis, 'level': level, 'decision': did})
        self.s.set_state(f'claimpromotions:{claim_id}', history)
        recorded = dict(self.recorded_levels(claim_id))
        recorded[axis] = level
        self.s.set_state(f'claimlevels:{claim_id}', recorded)
        return decision

    # ---------- licensing (pure: no writes) ----------
    def _licensing(self, claim, axis, level, ctx):
        """Reasons why the evidence closure does NOT license (axis, level) now; [] means licensed."""
        claim_id = claim['claim_id']
        deps = self.closure(claim['dependencies'])
        is_confirmation = (axis, level) in CONFIRMATION
        reasons, used_nodes, evaluations, resolved = [], set(), set(), set()
        for kind, count in REQUIRED_EVIDENCE.get((axis, level), []):
            candidates = sorted(d for d in deps if self.node(d)['kind'] == kind)
            if kind in EXTERNALLY_SIGNED:
                r, nodes, idents = self._signed_support(claim, kind, count, level, candidates, deps, ctx)
                reasons += r
                used_nodes |= nodes; evaluations |= idents; resolved |= nodes
                continue
            usable = []
            for d in candidates:
                n = self.node(d)
                if n['verdict'] not in PASSING:
                    continue
                if is_confirmation or axis == 'math' and level != 'EXECUTABLE':
                    ok, why = eligibility.eligible_for_confirmation(n['route'], n['source_hash']) \
                        if is_confirmation else eligibility.source_status(n['source_hash'])
                    if not ok:
                        reasons.append(f'{kind} {d[:12]} ineligible: {why}')
                        continue
                if n['verifier'] is not None:
                    trust = self.verifier_trust(n['verifier'])
                    if trust == 'CIRCULAR_JUSTIFICATION':
                        reasons.append(f'{kind} {d[:12]} checked by circularly justified verifier {n["verifier"]}')
                        continue
                    if trust == 'REVOKED':
                        reasons.append(f'{kind} {d[:12]} checked by revoked verifier {n["verifier"]}')
                        continue
                    if is_confirmation and trust != 'ANCHORED':
                        reasons.append(f'{kind} {d[:12]} checker {n["verifier"]} is {trust}')
                        continue
                if kind == 'bound_state':
                    why = self._bound_state_problems(d)
                    if why:
                        reasons.append(f'bound_state {d[:12]}: {why}')
                        continue
                usable.append((d, n))
            if kind == 'exact_check':
                distinct = {n['verifier'] for _, n in usable}
                if len(distinct) < count:
                    reasons.append(f'needs {count} independent exact checkers, found {len(distinct)}')
            elif kind == 'bound_state':
                if not usable:
                    reasons.append('optimality needs a checked BoundState with gap 0 and custody of its certificate')
            elif len(usable) < count:
                reasons.append(f'needs {count} valid {kind} artifact(s), found {len(usable)}')
            used_nodes |= {d for d, _ in usable}
        memo = {}
        effects = set()
        for d in claim['dependencies']:
            effects |= self.effects(d, memo, resolved=frozenset(resolved))
        if effects & CONTAMINATING and (is_confirmation or axis == 'novelty'):
            reasons.append('contaminated dependency (' + ', '.join(sorted(e.value for e in effects & CONTAMINATING)) + ')')
        if effects & SPECULATIVE and AXES[axis].index(level) >= 2:
            reasons.append('unresolved speculative dependency (' +
                           ', '.join(sorted(e.value for e in effects & SPECULATIVE)) + ')')
        if Effect.SELF_JUDGED in effects and AXES[axis].index(level) >= 1 and axis != 'novelty':
            reasons.append('self-judged evidence cannot support a checked or confirmed status')
        if Effect.APPROXIMATE in effects and axis == 'math' and level in ('FINITE_CERTIFIED', 'THEOREM_CHECKED',
                                                                          'OPTIMALITY_CHECKED'):
            reasons.append('approximate dependency cannot support an exact mathematical status')
        if Effect.MANUAL_INTERVENTION in effects and axis in ('improver',):
            reasons.append('manual intervention invalidates an autonomy/improver claim')
        return reasons, {'nodes': used_nodes, 'evaluations': evaluations, 'effects': effects}

    def _bound_state_problems(self, nid):
        """Hook for certificate custody (R-03); returns a reason string or None."""
        payload = self.payload(nid)
        if not isinstance(payload, dict) or payload.get('gap') != 0:
            return 'gap is not 0'
        return None

    def _signed_support(self, claim, kind, count, level, candidates, deps, ctx):
        """Distinct supporting evaluations of `kind` for this exact claim."""
        claim_id = claim['claim_id']
        reasons, nodes = [], set()
        reg, problems, _ = ctx.registry()
        if reg is None:
            return ['no externally controlled role registry: ' + '; '.join(problems)], set(), set()
        if not candidates:
            return [f'needs {count} signed {kind} receipt(s), found 0'], set(), set()
        if kind == 'external_priority_adjudication':
            good = {}
            for d in candidates:
                p, why, _ = ctx.opened(d, kind)
                if why:
                    reasons.append(f'{kind} {d[:12]} rejected: {why[0]}')
                    continue
                if p['claim_id'] != claim_id or p['statement_hash'] != digest(claim['statement']) \
                        or p['scope'] != claim['scope']:
                    reasons.append(f'{kind} {d[:12]} adjudicates a different claim, statement or scope')
                    continue
                if p['outcome'] != 'NOVEL_IN_SCOPE':
                    reasons.append(f'{kind} {d[:12]} outcome {p["outcome"]} is not support for novelty')
                    continue
                good[R.evaluation_identity(p)] = p; nodes.add(d)
            if len(good) < count:
                reasons.append(f'needs {count} supporting {kind}, found {len(good)}')
            return reasons, nodes, set(good)
        binding = claim.get('binding')
        if binding is None:
            return ['confirmation needs a claim bound to its preregistered evaluations '
                    '(create_claim(..., binding=receipts.binding_from_requests(...)))'], set(), set()
        anchors = {}
        for d in deps:
            if self.node(d)['kind'] == 'preregistration_anchor':
                p, why, env = ctx.opened(d, 'preregistration_anchor')
                if p is not None:
                    anchors[digest(env)] = (p, env)
        dead = set(self.s.state('evrevoked_evaluations', []))
        good = {}
        for d in candidates:
            n = self.node(d)
            p, why, env = ctx.opened(d, kind)
            if why:
                reasons.append(f'{kind} {d[:12]} rejected: {why[0]}')
                continue
            bad = []
            ok, w = eligibility.eligible_for_confirmation(n['route'], n['source_hash'])
            if not ok:
                bad.append(f'ineligible route/source: {w}')
            ok, w = eligibility.source_status(p['source_hash'])
            if not ok:
                bad.append(w)
            if n['verifier'] is not None and self.verifier_trust(n['verifier']) in ('CIRCULAR_JUSTIFICATION', 'REVOKED'):
                bad.append(f'wrapper names an untrusted verifier {n["verifier"]}')
            bad += R.binding_mismatches(p, claim_id, binding, kind)
            anchor = anchors.get(p['anchor_hash'])
            if anchor is None:
                bad.append('no verified preregistration anchor for this receipt in the evidence closure')
            else:
                bad += R.anchor_mismatches(p, *anchor)
            ident = R.evaluation_identity(p)
            if ident in dead:
                bad.append('evaluation revoked')
            if bad:
                reasons.append(f'{kind} {d[:12]} does not support claim {claim_id}: ' + '; '.join(bad[:3]))
                continue
            if p['outcome'] != 'SUPPORTED':
                reasons.append(f'{kind} {d[:12]} reports {p["outcome"]}: a negative or inconclusive evaluation '
                               'is not support')
                continue
            if ident in good and good[ident] != p:
                reasons.append(f'evaluation {ident[:12]} carries conflicting signed receipts')
                continue
            good[ident] = p; nodes.add(d)
        panels = Counter(p['panel_commitment'] for p in good.values())
        if any(c > 1 for c in panels.values()):
            reasons.append('one panel commitment supports more than one evaluation (exposed panels are retired)')
        if kind == 'sealed_generation_evaluation':
            chain = R.generation_chain(list(good.values()), binding['candidate_version'])
            if len(chain) < count:
                reasons.append(f'needs {count} consecutive confirmed generation transitions ending at the bound '
                               f'candidate, found {len(chain)}')
        elif kind == 'sealed_improver_evaluation' and level == 'CROSS_DOMAIN_CONFIRMED':
            if len(good) < count or len({p['domain'] for p in good.values()}) < 2:
                reasons.append('cross-domain confirmation needs supporting evaluations in at least two domains')
        elif len(good) < count:
            reasons.append(f'needs {count} distinct supporting {kind} evaluation(s), found {len(good)}')
        return reasons, nodes, set(good)

    def invalidated_claims(self):
        out = []
        for cid in self.claim_ids():
            hits = self.invalidation(cid)
            if hits:
                out.append({'claim': cid, 'revoked_dependencies': hits})
        return out

    def effective_report(self, claim_id):
        """Historical and current status of one claim, clearly separated (R-02)."""
        claim = self.claim(claim_id)
        hits = self.invalidation(claim_id)
        revoked = {r['artifact']: r for r in self.revocations()}
        return {'claim_id': claim_id, 'statement': claim['statement'], 'scope': claim['scope'],
                'dependencies': claim['dependencies'], 'binding': claim.get('binding'),
                'historical': {'recorded_levels': self.recorded_levels(claim_id),
                               'promotions': self.promotion_history(claim_id)},
                'effective_levels': self.levels(claim_id),
                'invalidated_by': [{'target': h, **({k: revoked[h][k] for k in ('reason', 'actor', 'at')}
                                                    if h in revoked else {})} for h in hits]}
