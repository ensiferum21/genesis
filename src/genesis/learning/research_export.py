"""Frozen equational research as a custodian-checkable campaign export (B20_R7, handoff s13).

A sealed statement evaluation compares frozen research successors (formal-research-successor-v1
descriptors). The custodian must rebuild them from a frozen campaign export, never from request
facts, so equational research gets the same kind of hash-chained store and export as solver
campaigns (``store.Store`` + ``cli.export_replication``):

  state     campaign_id, source_hash (write-once), phase CANDIDATE_FROZEN,
            frozen_candidate_descriptor and frozen_baseline_descriptor (write-once)
  entities  config 'resolved'          {domain: eq_<system>_v1, profile: 'equational-research'}
            successor_manifest <id>    custody manifests (learning.custody), every arm's
            proof_object <sha256>      {sha256, text}: every lemma proof the manifests name
            exposed_statement <hash>   {system, route, statement}: everything research saw
            candidate_version <hash>   {descriptor, baseline_descriptor, source, origin}

``exposed_statement`` must list every research-visible statement (pools, development targets,
library lemmas are added automatically from the manifests); the custodian screens its sealed
panel against them. The candidate is typically a learned policy's successor and the baseline a
fixed policy's or the empty library's, each from its own research run; which successor is the
baseline is frozen here, before any sealed panel exists.
"""
from pathlib import Path

from ..common import digest
from . import custody as CU
from . import equational as Q
from .statement_panels import statement_domain

ROUTES = ('pool', 'development', 'lemma', 'memory', 'curriculum', 'import')
KIND = 'formal-research-successor-v1'


def successor_descriptor(manifest, *, premise_k, prove_seconds, cpu_seconds, memory_mib=2048, wall_seconds=None):
    from .. import candidates as C
    return C.build_descriptor(KIND, statement_domain(manifest['system']),
                              {'system': manifest['system'], 'manifest_id': manifest['manifest_id'],
                               'premise_k': premise_k, 'prove_seconds': prove_seconds},
                              cpu_seconds=cpu_seconds, memory_mib=memory_mib, wall_seconds=wall_seconds)


def freeze(root, export_path, *, campaign_id, source_hash, candidate, baseline, objects, exposure, origin,
           premise_k=8, prove_seconds=1, cpu_seconds=None, memory_mib=2048, wall_seconds=None):
    """Write the frozen research store at ``root`` and its export at ``export_path``.

    candidate, baseline: successor manifests (learning.custody.successor_manifest) of the same
    system; objects: an ObjectStore holding every proof they name; exposure: iterable of
    (route, statement text) for research-visible material beyond the libraries."""
    from ..cli import export_replication
    from ..store import Store
    system = candidate['system']
    if baseline['system'] != system:
        raise ValueError('candidate and baseline successors must be of the same system')
    for m in (candidate, baseline):
        problems = CU.successor_problems(m, objects)
        if problems:
            raise ValueError(f'successor {m["manifest_id"][:12]} fails custody: {sorted({p["code"] for p in problems})}')
    cpu = cpu_seconds or prove_seconds + 2
    kw = dict(premise_k=premise_k, prove_seconds=prove_seconds, cpu_seconds=cpu, memory_mib=memory_mib,
              wall_seconds=wall_seconds or max(10, 4 * cpu))
    cand, base = successor_descriptor(candidate, **kw), successor_descriptor(baseline, **kw)
    if cand['descriptor_id'] == base['descriptor_id']:
        raise ValueError('candidate and baseline are the same successor')
    root = Path(root)
    with Store(root) as s:
        if s.state('phase') == 'CANDIDATE_FROZEN':
            raise FileExistsError('this research store is already frozen')
        s.set_state('campaign_id', campaign_id)
        s.set_state('source_hash', source_hash)
        s.save('config', 'resolved', {'domain': statement_domain(system), 'profile': 'equational-research'})
        for m in (candidate, baseline):
            s.save('successor_manifest', m['manifest_id'], m)
            for lem in m['lemmas']:
                s.save('proof_object', lem['proof_sha256'],
                       {'sha256': lem['proof_sha256'], 'text': objects.get(lem['proof_sha256']).decode()})
                s.save('exposed_statement', digest(['lemma', lem['statement']]),
                       {'system': system, 'route': 'lemma', 'statement': lem['statement']})
        for route, text in exposure:
            if route not in ROUTES:
                raise ValueError(f'unknown exposure route {route!r}')
            s.save('exposed_statement', digest([route, text]), {'system': system, 'route': route, 'statement': text})
        version = {'descriptor': cand, 'baseline_descriptor': base, 'source': source_hash, 'origin': origin}
        s.save('candidate_version', digest(version), version)
        s.set_state('frozen_candidate_descriptor', cand)
        s.set_state('frozen_baseline_descriptor', base)
        s.set_state('summary', {'generations': [{'baseline': 'frozen-baseline-successor'}],
                                'retained_dev_capabilities': []})
        s.set_state('phase', 'CANDIDATE_FROZEN')
        export_replication(root, Path(export_path), store=s)
    return {'export': str(export_path), 'candidate_version': digest(version), 'candidate': cand, 'baseline': base}


def statement_request(frozen, *, campaign_id, source_hash, analysis, panel_spec, seed, claim_id, statement, scope):
    """The statement evaluation request for a frozen research export (``freeze``'s return value).
    The claim statement and scope are committed here, before any sealed panel exists."""
    from ..common import bytes_hash
    from ..custodian import validate_request
    from ..kernel import receipts as R
    request = {'schema': R.REQUEST_STATEMENTS, 'campaign_id': campaign_id, 'claim_id': claim_id,
               'evidence_kind': 'sealed_evaluation', 'statement_hash': digest(statement), 'scope': scope,
               'generation_transition': None, 'transfer_source_domain': None,
               'campaign_export_sha256': bytes_hash(Path(frozen['export']).read_bytes()),
               'candidate_version': frozen['candidate_version'], 'source_hash': source_hash,
               'arms': {'candidate': frozen['candidate'], 'baseline': frozen['baseline']}, 'seed': seed,
               'task_count': panel_spec['per_range'] * len(panel_spec['ranges']),
               'domain': frozen['candidate']['domain'], 'analysis': analysis, 'panel_spec': panel_spec,
               'expected_evaluator_hash': source_hash}
    validate_request(request)
    return request


def research_material(facts):
    """(manifests by id, MemoryObjects, exposure list) rebuilt from campaign facts (custodian side)."""
    objects = CU.MemoryObjects({h: o['text'] for h, o in facts['proof_objects'].items()})
    exposure = []
    for item in facts['exposed_statements']:
        if item.get('system') not in Q.SYSTEMS or item.get('route') not in ROUTES:
            raise ValueError('malformed exposed statement in the export')
        exposure.append((item['system'], item['statement'], item['route']))
    return facts['successor_manifests'], objects, exposure


__all__ = ['freeze', 'successor_descriptor', 'statement_request', 'research_material', 'KIND', 'ROUTES']
