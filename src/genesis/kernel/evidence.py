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
import json

from .. import eligibility
from ..common import digest, utcnow
from . import receipts as R
from . import replay_contracts as RC
from .roles import load_role_registry

MATH_SCOPE = 'this finite host only'
THEOREM_SCOPE = 'this equation under these axioms only'


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
# Kinds the kernel can re-check itself; any other unsigned kind cannot license a level.
REPLAYABLE = {'witness_check', 'bound_state', 'execution_receipt'} | set(RC.CONTRACTED)   # RC: B20_R8 contracts
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
        self._nodes = {}  # immutable entity cache

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
            if not self._has_node(p):
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
        """Read from the immutable entity record, never from mutable state (a forged
        STATE_UPDATED event cannot change what a node says)."""
        node = self._nodes.get(nid)
        if node is None:
            row = self.s.db.execute("SELECT object_hash FROM entities WHERE kind='evidence_node' AND id=?",
                                    (nid,)).fetchone()
            if row is None:
                raise KeyError(nid)
            node = self.s.get(row[0])
            if digest(node) != nid:
                raise RuntimeError(f'evidence node {nid[:12]} does not hash to its identity')
            self._nodes[nid] = node
        return node

    def _has_node(self, nid):
        try:
            self.node(nid)
            return True
        except KeyError:
            return False

    def payload(self, nid):
        return self.s.get(self.node(nid)['payload_hash'])

    def register_verifier(self, identity, implementation_hash, *, validated_by=(), generated=False):
        """A verifier is itself an artifact; `validated_by` are receipts from other verifiers.

        A revoked identity stays revoked: checks name verifiers by identity, so
        re-registering the name would silently restore every check it made.
        """
        if identity in self.revoked_verifiers():
            raise PermissionError(f'verifier identity {identity!r} is revoked and cannot be registered again')
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
        # Convenience mirror only; the immutable revocation entities are authoritative.
        key = {'node': 'evrevoked', 'key': 'evrevoked_keys', 'evaluation': 'evrevoked_evaluations'}[target_type]
        self.s.set_state(key, sorted(self._revoked(target_type)))
        return record

    def _revoked(self, target_type):
        return {r['artifact'] for r in self.revocations() if r.get('target_type', 'node') == target_type}

    def apply_revocations(self, records):
        """Apply revocation records from a later feed (REVOCATIONS.json). Unknown nodes are skipped."""
        applied, skipped = [], []
        have = {(r.get('target_type', 'node'), r['artifact']) for r in self.revocations()}
        for r in records:
            target_type = r.get('target_type', 'node')
            if (target_type, r['artifact']) in have:
                continue
            if target_type == 'node' and not self._has_node(r['artifact']):
                skipped.append(r); continue
            self._revocation(target_type, r['artifact'], f"later feed: {r['reason']}", r.get('actor', 'unknown'))
            applied.append(r)
        return {'applied': applied, 'skipped_unknown': skipped}

    def revoke(self, nid, reason, actor):
        """Revoke an artifact node (a dependency, an ancestor, a verifier registration, an imported capability).

        Revoking a signed receipt also retires the evaluation it carries, so the same
        envelope cannot come back in another wrapper node or store."""
        node = self.node(nid)
        record = self._revocation('node', nid, reason, actor)
        if node['kind'] in SIGNED_KINDS:
            ident = R.evaluation_identity(R.unwrap_unverified(self.s.get(node['payload_hash'])))
            if ident is not None:
                self._revocation('evaluation', ident, f'receipt node {nid[:12]} revoked: {reason}', actor)
        return record

    def revoke_key(self, public_key_b64, reason, actor):
        """Signing-key compromise: receipts that verify only under this key stop counting."""
        key = R.normalize_key(public_key_b64)
        if key is None:
            raise ValueError('not a base64 Ed25519 public key')
        return self._revocation('key', key, reason, actor)

    def revoke_evaluation(self, identity, reason, actor):
        """Retire one evaluation (panel commitment + raw root) wherever its receipt appears."""
        if not R.hex64(identity):
            raise ValueError('evaluation identity')
        return self._revocation('evaluation', identity, reason, actor)

    def revoked_keys(self):
        return self._revoked('key')

    def _entities_of(self, kind):
        """All (id, object) of an immutable entity kind, cached until the count changes."""
        n = self.s.db.execute('SELECT count(*) FROM entities WHERE kind=?', (kind,)).fetchone()[0]
        cache = getattr(self, '_kind_cache', None)
        if cache is None:
            cache = self._kind_cache = {}
        if kind not in cache or cache[kind][0] != n:
            rows = self.s.db.execute('SELECT id, object_hash FROM entities WHERE kind=? ORDER BY id', (kind,)).fetchall()
            cache[kind] = (n, [(i, self.s.get(h)) for i, h in rows])
        return cache[kind][1]

    def revocations(self):
        out = [r for _, r in self._entities_of('evidence_revocation')
               if isinstance(r, dict) and isinstance(r.get('artifact'), str)]
        return sorted(out, key=lambda r: (str(r.get('at', '')), r['artifact']))

    def revocation_head(self):
        return digest({'nodes': sorted(self._revoked('node')), 'keys': sorted(self._revoked('key')),
                       'evaluations': sorted(self._revoked('evaluation'))})

    def revoked_ancestors(self, nid):
        return sorted(self.closure([nid]) & self._revoked('node'))

    def _registrations(self, identity):
        return [nid for nid in self._all_nodes() if self.node(nid)['kind'] == 'verifier'
                and self.node(nid)['verifier'] == identity]

    def revoked_verifiers(self):
        """Identities with ANY revoked registration: revoking one registration retires the name."""
        revoked = self._revoked('node')
        return {self.node(nid)['verifier'] for nid in revoked
                if self._has_node(nid) and self.node(nid)['kind'] == 'verifier'}

    def verifier_trust(self, verifier_identity):
        """ANCHORED, CIRCULAR_JUSTIFICATION, UNANCHORED, REVOKED or UNREGISTERED (§3.2)."""
        revoked = self._revoked('node')
        regs = self._registrations(verifier_identity)
        if not regs:
            return 'UNREGISTERED'
        if any(r in revoked for r in regs):
            return 'REVOKED'
        visiting, done = set(), {}
        dead = self.revoked_verifiers()

        def walk(identity):
            if identity in done:
                return done[identity]
            if identity in dead:
                done[identity] = 'REVOKED'
                return 'REVOKED'
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
    def create_claim(self, claim_id, statement, scope, dependencies, *, binding=None, problem=None):
        """Immutable claim.

        `binding` (kernel.receipts.CLAIM_BINDING) is required for any confirmation-level
        promotion; build it with receipts.binding_from_requests. The statement and scope
        must be the ones committed in the preregistered request.
        `problem` = {'task_sha256', 'value'} names the exact finite problem a mathematical
        claim is about; OPTIMALITY_CHECKED requires it.
        """
        if not R.claim_id_ok(claim_id):
            raise ValueError('claim identifier must be one printable line (no newline or control characters, '
                             'at most 200 characters)')
        for name, text in (('statement', statement), ('scope', scope)):
            if not isinstance(text, str) or not text or not text.isprintable() or len(text) > 2000:
                raise ValueError(f'claim {name} must be one printable line')
        for d in dependencies:
            self.node(d)
        claim = {'claim_id': claim_id, 'statement': statement, 'scope': scope, 'dependencies': sorted(dependencies)}
        if binding is not None:
            problems = R.check_binding(binding)
            if problems:
                raise ValueError('claim binding: ' + '; '.join(problems))
            if digest(statement) != binding['statement_hash'] or scope != binding['scope']:
                raise ValueError('claim statement/scope differ from the ones committed before evaluation')
            claim['binding'] = binding
        if problem is not None:
            theorem = isinstance(problem, dict) and problem.get('claim') == 'theorem'
            if theorem:
                # B20_R8: a theorem claim names a stored equation under its system's exact axioms.
                if set(problem) != {'theorem_sha256', 'claim'} or not R.hex64(problem['theorem_sha256']):
                    raise ValueError("a theorem problem is {theorem_sha256, claim: 'theorem'}")
                why = RC.theorem_problems(self.s.get(problem['theorem_sha256']))
                if why:
                    raise ValueError('theorem problem: ' + '; '.join(why))
            elif not isinstance(problem, dict) or set(problem) != {'task_sha256', 'value', 'claim'} \
                    or not R.hex64(problem['task_sha256']) or type(problem['value']) is not int \
                    or problem['claim'] not in ('lower_bound', 'optimum'):
                raise ValueError("problem must be {task_sha256, value, claim: 'lower_bound' | 'optimum'}")
            if statement != self.math_statement(problem):
                raise ValueError('a mathematical claim states exactly its problem: use EvidenceKernel.math_statement')
            want = THEOREM_SCOPE if theorem else MATH_SCOPE
            if scope != want:
                raise ValueError(f'a mathematical claim is confined to its checked problem: scope must be {want!r}')
            claim['problem'] = problem
        self.s.save('claim', claim_id, claim)  # raises if the identity is reused with other content
        if self.s.state(f'claimlevels:{claim_id}') is None:
            self.s.set_state(f'claimlevels:{claim_id}', dict(FLOOR))
        return claim

    def _problem_name(self, problem):
        if problem.get('claim') == 'theorem':
            t = self.s.get(problem['theorem_sha256'])
            if t.get('schema') == RC.LEAN_THEOREM_SCHEMA:
                return (f"the definitions of Lean theory package {t['package_sha256'][:16]} (statement "
                        f"{t['statement_id']}) [{problem['theorem_sha256'][:16]}]")
            return f"the {t['system']} axioms [{problem['theorem_sha256'][:16]}]"
        task = self.s.get(problem['task_sha256'])  # the problem must be in the store
        domain, task_id = task.get('domain'), task.get('task_id')
        if not all(isinstance(x, str) and x and x.isprintable() and len(x) <= 128 for x in (domain, task_id)):
            raise ValueError('stored task domain/task_id must be printable single-line labels')
        return f"{domain} host {task_id} [{problem['task_sha256'][:16]}]"

    def math_statement(self, problem):
        """The REQUESTED proposition of a mathematical claim, generated from the stored problem so
        the text cannot name a different host, domain or value. Generating it does not establish
        it: what may be asserted now is `current_wording` (external B14 review, F-01)."""
        name = self._problem_name(problem)
        if problem['claim'] == 'theorem':
            return f"under {name}, {self.s.get(problem['theorem_sha256'])['statement']} holds"
        if problem['claim'] == 'optimum':
            return f"the optimum for {name} is {problem['value']} edges"
        return f"{name} has a valid subgraph with {problem['value']} edges"

    def current_wording(self, claim_id, levels=None):
        """What this claim may assert NOW, derived from its own effective levels and kept apart
        from what was requested. Anything requested but not established is exported only as a
        marked conjecture. Contracts:
          GENERATED_FROM_PROBLEM       math claims: lower-bound text at WITNESS_VALID, optimum text
                                       only at OPTIMALITY_CHECKED (matching checked bounds)
          COMMITTED_BEFORE_EVALUATION  bound claims: the committed statement only while a
                                       confirmation level is effective
          FREE_TEXT_NOT_ASSERTED       anything else: never asserted (a keyword lint is not a
                                       semantic contract); levels exported, text only as a request"""
        claim = self.claim(claim_id)
        levels = levels or self.levels(claim_id)
        requested = claim['statement']
        problem = claim.get('problem')
        if problem is not None:
            contract, math = 'GENERATED_FROM_PROBLEM', levels['math']
            name = self._problem_name(problem)
            if problem['claim'] == 'theorem':
                current = self.math_statement(problem) if math == 'THEOREM_CHECKED' else None
            elif math == 'OPTIMALITY_CHECKED' and problem['claim'] == 'optimum':
                current = f"the optimum for {name} is {problem['value']} edges"
            elif math == 'FINITE_CERTIFIED' and problem['claim'] == 'optimum':
                current = f"the optimum for {name} is {problem['value']} edges (two exhaustive computations)"
            elif AXES['math'].index(math) >= AXES['math'].index('WITNESS_VALID'):
                current = f"{name} has a valid subgraph with {problem['value']} edges"
            else:
                current = None
        elif claim.get('binding') is not None:
            contract = 'COMMITTED_BEFORE_EVALUATION'
            established = any((a, v) in CONFIRMATION for a, v in levels.items() if a in AXES)
            current = requested if established else None
        else:
            # Free text has no semantic contract (a keyword lint is not one), so it is never asserted:
            # its levels are exported, its words only as an unproved request.
            contract = 'FREE_TEXT_NOT_ASSERTED'
            current = None
        conjecture = None if current == requested else f'NOT ESTABLISHED (requested, unproved): {requested}'
        return {'contract': contract, 'current_statement': current, 'conjecture': conjecture}

    def claim(self, claim_id):
        return self.s.get(self._entity('claim', claim_id))

    def claim_ids(self):
        return [cid for (cid,) in self.s.db.execute("SELECT id FROM entities WHERE kind='claim' ORDER BY id")]

    def _entity(self, kind, key):
        row = self.s.db.execute('SELECT object_hash FROM entities WHERE kind=? AND id=?', (kind, key)).fetchone()
        if row is None:
            raise KeyError(f'{kind}:{key}')
        return row[0]

    def promotion_history(self, claim_id):
        """Granted promotions for one claim, from the immutable decision records."""
        self._entity('claim', claim_id)
        out = []
        for did, d in self._entities_of('promotion'):
            if did != digest(d):
                continue  # not a content-addressed decision record
            if d.get('claim') == claim_id and d.get('axis') in AXES and d.get('level') in AXES[d['axis']]:
                out.append({'axis': d['axis'], 'level': d['level'], 'decision': did, 'at': d.get('at'),
                            'registry': d.get('registry')})
        return sorted(out, key=lambda x: (x['at'] or '', x['decision']))

    def recorded_levels(self, claim_id):
        """Historical: the highest level ever granted per axis, ignoring later revocation or trust changes."""
        out = dict(FLOOR)
        for h in self.promotion_history(claim_id):
            if AXES[h['axis']].index(h['level']) > AXES[h['axis']].index(out[h['axis']]):
                out[h['axis']] = h['level']
        return out

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
        hits = set(deps & self._revoked('node'))
        dead_verifiers = self.revoked_verifiers()
        dead_evaluations = self._revoked('evaluation')
        for d in deps:
            n = self.node(d)
            if n['verifier'] in dead_verifiers and n['kind'] != 'verifier':
                hits.add(f'verifier:{n["verifier"]}')
            if n['kind'] in SIGNED_KINDS and dead_evaluations:
                # Every signed schema (evaluation receipts and priority adjudications alike).
                ident = R.evaluation_identity(R.unwrap_unverified(self.s.get(n['payload_hash'])))
                if ident is not None and ident in dead_evaluations:
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
        # Convenience mirror of granted levels (not authoritative; see recorded_levels / levels).
        self.s.set_state(f'claimlevels:{claim_id}', self.recorded_levels(claim_id))
        return decision

    # ---------- licensing (pure: no writes) ----------
    def _licensing(self, claim, axis, level, ctx):
        """Reasons why the evidence closure does NOT license (axis, level) now; [] means licensed."""
        claim_id = claim['claim_id']
        deps = self.closure(claim['dependencies'])
        is_confirmation = (axis, level) in CONFIRMATION
        reasons, used_nodes, evaluations, resolved = [], set(), set(), set()
        if axis == 'math' and AXES['math'].index(level) >= AXES['math'].index('WITNESS_VALID'):
            problem = claim.get('problem')
            if problem is None:
                reasons.append('a mathematical claim must name its exact problem (create_claim(..., problem=...))')
            elif (problem['claim'] == 'theorem') != (level == 'THEOREM_CHECKED'):
                reasons.append('THEOREM_CHECKED is the math level of a theorem claim, and a theorem claim has no '
                               'finite-problem levels')
            elif level == 'OPTIMALITY_CHECKED' and problem['claim'] != 'optimum':
                reasons.append('OPTIMALITY_CHECKED needs a claim of the optimum, not of a lower bound')
        for kind, count in REQUIRED_EVIDENCE.get((axis, level), []):
            candidates = sorted(d for d in deps if self.node(d)['kind'] == kind)
            if kind in EXTERNALLY_SIGNED:
                r, nodes, idents = self._signed_support(claim, kind, count, level, candidates, deps, ctx)
                reasons += r
                used_nodes |= nodes; evaluations |= idents; resolved |= nodes
                continue
            usable = []
            if kind not in REPLAYABLE:
                # A producer-written verdict is a claim, not evidence (B14 red team C2).
                reasons.append(f'no replay contract for {kind}: producer-declared verdicts cannot license '
                               f'{axis} {level} (roadmap W03/W05 will add contracts)')
                continue
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
                    why = self._bound_state_problems(d, claim.get('problem'))
                    if why:
                        reasons.append(f'bound_state {d[:12]}: {why}')
                        continue
                if kind == 'witness_check':
                    why = self._witness_problems(d)
                    if why:
                        reasons.append(f'witness_check {d[:12]}: {why}')
                        continue
                    wp = self.payload(d)
                    if claim.get('problem') is not None and (wp['task_sha256'] != claim['problem'].get('task_sha256')
                                                             or wp['value'] != claim['problem'].get('value')):
                        reasons.append(f'witness_check {d[:12]} is for a different problem or value than the claim')
                        continue
                if kind == 'execution_receipt':
                    why = self._execution_problems(d)
                    if why:
                        reasons.append(f'execution_receipt {d[:12]}: {why}')
                        continue
                if kind in RC.CONTRACTED:
                    why = self._contract_problems(d, kind, claim.get('problem'), level)
                    if why:
                        reasons.append(f'{kind} {d[:12]}: {why}')
                        continue
                usable.append((d, n))
            if kind == 'exact_check':
                distinct = {self.payload(d)['method'] for d, _ in usable}
                if len(distinct) < count:
                    reasons.append(f'needs {count} exact checks by different methods that replay, found {len(distinct)}')
            elif kind == 'bound_state':
                if claim.get('problem') is None:
                    pass  # reported above
                elif not usable:
                    reasons.append('optimality needs a checked BoundState with gap 0 and custody of its certificate')
            elif len(usable) < count:
                reasons.append(f'needs {count} valid {kind} artifact(s), found {len(usable)}')
            used_nodes |= {d for d, _ in usable}
        if (axis, level) == ('causality', 'PLACEBO_CONTROLLED') and not reasons:
            comps = {k: {self._intervention_cache[d][1] for d in used_nodes
                         if self.node(d)['kind'] == k and d in self._intervention_cache} for k in ('ablation', 'placebo')}
            if not comps['ablation'] & comps['placebo']:
                reasons.append('PLACEBO_CONTROLLED needs an ablation and a placebo of the same component')
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

    WITNESS_FIELDS = frozenset({'schema', 'task', 'task_sha256', 'witness', 'value'})

    def _witness_problems(self, nid):
        """Replay a witness check: the stored problem, the stored witness, the dual predicates."""
        from ..graphs import check_witness
        from ..models import GraphTask
        cache = self.__dict__.setdefault('_witness_replays', {})
        if nid in cache:
            return cache[nid]
        p = self.payload(nid)
        why = None
        if not isinstance(p, dict) or p.get('schema') != 'genesis-witness-check-v2' or set(p) != self.WITNESS_FIELDS:
            why = 'not a replayable witness check (genesis-witness-check-v2 with the problem and the witness)'
        else:
            try:
                task = GraphTask.model_validate_json(self.s.get_bytes(p['task_sha256']))
                if digest(task.model_dump(mode='json')) != p['task_sha256']:
                    why = 'stored problem does not hash to task_sha256'
                elif check_witness(task, tuple(tuple(e) for e in p['witness']))['value'] != p['value']:
                    why = 'witness does not replay to the recorded value'
            except Exception as exc:
                why = f'witness replay failed ({type(exc).__name__})'
        cache[nid] = why
        return why

    def _contract_problems(self, nid, kind, problem, level=None):
        """B20_R8/R15 replay contracts (kernel.replay_contracts). Replays are cached per (node, problem,
        level, revocation state); a formal replay also per checker identity. Returns a reason or None."""
        cache = self.__dict__.setdefault('_contract_replays', {})
        ref = (nid, digest(problem) if problem is not None else None, level if kind == 'priority_check' else None,
               self.revocation_head())
        if ref not in cache:
            p = self.payload(nid)
            try:
                if kind == 'exact_check':
                    why, _ = RC.exact_problems(self.s.get, p, problem)
                elif kind == 'formal_check':
                    why, _ = RC.formal_problems(self.s.get, p, problem, revoked_verifiers=self.revoked_verifiers())
                elif kind == 'priority_check':
                    why, _ = RC.priority_problems(self.s.get, p, problem, level, library=self.library())
                else:
                    why = RC.dev_problems(self.s.get, p, self._attempt)
            except Exception as exc:                   # a replay that cannot run licenses nothing
                why = [f'replay could not run ({type(exc).__name__})']
            cache[ref] = '; '.join(why) if why else None
        return cache[ref]

    def _attempt(self, aid):
        """(status, request hash, receipt hash) of one attempt in this store's journal, or None."""
        row = self.s.db.execute('SELECT status,request,receipt FROM attempts WHERE id=?', (aid,)).fetchone()
        return tuple(row) if row else None

    def library(self):
        """The pinned library priority searches are replayed in (None when it is not on this machine)."""
        if '_library' not in self.__dict__:
            self._library = RC.pinned_library()
        return self._library

    @property
    def _intervention_cache(self):
        return self.__dict__.setdefault('_interventions', {})

    def _stored_arms(self, p):
        """The arms of the frozen request a v4 receipt names, if stored and equal to arms_sha256."""
        for h in (p['arms_sha256'], p['request_hash']):
            try:
                obj = self.s.get(h)
            except Exception:
                continue
            arms = obj if h == p['arms_sha256'] else (obj.get('arms') if isinstance(obj, dict) else None)
            if isinstance(arms, dict) and digest(arms) == p['arms_sha256']:
                return arms
        return None

    def _intervention_problems(self, nid, kind, p):
        """Provenance of a signed ablation/placebo: the arms the receipt commits to (arms_sha256, stored
        directly or inside the frozen request it names) differ from each other in exactly one registered
        component (replay_contracts.intervention_problems)."""
        if nid not in self._intervention_cache:
            arms = self._stored_arms(p)
            if not isinstance(arms, dict) or set(arms) != {'candidate', 'baseline'} \
                    or not all(isinstance(arms[a], dict) for a in arms):
                res = (['the arms the receipt commits to (arms_sha256) are not stored as a candidate/baseline pair'],
                       None)
            elif (arms['candidate'].get('descriptor_id'), arms['baseline'].get('descriptor_id')) != \
                    R.receipt_arm_ids(p):
                res = (['the stored arms are not the descriptors the receipt names'], None)
            else:
                try:
                    res = RC.intervention_problems(kind, arms['candidate'], arms['baseline'])
                except Exception as exc:
                    res = ([f'intervention replay could not run ({type(exc).__name__})'], None)
            self._intervention_cache[nid] = res
        return self._intervention_cache[nid][0]

    def _replication_problems(self, claim, p, deps, ctx, level):
        """An internal replication repeats a supporting sealed_evaluation of this claim: the same
        arms, analysis (up to the hypothesis family the custodian assigns per evidence kind, and the
        decision record each registration names) and domain, another panel and operator identity,
        registered after the original completed. Returns (problems, {the original node}); no problems:
        it repeats one (B20_R21: internal_replication and external_reproduction alike)."""
        originals = sorted(d for d in deps if self.node(d)['kind'] == 'sealed_evaluation')
        why, nodes, _ = self._signed_support(claim, 'sealed_evaluation', 1, level, originals, deps, ctx)
        if not nodes:
            return ['no supporting sealed_evaluation of this claim to replicate'] + why[:1], set()
        out = []
        for d in sorted(nodes):
            o = ctx.opened(d, 'sealed_evaluation')[0]
            bad = []
            if R.receipt_arm_ids(o) != R.receipt_arm_ids(p):
                bad.append('other arms')
            if R.replication_plan(o['analysis']) != R.replication_plan(p['analysis']) or o['domain'] != p['domain']:
                bad.append('another analysis or domain')
            if o['panel_commitment'] == p['panel_commitment']:
                bad.append('the same panel')
            if o['operator_id'] == p['operator_id']:
                bad.append('the same operator identity')
            if R._time(p['registered_at']) < R._time(o['completed_at']):
                bad.append('registered before the original completed')
            if not bad:
                return [], {d}
            out.append(f'original {d[:12]}: ' + ', '.join(bad))
        return ['does not replicate a supporting sealed_evaluation (' + '; '.join(out) + ')'], set()

    def _execution_problems(self, nid):
        """EXECUTABLE needs a reference to something that ran: a finished attempt or a stored IR program."""
        p = self.payload(nid)
        if not isinstance(p, dict):
            return 'no execution reference'
        if p.get('attempt'):
            row = self.s.db.execute('SELECT status FROM attempts WHERE id=?', (p['attempt'],)).fetchone()
            return None if row and row[0] == 'SUCCESS' else 'referenced attempt did not finish successfully'
        if p.get('ir_program'):
            row = self.s.db.execute("SELECT object_hash FROM entities WHERE kind='ir_program' AND id=?",
                                    (p['ir_program'],)).fetchone()
            ok = row is not None and (self.s.get(row[0]) or {}).get('schema') == 'genesis-ir-program-v1' \
                and bool(self.s.get(row[0]).get('nodes'))
            return None if ok else 'referenced IR program is not a recorded, non-empty program'
        return 'no execution reference (attempt or ir_program)'

    BOUND_FIELDS = frozenset({'schema', 'task', 'task_sha256', 'lower', 'upper', 'gap', 'lower_evidence',
                              'certificate_bundle'})

    def _campaign_history_problems(self, binding):
        """Campaign and source identity are write-once, and every bound request is a frozen
        request of THIS campaign whose export is a prefix of this store's history (B14 round 3)."""
        from .phases import PhaseError, _frozen_request
        written = {}
        for (raw,) in self.s.db.execute('SELECT body FROM events ORDER BY seq'):
            body = json.loads(raw)
            if body['kind'] == 'STATE_UPDATED':
                upd = self.s.get(body['payload'])
                if upd['key'] in ('campaign_id', 'source_hash'):
                    written.setdefault(upd['key'], set()).add(json.dumps(upd['value']))
        if any(len(v) > 1 for v in written.values()):
            return 'campaign identity or source was rewritten in this store'
        for rh in binding['request_hashes']:
            try:
                _frozen_request(self.s, rh)
            except PhaseError as exc:
                return f'bound request {rh[:12]} is not a frozen request of this campaign: {exc}'
        return None

    def _bound_state_problems(self, nid, problem=None):
        """Certificate custody AND checker replay for a BoundState (R-03). Returns a reason or None.

        The bound state must reference its lower evidence (a passing witness check
        of the same value on the same problem, as a parent) and a certificate bundle
        for that problem. The bundle is replayed here with the producing solver
        disabled (pinned proof checker on the stored CNF/proof; trivial bounds
        against the host's edge count; the witness by the dual predicates), so no
        entry point grants OPTIMALITY_CHECKED on custody alone. Replays are cached
        per bundle identity (immutable content). No checker means no status.
        """
        from ..verification.certificates import checker_only, custody_problems, replay
        p = self.payload(nid)
        if not isinstance(p, dict) or p.get('schema') != 'genesis-bound-state-v2' or set(p) != self.BOUND_FIELDS:
            return 'bound state lacks certificate custody (genesis-bound-state-v2 with lower and upper evidence)'
        if p['gap'] != 0 or p['upper'] != p['lower']:
            return 'gap is not 0'
        if problem is not None and (p['task_sha256'] != problem.get('task_sha256') or p['upper'] != problem.get('value')):
            return 'bound state is for a different problem or value than the claim'
        if p['lower_evidence'] not in self.node(nid)['parents'] or not self._has_node(p['lower_evidence']):
            return 'lower evidence is not a parent of the bound state'
        lower_node = self.node(p['lower_evidence'])
        lower_payload = self.payload(p['lower_evidence'])
        if lower_node['kind'] == 'witness_check' and self._witness_problems(p['lower_evidence']):
            return 'lower evidence does not replay: ' + self._witness_problems(p['lower_evidence'])
        if lower_node['kind'] != 'witness_check' or lower_node['verdict'] not in PASSING \
                or not isinstance(lower_payload, dict) or lower_payload.get('value') != p['lower'] \
                or lower_payload.get('task_sha256') != p['task_sha256']:
            return 'lower evidence is not a passing witness check of this value on this problem'
        try:
            bundle = self.s.get(p['certificate_bundle'])
        except Exception:
            return 'certificate bundle missing or altered'

        def has_object(h):
            try:
                self.s.get_bytes(h)
                return True
            except Exception:
                return False

        dead_checkers = sorted(self.revoked_verifiers())
        try:
            problems = custody_problems(bundle, has_object, dead_checkers)
        except Exception as exc:
            return f'malformed certificate bundle ({type(exc).__name__})'
        if problems:
            return '; '.join(problems)
        if bundle['problem']['task_sha256'] != p['task_sha256'] or bundle['lower']['value'] != p['lower'] \
                or bundle['upper']['value'] != p['upper']:
            return 'certificate bundle certifies a different problem or bound'
        # Replays are cached per (bundle identity, revocation state): a cache hit under a
        # since-revoked checker is not valid (B20_R1, Repair D).
        cache = self.__dict__.setdefault('_replays', {})
        ref = (p['certificate_bundle'], self.revocation_head())
        if ref not in cache:
            try:
                with checker_only():
                    cache[ref] = replay(bundle, self.s.get_bytes, dead_checkers)
            except Exception as exc:
                cache[ref] = {'status': 'CHECKER_ERROR', 'problems': [f'{type(exc).__name__}: {exc}']}
        r = cache[ref]
        if r['status'] != 'OPTIMALITY_CHECKED' or r.get('problems'):
            return f'certificate does not replay ({r["status"]}: ' + '; '.join(r.get('problems', []))[:160] + ')'
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
                if R.evaluation_identity(p) in self._revoked('evaluation'):
                    reasons.append(f'{kind} {d[:12]} adjudication revoked')
                    continue
                good[R.evaluation_identity(p)] = p; nodes.add(d)
            if len(good) < count:
                reasons.append(f'needs {count} supporting {kind}, found {len(good)}')
            return reasons, nodes, set(good)
        binding = claim.get('binding')
        if binding is None:
            return ['confirmation needs a claim bound to its preregistered evaluations '
                    '(create_claim(..., binding=receipts.binding_from_requests(...)))'], set(), set()
        if binding['campaign_id'] != self.s.state('campaign_id') or self.s.state('source_hash') not in \
                binding['source_hashes']:
            # The receipts must be about THIS campaign's history (B14 red team C1).
            return ['claim binding names a different campaign or source than this evidence store'], set(), set()
        history_problem = self._campaign_history_problems(binding)
        if history_problem:
            reasons.append(history_problem)
        anchors = {}
        for d in deps:
            if self.node(d)['kind'] == 'preregistration_anchor':
                p, why, env = ctx.opened(d, 'preregistration_anchor')
                if p is not None:
                    anchors[digest(env)] = (p, env)
        dead = self._revoked('evaluation')
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
                if R.evaluation_identity(anchor[0]) in dead:
                    bad.append('preregistration anchor revoked')
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
            originals = set()
            if kind in ('ablation', 'placebo'):
                extra = self._intervention_problems(d, kind, p)
            elif kind in R.REPLICATION_KINDS:
                extra, originals = self._replication_problems(claim, p, deps, ctx, level)
            else:
                extra = []
            if extra:
                reasons.append(f'{kind} {d[:12]}: ' + '; '.join(extra[:2]))
                continue
            nodes |= originals          # the verified evaluation a repetition repeats is used evidence too
            if ident in good and good[ident] != p:
                reasons.append(f'evaluation {ident[:12]} carries conflicting signed receipts')
                continue
            good[ident] = p; nodes.add(d)
        if history_problem:
            good, nodes = {}, set()
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
        levels = self.levels(claim_id)
        wording = self.current_wording(claim_id, levels)
        return {'claim_id': claim_id, 'current_statement': wording['current_statement'],
                'conjecture': wording['conjecture'], 'statement_contract': wording['contract'],
                'requested_statement': claim['statement'], 'scope': claim['scope'],
                'dependencies': claim['dependencies'], 'binding': claim.get('binding'),
                'problem': claim.get('problem'),
                # Producer-recorded history: what was granted, by whom (registry), when. It is
                # not evidence; effective_levels are re-derived from the evidence graph.
                'historical': {'recorded_levels': self.recorded_levels(claim_id),
                               'promotions': self.promotion_history(claim_id),
                               'status': 'PRODUCER_RECORDED_NOT_AUTHORITATIVE'},
                'effective_levels': levels,
                'invalidated_by': [{'target': h, **({k: revoked[h][k] for k in ('reason', 'actor', 'at')}
                                                    if h in revoked else {})} for h in hits]}
