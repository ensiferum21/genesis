"""B20_R79: the program-search study. Design: fresh seeds, the fixed constants, the search budget fits a 2-hour
run, no hand-written program anywhere in the study, the study is pinned and not resumable."""
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r79_program_search as M  # noqa: E402
from genesis.invention import solver_search as SS  # noqa: E402


class Design(unittest.TestCase):
    def test_seeds_are_fresh(self):
        for path in (ROOT / 'scripts').glob('*.py'):
            if path.name == 'b20r79_program_search.py':
                continue
            text = path.read_text()
            for s in (M.SEED, M.SEARCH_SEED):
                self.assertIsNone(re.search(rf'\b{s}\b', text), (path.name, s))

    def test_constants(self):
        self.assertEqual((M.PER_N, M.N, M.SEARCH_S), (16, 63, 6000.0))
        self.assertEqual((SS.POP, SS.CHILDREN, SS.LEADERS, SS.TOURNAMENT, SS.P_CROSS, SS.BUDGET),
                         (16, 8, 2, 3, 0.25, 0.25))
        self.assertEqual((SS.FINALISTS, SS.FINAL_BUDGETS, SS.FINAL_SEEDS), (4, (0.25, 1.0), 2))
        final = SS.FINALISTS * sum(SS.FINAL_BUDGETS) * SS.FINAL_SEEDS * M.PER_N   # 160 CPU s of final runs
        self.assertLess(M.SEARCH_S + final + 300, 7200)          # fits one 2-hour background run

    def test_no_hand_written_program_reaches_the_search(self):
        text = (ROOT / 'scripts' / 'b20r79_program_search.py').read_text()
        code = text.split('"""', 2)[2]
        for word in ("'body'", '"body"', "'descent'", "'sweep'", "'force'", "'drop'"):
            self.assertNotIn(word, code)
        self.assertIn('SS.search(tasks, reps, rep_by_id, SEARCH_S, SEARCH_SEED', code)

    def test_pinned_and_not_resumable(self):
        text = (ROOT / 'scripts' / 'b20r79_program_search.py').read_text()
        self.assertIn('R33.pinned_core()', text)
        self.assertIn('not resumable', text)


EV = ROOT / 'evidence' / 'program_search_b20r79'


class Record(unittest.TestCase):
    """B20_R79's outputs: the frozen program, its descriptor, the history and the anatomy."""

    @classmethod
    def setUpClass(cls):
        import json
        cls.s = json.loads((EV / 'search_summary.json').read_text())
        cls.frozen = json.loads((EV / 'discovered_program.json').read_text())
        cls.hist = [json.loads(l) for l in (EV / 'history.jsonl').read_text().splitlines() if l.strip()]

    def test_the_frozen_program(self):
        from genesis import candidates_v2 as C2
        from genesis.candidate_kinds import solver_program as KP
        from genesis.invention import solver_programs as SP
        prog = self.frozen['program']
        self.assertEqual(prog, self.s['program'])
        self.assertEqual(SP.problems(prog, KP.licensed_reps('triangle_free_host_v1')), [])
        d = self.frozen['descriptor_at_0.5s']
        self.assertEqual(C2.descriptor_problems(d, domain='triangle_free_host_v1'), [])
        self.assertEqual(d['parameters'], {'program': prog, 'cpu_seconds': 0.5})
        best = max(self.s['finalists'], key=lambda f: (f['final_mean'], -f['size']))
        self.assertEqual(best['program'], prog)
        self.assertEqual((best['final_mean'], SP.size(prog)), (287.3438, 10))

    def test_the_history(self):
        import json
        self.assertEqual(len(self.hist), self.s['search']['evaluations'])
        self.assertEqual(len({json.dumps(h['program'], sort_keys=True) for h in self.hist}),
                         self.s['search']['distinct_programs'])
        self.assertTrue(all(h['round'] == 0 for h in self.hist[:SS.POP]))
        self.assertEqual(round(sum(h['mean'] for h in self.hist[:SS.POP]) / SS.POP, 4),
                         self.s['initial_population_mean_fitness'])
        self.assertTrue(all(len(h['values']) == M.PER_N for h in self.hist))

    def test_the_anatomy(self):
        a = SS.anatomy(self.frozen['program'])
        self.assertEqual(a, self.s['anatomy'])
        self.assertEqual((a['swap_like'], a['kick'], a['cut_search'], a['phases'], a['restarts']),
                         (True, False, True, True, False))
        share = sum(SS.anatomy(h['program'])['swap_like'] for h in self.hist[-300:]) / 300
        self.assertGreater(share, 0.9)

    def test_hosts_are_fresh_and_in_the_addenda(self):
        import json
        import b20r23_e1b_readiness as RD
        from genesis.common import canonical
        from genesis.models import GraphTask
        tasks = [GraphTask.model_validate_json(canonical(t)) for t in json.loads((EV / 'hosts.json').read_text())['tasks']]
        self.assertEqual(len(RD.identities(tasks)), M.PER_N)
        for pkg in ('e1', 'e1b'):
            add = json.loads((ROOT / 'handoff' / pkg / 'exposure_hosts_addendum_b20r79.json').read_text())
            self.assertTrue(RD.identities(tasks) <= RD.identities([GraphTask.model_validate_json(canonical(t))
                                                                    for t in add]))


if __name__ == '__main__':
    unittest.main()
