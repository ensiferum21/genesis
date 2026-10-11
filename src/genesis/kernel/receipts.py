"""Trusted meaning of externally signed scientific evidence (roadmap W02, defect R-01).

One module decides what a signed scientific record says. The evidence kernel's
generic promotion API, the campaign phase machine, release preflight and the
custodian all call it, so no entry point can accept a receipt that another
would refuse.

Rules, all fail closed:

* The role allowed to sign an evidence kind is fixed in `KIND_ROLES` (trusted
  code). It is never read from a payload or a wrapper node.
* Every schema has an exact field set. Unknown schemas, missing or extra
  fields, malformed hashes, counts or probabilities are rejected.
* The scientific verdict is the signed `outcome`, and it must equal the outcome
  re-derived here from the signed counts and the preregistered analysis. An
  unsigned wrapper verdict is never the verdict. A valid NOT_SUPPORTED,
  INCONCLUSIVE or INVALID receipt counts as exactly that.
* A receipt is bound to one claim, campaign, candidate and baseline version,
  domain contract, preregistered request and anchor, evaluator, analysis, panel
  commitment and raw-evidence root.
* Evaluations are counted by identity (panel commitment + raw-evidence root),
  never by the number of wrapper nodes that carry the same envelope.

Hashes prove identity, not correctness or independence. Whether the signer is
an independent operator is outside what code can establish.
"""
from datetime import datetime

import base64

from .. import eligibility
from ..common import digest
from .stats import sign_test
from .signing import verify

SIGNED_EVIDENCE = 'genesis-signed-evidence-v1'      # evidence-node payload wrapper
SCIENTIFIC_RECEIPT = 'genesis-scientific-receipt-v2'
PREREG_ANCHOR = 'genesis-prereg-anchor-v3'
PRIORITY_ADJUDICATION = 'genesis-priority-adjudication-v1'
CLAIM_BINDING = 'genesis-claim-binding-v1'
REQUEST = 'genesis-evaluation-request-v3'

# Trusted map: evidence kind -> the only registry role whose key may sign it.
KIND_ROLES = {
    'preregistration_anchor': 'prereg_key',
    'sealed_evaluation': 'custodian_key',
    'sealed_transfer_evaluation': 'custodian_key',
    'sealed_improver_evaluation': 'custodian_key',
    'sealed_generation_evaluation': 'custodian_key',
    'external_reproduction': 'replicator_key',
    'external_priority_adjudication': 'priority_reviewer_key',
}
EVALUATION_KINDS = ('sealed_evaluation', 'sealed_transfer_evaluation', 'sealed_improver_evaluation',
                    'sealed_generation_evaluation', 'external_reproduction')
OUTCOMES = ('SUPPORTED', 'NOT_SUPPORTED', 'INCONCLUSIVE', 'INVALID')
PRIORITY_OUTCOMES = ('NOVEL_IN_SCOPE', 'PRIOR_ART_FOUND', 'INCONCLUSIVE')

# Domain semantics. W05 will replace this with DomainAdapter contracts; the hash
# changes whenever the stated semantics change, never because a comment did.
DOMAINS = {
    'c4_host_v2': {'objective': 'maximum number of host edges in a subgraph containing no 4-cycle',
                   'witness': 'subset of the host edge set', 'score': 'edge count',
                   'checker': 'genesis.graphs.check_witness (dual predicates)', 'version': 2},
    'triangle_free_host_v1': {'objective': 'maximum number of host edges in a subgraph containing no triangle',
                              'witness': 'subset of the host edge set', 'score': 'edge count',
                              'checker': 'genesis.graphs.check_witness (dual predicates)', 'version': 1},
}
ANALYSIS_V1 = {'primary': 'paired-edge-count', 'alpha': 0.05, 'family_sensitivity': True, 'hypotheses': 1}

RECEIPT_FIELDS = frozenset({
    'schema', 'evidence_kind', 'claim_id', 'statement_hash', 'scope', 'campaign_id', 'request_hash', 'anchor_hash',
    'candidate_version', 'candidate_program_hash', 'baseline_version', 'source_hash', 'evaluator_hash', 'analysis',
    'domain', 'domain_contract_hash', 'transfer_source_domain', 'generation_transition',
    'panel_commitment', 'task_count', 'raw_evidence_root', 'raw_evidence_complete',
    'expected_rows', 'completed_rows', 'execution_failures', 'wins', 'losses', 'ties',
    'paired_p', 'family_p', 'outcome', 'operator_id', 'registered_at', 'completed_at',
    'screen', 'independence'})
ANCHOR_FIELDS = frozenset({
    'schema', 'request_hash', 'claim_id', 'statement_hash', 'scope', 'evidence_kind', 'registration_slot',
    'registered_at', 'operator_id', 'exposure_registry_root', 'exposure_graphs', 'declaration_unscreenable_graphs',
    'panel_commitment'})
PRIORITY_FIELDS = frozenset({
    'schema', 'evidence_kind', 'claim_id', 'statement_hash', 'scope', 'reviewer_id',
    'search_record_root', 'decided_at', 'outcome'})
BINDING_FIELDS = frozenset({
    'schema', 'campaign_id', 'statement_hash', 'scope', 'candidate_version', 'candidate_program', 'baseline_versions',
    'domains', 'request_hashes', 'evaluator_hash', 'source_hashes'})


def hex64(h):
    return isinstance(h, str) and len(h) == 64 and all(c in '0123456789abcdef' for c in h)


def _nat(x):
    return type(x) is int and x >= 0


def _prob(x):
    return type(x) in (int, float) and 0 <= x <= 1


def _time(x):
    try:
        t = datetime.fromisoformat(x)
    except (TypeError, ValueError):
        return None
    return t if t.tzinfo is not None else None


def normalize_key(public_key_b64):
    """Canonical base64 of a raw Ed25519 public key (revocation compares keys, not strings)."""
    try:
        raw = base64.b64decode(public_key_b64, validate=True)
    except Exception:
        return None
    return base64.b64encode(raw).decode() if len(raw) == 32 else None


def program_identity(program):
    """Identity of a solver program: the hash of its validated canonical form, so two
    encodings of the same program (defaults omitted, key order) are the same program."""
    from ..common import canonical
    from ..models import SolverProgram
    return digest(SolverProgram.model_validate_json(canonical(program)).model_dump(mode='json'))


def registration_slots(request):
    """Slots a registration occupies; each may be used once at a custodian.

    * the claim slot: one sealed draw per claim (claim id in its campaign, kind, domain,
      generation position), so a claim cannot be re-run until a lucky draw appears;
    * the candidate slot: one sealed draw per candidate program in the same position, so
      renaming the claim does not buy another draw for the same candidate.
    Selection across *different* candidates and campaigns is a multiplicity question for
    a published registration log (W07; recorded as an open item)."""
    t = request.get('generation_transition')
    position = {'campaign_id': request['campaign_id'], 'evidence_kind': request['evidence_kind'],
                'domain': request['domain'], 'transfer_source_domain': request.get('transfer_source_domain'),
                'generation_index': t.get('index') if isinstance(t, dict) else None}
    return sorted({digest(dict(position, claim_id=request['claim_id'])),
                   digest(dict(position, candidate=program_identity(request['programs']['candidate'])))})


def registration_slot(request):
    """The anchor's commitment to the slots it occupies."""
    return digest({'slots': registration_slots(request)})


def domain_contract_hash(domain):
    if domain not in DOMAINS:
        raise ValueError(f'unknown domain {domain!r}')
    return digest({'schema': 'genesis-domain-contract-v1', 'domain': domain, **DOMAINS[domain]})


def claim_id_ok(x):
    """A claim identifier is ONE printable line: no newline, control, format (bidi) or
    separator characters, no surrounding whitespace, at most 200 characters (B15-REV-02)."""
    return isinstance(x, str) and 0 < len(x) <= 200 and x.isprintable() and x == x.strip()


_claim_id_ok = claim_id_ok


def _kind_extras(kind, domain, transfer, transition, candidate):
    """Kind-specific fields shared by requests and receipts."""
    out = []
    if kind == 'sealed_transfer_evaluation':
        if transfer not in DOMAINS or transfer == domain:
            out.append('transfer evaluation needs a different, known source domain')
    elif transfer is not None:
        out.append('transfer_source_domain is only allowed for transfer evaluations')
    if kind == 'sealed_generation_evaluation':
        if not isinstance(transition, dict) or set(transition) != {'index', 'from_version', 'to_version'}:
            out.append('generation evaluation needs generation_transition {index, from_version, to_version}')
        elif type(transition['index']) is not int or transition['index'] < 1 \
                or not hex64(transition['from_version']) or not hex64(transition['to_version']) \
                or transition['from_version'] == transition['to_version']:
            out.append('malformed generation transition')
        elif transition['to_version'] != candidate:
            out.append('generation transition must end at the evaluated candidate version')
    elif transition is not None:
        out.append('generation_transition is only allowed for generation evaluations')
    return out


def derive_outcome(p):
    """Outcome implied by signed counts under ANALYSIS_V1 (one-sided paired sign test)."""
    try:
        n = p['wins'] + p['losses'] + p['ties']
        valid = (p['raw_evidence_complete'] is True and p['completed_rows'] == p['expected_rows']
                 and n == p['task_count'] and p['paired_p'] == sign_test(p['wins'], p['losses']))
    except (KeyError, TypeError, ValueError):
        return 'INVALID'
    if not valid:
        return 'INVALID'
    if p['execution_failures']:
        return 'INCONCLUSIVE'
    alpha = p['analysis']['alpha']
    if p['wins'] > p['losses'] and max(p['paired_p'], p['family_p']) <= alpha:
        return 'SUPPORTED'
    return 'NOT_SUPPORTED'


def check_receipt(p, kind):
    """Strict schema and internal consistency of a scientific receipt payload."""
    if not isinstance(p, dict):
        return ['receipt payload is not an object']
    if p.get('schema') != SCIENTIFIC_RECEIPT:
        return [f'unknown receipt schema {p.get("schema")!r}']
    if set(p) != RECEIPT_FIELDS:
        return [f'receipt fields differ: missing {sorted(RECEIPT_FIELDS - set(p))[:4]}, '
                f'extra {sorted(set(p) - RECEIPT_FIELDS)[:4]}']
    out = []
    if p['evidence_kind'] != kind or kind not in EVALUATION_KINDS:
        out.append(f'receipt is for evidence kind {p["evidence_kind"]!r}, not {kind!r}')
    if not _claim_id_ok(p['claim_id']) or not isinstance(p['scope'], str) or not p['scope']:
        out.append('claim_id/scope')
    for k in ('campaign_id', 'request_hash', 'anchor_hash', 'candidate_version', 'candidate_program_hash',
              'baseline_version', 'source_hash', 'statement_hash', 'evaluator_hash', 'domain_contract_hash',
              'panel_commitment', 'raw_evidence_root'):
        if not hex64(p[k]):
            out.append(f'{k} is not a sha256 identity')
    if p['domain'] not in DOMAINS:
        out.append('unknown domain')
    elif p['domain_contract_hash'] != domain_contract_hash(p['domain']):
        out.append('domain contract hash does not match the domain semantics')
    if p['analysis'] != ANALYSIS_V1:
        out.append('unregistered analysis')
    out += _kind_extras(kind, p['domain'], p['transfer_source_domain'], p['generation_transition'],
                        p['candidate_version'])
    if p['candidate_program_hash'] == p['baseline_version']:
        out.append('candidate and baseline are the same program')
    if not all(_nat(p[k]) for k in ('task_count', 'expected_rows', 'completed_rows', 'execution_failures',
                                    'wins', 'losses', 'ties')) or p['task_count'] < 1:
        out.append('malformed counts')
    if not _prob(p['paired_p']) or not _prob(p['family_p']):
        out.append('malformed probabilities')
    if type(p['raw_evidence_complete']) is not bool:
        out.append('raw_evidence_complete must be boolean')
    if p['outcome'] not in OUTCOMES:
        out.append('unknown outcome')
    elif not out and p['outcome'] != derive_outcome(p):
        out.append(f'signed outcome {p["outcome"]} contradicts the signed analysis ({derive_outcome(p)})')
    before, after = _time(p['registered_at']), _time(p['completed_at'])
    if before is None or after is None or before >= after:
        out.append('invalid signed chronology')
    if not isinstance(p['operator_id'], str) or not p['operator_id']:
        out.append('operator_id')
    if not isinstance(p['screen'], str) or not isinstance(p['independence'], str):
        out.append('screen/independence fields')
    return out


def check_anchor(p):
    if not isinstance(p, dict) or p.get('schema') != PREREG_ANCHOR:
        return [f'unknown anchor schema {p.get("schema") if isinstance(p, dict) else None!r}']
    if set(p) != ANCHOR_FIELDS:
        return ['anchor fields differ']
    out = []
    for k in ('request_hash', 'exposure_registry_root', 'panel_commitment', 'statement_hash', 'registration_slot'):
        if not hex64(p[k]):
            out.append(f'anchor {k}')
    if not _claim_id_ok(p['claim_id']) or p['evidence_kind'] not in EVALUATION_KINDS \
            or not isinstance(p['scope'], str) or not p['scope']:
        out.append('anchor claim binding')
    if _time(p['registered_at']) is None:
        out.append('anchor time')
    if not _nat(p['exposure_graphs']) or not _nat(p['declaration_unscreenable_graphs']):
        out.append('anchor counts')
    if not isinstance(p['operator_id'], str) or not p['operator_id']:
        out.append('anchor operator')
    return out


def check_priority(p):
    if not isinstance(p, dict) or p.get('schema') != PRIORITY_ADJUDICATION or set(p) != PRIORITY_FIELDS:
        return ['priority adjudication schema']
    out = []
    if p['evidence_kind'] != 'external_priority_adjudication' or not _claim_id_ok(p['claim_id']):
        out.append('priority adjudication binding')
    if not hex64(p['statement_hash']) or not hex64(p['search_record_root']):
        out.append('priority adjudication hashes')
    if p['outcome'] not in PRIORITY_OUTCOMES:
        out.append('priority outcome')
    if _time(p['decided_at']) is None or not isinstance(p['reviewer_id'], str) or not p['reviewer_id'] \
            or not isinstance(p['scope'], str):
        out.append('priority adjudication fields')
    return out


def check_request(r):
    """Claim/kind part of a v3 evaluation request (the custodian checks the rest)."""
    out = []
    if not _claim_id_ok(r.get('claim_id')):
        out.append('claim_id')
    if not hex64(r.get('statement_hash')) or not isinstance(r.get('scope'), str) or not r.get('scope'):
        out.append('a request must commit to the claim statement (statement_hash) and scope before evaluation')
    programs = r.get('programs')
    if isinstance(programs, dict) and 'candidate' in programs and 'baseline' in programs:
        try:
            if program_identity(programs['candidate']) == program_identity(programs['baseline']):
                out.append('candidate and baseline are the same program')
        except Exception:
            out.append('candidate or baseline is not a valid program')
    if r.get('evidence_kind') not in EVALUATION_KINDS:
        out.append('evidence_kind')
    else:
        out += _kind_extras(r['evidence_kind'], r.get('domain'), r.get('transfer_source_domain'),
                            r.get('generation_transition'), r.get('candidate_version'))
    return out


def evaluation_identity(p):
    """Identity of one evaluation or adjudication; None if the payload has neither shape."""
    if not isinstance(p, dict):
        return None
    if p.get('schema') == PREREG_ANCHOR and 'request_hash' in p and 'panel_commitment' in p:
        return digest({'anchor': p['request_hash'], 'panel': p['panel_commitment']})
    if p.get('schema') == PRIORITY_ADJUDICATION and 'search_record_root' in p and 'claim_id' in p:
        return digest({'priority': p['search_record_root'], 'claim': p['claim_id']})
    if 'panel_commitment' in p and 'raw_evidence_root' in p:
        return digest({'panel': p['panel_commitment'], 'raw': p['raw_evidence_root']})
    return None


def wrap(envelope):
    """Evidence-node payload for a signed record. Nothing else may sit beside it."""
    return {'schema': SIGNED_EVIDENCE, 'envelope': envelope}


def unwrap_unverified(node_payload):
    """The envelope's claimed payload WITHOUT verification (for revocation lookups only)."""
    if isinstance(node_payload, dict) and node_payload.get('schema') == SIGNED_EVIDENCE \
            and isinstance(node_payload.get('envelope'), dict):
        inner = node_payload['envelope'].get('payload')
        return inner if isinstance(inner, dict) else None
    return None


def open_signed(node_payload, kind, pins, *, revoked_keys=()):
    """Verify a wrapped envelope under the role that trusted code assigns to `kind`.

    Revocation and trust-root policy are applied before the signature is
    considered. Returns (payload or None, problems).
    """
    if not isinstance(node_payload, dict) or set(node_payload) != {'schema', 'envelope'} \
            or node_payload['schema'] != SIGNED_EVIDENCE:
        return None, ['evidence node is not a bare signed-evidence wrapper']
    role = KIND_ROLES.get(kind)
    if role is None:
        return None, [f'no role may sign {kind}']
    key = (pins or {}).get(role)
    if not key:
        return None, [f'role {role} is not pinned in the trust registry']
    if normalize_key(key) is None or normalize_key(key) in {normalize_key(k) for k in revoked_keys}:
        return None, [f'the pinned {role} key is revoked or malformed']
    try:
        payload = verify(node_payload['envelope'], key)
    except Exception as exc:
        return None, [f'signature does not verify under the pinned {role} ({type(exc).__name__})']
    if kind == 'preregistration_anchor':
        problems = check_anchor(payload)
    elif kind == 'external_priority_adjudication':
        problems = check_priority(payload)
    else:
        problems = check_receipt(payload, kind)
        if not problems:
            ok, why = eligibility.source_status(payload['source_hash'])
            if not ok:
                problems = [why]
    return (payload if not problems else None), problems


# ---------- claim binding ----------

def check_binding(b):
    if not isinstance(b, dict) or b.get('schema') != CLAIM_BINDING or set(b) != BINDING_FIELDS:
        return ['claim binding schema']
    out = []
    for k in ('campaign_id', 'candidate_version', 'evaluator_hash', 'statement_hash'):
        if not hex64(b[k]):
            out.append(f'binding {k}')
    if b['candidate_program'] is not None and not hex64(b['candidate_program']):
        out.append('binding candidate_program')
    if not isinstance(b['scope'], str) or not b['scope']:
        out.append('binding scope')
    for k in ('baseline_versions', 'request_hashes', 'source_hashes'):
        v = b[k]
        if not isinstance(v, list) or not v or v != sorted(set(v)) or not all(hex64(h) for h in v):
            out.append(f'binding {k} must be a sorted non-empty list of identities')
    d = b['domains']
    if not isinstance(d, dict) or not d:
        out.append('binding domains')
    else:
        for name, h in d.items():
            if name not in DOMAINS or h != domain_contract_hash(name):
                out.append(f'binding domain {name!r} contract')
    return out


def binding_from_requests(requests):
    """Claim binding covering one or more frozen v3 requests for the same claim."""
    if not requests:
        raise ValueError('at least one request')
    for r in requests:
        problems = check_request(r)
        if problems:
            raise ValueError('request binding: ' + '; '.join(problems))
    keys = {(r['claim_id'], r['campaign_id'], r['expected_evaluator_hash'], r['statement_hash'], r['scope'])
            for r in requests}
    if len(keys) != 1:
        raise ValueError('requests disagree on claim, statement, scope, campaign or evaluator')
    chain = [r for r in requests if r['evidence_kind'] == 'sealed_generation_evaluation']
    if chain:
        final = max(chain, key=lambda r: r['generation_transition']['index'])['candidate_version']
        program = None  # each generation evaluates its own successor program
    else:
        versions = {(r['candidate_version'], program_identity(r['programs']['candidate'])) for r in requests}
        if len(versions) != 1:
            raise ValueError('requests evaluate different candidates (version or program)')
        final, program = versions.pop()
    domains = {}
    for r in requests:
        for d in (r['domain'], r.get('transfer_source_domain')):
            if d is not None:
                domains[d] = domain_contract_hash(d)
    b = {'schema': CLAIM_BINDING, 'campaign_id': requests[0]['campaign_id'],
         'statement_hash': requests[0]['statement_hash'], 'scope': requests[0]['scope'], 'candidate_version': final,
         'candidate_program': program,
         'baseline_versions': sorted({program_identity(r['programs']['baseline']) for r in requests}),
         'domains': domains, 'request_hashes': sorted({digest(r) for r in requests}),
         'evaluator_hash': requests[0]['expected_evaluator_hash'],
         'source_hashes': sorted({r['source_hash'] for r in requests})}
    problems = check_binding(b)
    if problems:
        raise ValueError('; '.join(problems))
    return b


def binding_mismatches(p, claim_id, binding, kind):
    """Why a verified evaluation receipt does not support this exact claim."""
    out = []
    if p['claim_id'] != claim_id:
        out.append('receipt is bound to a different claim')
    if p['statement_hash'] != binding['statement_hash'] or p['scope'] != binding['scope']:
        out.append('receipt was registered for a different claim statement or scope')
    if p['campaign_id'] != binding['campaign_id']:
        out.append('receipt is bound to a different campaign')
    if p['evaluator_hash'] != binding['evaluator_hash']:
        out.append('receipt names a different evaluator')
    if p['source_hash'] not in binding['source_hashes']:
        out.append('receipt names an unbound source identity')
    if p['request_hash'] not in binding['request_hashes']:
        out.append('receipt is not for a preregistered request of this claim')
    if p['baseline_version'] not in binding['baseline_versions']:
        out.append('receipt compares against an unbound baseline')
    if binding['domains'].get(p['domain']) != p['domain_contract_hash']:
        out.append('receipt domain is not bound to this claim')
    if p['transfer_source_domain'] is not None and p['transfer_source_domain'] not in binding['domains']:
        out.append('transfer source domain is not bound to this claim')
    if kind != 'sealed_generation_evaluation' and (p['candidate_version'] != binding['candidate_version']
                                                   or p['candidate_program_hash'] != binding['candidate_program']):
        out.append('receipt evaluates a different candidate version or program')
    return out


def anchor_mismatches(receipt, anchor_payload, anchor_envelope):
    out = []
    if receipt['anchor_hash'] != digest(anchor_envelope):
        out.append('receipt does not reference this preregistration anchor')
    if anchor_payload['request_hash'] != receipt['request_hash']:
        out.append('anchor registers a different request')
    if anchor_payload['panel_commitment'] != receipt['panel_commitment']:
        out.append('receipt panel differs from the preregistered panel commitment')
    if any(anchor_payload[k] != receipt[k] for k in ('claim_id', 'evidence_kind', 'statement_hash', 'scope')):
        out.append('anchor registers a different claim, statement, scope or evidence kind')
    if anchor_payload['registered_at'] != receipt['registered_at']:
        out.append('receipt chronology does not match the anchor')
    return out


def generation_chain(receipts, final_version):
    """Longest valid chain of successor transitions ending at `final_version`.

    Walking backwards from the final version, each earlier link must have the
    index one lower, end where the later link starts, and its candidate program
    must be the later link's baseline (each successor beat its predecessor).
    Versions and programs may not repeat (no cycles), and an ambiguous step
    (two different receipts for the same transition) ends the chain.
    """
    by_to = {}
    for p in receipts:
        by_to.setdefault(p['generation_transition']['to_version'], []).append(p)
    chain, version = [], final_version
    seen_versions, seen_programs = {final_version}, set()
    while version in by_to:
        later = chain[-1] if chain else None
        options = [p for p in by_to[version]
                   if (later is None or (p['generation_transition']['index'] == later['generation_transition']['index'] - 1
                                         and p['candidate_program_hash'] == later['baseline_version']))]
        if len(options) != 1:
            break
        p = options[0]
        start = p['generation_transition']['from_version']
        if start in seen_versions or p['candidate_program_hash'] in seen_programs \
                or p['baseline_version'] in seen_programs | {p['candidate_program_hash']}:
            break  # a cycle in versions or programs is not a lineage
        chain.append(p)
        seen_versions.add(start); seen_programs.add(p['candidate_program_hash'])
        version = start
    return chain


def accept_receipt(envelope, kind, pins, *, revoked_keys=()):
    """Single acceptance function for entry points that hold a bare envelope
    (phase machine, preflight): trusted role for the kind, strict schema,
    signed-outcome consistency and source eligibility. Returns (payload|None, problems)."""
    return open_signed(wrap(envelope), kind, pins, revoked_keys=revoked_keys)
