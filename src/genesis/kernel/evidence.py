"""Evidence DAG, epistemic effects, trust graph, claim promotion and revocation.

Spec anchors: §3.1-3.2 (release gate, trust root, CIRCULAR_JUSTIFICATION),
§4.3 (epistemic type and effect system), §7 (orthogonal evidence axes),
§15.1 (trust tower), §26.2 (evidence promotion), §37.3 (transitive invalidation).

Everything is stored as immutable Store entities; revocations and promotion
decisions are appended, never edited. Derived facts (effective effects,
revocation status, trust status) are recomputed from the immutable records.
"""
from enum import Enum
from .. import eligibility
from ..common import digest, utcnow


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

AXES = {
    'math': ['UNCHECKED', 'EXECUTABLE', 'WITNESS_VALID', 'FINITE_CERTIFIED', 'THEOREM_CHECKED', 'OPTIMALITY_CHECKED'],
    'utility': ['NOT_TESTED', 'DEV_ONLY', 'CONFIRMED_SAME_DOMAIN', 'CONFIRMED_TRANSFER'],
    'causality': ['NOT_TESTED', 'CORRELATED', 'ABLATION_SUPPORTED', 'PLACEBO_CONTROLLED'],
    'improver': ['NOT_TESTED', 'SAME_DOMAIN_CONFIRMED', 'CROSS_DOMAIN_CONFIRMED', 'MULTIGEN_CONFIRMED'],
    'novelty': ['UNKNOWN', 'REDISCOVERY', 'VARIANT', 'CANDIDATE_NOVEL', 'EXTERNALLY_CHECKED_NOVEL'],
    'replication': ['NONE', 'INTERNAL_INDEPENDENT', 'EXTERNAL_REPRODUCTION'],
}
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
# Kinds that must arrive signed by an externally pinned role (batch 2 registry).
EXTERNALLY_SIGNED = {'sealed_evaluation', 'sealed_transfer_evaluation', 'sealed_improver_evaluation',
                     'sealed_generation_evaluation', 'external_priority_adjudication', 'external_reproduction'}


class PromotionRejected(Exception):
    pass


def _norm_effects(effects):
    out = set()
    for e in effects:
        out.add(Effect(e))  # raises ValueError on unknown effect names: no typo can bypass the gate
    return out


class EvidenceKernel:
    """Single-writer evidence ledger on top of a genesis Store."""

    def __init__(self, store, *, anchors=None, role_registry_loader=None):
        self.s = store
        # identity -> description of externally anchored verifiers (pinned binaries, signed roles).
        self.anchors = dict(anchors or {})
        self._load_roles = role_registry_loader

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

    def node(self, nid):
        node = self.s.state(f'evnode:{nid}')
        if node is None:
            raise KeyError(nid)
        return node

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

    def effects(self, nid, _memo=None):
        """Effective effects: own effects plus inherited ones (§4.3).

        A passing check node resolves speculative taint from what it checked
        (a verified witness is no longer just a proposal); contamination,
        approximation and self-judgement are never resolved by checking.
        """
        memo = {} if _memo is None else _memo
        if nid in memo:
            return memo[nid]
        node = self.node(nid)
        inherited = set()
        for p in node['parents']:
            inherited |= self.effects(p, memo)
        if node['kind'] in CHECK_KINDS and node['verdict'] in ('VALID', 'SUPPORTED', 'PASS'):
            inherited -= SPECULATIVE
        memo[nid] = inherited | _norm_effects(node['effects'])
        return memo[nid]

    def revoke(self, nid, reason, actor):
        self.node(nid)
        record = {'artifact': nid, 'reason': reason, 'actor': actor, 'at': utcnow()}
        self.s.save('evidence_revocation', digest(record), record)
        revoked = set(self.s.state('evrevoked', []))
        revoked.add(nid)
        self.s.set_state('evrevoked', sorted(revoked))
        return record

    def revoked_ancestors(self, nid):
        revoked = set(self.s.state('evrevoked', []))
        return sorted(self.closure([nid]) & revoked)

    def verifier_trust(self, verifier_identity):
        """ANCHORED, CIRCULAR_JUSTIFICATION or UNANCHORED for one verifier identity (§3.2)."""
        nodes = [nid for nid in self._all_nodes() if self.node(nid)['kind'] == 'verifier'
                 and self.node(nid)['verifier'] == verifier_identity]
        if not nodes:
            return 'UNREGISTERED'
        node = self.node(nodes[0])
        impl = self.s.get(node['payload_hash'])['implementation_hash']
        if impl in self.anchors or verifier_identity in self.anchors:
            return 'ANCHORED'
        # Walk "validated by" receipts back to their verifiers.
        visiting, done = set(), {}

        def walk(identity):
            if identity in done:
                return done[identity]
            if identity in visiting:
                return 'CIRCULAR_JUSTIFICATION'
            visiting.add(identity)
            vnodes = [n for n in self._all_nodes() if self.node(n)['kind'] == 'verifier'
                      and self.node(n)['verifier'] == identity]
            result = 'UNANCHORED'
            for vn in vnodes:
                v = self.node(vn)
                if self.s.get(v['payload_hash'])['implementation_hash'] in self.anchors or identity in self.anchors:
                    result = 'ANCHORED'
                    break
                statuses = []
                for receipt in v['parents']:
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
    def create_claim(self, claim_id, statement, scope, dependencies):
        for d in dependencies:
            self.node(d)
        claim = {'claim_id': claim_id, 'statement': statement, 'scope': scope, 'dependencies': sorted(dependencies)}
        self.s.save('claim', claim_id, claim)
        self.s.set_state(f'claimlevels:{claim_id}', {axis: levels[0] for axis, levels in AXES.items()})
        return claim

    def claim(self, claim_id):
        return self.s.get(self._entity('claim', claim_id))

    def _entity(self, kind, key):
        row = self.s.db.execute('SELECT object_hash FROM entities WHERE kind=? AND id=?', (kind, key)).fetchone()
        if row is None:
            raise KeyError(f'{kind}:{key}')
        return row[0]

    def levels(self, claim_id):
        levels = self.s.state(f'claimlevels:{claim_id}')
        if levels is None:
            raise KeyError(claim_id)
        # A revoked dependency invalidates every granted level above the floor.
        if self.invalidation(claim_id):
            return {axis: AXES[axis][0] for axis in AXES} | {'invalidated': True}
        return levels

    def invalidation(self, claim_id):
        claim = self.claim(claim_id)
        hits = set()
        for d in claim['dependencies']:
            hits.update(self.revoked_ancestors(d))
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
        deps = self.closure(claim['dependencies'])
        memo = {}
        effects = set()
        for d in claim['dependencies']:
            effects |= self.effects(d, memo)
        reasons = []
        current = self.levels(claim_id)
        if current.get('invalidated'):
            reasons.append('claim has a revoked dependency: ' + ', '.join(self.invalidation(claim_id)[:3]))
        if AXES[axis].index(level) <= AXES[axis].index(current[axis]) and not current.get('invalidated'):
            reasons.append(f'{axis} already at {current[axis]}')
        is_confirmation = (axis, level) in CONFIRMATION
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
        # Required, validly checked evidence of the right kinds, from eligible routes.
        for kind, count in REQUIRED_EVIDENCE.get((axis, level), []):
            usable = []
            for d in deps:
                n = self.node(d)
                if n['kind'] != kind or n['verdict'] not in ('VALID', 'SUPPORTED', 'PASS'):
                    continue
                if is_confirmation or axis == 'math' and level != 'EXECUTABLE':
                    ok, why = eligibility.eligible_for_confirmation(n['route'], n['source_hash']) \
                        if is_confirmation else eligibility.source_status(n['source_hash'])
                    if not ok:
                        reasons.append(f'{kind} {d[:12]} ineligible: {why}')
                        continue
                if n['verifier'] is not None and kind not in ('verifier',):
                    trust = self.verifier_trust(n['verifier'])
                    if trust == 'CIRCULAR_JUSTIFICATION':
                        reasons.append(f'{kind} {d[:12]} checked by circularly justified verifier {n["verifier"]}')
                        continue
                    if is_confirmation and trust != 'ANCHORED':
                        reasons.append(f'{kind} {d[:12]} checker {n["verifier"]} is {trust}')
                        continue
                if kind in EXTERNALLY_SIGNED and not self._externally_signed(n):
                    reasons.append(f'{kind} {d[:12]} lacks a signature from an externally pinned role')
                    continue
                usable.append(n)
            if kind == 'exact_check':
                distinct = {u['verifier'] for u in usable}
                if len(distinct) < count:
                    reasons.append(f'needs {count} independent exact checkers, found {len(distinct)}')
            elif kind == 'bound_state':
                if not any(self.s.get(u['payload_hash']).get('gap') == 0 for u in usable):
                    reasons.append('optimality needs a checked BoundState with gap 0')
            elif len(usable) < count:
                reasons.append(f'needs {count} valid {kind} artifact(s), found {len(usable)}')
        if reasons:
            self.s.event('PROMOTION_REJECTED', {'claim': claim_id, 'axis': axis, 'level': level, 'reasons': reasons})
            raise PromotionRejected(reasons)
        new = dict(current)
        new.pop('invalidated', None)
        new[axis] = level
        decision = {'claim': claim_id, 'axis': axis, 'level': level, 'dependencies': sorted(deps),
                    'effects': sorted(e.value for e in effects), 'at': utcnow()}
        self.s.save('promotion', digest(decision), decision)
        self.s.set_state(f'claimlevels:{claim_id}', new)
        return decision

    def _externally_signed(self, node):
        if self._load_roles is None:
            return False
        registry, reasons = self._load_roles()
        if registry is None:
            return False
        from .signing import verify
        payload = self.s.get(node['payload_hash'])
        envelope = payload.get('signed_envelope') if isinstance(payload, dict) else None
        role = payload.get('signing_role') if isinstance(payload, dict) else None
        key = registry['pins'].get(role) if role else None
        if not envelope or not key:
            return False
        try:
            verify(envelope, key)
            return True
        except Exception:
            return False

    def invalidated_claims(self):
        out = []
        for (cid,) in self.s.db.execute("SELECT id FROM entities WHERE kind='claim'"):
            hits = self.invalidation(cid)
            if hits:
                out.append({'claim': cid, 'revoked_dependencies': hits})
        return out
