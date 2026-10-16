"""B20_R37: generator v2 (patterns on up to seven vertices). The generator keeps the expected
patterns, its ex(F) values are exact, the symmetry-breaking copy enumeration finds exactly the
copies of v1's enumeration, every rounding certificate is exactly valid, and a recipe's heartbeat
option is hoisted before the theorem. The Lean side runs in tests_formal and the study evidence."""
import itertools
from fractions import Fraction
import random
import unittest

from genesis.formal_research import search as S
from genesis.invention import cuts as C1
from genesis.invention import cuts_v2 as C2
from genesis.models import GraphTask


def host(n, edges):
    return GraphTask(task_id='t-v2', domain='triangle_free_host_v1', family='test', split='DEV', n=n,
                     edges=tuple(sorted(tuple(sorted(e)) for e in edges)))


class Generator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stats = {}
        cls.pats = C2.generate(stats=cls.stats)

    def test_keeps_v1_patterns_first_then_seven_vertex_ones(self):
        v1 = C1.generate()
        self.assertEqual([p['edges'] for p in self.pats[:2]], [p['edges'] for p in v1])
        self.assertEqual(len(self.pats), 9)
        self.assertEqual([p['vertices'] for p in self.pats[2:]], [7] * 7)
        k7 = self.pats[-1]
        self.assertEqual((len(k7['edges']), k7['ex']), (21, 12))       # Turán: K_{3,4}

    def test_ex_values_are_exact(self):
        for p in self.pats:
            if len(p['edges']) <= 16:
                self.assertEqual(p['ex'], C1.extremal(p['edges']))
            self.assertTrue(C1._tf(p['ex_witness']) and len(p['ex_witness']) == p['ex'])

    def test_every_rounding_certificate_is_exact(self):
        for i, p in enumerate(self.pats):
            cert = C2.proof_certificate(p, self.pats[:i])
            self.assertIsNotNone(cert)
            cover = {tuple(e): 0 for e in p['edges']}
            K = 0
            for kind, qid, verts, mult, rhs in cert['rows']:
                if kind == 'triangle':
                    edges = [tuple(sorted(x)) for x in itertools.combinations(verts, 2)]
                else:
                    q = next(x for x in self.pats if x['id'] == qid)
                    edges = [tuple(sorted((verts[a], verts[b]))) for a, b in q['edges']]
                    self.assertEqual(rhs, q['ex'])
                for e in edges:
                    cover[e] += mult
                K += mult * rhs
            for e, s in cert['slack'].items():
                cover[tuple(e)] += s
                K += s
            self.assertTrue(all(c >= cert['D'] for c in cover.values()))
            self.assertEqual((K, K // cert['D']), (cert['K'], p['ex']))


class Copies(unittest.TestCase):
    def test_fast_enumeration_finds_the_same_copies(self):
        pats = C2.generate()
        rng = random.Random(3701)
        for _ in range(4):
            n = 12
            t = host(n, [e for e in itertools.combinations(range(n), 2) if rng.random() < 0.6])
            for p in pats:
                if len(p['edges']) < 20:
                    self.assertEqual(set(C1.copies(t, p)[0]), set(C2.copies_fast(t, p)[0]), p['id'])
        k8 = host(8, itertools.combinations(range(8), 2))
        self.assertEqual(len(C2.copies_fast(k8, pats[-1])[0]), 8)               # C(8, 7) K7 copies
        self.assertEqual(C2.copies_fast(k8, pats[-1], limit=3), ([C2.copies_fast(k8, pats[-1])[0][i] for i in range(3)], True))


class Options(unittest.TestCase):
    def test_heartbeat_option_is_hoisted_before_the_theorem(self):
        opts, text = S.split_options('set_option maxHeartbeats 4000000 in\nintro S\nomega')
        self.assertEqual((opts, text), (['set_option maxHeartbeats 4000000 in'], 'intro S\nomega'))
        self.assertEqual(S.split_options('intro S\nomega'), ([], 'intro S\nomega'))
        self.assertEqual(S.split_options('set_option linter.all false in\nomega')[0], [])
        src = S.proof_module('PX', 'True', ['X'], ['GTDefs'], 'set_option maxHeartbeats 4000000 in\ntrivial')
        lines = src.splitlines()
        self.assertEqual(lines[lines.index('set_option maxHeartbeats 4000000 in') + 1], 'theorem proof : True := by')


if __name__ == '__main__':
    unittest.main()
