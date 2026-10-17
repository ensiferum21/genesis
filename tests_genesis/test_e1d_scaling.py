"""B20_R64: does E1d's advantage over HiGHS grow with host size? Design: fresh seeds, the arms (B20_R63's, a
subset), the settings, and the verdict rule.

Record (B20_R64): ADVANTAGE_GROWS on the re-run (crossover 8 s at n40, 32 s at n50, none within 64x at n60).
Run 1 is invalid by the criterion stated before the re-run (RERUN_NOTE.md): HiGHS must receive at least 0.9 of its
CPU budget (median, per arm and n, over hosts where it ran to its limit)."""
from pathlib import Path
import json
import re
import statistics
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r63_e1d_crossover as R63  # noqa: E402
import b20r64_e1d_scaling as M  # noqa: E402


class Design(unittest.TestCase):
    def test_seeds_are_fresh(self):
        for path in (ROOT / 'scripts').glob('*.py'):
            if path.name == 'b20r64_e1d_scaling.py':
                continue
            for s in (M.SEED, M.BOOT_SEED):
                self.assertIsNone(re.search(rf'\b{s}\b', path.read_text()), (path.name, s))

    def test_arms_are_r63s(self):
        A, B = M.arms(), R63.arms()
        self.assertEqual(list(A), ['candidate', 'highs_2s', 'highs_8s', 'highs_32s'])
        for n, (reg, d) in A.items():
            self.assertEqual(d['descriptor_id'], B[n][1]['descriptor_id'])

    def test_settings(self):
        self.assertEqual(M.NS, (40, 50, 60))
        self.assertEqual(M.PARAMS, {'p_in': 0.8, 'p_out': 0.06})
        self.assertLessEqual(max(M.NS), 63)

    def test_beyond_space_generator_matches_the_adapter_inside_the_space(self):
        from genesis.domains import ADAPTERS
        params = dict(M.PARAMS, n=40)
        a, _, _ = ADAPTERS[M.TF].generate(7, 3, 'DEV', 'planted_cluster', params, excluded=set())
        b, _ = M.generate_beyond_space(7, 3, 'DEV', params, set())
        self.assertEqual([t.model_dump() for t in a], [t.model_dump() for t in b])
        c, _ = M.generate_beyond_space(7, 2, 'DEV', dict(M.PARAMS, n=60), set())
        self.assertEqual([t.n for t in c], [60, 60])

    def test_rule(self):
        adv = lambda *vs: {R63.arm_name(b): {'verdict': v} for b, v in zip(M.BUDGETS, vs)}
        self.assertEqual(M.crossover(adv('ADVANTAGE', 'ADVANTAGE', 'ADVANTAGE')), (None, False))
        self.assertEqual(M.crossover(adv('ADVANTAGE', 'UNRESOLVED', 'ADVANTAGE')), (8.0, False))
        self.assertEqual(M.crossover(adv('UNRESOLVED_FAILURES', 'ADVANTAGE', 'ADVANTAGE')), (2.0, True))
        o = lambda c40, c60: M.overall({40: (c40, False), 50: (None, False), 60: (c60, False)})
        self.assertEqual(o(8.0, None), 'ADVANTAGE_GROWS')
        self.assertEqual(o(8.0, 32.0), 'ADVANTAGE_GROWS')
        self.assertEqual(o(8.0, 8.0), 'UNCHANGED')
        self.assertEqual(o(None, None), 'UNCHANGED')
        self.assertEqual(o(8.0, 2.0), 'ADVANTAGE_SHRINKS')
        self.assertEqual(o(None, 32.0), 'ADVANTAGE_SHRINKS')
        self.assertEqual(M.overall({40: (8.0, True), 60: (None, False)}), 'UNRESOLVED_FAILURES')



EV = ROOT / 'evidence' / 'e1d_scaling_b20r64'


def _rows(path):
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def cpu_delivery(rows):
    """{(arm, n): median CPU/budget over hosts where the arm ran to its limit (value below the best known)}."""
    out = {}
    for b in M.BUDGETS:
        a = R63.arm_name(b)
        for n in M.NS:
            ratios = [r['arms'][a]['cpu_ns'] / 1e9 / b for r in rows if r['n'] == n and r['arms'][a]['value'] <
                      max([r['optimum'] or 0] + [v['value'] for v in r['arms'].values()])]
            if ratios:
                out[(a, n)] = statistics.median(ratios)
    return out


class Record(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = json.loads((EV / 'summary.json').read_text())
        cls.rows = _rows(EV / 'rows.jsonl')
        cls.run1 = _rows(EV / 'run1_contended' / 'rows.jsonl')

    def test_verdict_recomputes_from_the_rows(self):
        self.assertEqual(len(self.rows), 30)
        v = M.verdict(self.rows)
        self.assertEqual(v['by_n'], self.s['by_n'])
        self.assertEqual(v['verdict'], self.s['verdict'])
        self.assertEqual(v['verdict'], 'ADVANTAGE_GROWS')
        self.assertEqual({n: x['crossover_budget_s'] for n, x in v['by_n'].items()}, {'40': 8.0, '50': 32.0, '60': None})
        self.assertEqual(self.s['descriptors'], {n: d['descriptor_id'] for n, (_, d) in M.arms().items()})

    def test_validity_criterion(self):
        rerun, first = cpu_delivery(self.rows), cpu_delivery(self.run1)
        self.assertTrue(rerun and all(x >= 0.9 for x in rerun.values()), rerun)
        self.assertTrue(any(x < 0.9 for x in first.values()), first)

    def test_hosts_are_the_same_and_in_the_addenda(self):
        import b20r23_e1b_readiness as RD
        from genesis.common import canonical
        from genesis.models import GraphTask
        self.assertEqual([r['task_id'] for r in self.rows], [r['task_id'] for r in self.run1])
        tasks = [GraphTask.model_validate_json(canonical(t)) for t in json.loads((EV / 'hosts.json').read_text())['tasks']]
        self.assertEqual([t.task_id for t in tasks], [r['task_id'] for r in self.rows])
        self.assertEqual(len(RD.identities(tasks)), 30)
        for pkg in ('e1', 'e1b'):
            add = json.loads((ROOT / 'handoff' / pkg / 'exposure_hosts_addendum_b20r64.json').read_text())
            self.assertTrue(RD.identities(tasks) <= RD.identities([GraphTask.model_validate_json(canonical(t))
                                                                    for t in add]))


if __name__ == '__main__':
    unittest.main()
