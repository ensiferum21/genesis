"""B20_R17 (s15.3, W10): machine-generated relational decoders.

Exact soundness agrees with exhaustive decoding; symmetry and reduction are invariances; the
generator's output is deterministic; only one generated decoder is outside the hand-written menu
at k <= 3; and the method runs it with a checker-valid witness.
"""
from itertools import combinations, permutations, product
import random
import unittest

from genesis.graphs import check_witness
from genesis.invention import relations as RL
from genesis.invention import representations as RP
from genesis.models import GraphTask

TRIANGLE = frozenset({(0, 1), (1, 2), (0, 2)})


def brute_sound(R, k):
    """No encoding of the 3-vertex host decodes a triangle (the exact counterexample shape)."""
    return all(RP.decode({'_py': lambda a, b: (a, b) in R}, dict(enumerate(c)), TRIANGLE) != TRIANGLE
               for c in product(range(k), repeat=3))


class Generator(unittest.TestCase):
    def test_exact_soundness_equals_exhaustive_decoding(self):
        for k in (2, 3):
            for R in RL.all_relations(k):
                self.assertEqual(RL.tf_sound(R, k), brute_sound(R, k), (k, sorted(R)))

    def test_sound_decoders_never_decode_a_triangle_on_random_hosts(self):
        rng = random.Random(5)
        sound = [(R, 3) for R in RL.all_relations(3) if RL.tf_sound(R, 3)]
        for _ in range(300):
            R, k = rng.choice(sound)
            n = rng.randint(3, 8)
            H = frozenset(p for p in combinations(range(n), 2) if rng.random() < 0.6)
            c = {v: rng.randrange(k) for v in range(n)}
            S = RP.decode({'_py': lambda a, b, R=R: (a, b) in R}, c, H)
            self.assertTrue(RP.DOMAINS['triangle_free_host_v1']['model'](S))

    def test_symmetry_and_reduction_are_invariances(self):
        R = frozenset({(0, 1), (1, 2), (2, 0)})
        forms = {RL.canonical(frozenset((p[x], p[y]) for x, y in R), 3) for p in permutations(range(3))}
        self.assertEqual(len(forms), 1)
        self.assertEqual(RL.reduce(frozenset({(0, 2), (2, 0)}), 3), (frozenset({(0, 1), (1, 0)}), 2))
        self.assertEqual(RL.canonical(frozenset({(1, 2)}), 3), RL.canonical(frozenset({(0, 1)}), 2))

    def test_generator_output_and_novelty_against_the_menu(self):
        out = RL.generate()
        self.assertEqual(out, RL.generate())                                  # deterministic
        self.assertEqual([(g['k'], g['relation'], g['equals_menu']) for g in out], [
            (2, [[0, 1], [1, 0]], 'adjacent_2 = cross_2'),
            (3, [[0, 1], [0, 2], [1, 0], [2, 0]], 'adjacent_3'),
            (3, [[0, 1], [1, 2], [2, 0]], None)])
        with self.assertRaises(ValueError):
            RL.generate(max_k=4)                                              # the grammar bound is not lifted

    def test_v2_merges_twins_and_lifts_the_bound_by_version_only(self):
        rng = random.Random(4)
        star = frozenset({(0, 1), (0, 2), (0, 3), (1, 0), (2, 0), (3, 0)})       # cross_2 with class 1 split three ways
        self.assertEqual(RL.merge_twins(star, 4), (frozenset({(0, 1), (1, 0)}), 2))
        merge = {0: 0, 1: 1, 2: 1, 3: 1}
        for _ in range(50):                                                   # same decoded sets after merging
            n = rng.randint(4, 9)
            H = frozenset(p for p in combinations(range(n), 2) if rng.random() < 0.5)
            c = {v: rng.randrange(4) for v in range(n)}
            split = RP.decode({'_py': lambda a, b: (a, b) in star}, c, H)
            merged = RP.decode({'_py': lambda a, b: (a, b) in {(0, 1), (1, 0)}}, {v: merge[x] for v, x in c.items()}, H)
            self.assertEqual(split, merged)
        out = RL.generate(4, 'v2')
        self.assertEqual([(g['k'], g['relation'], g['equals_menu']) for g in out], [
            (2, [[0, 1], [1, 0]], 'adjacent_2 = adjacent_3 = cross_2'),
            (3, [[0, 1], [1, 2], [2, 0]], None),
            (4, [[0, 1], [0, 2], [1, 0], [2, 3], [3, 0]], None)])
        with self.assertRaises(ValueError):
            RL.generate(5, 'v2')
        with self.assertRaises(RP.ProposalError):
            RL.proposal(4, [[0, 1]])                                          # v1 keeps k <= 3
        self.assertEqual(RL.proposal(4, [[0, 1], [0, 2], [1, 0], [2, 3], [3, 0]], 'v2')['origin'],
                         RL.VERSIONS['v2']['origin'])

    def test_proposals_are_typed_and_bounded(self):
        p = RL.proposal(3, [[0, 1], [1, 2], [2, 0]])
        self.assertEqual((p['id'], p['tf_sound_exact'], p['origin']), ('rel3_011220', True, RL.ORIGIN))
        for k, rel in ((4, [[0, 1]]), (3, []), (3, [[0, 3]]), (1, [[0, 0]])):
            with self.assertRaises(RP.ProposalError):
                RL.proposal(k, rel)
        self.assertFalse(RL.proposal(3, [[0, 1], [1, 2], [0, 2]])['tf_sound_exact'])
        src = RL.source([p])
        self.assertIn('def rel3_011220 (c : ℕ → Fin 3) (H : GT.Edges) : GT.Edges', src)
        roles = sorted(c['role'] for c in RL.conjectures([p]))
        self.assertEqual(roles, ['image', 'soundness'])
        names = [n for n, _ in RL.recipes([p])(RL.conjectures([p])[1], None)]
        self.assertEqual(names, ['class-triple-decide', 'class-triple-omega'])

    def test_the_method_runs_a_generated_decoder_with_a_valid_witness(self):
        rng = random.Random(9)
        n = 14
        edges = tuple(p for p in combinations(range(n), 2) if rng.random() < 0.45)
        p = RL.proposal(3, [[0, 1], [1, 2], [2, 0]])
        out = RP.represent_and_repair(n, edges, p, RP.tf_add_ok, cpu_seconds=0.05, seed=3)
        task = GraphTask(task_id='rl', domain='triangle_free_host_v1', n=n, edges=edges, family='t')
        self.assertEqual(check_witness(task, tuple(map(tuple, out['witness'])))['value'], out['value'])


if __name__ == '__main__':
    unittest.main()
