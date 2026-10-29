"""The Limitation Zoo's families (kernel side; `architecture/zoo.py`, 29 Oct 2026, for B20_R144): the base family is
unchanged draw for draw (four environments' digests, recorded before the families were added); the held-out families
H1 and H2 make simple graphs of their kinds with their own hidden senses, seeded apart from the base family, and
every class's incumbent is a well-formed AG with the same structure as in the base family."""
import hashlib
import json
from pathlib import Path
import statistics
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.architecture import graph as G  # noqa: E402
from genesis.architecture import zoo as Z  # noqa: E402
from genesis.senses import graph as SG  # noqa: E402

BASE = {(5, None): 'a6a002b42605d6bf2dc8ae6a208f0f3b9cfe198b556677db8f50ae0bdd4e5fe4',
        (7, 'FUSION_NEEDED'): '246e4077b49dfaee411f73cb2ace30f0ada256527fc620fbaf1c7211d8bb6f2b',
        (9, 'DECOY'): '6cb5a50cd4c58ff250fc690811ecbb734b5a71c2eee679458a4c45b869d7a1a7',
        (11, 'SEARCH_WEAK'): '754d8c3494c1d4f4f46f3a6a3d9ba712d4b88c5081485c7b5db0513f1d99e744'}


def blob(e):
    return hashlib.sha256(json.dumps({
        'cls': e.cls, 'delta': e.delta, 'ss': e.sigma_shared, 'si': e.sigma_indep, 'z': e.z_expr, 'cut': e.cut,
        'graphs': e.graphs, 'inc': e.incumbent,
        'draw': [e.draw('dev_a', i, c, 0) for i in range(3) for c in range(3)]}, sort_keys=True).encode()).hexdigest()


class Families(unittest.TestCase):
    def test_the_base_family_is_unchanged(self):
        for (idx, cls), want in BASE.items():
            self.assertEqual(blob(Z.environment(idx, 4242, cls)), want, (idx, cls))
            self.assertEqual(blob(Z.environment(idx, 4242, cls, 'base')), want)

    def test_held_out_families(self):
        self.assertEqual(Z.FAMILIES, ('base', 'H1', 'H2'))
        with self.assertRaises(ValueError):
            Z.environment(1, 4242, None, 'H9')
        kinds = {'H1': {'ws', 'ba'}, 'H2': {'pp', 'er'}}
        for fam in ('H1', 'H2'):
            seen = set()
            for idx in range(6):
                e = Z.environment(idx, 4242, None, fam)
                self.assertEqual(e.family, fam)
                for gs in e.graphs.values():
                    for g in gs:
                        seen.add(g['family'])
                        es = [(u, v) for u, v, _ in g['edges']]
                        self.assertEqual(es, sorted(set(es)))
                        self.assertTrue(all(0 <= u < v < g['n'] for u, v in es))
                        self.assertTrue(all(w in (1, -1) for _, _, w in g['edges']))
                if e.cls != 'FUSION_NEEDED':
                    self.assertIn(e.z_expr, list(Z.HIDDEN_OF[fam].values()))
                self.assertIsNone(SG.check(e.z_expr))
            self.assertEqual(seen, kinds[fam])
        a, b = Z.environment(4, 4242, 'NULL'), Z.environment(4, 4242, 'NULL', 'H1')
        self.assertNotEqual(a.seed, b.seed)
        h2 = Z.environment(2, 4242, 'SENSE_BLIND', 'H2')
        pos = [sum(w > 0 for *_, w in g['edges']) / max(1, len(g['edges'])) for g in h2.graphs['dev_a']]
        self.assertGreater(statistics.pstdev(pos), 0.1)                 # the positive share varies by graph

    def test_incumbents_are_well_formed_in_every_family(self):
        for fam in Z.FAMILIES:
            for i, cls in enumerate(Z.CLASSES):
                e = Z.environment(100 + i, 4242, cls, fam)
                self.assertEqual(G.check(e.incumbent), [], (fam, cls))
                base = Z.environment(100 + i, 4242, cls)
                self.assertEqual(sorted(e.incumbent['nodes']), sorted(base.incumbent['nodes']))
                self.assertGreater(e.oracle('sealed'), -1e-12)


if __name__ == '__main__':
    unittest.main()
