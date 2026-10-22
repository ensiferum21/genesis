"""B20_R83-R86: generations of the program search and the test of compounding. Design: fresh seeds; the three
searches' configuration (libraries, hosts, output places); refusals without earlier generations; the labels and the
headline; the analysis on synthetic rows; arms with stand-in programs; pinning."""
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r83_generation_search as G  # noqa: E402
import b20r86_generations_eval as M  # noqa: E402

GEN1_STAND_IN = {'rep': 'cross_2', 'body': [['init'], ['descent']]}
LIB_STAND_IN = {'rep': 'cross_2', 'body': [['macro', 0], ['sweep', 'drop', 'improve']], 'library': [[['init'], ['descent']]]}


def synth(target, succ, cpu=0.6e9):
    runs = {a: {str(t): [{'value': target if i < succ.get(a, {}).get(t, 0) else target - 1, 'run': 'SUCCESS',
                          'cpu_ns': int(cpu), 'isolation': 'OCI_RUNC_NO_NETWORK_RO_ROOT_SECCOMP'} for i in range(3)]
                for t in M.LADDER} for a in M.ARMS}
    return {'n': 63, 'edges': 460, 'target': target, 'target_certified': True, 'runs': runs,
            'exact': {'cpsat': {'status': 'SUCCESS', 'value': target - 1, 'claims_optimal': False}},
            'reference': {'wall_s': 30.0}, 'cpu_ns': {a: {str(t): int(cpu) for t in M.LADDER} for a in M.ARMS}}


class Design(unittest.TestCase):
    def test_seeds_are_fresh(self):
        own = {'b20r83_generation_search.py': [c[k] for c in G.STUDIES.values() for k in ('host_seed', 'search_seed')
                                               if c[k] is not None],
               'b20r86_generations_eval.py': [M.SEED, M.BOOT_SEED]}
        self.assertEqual(len(own['b20r83_generation_search.py']), 5)
        for path in (ROOT / 'scripts').glob('*.py'):
            for name, seeds in own.items():
                if path.name != name:
                    for s in seeds:
                        self.assertIsNone(re.search(rf'\b{s}\b', path.read_text()), (path.name, s))

    def test_configuration(self):
        self.assertEqual([len(G.STUDIES[s]['library']) for s in ('b20r83', 'b20r84', 'b20r85')], [1, 0, 2])
        self.assertEqual(G.STUDIES['b20r84']['hosts_from'], G.STUDIES['b20r83']['out'] / 'hosts.json')
        self.assertEqual(G.STUDIES['b20r85']['library'], (G.GEN1, G.GEN2))
        self.assertEqual(G.GEN2, G.STUDIES['b20r83']['out'] / 'program.json')
        self.assertEqual(M.SOURCES['gen2'], G.GEN2)
        self.assertEqual(M.SOURCES['control'], G.STUDIES['b20r84']['out'] / 'program.json')
        self.assertEqual(M.SOURCES['gen3'], G.STUDIES['b20r85']['out'] / 'program.json')
        self.assertEqual((G.SEARCH_S, G.PER_N, G.N), (6000.0, 16, 63))

    def test_refusals(self):
        with self.assertRaises(SystemExit):
            G.main(['b20r99', 'x'])
        with self.assertRaises(SystemExit):
            G.main(['b20r83', str(ROOT / 'evidence' / 'elsewhere')])
        if not G.GEN2.exists():
            with self.assertRaises(SystemExit):
                G.library_for('b20r85')
        if not all(p.exists() for p in M.SOURCES.values()):
            with self.assertRaises(SystemExit):
                M.programs()

    def test_labels_and_headline(self):
        def p(v1, v2):
            return {'q0.5': {'verdict': v1}, 'q0.75': {'verdict': v2}}
        self.assertEqual(M.change(p('A_FASTER', 'UNRESOLVED')), 'IMPROVES')
        self.assertEqual(M.change(p('COMPARABLE', 'B_FASTER')), 'WORSENS')
        self.assertEqual(M.change(p('COMPARABLE', 'COMPARABLE')), 'NO_DIFFERENCE')
        self.assertEqual(M.change(p('A_FASTER', 'B_FASTER')), 'UNRESOLVED')
        self.assertEqual(M.change(p('A_FASTER', 'A_FASTER'), 'LIBRARY_HELPS', 'LIBRARY_HURTS'), 'LIBRARY_HELPS')
        self.assertEqual(M.headline('IMPROVES', 'IMPROVES', 'LIBRARY_HELPS'), 'COMPOUNDS')
        self.assertEqual(M.headline('IMPROVES', 'IMPROVES', 'UNRESOLVED'), 'PARTIAL')
        self.assertEqual(M.headline('IMPROVES', 'NO_DIFFERENCE', 'LIBRARY_HELPS'), 'PARTIAL')
        self.assertEqual(M.headline('IMPROVES', 'WORSENS', 'LIBRARY_HELPS'), 'NO_COMPOUNDING')
        self.assertEqual(M.headline('NO_DIFFERENCE', 'UNRESOLVED', 'LIBRARY_HELPS'), 'NO_COMPOUNDING')

    def test_analysis_on_synthetic_rows(self):
        # gen1 at 2 s, gen2 at 0.25 s, gen3 at 0.05 s, control at 2 s, engine at 0.25 s, on every host
        rows = [synth(300, {'gen1': {2.0: 3}, 'gen2': {0.25: 3}, 'gen3': {0.05: 3}, 'control': {2.0: 3},
                            'engine': {0.25: 3}}) for _ in range(M.PER_N)]
        a = M.analyse(rows)
        self.assertEqual(a['labels'], {'transition_1_2': 'IMPROVES', 'transition_2_3': 'IMPROVES',
                                       'library_effect': 'LIBRARY_HELPS', 'headline': 'COMPOUNDS'})
        self.assertEqual(a['vs_engine']['gen3']['q0.5']['verdict'], 'A_FASTER')
        self.assertIsNone(M.validity(rows)[0])

    def test_arms_with_stand_in_programs(self):
        progs = {'gen1': (GEN1_STAND_IN, 'a'), 'gen2': (LIB_STAND_IN, 'b'), 'gen3': (LIB_STAND_IN, 'c'),
                 'control': (dict(LIB_STAND_IN, body=[['init'], ['descent']], library=[]), 'd')}
        D = M.arm_descriptors(progs)
        self.assertEqual(len(D), len(M.ARMS) * len(M.LADDER))
        self.assertEqual(D[('gen1', 0.5)][1]['kind'], 'solver-program-v1')
        self.assertEqual({D[(a, 0.5)][1]['kind'] for a in ('gen2', 'gen3', 'control')}, {'solver-library-v1'})
        self.assertEqual(D[('engine', 0.5)][1]['kind'], 'hybrid-swap-v1')

    def test_pinned(self):
        for name in ('b20r83_generation_search.py', 'b20r86_generations_eval.py'):
            self.assertIn('R33.pinned_core()', (ROOT / 'scripts' / name).read_text())


class RecordB20R83(unittest.TestCase):
    """B20_R83's outputs: the frozen generation-2 program and its history."""

    @classmethod
    def setUpClass(cls):
        import json
        d = G.STUDIES['b20r83']['out']
        cls.s = json.loads((d / 'summary.json').read_text())
        cls.frozen = json.loads((d / 'program.json').read_text())
        cls.hist = [json.loads(l) for l in (d / 'history.jsonl').read_text().splitlines() if l.strip()]

    def test_the_frozen_program(self):
        import json
        from genesis import candidates_v2 as C2
        from genesis.candidate_kinds import solver_program as KP
        from genesis.invention import solver_library as SL
        prog = self.frozen['program']
        self.assertEqual(SL.problems(prog, KP.licensed_reps('triangle_free_host_v1')), [])
        gen1 = json.loads(G.GEN1.read_text())['program']
        self.assertEqual(prog['library'], [SL.as_library_entry(gen1)])
        self.assertEqual(self.frozen['macros_used'], [0])
        self.assertEqual(C2.descriptor_problems(self.frozen['descriptor_at_0.5s'], domain='triangle_free_host_v1'), [])
        best = max(self.s['search']['finalists'], key=lambda f: (f['final_mean'], -f['size']))
        self.assertEqual((best['body'], best['rep'], best['final_mean']), (prog['body'], prog['rep'], 291.5938))

    def test_the_history(self):
        self.assertEqual(len(self.hist), self.s['search']['evaluations'])
        self.assertTrue(all(h['round'] == 0 for h in self.hist[:16]))
        self.assertEqual(self.s['search']['macro_use_in_final_population'], 16)


class RecordB20R84(unittest.TestCase):
    def test_the_frozen_control_has_no_library_and_used_b20r83_s_hosts(self):
        import json
        from genesis.candidate_kinds import solver_program as KP
        from genesis.invention import solver_library as SL
        d = G.STUDIES['b20r84']['out']
        frozen = json.loads((d / 'program.json').read_text())
        s = json.loads((d / 'summary.json').read_text())
        self.assertEqual(frozen['program']['library'], [])
        self.assertEqual(SL.problems(frozen['program'], KP.licensed_reps('triangle_free_host_v1')), [])
        best = max(s['search']['finalists'], key=lambda f: (f['final_mean'], -f['size']))
        self.assertEqual((best['body'], best['final_mean']), (frozen['program']['body'], 291.6094))
        a = json.loads((d / 'hosts.json').read_text())['tasks']
        b = json.loads((G.STUDIES['b20r83']['out'] / 'hosts.json').read_text())['tasks']
        self.assertEqual([t['task_id'] for t in a], [t['task_id'] for t in b])


class RecordB20R85(unittest.TestCase):
    """B20_R85's outputs: the frozen generation-3 program (library: generations 1 and 2) and its history."""

    @classmethod
    def setUpClass(cls):
        import json
        d = G.STUDIES['b20r85']['out']
        cls.s = json.loads((d / 'summary.json').read_text())
        cls.frozen = json.loads((d / 'program.json').read_text())
        cls.hist = [json.loads(l) for l in (d / 'history.jsonl').read_text().splitlines() if l.strip()]

    def test_the_frozen_program(self):
        import json
        from genesis import candidates_v2 as C2
        from genesis.candidate_kinds import solver_program as KP
        from genesis.invention import solver_library as SL
        prog = self.frozen['program']
        self.assertEqual(SL.problems(prog, KP.licensed_reps('triangle_free_host_v1')), [])
        gen1 = json.loads(G.GEN1.read_text())['program']
        gen2 = json.loads(G.GEN2.read_text())['program']
        self.assertEqual(prog['library'], [SL.as_library_entry(gen1), SL.as_library_entry(gen2)])
        self.assertEqual(self.frozen['macros_used'], [0, 1])
        self.assertEqual(C2.descriptor_problems(self.frozen['descriptor_at_0.5s'], domain='triangle_free_host_v1'), [])
        best = max(self.s['search']['finalists'], key=lambda f: (f['final_mean'], -f['size']))
        self.assertEqual((best['body'], best['rep'], best['final_mean']), (prog['body'], prog['rep'], 290.0))

    def test_the_history_and_the_hosts(self):
        import json
        self.assertEqual(len(self.hist), self.s['search']['evaluations'])
        self.assertTrue(all(h['round'] == 0 for h in self.hist[:16]))
        self.assertEqual(self.s['search']['macro_use_in_final_population'], 16)
        self.assertEqual(self.s['seeds'], {'hosts': 20268501, 'search': 20268502})
        a = json.loads((G.STUDIES['b20r85']['out'] / 'hosts.json').read_text())['tasks']
        others = [json.loads((G.STUDIES[k]['out'] / 'hosts.json').read_text())['tasks'] for k in ('b20r83', 'b20r84')]
        self.assertEqual(len(a), 16)
        self.assertFalse({t['task_id'] for t in a} & {t['task_id'] for o in others for t in o})


if __name__ == '__main__':
    unittest.main()
