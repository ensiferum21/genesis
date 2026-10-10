"""Known-answer ladder: answer-key integrity, classification and end-to-end runs."""
import json
from pathlib import Path
import tempfile
import unittest

from genesis.ladder import (A006855, A006855_FRONTIER, answer_key, answer_key_digest, classify,
                            default_preregistration, ladder_task, run_ladder, LadderPreregistration)
from genesis.graphs import certified_optimum, universal_upper
from genesis.models import SolverProgram
from genesis.store import Store
from genesis.cli import main as cli_main


class AnswerKeyIntegrity(unittest.TestCase):
    def test_transcribed_c4_values_match_exact_solvers_where_feasible(self):
        # K_n has n(n-1)/2 edges; the dual exact optimizers handle <= 24 edges (n <= 7).
        for n in range(1, 8):
            self.assertEqual(certified_optimum(ladder_task('c4_host_v2', n))['value'], A006855[n - 1], n)

    def test_mantel_values_match_exact_solvers_where_feasible(self):
        for n in range(1, 8):
            self.assertEqual(certified_optimum(ladder_task('triangle_free_host_v1', n))['value'], n * n // 4)

    def test_published_values_respect_the_proved_universal_upper_bound(self):
        for n in range(1, 41):
            self.assertLessEqual(A006855[n - 1], universal_upper(ladder_task('c4_host_v2', n))['value'], n)
        for n, (lo, hi) in A006855_FRONTIER.items():
            self.assertLessEqual(lo, hi)
            self.assertLessEqual(hi, universal_upper(ladder_task('c4_host_v2', n))['value'])

    def test_sequence_is_nondecreasing(self):
        self.assertTrue(all(a <= b for a, b in zip(A006855, A006855[1:])))

    def test_digest_binds_key(self):
        self.assertEqual(len(answer_key_digest('c4_host_v2')), 64)
        self.assertNotEqual(answer_key_digest('c4_host_v2'), answer_key_digest('triangle_free_host_v1'))


class Classification(unittest.TestCase):
    def setUp(self):
        self.key = answer_key('c4_host_v2')

    def test_exact_rungs(self):
        self.assertEqual(classify(127, 40, self.key)['status'], 'MATCHES_KNOWN_OPTIMUM')
        self.assertEqual(classify(120, 40, self.key)['shortfall'], 7)
        self.assertEqual(classify(128, 40, self.key)['status'], 'HARNESS_ERROR')

    def test_frontier_rungs_never_claim_discovery(self):
        self.assertEqual(classify(132, 41, self.key)['status'], 'WITHIN_PUBLISHED_BOUNDS')
        candidate = classify(133, 41, self.key)
        self.assertEqual(candidate['status'], 'EXCEEDS_PUBLISHED_LOWER_BOUND_CANDIDATE')
        self.assertIn('external literature/priority check', candidate['requires'])
        self.assertEqual(classify(134, 41, self.key)['status'], 'HARNESS_ERROR')


class Preregistration(unittest.TestCase):
    def test_overlapping_rungs_rejected(self):
        with self.assertRaises(ValueError):
            default_preregistration(development=(4, 5), test=(5, 6))

    def test_stale_answer_key_rejected(self):
        good = default_preregistration(development=(4,), test=(5,)).model_dump(mode='json')
        good['answer_key_sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            LadderPreregistration.model_validate(good)


class EndToEnd(unittest.TestCase):
    def test_small_ladder_runs_through_bounded_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'ladder'
            prereg = default_preregistration(development=(4,), test=(5, 6, 8), cpu_seconds=0.3,
                                             candidate=SolverProgram(rounds=8, exchange=True))
            results = run_ladder(root, prereg)
            self.assertEqual(results['status'], 'PUBLIC_CALIBRATION_COMPLETE')
            self.assertFalse(results['promotion_allowed'])
            arms = [name for name, _ in prereg.arms]
            self.assertEqual(len(results['rows']), 4 * len(arms))
            for row in results['rows']:
                self.assertGreaterEqual(row['realized_cpu_ns'], row['budget_cpu_ns'])  # every arm fully charged
                self.assertIn(row['classification']['status'], ('MATCHES_KNOWN_OPTIMUM', 'BELOW_KNOWN_OPTIMUM'))
            with Store(root) as s:
                s.verify()
                kinds = [json.loads(b)['kind'] for (b,) in s.db.execute('SELECT body FROM events ORDER BY seq')]
                first_attempt = kinds.index('ATTEMPT_STARTED')
                self.assertIn('ENTITY_COMMITTED', kinds[:first_attempt])  # preregistration persisted first
                statuses = {r[0] for r in s.db.execute('SELECT status FROM attempts')}
                self.assertNotIn('RUNNING', statuses)
            self.assertTrue((root / 'reports' / 'ladder_report.md').read_text().startswith('# Known-answer ladder'))

    def test_destination_must_be_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'x').write_text('x')
            with self.assertRaises(FileExistsError):
                run_ladder(tmp, default_preregistration(development=(4,), test=(5,), cpu_seconds=0.1))

    def test_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            cli_main(['benchmark', 'ladder', str(Path(tmp) / 'l'), '--domain', 'triangle_free_host_v1',
                      '--dev', '4', '--test', '5,6', '--cpu-seconds', '0.2'])
            results = json.loads((Path(tmp) / 'l' / 'reports' / 'ladder_results.json').read_text())
            self.assertEqual(results['domain'], 'triangle_free_host_v1')


if __name__ == '__main__':
    unittest.main()
