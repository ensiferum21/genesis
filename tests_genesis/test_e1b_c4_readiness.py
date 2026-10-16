"""B20_R50: E1b's C4 readiness under the DRAFT rule e1-hard-v2-c4tree-draft. Design: the draft changes only the
reference (and its name and note) relative to e1-hard-v2; no study adopts it (B20_R51 lists it as a DRAFT so that
records using it can be checked); the arms are B20_R23's C4
candidate, its three DSL baselines and the registered ablation and placebo of that same candidate; the C4 MIP
and the tree reference agree on a small host's optimum. Record: the calibration and the selection recompute
from the rows, the pilot's verdicts recompute, and the hosts are fresh and in the exposure addenda."""
import itertools
import json
from pathlib import Path
import sys
import unittest

from genesis import calibration as CAL
from genesis.common import digest
from genesis.discovery import generated_certify_c4 as GC4
from genesis.kernel import replay_contracts as RC
from genesis.models import GraphTask

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r50_e1b_c4_readiness as R50  # noqa: E402

EVIDENCE = ROOT / 'evidence' / 'e1b_c4_readiness_b20r50'


class Design(unittest.TestCase):
    def test_the_draft_changes_only_the_reference(self):
        base = CAL.SELECTION_RULE_E1_HARD_V2
        self.assertEqual({k for k in set(base) | set(R50.RULE) if base.get(k) != R50.RULE.get(k)},
                         {'name', 'measurement', 'note'})
        self.assertEqual({k for k in base['measurement'] if base['measurement'][k] != R50.RULE['measurement'][k]},
                         {'reference'})
        self.assertNotIn(R50.RULE['name'], CAL.RULES_BY_NAME)              # a DRAFT (registered as such in B20_R51)
        cfg = json.loads((ROOT / CAL.CONFIG).read_text())
        self.assertNotIn(R50.RULE['name'], {e.get('rule') for s in cfg.get('studies', {}).values() for e in s.values()})
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


class Record(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads((EVIDENCE / 'calibration_record.json').read_text())
        cls.cal_rows = [json.loads(l) for l in (EVIDENCE / 'calibration_rows.jsonl').read_text().splitlines() if l.strip()]
        cls.pilot_rows = [json.loads(l) for l in (EVIDENCE / 'pilot_rows.jsonl').read_text().splitlines() if l.strip()]
        cls.summary = json.loads((EVIDENCE / 'summary.json').read_text())
        cls.pilot = json.loads((EVIDENCE / 'pilot_summary.json').read_text())

    def test_calibration_and_selection_recompute(self):
        saved = json.loads((EVIDENCE / 'calibration_hosts.json').read_text())
        self.assertEqual([digest(t) for s in saved['settings'] for t in s['tasks']], [r['task_sha256'] for r in self.cal_rows])
        sums = []
        for s in self.record['settings']:
            rows = [r for r in self.cal_rows if r['setting'] == s['index']]
            self.assertEqual(CAL.summarize(rows, R50.RULE), s['summary'])
            self.assertEqual(CAL.eligible(s['summary'], R50.RULE), s['ineligible_because'])
            sums.append(s)
        self.assertEqual(CAL.select(sums, R50.RULE), self.record['selected'])
        self.assertEqual(self.record['rule'], json.loads(json.dumps(R50.RULE)))

    def test_pilot_verdicts_recompute(self):
        names = ['candidate', *R50.DSL, *R50.CAUSAL, *R50.MIP_BUDGETS]
        self.assertEqual(len(self.pilot_rows), 30)
        for key, comps in (('readiness', list(R50.DSL)), ('ablation', ['ablation']), ('placebo', ['placebo'])):
            a, _ = R50.analyse(self.pilot_rows, names, comps)
            saved = self.pilot['contrasts'][key]
            for k in ('verdict', 'comparator', 'mean_difference', 'wins_ties_losses', 'certified_by_stratum'):
                self.assertEqual(a[k], saved[k], (key, k))
        self.assertEqual(self.summary['verdicts'], {k: v['verdict'] for k, v in self.pilot['contrasts'].items()})
        self.assertEqual(R50.descriptive(self.pilot_rows, names), self.pilot['descriptive'])

    def test_hosts_are_fresh_and_in_the_exposure_addenda(self):
        cal = [t for s in json.loads((EVIDENCE / 'calibration_hosts.json').read_text())['settings'] for t in s['tasks']]
        pilot = json.loads((EVIDENCE / 'pilot_hosts.json').read_text())['tasks']
        ids = {t['task_id'] for t in cal + pilot}
        self.assertEqual(len(ids), 62)
        for d in ('c4_certification_b20r47', 'c4_tree_certification_b20r48', 'c4_rows_ablation_b20r49'):
            other = json.loads((ROOT / 'evidence' / d / 'hosts.json').read_text())['tasks']
            self.assertFalse(ids & {t['task_id'] for t in other})
        for pkg in ('handoff/e1', 'handoff/e1b'):
            listed = set()
            for p in sorted((ROOT / pkg).glob('exposure_hosts_addendum_*.json')):
                listed |= {t['task_id'] for t in json.loads(p.read_text())}
            self.assertTrue(ids <= listed)


if __name__ == '__main__':
    unittest.main()
