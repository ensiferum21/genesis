"""B20_R58: the sum-free pattern-selection pilot. Design: R56's settings with fresh development and evaluation seeds;
subsets keep only the named patterns; the pattern sets are NONE, ALL and TOP-k by development score; the verdict
follows the preregistered rule.

Record (B20_R58): the verdict recomputes from the rows (NO_HEADROOM: ALL certifies 13 of 16, more than NONE's 10 and
every TOP-k's 9-11); every (host, set) pair ran and every certificate is VALID; the hosts are the script's."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r56_sf_tree_certification as R56  # noqa: E402
import b20r57_sf_hard_certification as R57  # noqa: E402
import b20r58_sf_pattern_selection as M  # noqa: E402


class Design(unittest.TestCase):
    def test_constants_and_hosts(self):
        self.assertEqual(M.SETTINGS, R56.SETTINGS)
        self.assertEqual((M.PER, M.SECONDS, M.KS, M.WITHIN), (8, 30, (1, 2, 4, 8), 0.5))
        seeds = set(M.DEV_SEEDS) | set(M.EVAL_SEEDS)
        self.assertEqual(len(seeds), 4)
        self.assertFalse(seeds & (set(R56.SEEDS) | set(R57.SEEDS)))
        dev, ev = M.make_hosts(M.DEV_SEEDS, 'dev'), M.make_hosts(M.EVAL_SEEDS, 'eval')
        self.assertEqual((len(dev), len(ev)), (16, 16))
        self.assertEqual(dev, M.make_hosts(M.DEV_SEEDS, 'dev'))
        prior = {tuple(t['elements']) for t in R56.make_hosts()}
        for seed, (N, p) in zip(R57.SEEDS, R57.SETTINGS):
            prior |= {tuple(R57.candidate(seed, i, N, p)['elements']) for i in range(R57.MAX_CANDIDATES)}
        self.assertFalse({tuple(t['elements']) for t in dev + ev} & prior)
        self.assertFalse({t['task_id'] for t in dev} & {t['task_id'] for t in ev})

    def test_subsets_and_sets(self):
        reg = {'schema': 's', 'package_sha256': 'p', 'patterns': {f'q{i}': {'i': i} for i in range(10)}}
        self.assertEqual(sorted(M.subset(reg, ['q3', 'q1'])['patterns']), ['q1', 'q3'])
        sc = {'ranked': [f'q{i}' for i in (4, 2, 9, 0, 1, 3, 5, 6, 7, 8)], 'dev_k': 2}
        sets = M.sets_of(sc, reg)
        self.assertEqual(sets['NONE'], [])
        self.assertEqual(len(sets['ALL']), 10)
        self.assertEqual(sets['TOP2'], ['q4', 'q2'])
        self.assertEqual(sorted(sets), ['ALL', 'NONE', 'TOP1', 'TOP2', 'TOP4', 'TOP8'])


def row(task, name, certified, wall, upper=10):
    lower = upper if certified else upper - 3
    return {'task_id': task, 'stratum': 's', 'set': name, 'patterns': [],
            'side': {'lower': lower, 'upper': upper, 'wall_s': wall, 'check': {'verdict': 'VALID', 'bound': upper},
                     'witness_valid': True, 'witness_value': lower}}


def grid(cert):
    """cert: {set: (number certified of 16, wall per host)}"""
    out = []
    for name, (c, w) in cert.items():
        for h in range(16):
            out.append(row(f'h{h}', name, h < c, w))
    return out


class Verdict(unittest.TestCase):
    def test_rule(self):
        sc = {'dev_k': 2}
        base = {'NONE': (8, 20.0), 'ALL': (9, 25.0), 'TOP1': (9, 20.0), 'TOP2': (10, 20.0), 'TOP4': (9, 22.0),
                'TOP8': (9, 25.0)}
        v = M.verdict(grid(base), sc)
        self.assertEqual((v['verdict'], v['H'], v['base'], v['oracle'], v['dev_minus_base']),
                         ('WEAK_HEADROOM', 1, 'ALL', 'TOP2', 1))
        v = M.verdict(grid(dict(base, TOP4=(12, 20.0))), sc)
        self.assertEqual((v['verdict'], v['H'], v['oracle']), ('SELECTION_HEADROOM', 3, 'TOP4'))
        v = M.verdict(grid(dict(base, TOP2=(9, 18.0))), sc)
        self.assertEqual((v['verdict'], v['H']), ('WEAK_HEADROOM', 0))              # 18 <= 0.75 * 25
        v = M.verdict(grid(dict(base, TOP1=(8, 20.0), TOP2=(9, 24.0), TOP4=(9, 24.5), TOP8=(9, 25.0))), sc)
        self.assertEqual((v['verdict'], v['H']), ('NO_HEADROOM', 0))
        bad = grid(base)
        bad[0]['side']['check']['verdict'] = 'REJECTED'
        self.assertEqual(M.verdict(bad, sc)['verdict'], 'DEFECT_FOUND')



EV = ROOT / 'evidence' / 'sf_pattern_selection_b20r58'


class Record(unittest.TestCase):
    def test_the_verdict_recomputes(self):
        rows = [json.loads(l) for l in (EV / 'rows.jsonl').read_text().splitlines() if l.strip()]
        sc = json.loads((EV / 'scores.json').read_text())
        summary = json.loads((EV / 'summary.json').read_text())
        v = M.verdict(rows, sc)
        for k in ('verdict', 'H', 'base', 'oracle', 'dev_k', 'dev_minus_base', 'table'):
            self.assertEqual(v[k], summary[k], k)
        self.assertEqual((v['verdict'], v['base'], v['H']), ('NO_HEADROOM', 'ALL', -2))
        self.assertEqual({k: x['certified'] for k, x in v['table'].items()},
                         {'NONE': 10, 'ALL': 13, 'TOP1': 9, 'TOP2': 10, 'TOP4': 10, 'TOP8': 11})
        self.assertEqual(len(rows), 16 * 6)

    def test_hosts_are_the_scripts(self):
        tasks = json.loads((EV / 'hosts.json').read_text())['tasks']
        made = M.make_hosts(M.DEV_SEEDS, 'dev') + M.make_hosts(M.EVAL_SEEDS, 'eval')
        self.assertEqual([{k: t[k] for k in ('task_id', 'elements', 'role')} for t in tasks],
                         [{k: t[k] for k in ('task_id', 'elements', 'role')} for t in made])


if __name__ == '__main__':
    unittest.main()
