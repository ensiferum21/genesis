"""B20_R110: the engine at 60 s on Gset (design): the configuration rule (B20_R108's only if it matured better at
10 s, each file checked against its study), the analysis and its sign test against 10 s, record candidates flagged,
and the registered output."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r110_gset_long as M  # noqa: E402
from genesis.common import digest  # noqa: E402


def study(d, name, label=None, tamper=False):
    p = Path(d) / name
    p.mkdir()
    configs = {'chosen': {'random': {'10': {'L0': 0.05}}}, 'name': name}
    (p / 'configs.json').write_text(json.dumps(configs))
    s = {'configs_sha256': digest(configs) if not tamper else '0', 'valid': True}
    if label:
        s['labels'] = {'maturation@10': {'label': label}}
    (p / 'summary.json').write_text(json.dumps(s))
    return p


class Design(unittest.TestCase):
    def test_configuration_rule(self):
        with tempfile.TemporaryDirectory() as d:
            a = study(d, 'a')
            self.assertEqual(M.choose_configs(a, Path(d) / 'missing')[0], 'a')
            b = study(d, 'b', 'NO_DIFFERENCE')
            self.assertEqual(M.choose_configs(a, b)[0], 'a')
            c = study(d, 'c', 'MATURED_BETTER')
            self.assertEqual(M.choose_configs(a, c)[0], 'c')
            e = study(d, 'e', 'MATURED_BETTER', tamper=True)
            with self.assertRaises(SystemExit):
                M.choose_configs(a, e)

    def test_analysis(self):
        best = {f'G{i}': 100 for i in range(1, 55)}
        rows = [{'instance': f'G{i}', 'family': 'random', 'value': 100, 'ten': 99} for i in range(1, 55)]
        a = M.analyse(rows, best)
        self.assertEqual((a['vs_10s']['label'], a['reach_best_known'], a['record_candidates']), ('LONGER_HELPS', 54, []))
        rows[0]['value'] = 101
        self.assertEqual(M.analyse(rows, best)['record_candidates'], [{'instance': 'G1', 'value': 101, 'best_known': 100}])
        same = [dict(r, value=99) for r in rows]
        self.assertEqual(M.analyse(same, best)['vs_10s']['label'], 'NO_DIFFERENCE')

    def test_refuses_another_output(self):
        with self.assertRaises(SystemExit):
            M.main([str(ROOT / 'evidence' / 'elsewhere')])


if __name__ == '__main__':
    unittest.main()
