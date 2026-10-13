"""Test-only builders for signed scientific evidence (fixture keys, not independent roles).

Produces payloads in exactly the shape the custodian signs (kernel.receipts),
so kernel, phase and preflight tests exercise the shared validator without a
full sealed run. Nothing here is importable from src/.
"""
import base64
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from genesis.common import digest
from genesis.evaluation import sign_test
from genesis.kernel import receipts as R
from genesis.kernel.signing import sign
from genesis.models import Limits, SolverProgram

ROLES = ('prereg', 'custodian', 'auditor', 'release', 'root', 'replicator', 'priority_reviewer', 'outsider')


def keypair(directory, name):
    k = Ed25519PrivateKey.generate()
    path = Path(directory) / f'{name}.pem'
    path.write_bytes(k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                     serialization.NoEncryption()))
    pub = base64.b64encode(k.public_key().public_bytes(serialization.Encoding.Raw,
                                                       serialization.PublicFormat.Raw)).decode()
    return path, pub


class SignedFixture:
    export_sha256 = 'e' * 64
    def __init__(self, directory):
        self.keys = {n: keypair(directory, n) for n in ROLES}
        self.registry = {'pins': {'custodian_key': self.keys['custodian'][1], 'prereg_key': self.keys['prereg'][1],
                                  'auditor_key': self.keys['auditor'][1], 'release_key': self.keys['release'][1],
                                  'replicator_key': self.keys['replicator'][1],
                                  'priority_reviewer_key': self.keys['priority_reviewer'][1],
                                  'release_authority_id': 'FIXTURE_BOARD'}}
        self._tick = 0
        self.export_sha256 = 'e' * 64

    def bind_store(self, store):
        """Make `store` a campaign the fixture requests belong to: identity, and an export the
        requests bind (kernel and phase checks require bound requests to be this campaign's)."""
        from genesis.cli import export_replication
        from genesis.common import bytes_hash
        store.set_state('campaign_id', 'a' * 64); store.set_state('source_hash', 'c' * 64)
        export = store.root / 'exports' / 'campaign_export.zip'
        export_replication(store.root, export, store=store)
        self.export_sha256 = bytes_hash(export.read_bytes())

    def sign(self, payload, role):
        return sign(payload, self.keys[role][0])

    STATEMENT = 'the frozen candidate has a higher paired edge count than the frozen baseline on the sealed panel'
    SCOPE = 'c4_host_v2 sealed panel'

    def request(self, claim_id='claim-1', kind='sealed_evaluation', *, candidate='b' * 64, campaign='a' * 64,
                domain='c4_host_v2', transition=None, transfer=None, task_count=40, seed=1, baseline_rounds=1,
                candidate_program=None, baseline_program=None, statement=None, scope=None, export_sha256=None):
        programs = {'baseline': baseline_program or SolverProgram(rounds=baseline_rounds).model_dump(mode='json'),
                    'candidate': candidate_program or SolverProgram(weights=(0, 0, 0, 1)).model_dump(mode='json')}
        return {'schema': R.REQUEST, 'campaign_id': campaign, 'claim_id': claim_id, 'evidence_kind': kind,
                'statement_hash': digest(statement or self.STATEMENT), 'scope': scope or self.SCOPE,
                'generation_transition': transition, 'transfer_source_domain': transfer,
                'candidate_version': candidate, 'campaign_export_sha256': export_sha256 or self.export_sha256,
                'source_hash': 'c' * 64,
                'programs': programs,
                'limits': Limits().model_dump(mode='json'), 'seed': seed, 'task_count': task_count,
                'domain': domain, 'analysis': dict(R.ANALYSIS_V1), 'exposed_graph_fingerprints': [],
                'expected_evaluator_hash': 'c' * 64}

    def _time(self):
        self._tick += 1
        return f'2026-10-10T00:{self._tick // 60:02d}:{self._tick % 60:02d}+00:00'

    def anchor(self, request, *, panel=None, role='prereg', **overrides):
        payload = {'schema': R.PREREG_ANCHOR, 'request_hash': digest(request), 'claim_id': request['claim_id'],
                   'statement_hash': request['statement_hash'], 'scope': request['scope'],
                   'evidence_kind': request['evidence_kind'], 'registration_slot': R.registration_slot(request),
                   'registered_at': self._time(),
                   'operator_id': 'FIXTURE_OPERATOR_NOT_INDEPENDENT', 'exposure_registry_root': 'd' * 64,
                   'exposure_graphs': 10, 'declaration_unscreenable_graphs': 0,
                   'panel_commitment': panel or digest({'panel': digest(request)})}
        payload.update(overrides)
        return self.sign(payload, role)

    def receipt_payload(self, request, anchor, *, wins=30, losses=5, ties=5, raw=None, family_p=0.01, **overrides):
        p = {'schema': R.SCIENTIFIC_RECEIPT, 'evidence_kind': request['evidence_kind'],
             'claim_id': request['claim_id'], 'statement_hash': request['statement_hash'], 'scope': request['scope'],
             'campaign_id': request['campaign_id'], 'request_hash': digest(request),
             'anchor_hash': digest(anchor), 'candidate_version': request['candidate_version'],
             'candidate_program_hash': R.program_identity(request['programs']['candidate']),
             'baseline_version': R.program_identity(request['programs']['baseline']), 'source_hash': request['source_hash'],
             'evaluator_hash': request['expected_evaluator_hash'], 'analysis': dict(request['analysis']),
             'domain': request['domain'], 'domain_contract_hash': R.domain_contract_hash(request['domain']),
             'transfer_source_domain': request['transfer_source_domain'],
             'generation_transition': request['generation_transition'],
             'panel_commitment': anchor['payload']['panel_commitment'], 'task_count': wins + losses + ties,
             'raw_evidence_root': raw or digest({'raw': digest(request)}), 'raw_evidence_complete': True,
             'expected_rows': 2 * (wins + losses + ties), 'completed_rows': 2 * (wins + losses + ties),
             'execution_failures': 0, 'wins': wins, 'losses': losses, 'ties': ties,
             'paired_p': sign_test(wins, losses), 'family_p': family_p, 'outcome': None,
             'operator_id': 'FIXTURE_OPERATOR_NOT_INDEPENDENT', 'registered_at': anchor['payload']['registered_at'],
             'completed_at': self._time(), 'screen': 'FIXTURE', 'independence': 'OPERATOR_ATTESTATION_REQUIRED'}
        p['outcome'] = R.derive_outcome(p)
        p.update(overrides)
        return p

    def receipt(self, request, anchor, *, role='custodian', **kw):
        return self.sign(self.receipt_payload(request, anchor, **kw), role)


def record_evaluation(kernel, fixture, request, parents=(), *, anchor=None, receipt=None,
                      route='genesis.custodian.evaluate', source='c' * 64, **receipt_kw):
    """Record anchor + receipt nodes the way a custodian hand-off would. Returns (anchor_node, receipt_node)."""
    anchor = anchor or fixture.anchor(request)
    receipt = receipt or fixture.receipt(request, anchor, **receipt_kw)
    kernel.s.save('frozen_request', digest(request), request)  # the campaign froze this request
    a = kernel.record_signed('preregistration_anchor', anchor, route=route, source_hash=source)
    r = kernel.record_signed(request['evidence_kind'], receipt, parents=list(parents) + [a], route=route,
                             source_hash=source)
    return a, r


def chain_requests(fx, claim_id, n, *, versions=None, seed=0, index_order=None):
    """n consecutive successor transitions: link i compares program P(i+1) against its predecessor P(i)."""
    v = versions or [f'{i + 1}' * 64 for i in range(n + 1)]
    progs = [SolverProgram(rounds=i + 1).model_dump(mode='json') for i in range(n + 1)]
    idx = index_order or list(range(1, n + 1))
    return [fx.request(claim_id=claim_id, kind='sealed_generation_evaluation', candidate=v[i + 1], seed=seed + i,
                       transition={'index': idx[i], 'from_version': v[i], 'to_version': v[i + 1]},
                       baseline_program=progs[i], candidate_program=progs[i + 1])
            for i in range(n)]


def campaign_export(directory, *, campaign_id='a' * 64, source_hash='c' * 64, domain='c4_host_v2', hosts=(),
                    name='export.zip', candidate_program=None, baseline_name='multistart', descriptor=None,
                    descriptor_rewrites=()):
    """A minimal but real frozen campaign export: hash-chained store with campaign identity, source,
    one configuration, a frozen candidate (latest_program + candidate_version document), the
    strongest-baseline record, and optional research-visible hosts. Returns (path, frozen) where
    `frozen` gives the request fields that describe this candidate."""
    from genesis.cli import export_replication
    from genesis.dsl import baseline_programs
    from genesis.store import Store
    root = Path(directory) / f'campaign-{name}'
    program = candidate_program or SolverProgram(weights=(0, 0, 0, 1)).model_dump(mode='json')
    version = {'program': program, 'source': source_hash, 'fixture': name}
    with Store(root) as s:
        s.set_state('campaign_id', campaign_id)
        s.set_state('source_hash', source_hash)
        s.save('config', 'resolved', {'domain': domain, 'profile': 'fixture'})
        for t in hosts:
            s.put({'kind': 'solver', 'task': t.model_dump(mode='json')})
        s.set_state('latest_program', program)
        s.set_state('summary', {'generations': [{'baseline': baseline_name}], 'retained_dev_capabilities': []})
        if descriptor is not None:
            # B20_R5: a frozen executable candidate (write-once state + candidate_version document).
            version = {'descriptor': descriptor, 'source': source_hash, 'fixture': name}
            for earlier in descriptor_rewrites:      # fixture for a rewritten history
                s.set_state('frozen_candidate_descriptor', earlier)
            s.set_state('frozen_candidate_descriptor', descriptor)
        s.save('candidate_version', digest(version), version)
        s.set_state('phase', 'CANDIDATE_FROZEN')
    dest = Path(directory) / name
    export_replication(root, dest)
    frozen = {'candidate_version': digest(version), 'source_hash': source_hash, 'campaign_id': campaign_id,
              'programs': {'baseline': baseline_programs()[baseline_name].model_dump(mode='json'),
                           'candidate': program}}
    return dest, frozen


def path4():
    from genesis.models import GraphTask
    return GraphTask(task_id='path4', n=4, edges=((0, 1), (1, 2), (2, 3)), family='path')


def witness_payload(store, task=None, witness=None):
    """A replayable witness check (genesis-witness-check-v2): the problem is stored, the witness re-checked."""
    from genesis.graphs import check_witness
    task = task or path4()
    witness = [list(e) for e in (witness if witness is not None else task.edges)]
    sha = store.put(task.model_dump(mode='json'))
    value = check_witness(task, tuple(tuple(e) for e in witness))['value']
    return {'schema': 'genesis-witness-check-v2', 'task': task.task_id, 'task_sha256': sha, 'witness': witness,
            'value': value}


def fixture_campaign(directory, fx, **request_kw):
    """A store that is a real (tiny) campaign: identity, export bound to the frozen request, frozen request."""
    from genesis.cli import export_replication
    from genesis.common import bytes_hash
    from genesis.store import Store
    root = Path(directory) / f'fixture-campaign-{len(list(Path(directory).glob("fixture-campaign-*")))}'
    with Store(root) as s:
        s.set_state('campaign_id', request_kw.get('campaign', 'a' * 64))
        s.set_state('source_hash', 'c' * 64)
    export_replication(root, root / 'exports' / 'campaign_export.zip')
    request = fx.request(export_sha256=bytes_hash((root / 'exports' / 'campaign_export.zip').read_bytes()), **request_kw)
    with Store(root) as s:
        s.save('frozen_request', digest(request), request)
        s.set_state('frozen_request_hash', digest(request))
    return root, request


def math_claim(kernel, claim_id, deps, *, value=3, claim='lower_bound', task=None, scope='this finite host only'):
    """A mathematical claim the way the kernel requires it: about a stored problem, with the
    kernel-generated statement."""
    task = task or path4()
    problem = {'task_sha256': kernel.s.put(task.model_dump(mode='json')), 'value': value, 'claim': claim}
    return kernel.create_claim(claim_id, kernel.math_statement(problem), scope, deps, problem=problem)
