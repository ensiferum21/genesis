"""B20_R59: the internal replication of B20_R57. Design: B20_R57's protocol with fresh seeds only; the replication
rule.

Record (B20_R59): NOT_REPLICATED. The primary verdict recomputes as NO_CERTIFICATION_UTILITY (21 vs 23, 0/2, p 0.25);
the secondary BOUND_UTILITY replicates (+3.875 [2.675, 5.125]); the replication record follows the rule; the hosts are
the script's fresh candidates."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r56_sf_tree_certification as R56  # noqa: E402
import b20r57_sf_hard_certification as R57  # noqa: E402
import b20r58_sf_pattern_selection as R58  # noqa: E402
import b20r59_sf_replication as M  # noqa: E402


class Design(unittest.TestCase):
    def test_fresh_seeds_only(self):
        used = set(R56.SEEDS) | set(R57.SEEDS) | set(R58.DEV_SEEDS) | set(R58.EVAL_SEEDS)
        self.assertFalse(set(M.SEEDS) & used)
        self.assertEqual(len(M.SEEDS), len(R57.SEEDS))
        prior = {tuple(R57.candidate(s, i, N, p)['elements']) for s, (N, p) in zip(R57.SEEDS, R57.SETTINGS)
                 for i in range(R57.MAX_CANDIDATES)}
        new = {tuple(R57.candidate(s, i, N, p)['elements']) for s, (N, p) in zip(M.SEEDS, R57.SETTINGS)
               for i in range(R57.MAX_CANDIDATES)}
        self.assertFalse(prior & new)

    def test_rule(self):
        s = lambda v, b='BOUND_UTILITY': {'verdict': v, 'bound': {'verdict': b}}
        self.assertEqual(M.replication_verdict(s('CERTIFICATION_UTILITY'))['replication'], 'REPLICATED')
        self.assertEqual(M.replication_verdict(s('NO_CERTIFICATION_UTILITY'))['replication'], 'NOT_REPLICATED')
        self.assertEqual(M.replication_verdict(s('DEFECT_FOUND'))['replication'], 'DEFECT_FOUND')



EV = ROOT / 'evidence' / 'sf_replication_b20r59'


class Record(unittest.TestCase):
    def test_the_replication_record(self):
        rows = [json.loads(l) for l in (EV / 'rows.jsonl').read_text().splitlines() if l.strip()]
        screen = [json.loads(l) for l in (EV / 'screen.jsonl').read_text().splitlines() if l.strip()]
        summary = json.loads((EV / 'summary.json').read_text())
        old = (R57.SEEDS, R57.BOOT_SEED)
        R57.SEEDS, R57.BOOT_SEED = M.SEEDS, M.BOOT_SEED
        try:
            v = R57.verdict_of(rows)
        finally:
            R57.SEEDS, R57.BOOT_SEED = old
        for k in ('verdict', 'passes', 'pooled', 'mcnemar_p_one_sided', 'wall_saving_a_minus_c', 'bound'):
            self.assertEqual(v[k], summary[k], k)
        self.assertEqual((v['verdict'], v['bound']['verdict']), ('NO_CERTIFICATION_UTILITY', 'BOUND_UTILITY'))
        self.assertEqual((v['pooled']['certified_a'], v['pooled']['certified_c']), (21, 23))
        rep = json.loads((EV / 'replication.json').read_text())
        self.assertEqual(rep, M.replication_verdict(summary))
        self.assertEqual(rep['replication'], 'NOT_REPLICATED')
        self.assertEqual(len(rows), 40)
        for s in screen:
            seed = int(s['task_id'].rsplit('_', 1)[1]) - s['index']
            self.assertIn(seed, M.SEEDS)
            self.assertEqual(s['included'], s['screen_lower'] != s['screen_upper'])


if __name__ == '__main__':
    unittest.main()
