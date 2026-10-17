"""B20_R62: power analyses bound to the custodian's families, and sizing at 10,000 simulations.

Checks:
  * every written power analysis is bound to the family the custodian assigns (its plan-core digest);
  * the four rebound analyses are exactly the registered recomputation (1,000 simulations) under that family;
  * each 10,000-simulation analysis chooses the first grid size whose power reaches the target, and a spot check
    re-simulates the chosen power of the analysis the brief flagged (E1b-C4 placebo);
  * the summary's choices and `size_changes` follow from the files.
"""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r61_statistician_brief as S  # noqa: E402
import b20r62_power_rebind as M  # noqa: E402
from genesis.common import digest  # noqa: E402
from genesis.kernel.analysis import plan_core  # noqa: E402
from genesis.power import _pilot, simulate_power  # noqa: E402

SUMMARY = json.loads((M.OUT / 'summary.json').read_text())
BY = {r['analysis']: r for r in SUMMARY['analyses']}
ANALYSES = {a[0]: a for a in S.ANALYSES}


def _load(rel):
    return json.loads((ROOT / rel).read_text())


class Binding(unittest.TestCase):
    def test_every_written_analysis_is_bound_to_the_assigned_family(self):
        self.assertEqual(set(BY), set(ANALYSES))
        for name, r in BY.items():
            domain = ANALYSES[name][4]
            want = digest(plan_core(S.plan(domain, r['assigned_family'])))
            for key in ('rebound', 'fine'):
                if key in r:
                    self.assertEqual(_load(r[key])['plan_core_sha256'], want, (name, key))

    def test_the_rebound_analyses_are_the_registered_recomputation(self):
        rebound = [n for n, r in BY.items() if 'rebound' in r]
        self.assertEqual(rebound, ['E1b ablation', 'E1b placebo', 'E1b-C4 ablation', 'E1b-C4 placebo'])
        for n in rebound:
            self.assertEqual(_load(BY[n]['rebound']), S.recompute(ANALYSES[n], BY[n]['assigned_family']), n)


class Fine(unittest.TestCase):
    def test_choice_is_the_first_grid_size_reaching_the_target(self):
        for name, r in BY.items():
            d = _load(r['fine'])
            first = next(row for row in d['table'] if row['power'] is not None and row['power'] >= S.TARGET)
            self.assertEqual(d['chosen'], first, name)
            self.assertEqual(r['fine_choice'], {k: first[k] for k in ('tasks_per_stratum', 'total_tasks', 'power')})

    def test_spot_check_the_flagged_analysis(self):
        a = ANALYSES['E1b-C4 placebo']
        d = _load(BY['E1b-C4 placebo']['fine'])
        n = d['chosen']['tasks_per_stratum']
        p = simulate_power(_pilot(S.pilot_rows(a), 'centred'), S.plan(a[4], 'placebo'), n, sims=M.FINE)
        self.assertEqual(round(p, 4), d['chosen']['power'])

    def test_summary_follows_from_the_files(self):
        for name, r in BY.items():
            self.assertEqual(r['stored_choice']['tasks_per_stratum'], _load(r['stored'])['chosen']['tasks_per_stratum'])
            self.assertEqual(r['size_changes'],
                             r['fine_choice']['tasks_per_stratum'] != r['stored_choice']['tasks_per_stratum'])
        self.assertEqual(SUMMARY['changes'], [n for n, r in BY.items() if r['size_changes']])


if __name__ == '__main__':
    unittest.main()
