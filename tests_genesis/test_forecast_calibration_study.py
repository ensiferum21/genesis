"""B20_R170 (Foundry G2) design tests: fresh, disjoint seeds and families; the extra budget and Holm; the verdict
rule; the refusals; and the study run end to end through its REGISTERED path (registered=True) on rehearsal worlds
with the output, the pins and the budgets redirected, so that the validity a registered run computes is itself
tested (B20_R141's lesson). Rehearsal worlds use seeds no study uses (888xxx)."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r170_forecast_calibration as S  # noqa: E402

PREREGISTRATION = '405741e'         # the commit that preregistered the script


def digest_at(commit, rel):
    import hashlib
    import subprocess
    try:
        out = subprocess.run(['git', '-C', str(ROOT), 'show', f'{commit}:{rel}'], capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return hashlib.sha256(out.stdout).hexdigest() if out.returncode == 0 else None


class Design(unittest.TestCase):
    def test_pins_at_the_preregistration_commit(self):
        import re
        self.assertEqual(set(S.PINNED), set(S.MODULES))
        at = {m: digest_at(PREREGISTRATION, 'src/genesis/frontier/' + m) for m in S.PINNED}
        if all(v is not None for v in at.values()):
            self.assertEqual(at, S.PINNED)
        script = digest_at(PREREGISTRATION, 'scripts/b20r170_forecast_calibration.py')
        if script is not None:
            self.assertEqual(script, '8aa46929e64a743b5eaba1eadde2dc285a6b445643486405e6eae5b691e2357d')
        others = [p for p in (ROOT / 'scripts').glob('*.py') if p.name != 'b20r170_forecast_calibration.py']
        self.assertFalse(any(re.search(rf'\b{S.SEALED_SEED}\b', p.read_text()) for p in others))

    def test_worlds_are_fresh_and_disjoint(self):
        import b20r156_frontier_worlds as F3
        import b20r163_frontier_meta as F6
        ws = S.worlds()
        self.assertEqual(len(ws), 30)
        self.assertEqual(sum(1 for w in ws if w[3]), 6)
        seeds = {w[2] for w in ws} | {S.meta_world()[2]}
        self.assertEqual(len(seeds), 31)
        others = {w[2] for w in F3.worlds()} | {w[2] for w in F6.worlds()} | {F6.meta_world()[2]}
        others |= set(range(881000, 881006)) | {887001}
        self.assertFalse(seeds & others)
        for fam, spec in S.FAMILIES.items():
            self.assertNotIn(spec, list(F3.FAMILIES.values()) + list(F6.FAMILIES.values()), fam)
        self.assertNotIn(S.SEALED_SEED, (F3.SEALED_SEED, F6.SEALED_SEED))

    def test_extra_budget_and_holm(self):
        self.assertEqual(S.extra_budget(144000), 6000)
        self.assertEqual(S.extra_budget(144005, 24), 6000)
        self.assertEqual(S.extra_budget(10, 24), 0)
        adj = S.holm({'P1': 0.04, 'P2': 0.01})
        self.assertEqual(adj, {'P2': 0.02, 'P1': 0.04})
        self.assertEqual(S.holm({'P1': 0.03, 'P2': 0.03}), {'P1': 0.06, 'P2': 0.06})

    def test_verdict_rule(self):
        def res(p1, p2):
            return {'P1': {'pass': p1}, 'P2': {'pass': p2}}
        self.assertEqual(S.verdict(False, res(True, True), False), 'INVALID')
        self.assertEqual(S.verdict(True, res(True, True), False), 'CALIBRATION_INVENTED_AND_PAYS')
        self.assertEqual(S.verdict(True, res(False, True), False), 'CALIBRATION_INVENTED')
        self.assertEqual(S.verdict(True, res(True, False), False), 'PAYS_WITHOUT_CALIBRATION')
        self.assertEqual(S.verdict(True, res(False, False), True), 'NOT_SHOWN (IDENTITY_PROMOTED)')

    def test_analysis_on_synthetic_rows(self):
        ws = [(f'J-{i}', 'Ja', 888100 + i, False) for i in range(14)] + [('J-null', 'Ja', 888199, True)]
        rows = {}
        for i, (k, fam, s, null) in enumerate(ws):
            for arm, v, hits in (('P', 0.80, 18), ('D', 0.86, 13), ('D0', 0.79, 13)):
                rows[(k, arm)] = {'value': 0.0 if null else v + 0.001 * i, 'coverage': {'n': 20, 'hits': hits},
                                  'cpu_s': 1.0, 'total': 0.0}
        r = S.analyse(rows, ws)
        self.assertFalse(r['P1']['pass'])
        self.assertTrue(r['P2']['pass'])
        self.assertAlmostEqual(r['P2']['coverage_P'], 0.9)
        self.assertEqual(S.verdict(True, r, False), 'CALIBRATION_INVENTED')

    def test_refusals(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(SystemExit):
                S.main([str(Path(d) / 'elsewhere')])
            with self.assertRaises(SystemExit):
                S.main([d], output=d, pinned={'allocate.py': 'x'})


class RegisteredPath(unittest.TestCase):
    def test_main_runs_through_the_registered_path(self):
        ws = [('Ja-r0', 'Ja', 888001, False), ('Jb-r0', 'Jb', 888002, False), ('Ja-rnull', 'Ja', 888003, True)]
        meta = ('Ga-r', 'Ga', 888000, False)
        with tempfile.TemporaryDirectory() as d:
            rc = S.main([d], registered=True, world_list=ws, meta=meta, b_in=1500, meta_budget=6000, budget=1500,
                        output=d, pinned=S.pins())          # at the preregistration commit, S.pins() == S.PINNED
            self.assertEqual(rc, 0)
            s = json.loads((Path(d) / 'summary.json').read_text())
        self.assertTrue(s['pins_ok'] and s['nulls_ok'] and s['spent_ok'], s)
        self.assertTrue(s['valid'])
        self.assertEqual(s['results']['P2']['worlds'] < S.MIN_WORLDS, True)
        self.assertFalse(s['results']['P2']['pass'])
        self.assertIn(s['verdict'], ('NOT_SHOWN', 'NOT_SHOWN (IDENTITY_PROMOTED)', 'PAYS_WITHOUT_CALIBRATION'))
        from genesis.frontier import calibrate as CAL
        self.assertEqual(set(s['S4']['promoted']), set(CAL.GRID))


if __name__ == '__main__':
    unittest.main()
