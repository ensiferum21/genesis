"""B20_R72: physics move rules in the system's representation engine. Design: fresh seeds, the arms and their
shared profile, the verdict rule and the overall rule on synthetic rows. Record: the verdict recomputes from the saved rows."""
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r72_represent_moves as M  # noqa: E402


def row(values, cpu=0.6e9, opt=None, upper=270):
    return {'optimum': opt, 'reference': {'upper': upper},
            'arms': {n: {'value': v, 'run': 'SUCCESS', 'cpu_ns': int(cpu)} for n, v in values.items()}}


class Design(unittest.TestCase):
    def test_seeds_are_fresh(self):
        for path in (ROOT / 'scripts').glob('*.py'):
            if path.name == 'b20r72_represent_moves.py':
                continue
            text = path.read_text()
            for s in (M.SEED, M.BOOT_SEED):
                self.assertIsNone(re.search(rf'\b{s}\b', text), (path.name, s))

    def test_arms(self):
        import json
        A = M.arms()
        self.assertEqual(len(A), 1 + len(M.REPS_) * len(M.MOVES) + 2)
        frozen = json.loads((ROOT / 'handoff' / 'e1d' / 'candidate_descriptor.json').read_text())
        self.assertEqual(A['candidate'], ('v1', frozen))
        for r in M.REPS_:
            for m in M.MOVES:
                reg, d = A[M.arm_name(r, m)]
                self.assertEqual((reg, d['kind'], d['parameters']),
                                 ('v2', 'represent-search-v1', {'representation': r, 'move': m, 'cpu_seconds': 0.5}))
        self.assertNotIn('adjacent_2', M.REPS_)               # decodes exactly as cross_2

    def test_verdicts(self):
        self.assertEqual(M.verdict([0.6, 2.0], 0), 'IMPROVES')
        self.assertEqual(M.verdict([-2.0, -0.6], 0), 'WORSENS')
        self.assertEqual(M.verdict([-0.4, 0.4], 0), 'NO_MATERIAL_DIFFERENCE')
        self.assertEqual(M.verdict([-0.4, 1.0], 0), 'UNRESOLVED')
        self.assertEqual(M.verdict([0.6, 2.0], 1), 'UNRESOLVED_FAILURES')

    def test_overall_on_synthetic_rows(self):
        names = list(M.arms())
        base = {n: 260 for n in names}
        rows = []
        for i in range(20):
            v = dict(base)
            for r in M.REPS_:
                v[M.arm_name(r, 'anneal')] = 262 + (i % 2)      # anneal +2..+3 everywhere
                v[M.arm_name(r, 'eo')] = 260 + (i % 3 == 0)     # eo +0.35 on average
            rows.append(row(v))
        a = M.analyse(rows, names)
        self.assertEqual((a['verdict'], a['improving_moves']), ('IMPROVES_EVERY_REPRESENTATION', ['anneal']))
        self.assertEqual(a['primary']['cross_2/eo - cross_2/descent']['verdict'], 'UNRESOLVED')
        some = [dict(r, arms=dict(r['arms'], **{M.arm_name('ordered_2', 'anneal'): {'value': 260, 'run': 'SUCCESS',
                                                                                      'cpu_ns': int(0.6e9)}}))
                for r in rows]
        self.assertEqual(M.analyse(some, names)['verdict'], 'IMPROVES_SOME')
        flat = [row(base) for _ in range(20)]
        self.assertEqual(M.analyse(flat, names)['verdict'], 'NO_GENERAL_IMPROVEMENT')
        slow = [row(base, cpu=0.3e9) for _ in range(20)]
        self.assertEqual(M.analyse(slow, names)['verdict'], 'INVALID_CPU_DELIVERY')

    def test_the_study_is_pinned(self):
        self.assertIn('R33.pinned_core()', (ROOT / 'scripts' / 'b20r72_represent_moves.py').read_text())


EV = ROOT / 'evidence' / 'represent_moves_b20r72'


class Record(unittest.TestCase):
    """B20_R72's saved rows: the analysis and verdict recompute, the arms are the recorded ones, the hosts are fresh."""

    @classmethod
    def setUpClass(cls):
        import json
        cls.s = json.loads((EV / 'summary.json').read_text())
        cls.rows = [json.loads(l) for l in (EV / 'rows.jsonl').read_text().splitlines() if l.strip()]

    def test_verdict_recomputes_from_the_rows(self):
        self.assertEqual(len(self.rows), M.HOSTS)
        a = M.analyse(self.rows, list(self.s['descriptors']))
        for k in ('verdict', 'improving_moves', 'primary', 'secondary', 'failures', 'cpu_s_median', 'hosts'):
            self.assertEqual(a[k], self.s[k], k)
        self.assertEqual(self.s['verdict'], 'NO_GENERAL_IMPROVEMENT')
        self.assertEqual({k: v['verdict'] for k, v in self.s['primary'].items()},
                         {'cross_2/eo - cross_2/descent': 'NO_MATERIAL_DIFFERENCE',
                          'cross_2/anneal - cross_2/descent': 'UNRESOLVED',
                          'adjacent_3/eo - adjacent_3/descent': 'NO_MATERIAL_DIFFERENCE',
                          'adjacent_3/anneal - adjacent_3/descent': 'NO_MATERIAL_DIFFERENCE',
                          'ordered_2/eo - ordered_2/descent': 'WORSENS',
                          'ordered_2/anneal - ordered_2/descent': 'WORSENS'})

    def test_arms_are_the_recorded_ones(self):
        self.assertEqual(self.s['descriptors'], {n: d['descriptor_id'] for n, (_, d) in M.arms().items()})
        for r in self.rows:
            self.assertEqual({a['isolation'] for a in r['arms'].values()}, {'OCI_RUNC_NO_NETWORK_RO_ROOT_SECCOMP'})
            if r['optimum'] is not None:
                self.assertTrue(all(a['value'] <= r['optimum'] for a in r['arms'].values()))

    def test_hosts_are_fresh_and_in_the_addenda(self):
        import json
        import b20r23_e1b_readiness as RD
        from genesis.common import canonical
        from genesis.models import GraphTask
        tasks = [GraphTask.model_validate_json(canonical(t)) for t in json.loads((EV / 'hosts.json').read_text())['tasks']]
        self.assertEqual([t.task_id for t in tasks], [r['task_id'] for r in self.rows])
        self.assertEqual(len(RD.identities(tasks)), M.HOSTS)
        for pkg in ('e1', 'e1b'):
            add = json.loads((ROOT / 'handoff' / pkg / 'exposure_hosts_addendum_b20r72.json').read_text())
            self.assertTrue(RD.identities(tasks) <= RD.identities([GraphTask.model_validate_json(canonical(t))
                                                                    for t in add]))


if __name__ == '__main__':
    unittest.main()
