"""B20_R80 and B20_R81: the random-program control and the test of the self-found solver. Design: fresh seeds; the
control samples random programs only and chooses as the search does; the three labels and B20_R77's replication on
synthetic pairs; the analysis on synthetic rows; the study refuses to run without the two frozen programs."""
import json
from pathlib import Path
import random
import re
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r80_random_program_control as C  # noqa: E402
import b20r81_self_found_solver as M  # noqa: E402
from genesis.candidate_kinds import solver_program as KP  # noqa: E402
from genesis.invention import representations as R  # noqa: E402
from genesis.invention import solver_programs as SP  # noqa: E402
from genesis.invention import solver_search as SS  # noqa: E402
from genesis.models import GraphTask  # noqa: E402

TF = 'triangle_free_host_v1'
STAND_IN = {'rep': 'cross_2', 'body': [['init'], ['descent']]}


def synth(target, succ, cpu=0.6e9):
    runs = {a: {str(t): [{'value': target if i < succ.get(a, {}).get(t, 0) else target - 1, 'run': 'SUCCESS',
                          'cpu_ns': int(cpu), 'isolation': 'OCI_RUNC_NO_NETWORK_RO_ROOT_SECCOMP'} for i in range(3)]
                for t in M.LADDER} for a in M.ARMS}
    return {'n': 63, 'edges': 460, 'target': target, 'target_certified': True, 'runs': runs,
            'exact': {'cpsat': {'status': 'SUCCESS', 'value': target - 2, 'claims_optimal': False}},
            'reference': {'wall_s': 30.0}, 'cpu_ns': {a: {str(t): int(cpu) for t in M.LADDER} for a in M.ARMS}}


class Design(unittest.TestCase):
    def test_seeds_are_fresh(self):
        own = {'b20r80_random_program_control.py': (C.SEED,), 'b20r81_self_found_solver.py': (M.SEED, M.BOOT_SEED)}
        for path in (ROOT / 'scripts').glob('*.py'):
            for name, seeds in own.items():
                if path.name == name:
                    continue
                for s in seeds:
                    self.assertIsNone(re.search(rf'\b{s}\b', path.read_text()), (path.name, s))

    def test_the_control_samples_random_programs_and_chooses_as_the_search_does(self):
        rng = random.Random(2)
        hosts = [GraphTask(task_id=f'h{i}', domain=TF, n=12,
                           edges=tuple(sorted({tuple(sorted(rng.sample(range(12), 2))) for _ in range(35)})),
                           family='fixture', split='DEV') for i in range(2)]
        reps = KP.licensed_reps(TF)
        hist = []
        with mock.patch.object(SS, 'BUDGET', 0.02), mock.patch.object(SS, 'FINAL_BUDGETS', (0.02,)):
            best, rep = C.random_search(hosts, reps, {r['id']: r for r in R.proposals()}, 1.5, 3,
                                        log=lambda m: None, history=hist)
        self.assertEqual(SP.problems(best, reps), [])
        self.assertTrue(all(h['round'] == 0 for h in hist))                   # never re-evaluated, never mutated
        self.assertEqual(len(rep['finalists']), min(SS.FINALISTS, rep['programs']))
        self.assertEqual(C.SEARCH_S, 6000.0)
        self.assertEqual(C.TRAINING, ROOT / 'evidence' / 'program_search_b20r79' / 'hosts.json')

    def test_labels(self):
        def p(v1, v2):
            return {'q0.5': {'verdict': v1}, 'q0.75': {'verdict': v2}}
        self.assertEqual(M.label_vs_builder(p('A_FASTER', 'A_FASTER')), 'SELF_FOUND_BEATS_BUILDER')
        self.assertEqual(M.label_vs_builder(p('A_FASTER', 'B_FASTER')), 'BUILDER_BEATS_SELF_FOUND')
        self.assertEqual(M.label_vs_builder(p('COMPARABLE', 'COMPARABLE')), 'SELF_FOUND_MATCHES_BUILDER')
        self.assertEqual(M.label_vs_builder(p('COMPARABLE', 'UNRESOLVED')), 'UNRESOLVED')
        self.assertEqual(M.label_vs_random(p('A_FASTER', 'UNRESOLVED')), 'SEARCH_HELPS')
        self.assertEqual(M.label_vs_random(p('UNRESOLVED', 'B_FASTER')), 'SEARCH_HURTS')
        self.assertEqual(M.label_vs_random(p('COMPARABLE', 'COMPARABLE')), 'NO_DIFFERENCE')
        self.assertEqual(M.label_vs_random(p('A_FASTER', 'B_FASTER')), 'UNRESOLVED')
        both = {S: p('A_FASTER', 'A_FASTER') for S in M.SOTAS}
        self.assertEqual(M.label_vs_sota(both, 'SELF_FOUND'), 'SELF_FOUND_BEATS_SOTA')
        self.assertEqual(M.label_vs_sota(dict(both, cpsat=p('A_FASTER', 'B_FASTER')), 'X'), 'SOTA_BEATS_X')
        self.assertEqual(M.label_vs_sota(dict(both, burer=p('UNRESOLVED', 'A_FASTER')), 'X'), 'MIXED')

    def test_analysis_on_synthetic_rows(self):
        # found = engine everywhere (0.1 s); random never; BURER2002 on 4 of 24 hosts; CP-SAT never
        rows = [synth(300, {'found': {0.1: 3, 2.0: 3}, 'engine': {0.1: 3, 2.0: 3}, 'dsb': {0.5: 3},
                            'system': {2.0: 3}, 'burer': {0.05: 3} if i < 4 else {}}) for i in range(M.PER_N)]
        a = M.analyse(rows)
        self.assertEqual(a['labels'], {'gv4_found_vs_builder': 'SELF_FOUND_MATCHES_BUILDER',
                                       'found_vs_random': 'SEARCH_HELPS', 'found_vs_sota': 'SELF_FOUND_BEATS_SOTA',
                                       'b20r77_replication': 'ENGINE_BEATS_SOTA'})
        self.assertEqual(a['arms']['found']['reached_within_2s'], 24)
        self.assertEqual(a['found_vs_system']['q0.5']['verdict'], 'A_FASTER')
        self.assertIsNone(M.validity(rows)[0])
        slow = [dict(r, cpu_ns={x: {str(t): int(0.3e9) for t in M.LADDER} for x in M.ARMS}) for r in rows]
        self.assertEqual(M.validity(slow)[0], 'INVALID_CPU_DELIVERY')

    def test_arms_with_a_stand_in_program(self):
        D = M.arm_descriptors({'found': (STAND_IN, 'x'), 'random': (STAND_IN, 'y')})
        self.assertEqual(len(D), len(M.ARMS) * len(M.LADDER))
        self.assertEqual((D[('found', 0.5)][1]['kind'], D[('found', 0.5)][1]['parameters']),
                         ('solver-program-v1', {'program': STAND_IN, 'cpu_seconds': 0.5}))
        self.assertEqual(D[('engine', 2.0)][1]['kind'], 'hybrid-swap-v1')

    def test_refuses_without_the_frozen_programs(self):
        if M.FOUND.exists() and M.RANDOM.exists():
            progs = M.programs()
            self.assertEqual(set(progs), {'found', 'random'})
        else:
            with self.assertRaises(SystemExit):
                M.programs()

    def test_pinned(self):
        for name in ('b20r80_random_program_control.py', 'b20r81_self_found_solver.py'):
            self.assertIn('R33.pinned_core()', (ROOT / 'scripts' / name).read_text())


class RecordB20R80(unittest.TestCase):
    """B20_R80's outputs: the frozen random-search program and its history."""

    @classmethod
    def setUpClass(cls):
        d = ROOT / 'evidence' / 'random_program_control_b20r80'
        cls.s = json.loads((d / 'control_summary.json').read_text())
        cls.frozen = json.loads((d / 'random_program.json').read_text())
        cls.hist = [json.loads(l) for l in (d / 'history.jsonl').read_text().splitlines() if l.strip()]

    def test_the_frozen_program(self):
        from genesis import candidates_v2 as C2
        prog = self.frozen['program']
        self.assertEqual(prog, self.s['program'])
        self.assertEqual(SP.problems(prog, KP.licensed_reps(TF)), [])
        self.assertEqual(C2.descriptor_problems(self.frozen['descriptor_at_0.5s'], domain=TF), [])
        best = max(self.s['finalists'], key=lambda f: (f['final_mean'], -f['size']))
        self.assertEqual((best['program'], best['final_mean']), (prog, 287.2969))
        self.assertFalse(SS.anatomy(prog)['swap_like'])

    def test_the_history(self):
        self.assertEqual(len(self.hist), self.s['programs'])
        self.assertEqual(len({json.dumps(h['program'], sort_keys=True) for h in self.hist}), len(self.hist))
        self.assertTrue(all(h['round'] == 0 for h in self.hist))
        hosts = json.loads((ROOT / 'evidence' / 'program_search_b20r79' / 'hosts.json').read_text())['tasks']
        self.assertEqual(self.s['training_host_ids'], [t['task_id'] for t in hosts])


class RecordB20R81(unittest.TestCase):
    """B20_R81's saved rows: valid; the labels recompute; the programs are the frozen ones; the hosts are in the addenda."""

    @classmethod
    def setUpClass(cls):
        d = ROOT / 'evidence' / 'self_found_solver_b20r81'
        cls.s = json.loads((d / 'summary.json').read_text())
        cls.rows = [json.loads(l) for l in (d / 'rows.jsonl').read_text().splitlines() if l.strip()]

    def test_valid_and_the_labels_recompute(self):
        self.assertEqual(len(self.rows), M.PER_N)
        invalid, _, fail = M.validity(self.rows)
        self.assertIsNone(invalid)
        self.assertEqual(set(fail.values()), {0.0})
        a = json.loads(json.dumps(M.analyse(self.rows)))
        for k in ('labels', 'found_vs_engine', 'found_vs_random', 'found_vs_sota', 'engine_vs_sota', 'arms'):
            self.assertEqual(a[k] if k != 'labels' else a['labels'], self.s[k], k)
        self.assertEqual(self.s['labels'], {'gv4_found_vs_builder': 'UNRESOLVED', 'found_vs_random': 'UNRESOLVED',
                                            'found_vs_sota': 'SELF_FOUND_BEATS_SOTA',
                                            'b20r77_replication': 'ENGINE_BEATS_SOTA'})
        # the builder's engine is faster, but the interval ends exactly at the boundary
        self.assertEqual([self.s['found_vs_engine'][q]['interval_90'][1] for q in ('q0.5', 'q0.75')], [-1.0, -1.0])
        self.assertEqual(self.s['found_vs_engine']['b20r76_per_host_median']['verdict'], 'B_FASTER')

    def test_the_programs_are_the_frozen_ones(self):
        import hashlib
        for arm, path in (('found', M.FOUND), ('random', M.RANDOM)):
            self.assertEqual(self.s['programs'][arm]['file_sha256'], hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertEqual(self.s['programs'][arm]['program'], json.loads(path.read_text())['program'])

    def test_values_bounded_and_isolated(self):
        for r in self.rows:
            self.assertLessEqual(r['target'], r['reference']['upper'])
            for a in M.ARMS:
                for t in M.LADDER:
                    for x in r['runs'][a][str(t)]:
                        self.assertLessEqual(x['value'], r['target'])
                        self.assertEqual(x['isolation'], 'OCI_RUNC_NO_NETWORK_RO_ROOT_SECCOMP')

    def test_hosts_are_fresh_and_in_the_addenda(self):
        import b20r23_e1b_readiness as RD
        from genesis.common import canonical
        from genesis.models import GraphTask
        d = ROOT / 'evidence' / 'self_found_solver_b20r81'
        tasks = [GraphTask.model_validate_json(canonical(t)) for t in json.loads((d / 'hosts.json').read_text())['tasks']]
        self.assertEqual([t.task_id for t in tasks], [r['task_id'] for r in self.rows])
        train = json.loads((ROOT / 'evidence' / 'program_search_b20r79' / 'hosts.json').read_text())['tasks']
        self.assertFalse(RD.identities(tasks) & RD.identities([GraphTask.model_validate_json(canonical(t)) for t in train]))
        for pkg in ('e1', 'e1b'):
            add = json.loads((ROOT / 'handoff' / pkg / 'exposure_hosts_addendum_b20r81.json').read_text())
            self.assertTrue(RD.identities(tasks) <= RD.identities([GraphTask.model_validate_json(canonical(t))
                                                                    for t in add]))


if __name__ == '__main__':
    unittest.main()
