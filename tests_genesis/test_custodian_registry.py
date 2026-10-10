"""GI6-10: the custodian builds its own exposure registry and rejects omissions.

Each test reproduces the audit's attack shape with fixture keys and public
graphs only. Fixture signatures demonstrate protocol behaviour, not operator
independence.
"""
import base64
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from genesis.common import bytes_hash, canonical, code_identity, digest
from genesis.custodian import register, evaluate, adjudicate, verify
from genesis.graphs import canonical_graph, relabel
from genesis.models import GraphTask, Limits, SolverProgram

REPO = Path(__file__).resolve().parents[1]


def legacy_hosts(seed=20261009, count=60):
    sys.path.insert(0, str(REPO / 'legacy_batch42'))
    try:
        from c4_hard_cases import sample_cases
        return sample_cases(seed=seed, count=count)
    finally:
        sys.path.remove(str(REPO / 'legacy_batch42'))


def as_task(case, task_id, split='CONFIRM', perm=None):
    t = GraphTask(task_id=task_id, n=case['n'], edges=tuple(tuple(e) for e in case['host']), family='fixture', split=split)
    return relabel(t, perm) if perm else t


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / 'private'; self.root.mkdir(mode=0o700); self.root.chmod(0o700)
        k = Ed25519PrivateKey.generate(); self.key = self.base / 'custodian.pem'
        self.key.write_bytes(k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                             serialization.NoEncryption()))
        self.public = base64.b64encode(k.public_key().public_bytes(serialization.Encoding.Raw,
                                                                   serialization.PublicFormat.Raw)).decode()
        self.manifest = self.root / 'exposure_manifest.json'
        self.write_manifest([{'kind': 'legacy_generator', 'label': 'legacy-public-60', 'module': 'c4_hard_cases',
                              'function': 'sample_cases', 'kwargs': {'seed': 20261009, 'count': 60}}])

    def write_manifest(self, sources):
        if self.manifest.exists():
            self.manifest.chmod(0o600)
        self.manifest.write_text(json.dumps({'schema': 'genesis-exposure-manifest-v1', 'sources': sources}))
        self.manifest.chmod(0o600)

    def export_with(self, tasks, name='export.zip', campaign='a'):
        from tests_genesis.signed_fixtures import campaign_export
        path, frozen = campaign_export(self.base, campaign_id=campaign * 64, source_hash=code_identity(REPO)['sha256'],
                                       hosts=tasks, name=name)
        self.__dict__.setdefault('frozen', {})[str(path)] = frozen
        return path

    def request(self, export, declared=(), task_count=2, campaign='a'):
        source = code_identity(REPO)['sha256']
        frozen = self.frozen[str(export)]
        return {'schema': 'genesis-evaluation-request-v3', 'campaign_id': campaign * 64,
                'candidate_version': frozen['candidate_version'],
                'claim_id': f'utility-{campaign}', 'evidence_kind': 'sealed_evaluation',
                'statement_hash': '5' * 64, 'scope': 'fixture panel',
                'generation_transition': None, 'transfer_source_domain': None,
                'campaign_export_sha256': bytes_hash(export.read_bytes()),
                'source_hash': source, 'programs': frozen['programs'],
                'limits': Limits().model_dump(mode='json'), 'seed': 42, 'task_count': task_count, 'domain': 'c4_host_v2',
                'analysis': {'primary': 'paired-edge-count', 'alpha': .05, 'family_sensitivity': True, 'hypotheses': 1},
                'exposed_graph_fingerprints': list(declared), 'expected_evaluator_hash': source}

    def default_pool(self):
        return self.pool(self.fresh_tasks(2), 'default_pool.json')

    def pool(self, tasks, name='pool.json'):
        path = self.base / name
        path.write_bytes(canonical([t.model_dump(mode='json') for t in tasks]))
        return path

    def fresh_tasks(self, count=2):
        from genesis.research import make_panel
        tasks, _ = make_panel(9917, count, 'c4_host_v2', 'CONFIRM')
        return tasks


class ExposureDeclaration(Fixture):
    def test_gi6_10_builder_omitting_a_visible_host_is_rejected(self):
        visible = as_task(legacy_hosts()[3], 'dev-visible', split='DEV')
        export = self.export_with([visible])
        with self.assertRaisesRegex(ValueError, 'omits 1 host'):
            register(self.root, self.request(export, declared=[]), self.key, 'fixture',
                     exposure_manifest=self.manifest, campaign_export=export, pool=self.default_pool())

    def test_complete_declaration_is_accepted(self):
        visible = as_task(legacy_hosts()[3], 'dev-visible', split='DEV')
        export = self.export_with([visible])
        anchor = register(self.root, self.request(export, declared=[canonical_graph(visible)]), self.key, 'fixture',
                          exposure_manifest=self.manifest, campaign_export=export, pool=self.default_pool())
        payload = verify(anchor, self.public)
        self.assertEqual(payload['schema'], 'genesis-prereg-anchor-v3')
        self.assertGreater(payload['exposure_graphs'], 0)

    def test_export_binding_mismatch_rejected(self):
        export = self.export_with([])
        request = self.request(export)
        other = self.export_with(self.fresh_tasks(1), name='other.zip')
        with self.assertRaisesRegex(ValueError, 'does not match'):
            register(self.root, request, self.key, 'fixture', exposure_manifest=self.manifest, campaign_export=other,
                     pool=self.default_pool())

    def test_v1_request_refused(self):
        export = self.export_with([])
        request = self.request(export)
        request['schema'] = 'genesis-evaluation-request-v1'
        del request['campaign_export_sha256']
        with self.assertRaisesRegex(ValueError, 'schema'):
            register(self.root, request, self.key, 'fixture', exposure_manifest=self.manifest, campaign_export=export,
                     pool=self.default_pool())

    def test_missing_manifest_source_fails_closed(self):
        self.write_manifest([{'kind': 'campaign_store', 'path': 'public_runs/not_here'}])
        export = self.export_with([])
        with self.assertRaises((ValueError, FileNotFoundError)):
            register(self.root, self.request(export), self.key, 'fixture', exposure_manifest=self.manifest,
                     campaign_export=export, pool=self.default_pool())

    def test_manifest_writable_by_others_rejected(self):
        self.manifest.chmod(0o666)
        export = self.export_with([])
        with self.assertRaisesRegex(ValueError, 'custodian-owned'):
            register(self.root, self.request(export), self.key, 'fixture', exposure_manifest=self.manifest,
                     campaign_export=export, pool=self.default_pool())


class PanelScreening(Fixture):
    def test_gi6_10_relabelled_public_legacy_host_blocked_with_empty_declaration(self):
        # The audit's shape: builder declares nothing; the panel reuses an old public host.
        case = legacy_hosts()[5]
        n = case['n']
        reused = as_task(case, 'confirm-0', perm=tuple(reversed(range(n))))
        tasks = [reused, self.fresh_tasks(1)[0]]
        export = self.export_with([])
        request = self.request(export)
        pool = self.pool(tasks)
        register(self.root, request, self.key, 'fixture', exposure_manifest=self.manifest, campaign_export=export,
                 pool=pool)
        with self.assertRaisesRegex(ValueError, 'research-visible exposure'):
            evaluate(self.root, digest(request), pool, self.key, 'fixture')

    def test_near_duplicate_requires_adjudication(self):
        case = legacy_hosts()[7]
        es = set(tuple(e) for e in case['host'])
        missing = next((u, v) for u in range(case['n']) for v in range(u + 1, case['n']) if (u, v) not in es)
        near = GraphTask(task_id='confirm-near', n=case['n'], edges=tuple(sorted(es | {missing})), family='f', split='CONFIRM')
        tasks = [near, self.fresh_tasks(1)[0]]
        export = self.export_with([])
        request = self.request(export)
        pool = self.pool(tasks)
        register(self.root, request, self.key, 'fixture', exposure_manifest=self.manifest, campaign_export=export,
                 pool=pool)
        with self.assertRaisesRegex(ValueError, 'requires adjudication'):
            evaluate(self.root, digest(request), pool, self.key, 'fixture')
        adjudicate(self.root, near, 'ALLOW', self.key, 'fixture', 'reviewed: distinct optimum structure')
        receipt = evaluate(self.root, digest(request), pool, self.key, 'fixture')
        self.assertEqual(verify(receipt, self.public)['completed_rows'], 4)

    def test_relabelled_reuse_of_a_consumed_panel_blocked(self):
        tasks = self.fresh_tasks(2)
        export = self.export_with([])
        first = self.request(export)
        pool = self.pool(tasks)
        register(self.root, first, self.key, 'fixture', exposure_manifest=self.manifest, campaign_export=export,
                 pool=pool)
        evaluate(self.root, digest(first), pool, self.key, 'fixture')
        export_c = self.export_with([], name='export-c.zip', campaign='c')
        second = self.request(export_c, campaign='c')
        changed = [relabel(t, tuple(reversed(range(t.n)))) for t in tasks]
        pool2 = self.pool(changed, 'pool2.json')
        register(self.root, second, self.key, 'fixture', exposure_manifest=self.manifest, campaign_export=export_c,
                 pool=pool2)
        with self.assertRaisesRegex(ValueError, 'already consumed'):
            evaluate(self.root, digest(second), pool2, self.key, 'fixture')

    def test_isomorphic_duplicates_inside_a_panel_rejected(self):
        t = self.fresh_tasks(1)[0]
        dup = relabel(t, tuple(reversed(range(t.n)))).model_copy(update={'task_id': 'confirm-dup'})
        export = self.export_with([])
        request = self.request(export)
        pool = self.pool([t, dup])
        register(self.root, request, self.key, 'fixture', exposure_manifest=self.manifest, campaign_export=export,
                 pool=pool)
        with self.assertRaisesRegex(ValueError, 'isomorphic duplicates'):
            evaluate(self.root, digest(request), pool, self.key, 'fixture')


class RegistryReproducesAudit(unittest.TestCase):
    def test_legacy_corpora_dedupe_and_large_symmetric_hosts_are_indexable(self):
        from genesis.exposure import GraphIndex
        from genesis.ladder import ladder_task
        index = GraphIndex()
        for n in (20, 40, 63):
            t = ladder_task('c4_host_v2', n)
            self.assertTrue(index.add(t.n, t.edges, f'K{n}'))
        k40 = ladder_task('c4_host_v2', 40)
        self.assertEqual(index.find(k40.n, k40.edges), 'K40')  # canonical_graph would refuse this host


if __name__ == '__main__':
    unittest.main()


class EndToEndDeclaration(Fixture):
    def test_real_campaign_export_declaration_is_complete(self):
        from genesis.campaign import Campaign
        from genesis.cli import request_bundle
        from genesis.common import load_json
        from genesis.models import Config
        root = self.base / 'campaign'
        Campaign.initialize(root, Config(generations=1, tasks_per_panel=3, proposals_per_epoch=2, research_trials=8))
        with Campaign(root) as c:
            c.run()
            path = request_bundle(c, 3)
        request = load_json(path)
        export = root / 'exports' / 'campaign_export.zip'
        pool = self.pool(self.fresh_tasks(3), 'e2e_pool.json')
        anchor = register(self.root, request, self.key, 'fixture', exposure_manifest=self.manifest,
                          campaign_export=export, pool=pool)
        self.assertEqual(verify(anchor, self.public)['request_hash'], digest(request))


class ResearchScreening(Fixture):
    def test_research_visible_candidate_matching_a_sealed_graph_is_blocked(self):
        tasks = self.fresh_tasks(2)
        export = self.export_with([])
        request = self.request(export)
        pool = self.pool(tasks)
        register(self.root, request, self.key, 'fixture', exposure_manifest=self.manifest, campaign_export=export,
                 pool=pool)
        evaluate(self.root, digest(request), pool, self.key, 'fixture')
        from genesis.custodian import screen_for_research
        moved = relabel(tasks[0], tuple(reversed(range(tasks[0].n))))
        (self.root / 'sealed_statements').mkdir()
        (self.root / 'sealed_statements' / 'panel.json').write_text(json.dumps(
            ['theorem s (x y : Nat) (h : x ≤ y) : x + 0 ≤ y := by omega']))
        receipt = screen_for_research(self.root, [
            {'kind': 'graph', 'n': moved.n, 'edges': [list(e) for e in moved.edges]},
            {'kind': 'lemma', 'text': 'theorem mine (a b : Nat) (q : a ≤ b) : a + 0 ≤ b := by simp_all'},
            {'kind': 'lemma', 'text': 'theorem other (l : List Nat) : l.length = l.length := rfl'}],
            self.key, 'fixture')
        decisions = [d['decision'] for d in verify(receipt, self.public)['decisions']]
        self.assertEqual(decisions, ['BLOCK', 'BLOCK', 'ALLOW'])
        self.assertTrue((self.root / 'screening_ledger.jsonl').read_text().count('\n') == 3)
