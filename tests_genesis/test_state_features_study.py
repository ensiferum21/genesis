"""B20_R172 (Foundry G4) design tests: fresh, disjoint seeds and families; even spacing of replayed decisions; the
extra budget; the verdict rule; the analysis on synthetic rows; the refusals; and the study run end to end through
its REGISTERED path (registered=True) on rehearsal worlds with the output, pins and budgets redirected (B20_R141's
lesson). Rehearsal worlds use seeds no study uses (889xxx)."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r172_state_features as S  # noqa: E402

PREREGISTRATION = None              # the commit that preregistered the script (set after it)


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
        if PREREGISTRATION:
            at = {m: digest_at(PREREGISTRATION, 'src/genesis/frontier/' + m) for m in S.PINNED}
            if all(v is not None for v in at.values()):
                self.assertEqual(at, S.PINNED)
        others = [p for p in (ROOT / 'scripts').glob('*.py') if p.name != 'b20r172_state_features.py']
        self.assertFalse(any(re.search(rf'\b{S.SEALED_SEED}\b', p.read_text()) for p in others))

    def test_worlds_are_fresh_and_disjoint(self):
        import b20r156_frontier_worlds as F3
        import b20r163_frontier_meta as F6
        import b20r170_forecast_calibration as G2
        ws = S.worlds()
        self.assertEqual((len(ws), sum(1 for w in ws if w[3])), (30, 6))
        seeds = {w[2] for w in ws} | {w[2] for w in S.training_worlds()}
        self.assertEqual(len(seeds), 32)
        others = {w[2] for w in F3.worlds()} | {w[2] for w in F6.worlds()} | {w[2] for w in G2.worlds()}
        others |= {F6.meta_world()[2], G2.meta_world()[2]} | set(range(887000, 887100)) | set(range(881000, 881006))
        self.assertFalse(seeds & others)
        specs = list(F3.FAMILIES.values()) + list(F6.FAMILIES.values()) + list(G2.FAMILIES.values())
        for fam, spec in S.FAMILIES.items():
            self.assertNotIn(spec, specs, fam)
        self.assertNotIn(S.SEALED_SEED, (F3.SEALED_SEED, F6.SEALED_SEED, G2.SEALED_SEED))

    def test_spacing_and_extra_budget(self):
        self.assertEqual(S.spaced(list(range(10)), 20), list(range(10)))
        self.assertEqual(S.spaced(list(range(100)), 4), [0, 25, 50, 75])
        self.assertEqual(S.extra_budget(72000), 3000)
        self.assertEqual(S.extra_budget(72009, 24), 3000)

    def test_verdict_and_analysis(self):
        ws = [(f'L-{i}', 'La', 889100 + i, False) for i in range(12)] + [('L-null', 'La', 889199, True)]
        rows = {}
        for i, (k, fam, s, null) in enumerate(ws):
            for arm, v in (('P', 0.86), ('D', 0.84), ('D0', 0.80)):
                rows[(k, arm)] = {'value': v + 0.002 * i * (arm == 'P'), 'cpu_s': 1.0, 'total': 0.0 if null else 1.0}
            if not null:
                rows[(k, 'D0')]['S7'] = {'index': 0.80, 'feature': 0.85 + 0.001 * i}
        r = S.analyse(rows, ws)
        self.assertEqual(r['P1']['label'], 'FEATURE_PAYS')
        self.assertEqual(r['S1']['label'], 'FEATURE_BETTER')
        self.assertEqual(r['S7']['label'], 'FEATURE_GENERALISES')
        self.assertEqual(S.verdict(True, r, False), 'FEATURE_PAYS')
        self.assertEqual(S.verdict(False, r, False), 'INVALID')
        r['P1']['label'] = 'NOT_SHOWN'
        self.assertEqual(S.verdict(True, r, True), 'NOT_SHOWN (NOTHING_PROPOSED)')

    def test_refusals(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(SystemExit):
                S.main([str(Path(d) / 'elsewhere')])
            with self.assertRaises(SystemExit):
                S.main([d], output=d, pinned={'allocate.py': 'x'})


class RegisteredPath(unittest.TestCase):
    def test_main_runs_through_the_registered_path(self):
        ws = [('La-r0', 'La', 889001, False), ('Lb-r0', 'Lb', 889002, False), ('La-rnull', 'La', 889003, True)]
        train = [('Ka-r0', 'Ka', 889000, False)]
        with tempfile.TemporaryDirectory() as d:
            rc = S.main([d], registered=True, world_list=ws, train=train, budget=3000, pairs_per=30, output=d,
                        pinned=S.pins())                  # at the preregistration commit, S.pins() == S.PINNED
            self.assertEqual(rc, 0)
            s = json.loads((Path(d) / 'summary.json').read_text())
        self.assertTrue(s['pins_ok'] and s['nulls_ok'] and s['spent_ok'], s)
        self.assertTrue(s['valid'])
        self.assertGreater(s['S4']['c_search'], 3000)
        self.assertIn(s['verdict'], ('NOT_SHOWN', 'NOT_SHOWN (NOTHING_PROPOSED)', 'FEATURE_PAYS'))


if __name__ == '__main__':
    unittest.main()
