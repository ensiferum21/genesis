"""Lean checker canaries (spec §37): positive, negative and adversarial proofs.

Prescreen-bypass tests patch the prescreen away to prove that the deeper layers
(type check against the trusted spec, axiom audit, stage isolation) still hold.
"""
from itertools import combinations
import unittest
from unittest import mock

from genesis.models import GraphTask
from genesis import sandbox
from genesis.verification import lean
from genesis.verification.tools import available

READY = available('lean') and sandbox.available()
K4 = GraphTask(task_id='k4', n=4, edges=tuple(combinations(range(4), 2)), family='complete')
GOOD = [(0, 1), (0, 2), (0, 3), (1, 2)]


def proof(body):
    return f'import GenesisSpec\nnamespace GenesisProof\n{body}\nend GenesisProof\n'.encode()


def false_spec():
    """A spec whose Statement is false (the witness contains a 4-cycle); built without the guard."""
    spec, meta = lean.witness_spec(K4, GOOD)
    text = spec.decode().replace('def witness : List (Nat × Nat) := [(0, 1), (0, 2), (0, 3), (1, 2)]',
                                 'def witness : List (Nat × Nat) := [(0, 1), (0, 2), (1, 3), (2, 3)]')
    return text.encode()


@unittest.skipUnless(READY, 'pinned Lean toolchain or sandbox unavailable')
class Canaries(unittest.TestCase):
    def test_positive_canary_checks_with_no_axioms(self):
        r = lean.check_witness_formally(K4, GOOD)
        self.assertEqual(r['status'], 'CHECKED', r.get('logs'))
        self.assertEqual(r['axioms'], [])
        self.assertEqual(set(r['stages']), {'spec', 'proof', 'check'})
        self.assertIn('lean_sha256', r['environment'])

    def test_triangle_domain_witness_checks(self):
        task = GraphTask(task_id='k5t', domain='triangle_free_host_v1', n=5, edges=tuple(combinations(range(5), 2)),
                         family='complete')
        self.assertEqual(lean.check_witness_formally(task, [(0, 2), (0, 3), (1, 2), (1, 3), (0, 4), (1, 4)])['status'],
                         'CHECKED')

    def test_false_statement_cannot_be_proved_by_decide(self):
        r = lean.check(false_spec(), lean.default_proof())
        self.assertEqual(r['status'], 'ELABORATION_ERROR', r.get('logs'))

    def test_proof_of_a_different_statement_is_a_mismatch(self):
        spec, _ = lean.witness_spec(K4, GOOD)
        r = lean.check(spec, proof('theorem proof : True := trivial'))
        self.assertEqual(r['status'], 'STATEMENT_MISMATCH', r.get('logs'))

    def test_invalid_witness_never_reaches_lean(self):
        with self.assertRaises(ValueError):
            lean.witness_spec(K4, [(0, 1), (1, 2), (2, 3), (0, 3)])

    def test_prescreen_blocks_known_escape_hatches(self):
        spec, _ = lean.witness_spec(K4, GOOD)
        for body, fragment in [('theorem proof : GenesisSpec.Statement := sorry', 'sorry'),
                               ('axiom cheat : GenesisSpec.Statement\ntheorem proof : GenesisSpec.Statement := cheat',
                                'axiom'),
                               ('theorem proof : GenesisSpec.Statement := by\n  unfold GenesisSpec.Statement\n'
                                '  native_decide', 'native_decide'),
                               ('#eval IO.FS.writeFile "/work/out/x" "y"\ntheorem proof : True := trivial', '#eval'),
                               ('set_option debug.skipKernelTC true\ntheorem proof : True := trivial', 'skipKernelTC'),
                               ('initialize foo : Nat ← pure 1\ntheorem proof : True := trivial', 'initialize')]:
            r = lean.check(spec, proof(body))
            self.assertEqual(r['status'], 'FORBIDDEN_CONSTRUCT', body)
            self.assertIn(fragment, r['reason'])
        r = lean.check(spec, b'import Mathlib\n' + proof('theorem proof : True := trivial'))
        self.assertEqual(r['status'], 'FORBIDDEN_CONSTRUCT')


@unittest.skipUnless(READY, 'pinned Lean toolchain or sandbox unavailable')
class DefenceInDepth(unittest.TestCase):
    """With the prescreen disabled, the axiom audit and stage isolation still hold."""

    def setUp(self):
        patcher = mock.patch.object(lean, 'prescreen', return_value=None)
        patcher.start(); self.addCleanup(patcher.stop)
        self.spec, _ = lean.witness_spec(K4, GOOD)

    def test_native_decide_is_caught_by_the_axiom_audit(self):
        r = lean.check(self.spec, proof('theorem proof : GenesisSpec.Statement := by\n'
                                        '  unfold GenesisSpec.Statement\n  native_decide'))
        self.assertEqual(r['status'], 'DISALLOWED_AXIOM', r.get('logs'))
        # Lean 4.34 records native_decide as a generated axiom (older versions: Lean.ofReduceBool).
        self.assertTrue(any('native_decide' in a or 'ofReduceBool' in a for a in r['disallowed']), r['disallowed'])

    def test_declared_axiom_is_caught_by_the_axiom_audit(self):
        r = lean.check(false_spec(), proof('axiom cheat : GenesisSpec.Statement\n'
                                           'theorem proof : GenesisSpec.Statement := cheat'))
        self.assertEqual(r['status'], 'DISALLOWED_AXIOM', r.get('logs'))
        self.assertIn('GenesisProof.cheat', r['disallowed'])

    def test_sorry_is_caught_by_the_axiom_audit(self):
        r = lean.check(false_spec(), proof('theorem proof : GenesisSpec.Statement := sorry'))
        self.assertEqual(r['status'], 'DISALLOWED_AXIOM', r.get('logs'))
        self.assertIn('sorryAx', r['disallowed'])

    def test_elaboration_time_tampering_cannot_reach_the_trusted_stages(self):
        # The untrusted proof tries to replace the compiled spec with one whose Statement is True,
        # and to forge the checker's report. Both target files that only exist in its own sandbox run.
        attack = proof(
            '#eval do\n'
            '  IO.FS.writeFile "/work/out/GenesisSpec.olean" "forged"\n'
            '  IO.FS.writeFile "/work/out/check.log" "GENESIS-x axioms []"\n'
            'theorem proof : GenesisSpec.Statement := by\n  unfold GenesisSpec.Statement\n  decide')
        r = lean.check(false_spec(), attack)
        self.assertNotEqual(r['status'], 'CHECKED', r.get('logs'))


if __name__ == '__main__':
    unittest.main()
