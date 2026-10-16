"""B20_R50: E1b's C4 readiness under the DRAFT rule e1-hard-v2-c4tree-draft. Design: the draft changes only the
reference (and its name and note) relative to e1-hard-v2; no study adopts it; the arms are B20_R23's C4
candidate, its three DSL baselines and the registered ablation and placebo of that same candidate; the C4 MIP
and the tree reference agree on a small host's optimum. Record tests are added with the result."""
import itertools
from pathlib import Path
import sys
import unittest

from genesis import calibration as CAL
from genesis.discovery import generated_certify_c4 as GC4
from genesis.kernel import replay_contracts as RC
from genesis.models import GraphTask

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r50_e1b_c4_readiness as R50  # noqa: E402


class Design(unittest.TestCase):
    def test_the_draft_changes_only_the_reference(self):
        base = CAL.SELECTION_RULE_E1_HARD_V2
        self.assertEqual({k for k in set(base) | set(R50.RULE) if base.get(k) != R50.RULE.get(k)},
                         {'name', 'measurement', 'note'})
        self.assertEqual({k for k in base['measurement'] if base['measurement'][k] != R50.RULE['measurement'][k]},
                         {'reference'})
        self.assertNotIn(R50.RULE['name'], CAL.DRAFT_RULES_BY_NAME)        # not registered, so no study can adopt it
        self.assertEqual(R50.GRID[:2], [('erdos', {'n': 30, 'p': 0.2}), ('erdos', {'n': 36, 'p': 0.17})])
        self.assertEqual((R50.PER, R50.CAL_SEED, R50.PILOT_N, R50.PILOT_SEED), (8, 20265001, 30, 20265051))

    def test_arms(self):
        arms = R50.arms()
        self.assertEqual(sorted(arms), sorted(['candidate', *R50.DSL, *R50.CAUSAL]))
        self.assertTrue(all(d['domain'] == 'c4_host_v2' for d in arms.values()))
        for kind in R50.CAUSAL:
            why, path = RC.intervention_problems(kind, arms['candidate'], arms[kind])
            self.assertFalse(why)
            self.assertEqual(path, ('init',))

    def test_mip_and_reference_agree_on_a_small_host(self):
        t = GraphTask(task_id='k6', domain='c4_host_v2', family='test', split='DEV', n=6,
                      edges=tuple(itertools.combinations(range(6), 2)))
        m, sel = R50.mip(t, 2.0)
        self.assertEqual(m['value'], 7)                                        # ex(K6, C4) = 7
        ref, opt = R50.reference(t, [('mip', sel)], GC4.load_registry(), 30)
        self.assertEqual(opt, 7)
        self.assertEqual(ref['check'], 'VALID')


if __name__ == '__main__':
    unittest.main()
