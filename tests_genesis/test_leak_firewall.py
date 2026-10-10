"""Leak firewall fixtures (spec §38: known exact / alpha / near duplicates must be caught)."""
from itertools import combinations
import tempfile
import unittest

from genesis.graphs import relabel
from genesis.kernel.evidence import EvidenceKernel
from genesis.kernel.leakscan import OracleScreener, SealedIndex, canonical_statement, screen, scanner_version
from genesis.kernel.memory import TheoremMemory
from genesis.models import GraphTask
from genesis.store import Store

SEALED = 'theorem sealed_target (x y : Nat) (h : x ≤ y) : x + 0 ≤ y := by omega'
ALPHA = '''/- docstring -/ @[simp]
theorem   my_own_lemma  (a b : Nat)  -- comment
   (hab : a ≤ b) : a + 0 ≤ b := by
  simp_all'''
NEAR = 'theorem near (x y : Nat) (h : x ≤ y) : x + 0 ≤ y + 0 := by omega'
SIMILAR = 'theorem tweak (x y : Nat) (h : x ≤ y) : x + 1 ≤ y + 1 := by omega'
UNRELATED = 'theorem rev_rev (l : List Nat) : l.reverse.reverse = l := by simp'


class Statements(unittest.TestCase):
    def setUp(self):
        self.index = SealedIndex(); self.index.add_statement('S1', SEALED)

    def test_exact_alpha_near_and_unrelated(self):
        self.assertEqual(screen({'kind': 'statement', 'text': SEALED}, self.index)['reason'], 'EXACT_MATCH')
        self.assertEqual(screen({'kind': 'statement', 'text': ALPHA}, self.index)['reason'], 'STRUCTURAL_MATCH')
        self.assertNotEqual(screen({'kind': 'statement', 'text': NEAR}, self.index)['decision'], 'ALLOW')
        self.assertEqual(screen({'kind': 'statement', 'text': SIMILAR}, self.index)['decision'],
                         'QUARANTINE_FOR_ADJUDICATION')
        self.assertEqual(screen({'kind': 'statement', 'text': UNRELATED}, self.index)['decision'], 'ALLOW')

    def test_canonicalization_rules(self):
        self.assertEqual(canonical_statement(SEALED), canonical_statement(ALPHA))
        self.assertIn('v0.reverse.reverse', ' '.join(canonical_statement(UNRELATED)))
        # Commutative reordering is NOT normalized without proof of equivalence.
        self.assertNotEqual(canonical_statement('theorem a (x y : Nat) : x + y = 1'),
                            canonical_statement('theorem a (x y : Nat) : y + x = 1'))

    def test_unknown_kinds_fail_closed(self):
        self.assertEqual(screen({'kind': 'binary_blob', 'text': 'x'}, self.index)['decision'], 'BLOCK')

    def test_scanner_version_is_stable_and_binds_thresholds(self):
        self.assertEqual(scanner_version(), scanner_version())
        self.assertEqual(len(self.index.digest()), 64)


class Graphs(unittest.TestCase):
    def test_relabelled_and_one_edge_neighbours(self):
        index = SealedIndex()
        host = GraphTask(task_id='s', n=7, edges=tuple(sorted(((0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (0, 6),
                                                               (1, 5)))), family='f')
        index.add_graph('G1', host.n, host.edges)
        moved = relabel(host, (3, 4, 5, 6, 0, 1, 2))
        self.assertEqual(screen({'kind': 'graph', 'n': 7, 'edges': moved.edges}, index)['reason'], 'STRUCTURAL_MATCH')
        plus = tuple(sorted(set(host.edges) | {(0, 3)}))
        self.assertEqual(screen({'kind': 'graph', 'n': 7, 'edges': plus}, index)['decision'],
                         'QUARANTINE_FOR_ADJUDICATION')
        fresh = tuple(combinations(range(5), 2))
        self.assertEqual(screen({'kind': 'graph', 'n': 5, 'edges': fresh}, index)['decision'], 'ALLOW')


class Oracle(unittest.TestCase):
    def test_research_sees_only_the_decision_and_budget_is_enforced(self):
        index = SealedIndex(); index.add_statement('S1', SEALED)
        oracle = OracleScreener(index, query_budget=2)
        answer = oracle({'kind': 'statement', 'text': SIMILAR})
        self.assertEqual(set(answer), {'decision', 'scanner_version'})
        oracle({'kind': 'statement', 'text': UNRELATED})
        self.assertEqual(oracle({'kind': 'statement', 'text': UNRELATED})['decision'], 'BLOCK')
        self.assertEqual(oracle.private_ledger()[0]['reason'], 'SIMILAR')


class TheoremMemoryRule(unittest.TestCase):
    def test_admission_and_transitive_invalidation_after_a_later_audit(self):
        with tempfile.TemporaryDirectory() as d, Store(d) as s:
            k = EvidenceKernel(s)
            mem = TheoremMemory(s, k)
            empty = OracleScreener(SealedIndex())
            r1 = mem.admit('lemma-1', 'lemma', ALPHA, parents=[], screener=empty, route='genesis.campaign',
                           source_hash='a' * 64)
            self.assertTrue(r1['visible'])
            from tests_genesis.signed_fixtures import witness_payload
            check = k.record('witness_check', witness_payload(s), parents=[r1['node']], route='genesis.campaign',
                             source_hash='a' * 64, verdict='VALID')
            from tests_genesis.signed_fixtures import math_claim
            math_claim(k, 'c', [check])
            k.promote('c', 'math', 'WITNESS_VALID')
            # A new sealed panel is built later and contains the same theorem.
            later = SealedIndex(); later.add_statement('S-new', SEALED)
            revoked = mem.audit(OracleScreener(later), {'lemma-1': ALPHA}, auditor='leak-audit')
            self.assertEqual(revoked, ['lemma-1'])
            self.assertEqual(mem.visible(), {})
            self.assertTrue(k.levels('c')['invalidated'])
            s.verify()

    def test_blocked_and_quarantined_items_never_become_visible(self):
        with tempfile.TemporaryDirectory() as d, Store(d) as s:
            mem = TheoremMemory(s, EvidenceKernel(s))
            index = SealedIndex(); index.add_statement('S1', SEALED)
            oracle = OracleScreener(index)
            for item, text in (('a', SEALED), ('b', SIMILAR)):
                self.assertFalse(mem.admit(item, 'lemma', text, parents=[], screener=oracle,
                                           route='genesis.campaign', source_hash='a' * 64)['visible'])
            self.assertEqual(mem.visible(), {})


class Elaborated(unittest.TestCase):
    def test_lean_elaborated_layer_catches_forall_vs_binder_forms(self):
        from genesis.verification.tools import available
        from genesis import sandbox
        if not (available('lean') and sandbox.available()):
            self.skipTest('pinned Lean or sandbox unavailable')
        from genesis.verification.lean import elaborated_fingerprints
        forall = 'theorem bar : ∀ p q : Nat, p ≤ q → p + 0 ≤ q := by intro p q h; omega'
        sealed_fp = elaborated_fingerprints([SEALED])          # evaluator-side run
        cand_fp = elaborated_fingerprints([forall, SIMILAR])   # separate candidate run
        index = SealedIndex(); index.add_statement('S1', SEALED, sealed_fp.get(0))
        self.assertEqual(screen({'kind': 'statement', 'text': forall}, index)['decision'], 'ALLOW')  # text misses it
        self.assertEqual(screen({'kind': 'statement', 'text': forall}, index, cand_fp.get(0))['reason'],
                         'ELABORATED_MATCH')
        self.assertNotEqual(cand_fp.get(1), sealed_fp.get(0))


if __name__ == '__main__':
    unittest.main()
