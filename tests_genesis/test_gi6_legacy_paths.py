"""GI6-01/02/03/08: legacy trust paths fail closed and cannot feed promotion."""
import ast
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from genesis.eligibility import eligible_for_confirmation, route_status

REPO = Path(__file__).resolve().parents[1]


class GI6_01_ReusedLemmaId(unittest.TestCase):
    def test_false_theorem_under_a_reused_id_is_rejected(self):
        from gap_engine.adapters.induction.checker import CheckError, LemmaStore
        from gap_engine.adapters.induction.theory import Theory
        theory = Theory.default(); parse = theory.parser()
        store = LemmaStore(theory)
        refl = {'rule': 'rewrite', 'left': [], 'right': []}
        self.assertTrue(store.verify('L1', _eq(parse, 'Z = Z'), refl))
        with self.assertRaises(CheckError):
            store.verify('L1', _eq(parse, 'Z = S Z'), refl)
        self.assertEqual(len(store.order), 1)


def _eq(parse, text):
    from gap_engine.adapters.induction.theory import Equation
    return Equation(*parse.parse_eq(text))


class GI6_02_NoUnsafeDeserialization(unittest.TestCase):
    BANNED = {('pickle', 'load'), ('pickle', 'loads'), ('pickle', 'Unpickler'), ('marshal', 'load'),
              ('marshal', 'loads'), ('shelve', 'open'), ('dill', 'load'), ('dill', 'loads'),
              ('joblib', 'load'), ('cloudpickle', 'load'), ('cloudpickle', 'loads')}

    def test_no_unsafe_deserialization_calls_in_shipped_code(self):
        offenders = []
        for directory in ('src', 'scripts', 'custody_reference', 'legacy_batch42'):
            for path in (REPO / directory).rglob('*.py'):
                if '__pycache__' in path.parts or path.name.startswith('test_'):
                    continue
                tree = ast.parse(path.read_text(), str(path))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) \
                            and (node.value.id, node.attr) in self.BANNED:
                        offenders.append(f'{path.relative_to(REPO)}:{node.lineno} {node.value.id}.{node.attr}')
                    if isinstance(node, ast.Call) and getattr(node.func, 'attr', None) == 'load' \
                            and any(k.arg == 'allow_pickle' and getattr(k.value, 'value', False) is True
                                    for k in node.keywords):
                        offenders.append(f'{path.relative_to(REPO)}:{node.lineno} numpy load allow_pickle=True')
        self.assertEqual(offenders, [])

    def test_no_pickle_caches_tracked(self):
        tracked = subprocess.run(['git', 'ls-files'], cwd=REPO, capture_output=True, text=True)
        if tracked.returncode == 0:
            paths = tracked.stdout.splitlines()
        else:
            # An extracted checkpoint is not a git checkout; every file in it is shipped, so check them all.
            # (B15 clean-room rehearsal: a skip here made the mandatory matrix depend on hidden state.)
            paths = [str(q.relative_to(REPO)) for q in REPO.rglob('*') if q.is_file()]
        bad = [p for p in paths if p.endswith(('.pkl', '.pickle', '.joblib'))]
        self.assertEqual(bad, [])


class GI6_03_SemanticReplay(unittest.TestCase):
    """Irrelevant feature edits, renaming and answer changes cannot refresh a sealed task."""

    def setUp(self):
        from custody_reference.evaluator import canonical, file_sha
        from custody_reference.private_evidence import configure_semantics
        self.canonical, self.file_sha = canonical, file_sha
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.candidates = {}
        for arm in ('D', 'U', 'V2n', 'V2p'):
            p = self.root / f'{arm}.json'
            p.write_bytes(canonical({'expr': {'op': 'const', 'value': 0}}))
            self.candidates[arm] = p
        self.key = self.root / 'key.pem'
        self.key.write_bytes(Ed25519PrivateKey.generate().private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        self.res = self.root / 'reservations'; self.res.mkdir(mode=0o700); self.res.chmod(0o700)
        configure_semantics(self.res, domain='synthetic-linear-v1', required_features=['x'],
                            ignored_features=['unused'])

    def run_pool(self, name, pool, campaign):
        from custody_reference.evaluator import evaluate_frozen
        pool_path = self.root / f'{name}.json'; pool_path.write_bytes(self.canonical(pool))
        prereg = self.root / f'{name}-prereg.json'
        prereg.write_bytes(self.canonical({'protocol': 'genesis-reference-evaluator-v1',
                                           'pool_sha256': self.file_sha(pool_path),
                                           'candidate_sha256': {a: self.file_sha(p) for a, p in self.candidates.items()},
                                           'evaluation_budget_per_arm': len(pool), 'campaign_id': campaign}))
        return evaluate_frozen(pool_path, self.candidates, prereg, self.key, self.root / f'{name}-out',
                               custodian_id='local-reference', reservation_dir=self.res)

    def test_irrelevant_feature_and_answer_changes_cannot_rerun(self):
        self.run_pool('first', [{'id': 'a', 'features': {'x': 2}, 'answer': 4}], 'c1')
        disguised = [{'id': 'renamed', 'features': {'x': 2, 'unused': 999}, 'answer': 5}]
        with self.assertRaisesRegex(FileExistsError, 'already reserved'):
            self.run_pool('second', disguised, 'c2')


class GI6_08_LegacyScorer(unittest.TestCase):
    def test_forged_size_and_negative_cost_rejected(self):
        sys.path.insert(0, str(REPO / 'legacy_batch42'))
        try:
            from c4_resource_benchmark import measure
        finally:
            sys.path.remove(str(REPO / 'legacy_batch42'))
        host = [(0, 1), (1, 2), (2, 3), (0, 3)]
        forged = lambda n, h, seed, budget: {'selected': [], 'size': 9, 'queries': 5}
        with self.assertRaises(RuntimeError):
            measure(forged, 4, host, seed=1, budget=60)
        negative = lambda n, h, seed, budget: {'selected': [(0, 1)], 'size': 1, 'queries': -1}
        with self.assertRaises(RuntimeError):
            measure(negative, 4, host, seed=1, budget=60)

    def test_legacy_routes_cannot_feed_promotion(self):
        for route in ('legacy_batch42.c4_resource_benchmark', 'gap_engine.adapters.induction',
                      'custody_reference.evaluator', 'genesis.campaign', 'genesis.ladder', 'something.new'):
            self.assertFalse(route_status(route)[0], route)
        self.assertTrue(route_status('genesis.custodian.evaluate')[0])
        ok, reason = eligible_for_confirmation(
            'genesis.custodian.evaluate', 'fb81f1f00e2044a9c77e958c382f8bcdf4af44fb9e4f37050f5a1571732d43b8')
        self.assertFalse(ok)
        self.assertIn('revoked', reason)


if __name__ == '__main__':
    unittest.main()
