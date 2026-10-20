"""B20_R95 (design): the configuration race for tfxw-v1 on large hosts. Seeds are fresh, the 64 configurations are
valid with the two disclosed entrants last, the cells and the halving schedule are what the docstring says, the score is
the Evaluation's anytime score against the target, and earlier large-domain hosts are excluded."""
import importlib.util
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / f'{name}.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


R95 = load('b20r95_configure_tfxw')


def earlier_seeds():
    seen = set()
    for p in (ROOT / 'scripts').glob('*.py'):
        if p.name.startswith('b20r95'):
            continue
        seen |= {int(x) for x in re.findall(r'\b(2026\d{4})\b', p.read_text())}
    return seen


class Design(unittest.TestCase):
    def test_fresh_seeds(self):
        seeds = {R95.HOST_SEED + i for i in range(len(R95.CELLS))} | {R95.CONFIG_SEED}
        self.assertFalse(seeds & earlier_seeds())

    def test_configurations(self):
        from genesis.candidate_kinds import tfxw as TW
        cs = R95.configurations()
        self.assertEqual(len(cs), 64)
        self.assertEqual(cs[62], R95.r89_config())
        self.assertEqual(cs[62]['kpick'], 1)
        self.assertEqual(cs[63], TW.DEFAULT)
        self.assertTrue(all(TW.check_config(c) is None for c in cs))
        self.assertEqual(len({json.dumps(c, sort_keys=True) for c in cs}), 64)

    def test_cells_schedule_and_score(self):
        self.assertEqual([(f, p['n']) for f, p in R95.CELLS],
                         [('planted_cluster', 128), ('erdos', 128), ('planted_cluster', 256), ('erdos', 256)])
        self.assertEqual(R95.ROUNDS, ((4, 1, 16), (8, 1, 8), (16, 2, 4), (16, 3, 4)))
        self.assertEqual(R95.BUDGETS, (1.0, 5.0))
        from genesis.models_large import LargeGraphTask
        t = LargeGraphTask(task_id='x', n=4, edges=((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)), family='f')
        self.assertEqual(R95.score(t, 4, 4), 1.0)                 # (6 - 4 + 1) / (6 - 4 + 1)
        self.assertAlmostEqual(R95.score(t, 4, 3), 3 / 4)
        self.assertGreater(R95.score(t, 3, 4), 1.0)               # beating the target scores above 1

    def test_earlier_large_hosts_are_excluded(self):
        from genesis import domains as DM
        a = DM.adapter(R95.LARGE)
        tasks, seen, _ = a.generate(5, 2, 'DEV', 'erdos', {'n': 70, 'p': 0.1})
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'evidence' / 'x').mkdir(parents=True)
            (Path(d) / 'evidence' / 'x' / 'hosts.json').write_text(json.dumps(
                {'tasks': [t.model_dump(mode='json') for t in tasks]}))
            (Path(d) / 'evidence' / 'y').mkdir()
            (Path(d) / 'evidence' / 'y' / 'hosts.json').write_text(json.dumps(
                {'tasks': [{'task_id': 's', 'domain': 'triangle_free_host_v1', 'n': 3, 'edges': [], 'family': 'f'}]}))
            self.assertEqual(R95.large_exposure(d), seen)

    def test_run_and_check(self):
        from genesis import domains as DM
        t = DM.adapter(R95.LARGE).generate(9, 1, 'DEV', 'planted_cluster', {'n': 100, 'p_in': 0.8, 'p_out': 0.06})[0][0]
        v = R95.run_tfxw(t, R95.r89_config(), 0.2, 1)
        self.assertGreater(v, len(t.edges) // 2)
        missing = next((u, v) for u in range(t.n) for v in range(u + 1, t.n) if (u, v) not in set(t.edges))
        with self.assertRaises(RuntimeError):
            R95.check(t, [missing])                               # an edge outside the host
        nb = {}
        for u, v in t.edges:
            nb.setdefault(u, set()).add(v)
        tri = next((u, v, w) for u, v in t.edges for w in nb.get(v, ()) if w in nb.get(u, ()))
        with self.assertRaises(RuntimeError):
            R95.check(t, [(tri[0], tri[1]), (tri[1], tri[2]), (tri[0], tri[2])])


if __name__ == '__main__':
    unittest.main()
