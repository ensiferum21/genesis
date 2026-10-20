"""B20_R89 and B20_R90 (design): the configuration race and the head-to-head with the strongest MaxSAT solvers. Seeds
are fresh, every arm builds under one profile per part, the race draws valid configurations and halves as declared,
and the labels say what the preregistration says on synthetic data."""
import importlib.util
import json
import math
from pathlib import Path
import re
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / f'{name}.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


R89 = load('b20r89_configure_tfx')
R90 = load('b20r90_beat_the_champions')


def earlier_seeds():
    seen = set()
    for p in (ROOT / 'scripts').glob('*.py'):
        if p.name.startswith(('b20r89', 'b20r90')):
            continue
        seen |= {int(x) for x in re.findall(r'\b(2026\d{4})\b', p.read_text())}
    return seen


class Design89(unittest.TestCase):
    def test_seeds_are_fresh(self):
        self.assertFalse({R89.HOST_SEED, R89.CONFIG_SEED} & earlier_seeds())

    def test_configurations(self):
        from genesis.candidate_kinds import tfx as T
        cs = R89.configurations()
        self.assertEqual(len(cs), 128)
        self.assertEqual(cs, R89.configurations())                          # deterministic
        self.assertTrue(all(T.check_config(c) is None for c in cs))
        self.assertEqual(cs[R89.DRAWN], T.DEFAULT)
        self.assertEqual(cs[R89.DRAWN + 1], dict(T.DEFAULT, ws=2, K=8))
        self.assertGreater(len({json.dumps(c, sort_keys=True) for c in cs}), 120)

    def test_the_halving_schedule(self):
        kept = [128]
        for nh, ns, keep in R89.ROUNDS:
            self.assertEqual(keep * 2, kept[-1])
            kept.append(keep)
        self.assertEqual([r[0] for r in R89.ROUNDS], [4, 8, 16, 32, 32])
        self.assertEqual(R89.ROUNDS[-1][1], 4)
        self.assertEqual(R89.BUDGETS, (0.02, 0.05, 0.1, 0.25))

    def test_a_run_is_checked(self):
        from genesis.candidate_kinds import tfx as T
        from genesis.models import GraphTask
        from itertools import combinations
        t = GraphTask(task_id='x', domain=R89.TF, n=10, edges=tuple(combinations(range(10), 2)), family='f',
                      split='DEV')
        self.assertEqual(R89.run_tfx(t, T.DEFAULT, 0.05, 3), 25)
        self.assertNotEqual(R89.seed_of(1, 'x', 0, 0.05), R89.seed_of(2, 'x', 0, 0.05))


def row(task_id, tts, long=None, target=10, tfx_best=10, family='P', arms=None):
    """A synthetic row whose ladder runs give the requested TTS* per arm (inf: never reached)."""
    arms = arms or R90.ARMS[family]
    runs = {}
    for a in arms:
        runs[a] = {}
        for t in R90.LADDER:
            hit = not math.isinf(tts[a]) and t >= tts[a]
            v = target if hit else target - 1
            if a == 'tfx':
                v = tfx_best if hit or tfx_best < target else target - 1
            runs[a][str(t)] = [{'value': v, 'run': 'SUCCESS', 'cpu_ns': int(t * 1e9)}] * 3
    long = long or {}
    return {'task_id': task_id, 'family': family, 'runs': runs, 'target': target, 'target_certified': True,
            'edges': 400, 'cpu_ns': {a: {'0.5': int(0.6e9)} for a in arms},
            'long': {a: {'value': long.get(a, target), 'run': 'SUCCESS', 'cpu_ns': 1} for a in R90.LONG_ARMS},
            'exact': {'cpsat': {'claims_optimal': False, 'value': target - 1}}}


def rows(n, tts_fn, family='P', **kw):
    return [row(f'h{i}', tts_fn(i), family=family, **kw) for i in range(n)]


class Design90(unittest.TestCase):
    def test_seeds_are_fresh_and_families_as_declared(self):
        seeds = {R90.FAMILIES[f]['seed'] for f in R90.FAMILIES} | {R90.BOOT_SEED}
        self.assertEqual(len(seeds), 3)
        self.assertFalse(seeds & earlier_seeds())
        self.assertEqual(R90.FAMILIES['P']['params'], {'n': 63, 'p_in': 0.8, 'p_out': 0.06})
        self.assertEqual(R90.FAMILIES['D']['params'], {'n': 63, 'p_in': 0.5, 'p_out': 0.5})
        self.assertEqual((R90.FAMILIES['P']['count'], R90.FAMILIES['D']['count']), (24, 12))
        self.assertEqual(R90.LADDER, (0.05, 0.1, 0.25, 0.5, 2.0))

    def test_every_arm_builds_and_parts_share_a_profile(self):
        from genesis.candidate_kinds import tfx as T
        D = R90.arm_descriptors(dict(T.DEFAULT))
        self.assertEqual(len(D), len(R90.ARMS['P']) * len(R90.LADDER) + len(R90.LONG_ARMS))
        self.assertEqual({D[('deepdist', 0.5)][1]['kind'], D[('tfx', 2.0)][1]['kind'], D[('mq1', 0.1)][1]['kind']},
                         {'maxsat-anytime-v1', 'tfx-v1', 'mqlib-heuristic-v1'})
        self.assertEqual(D[('aperture', R90.LONG_T)][1]['resource_profile']['cpu_seconds'], 12)

    def test_the_frozen_configuration_is_required_and_checked(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'config.json'
            with mock.patch.object(R90, 'CONFIG', p):
                with mock.patch.object(R90, 'ROOT', Path(d)):
                    with self.assertRaises(SystemExit):
                        R90.frozen_config()
                    p.write_text(json.dumps({'config': {'ws': 9}}))
                    with self.assertRaises(SystemExit):
                        R90.frozen_config()

    def test_labels(self):
        inf = math.inf
        fast = {a: 0.05 for a in R90.ARMS['P']}
        # tfx at 0.05 on every host, every champion at 2 s or never: tfx beats each and the VBS
        rs = rows(24, lambda i: dict(fast, **{c: 2.0 for c in R90.CHAMPIONS}))
        labels, fam = R90.analyse({'P': rs, 'D': rows(12, lambda i: dict({a: 0.05 for a in R90.ARMS['D']},
                                                                          **{c: inf for c in R90.CHAMPIONS}), 'D')})
        self.assertEqual(labels['champions_P'], 'TFX_BEATS_EVERY_CHAMPION')
        self.assertEqual(labels['vbs_P'], 'TFX_BEATS_VBS')
        self.assertEqual(labels['champions_D'], 'TFX_BEATS_EVERY_CHAMPION')
        self.assertEqual(labels['long_budget'], 'NO_CHAMPION_FINDS_MORE')
        # one champion as fast as tfx everywhere: not every champion is beaten, and the VBS is matched
        rs = rows(24, lambda i: {**fast, **{c: 2.0 for c in R90.CHAMPIONS}, 'deepdist': 0.05})
        labels, _ = R90.analyse({'P': rs, 'D': rows(12, lambda i: {a: 0.05 for a in R90.ARMS['D']}, 'D')})
        self.assertEqual(labels['champions_P'], 'MIXED')
        self.assertEqual(labels['vbs_P'], 'TFX_MATCHES_VBS')
        self.assertEqual(labels['champions_D'], 'TFX_MATCHES_CHAMPIONS')
        # a champion faster than tfx: A_CHAMPION_BEATS_TFX and VBS_BEATS_TFX
        rs = rows(24, lambda i: {**fast, **{c: 2.0 for c in R90.CHAMPIONS if c != 'spb'}, 'tfx': 2.0})
        labels, _ = R90.analyse({'P': rs, 'D': rows(12, lambda i: {a: 0.05 for a in R90.ARMS['D']}, 'D')})
        self.assertEqual(labels['champions_P'], 'A_CHAMPION_BEATS_TFX')
        self.assertEqual(labels['vbs_P'], 'VBS_BEATS_TFX')

    def test_the_vbs_is_the_per_host_best_champion(self):
        arms = R90.ARMS['P']
        rs = [row('a', dict({a: 2.0 for a in arms}, deepdist=0.1)), row('b', dict({a: 2.0 for a in arms}, tt=0.25))]
        T_ = R90.tts_table(rs, arms)
        self.assertEqual(T_['vbs'], [0.1, 0.25])
        self.assertEqual(T_['mqvbs'], [2.0, 2.0])

    def test_long_budget_counts_hosts_where_a_champion_finds_more(self):
        rs = [row('a', {a: 0.05 for a in R90.ARMS['P']}, long={'nuwls': 11}),
              row('b', {a: 0.05 for a in R90.ARMS['P']})]
        found = R90.long_budget(rs)
        self.assertEqual([(x['task_id'], x['champions_10s']) for x in found], [('a', {'nuwls': 11})])

    def test_validity(self):
        rs = rows(24, lambda i: {a: 0.05 for a in R90.ARMS['P']})
        rd = rows(12, lambda i: {a: 0.05 for a in R90.ARMS['D']}, 'D')
        self.assertIsNone(R90.validity({'P': rs, 'D': rd})[0])
        rs[0]['runs']['tt']['0.05'] = [{'value': 0, 'run': 'FAILED', 'cpu_ns': 0}] * 3   # 3 of 384: within 1%
        self.assertIsNone(R90.validity({'P': rs, 'D': rd})[0])
        rs[1]['runs']['tt']['0.1'] = [{'value': 0, 'run': 'FAILED', 'cpu_ns': 0}] * 3    # 6 of 384
        self.assertEqual(R90.validity({'P': rs, 'D': rd})[0], 'INVALID_FAILURES')
        rs[1]['runs']['tt']['0.1'] = rs[2]['runs']['tt']['0.1']
        rd[0]['long']['aperture'] = {'value': 0, 'run': 'FAILED', 'cpu_ns': 0}           # 1 of 192 Part A + C runs
        self.assertIsNone(R90.validity({'P': rs, 'D': rd})[0])
        rd[1]['long']['aperture'] = rd[2]['long']['aperture'] = rd[0]['long']['aperture']
        self.assertEqual(R90.validity({'P': rs, 'D': rd})[0], 'INVALID_FAILURES')
        rd[0]['long']['aperture'] = rd[1]['long']['aperture'] = rd[2]['long']['aperture'] = rd[3]['long']['aperture']
        for r in rs:
            r['cpu_ns']['aperture']['0.5'] = int(0.3e9)
        self.assertEqual(R90.validity({'P': rs, 'D': rd})[0], 'INVALID_CPU_DELIVERY')


class RecordB20R89(unittest.TestCase):
    def test_the_frozen_configuration(self):
        from genesis.candidate_kinds import tfx as T
        d = ROOT / 'evidence' / 'configure_tfx_b20r89'
        cfg = json.loads((d / 'config.json').read_text())
        s = json.loads((d / 'summary.json').read_text())
        self.assertIsNone(T.check_config(cfg['config']))
        self.assertEqual((cfg['config'], cfg['index']), (s['frozen'], s['frozen_index']))
        final = {int(k): v['mean_gap'] for k, v in s['final_four'].items()}
        self.assertEqual(min(final, key=lambda c: (final[c], c)), cfg['index'])
        self.assertEqual(cfg['config'], R89.configurations()[cfg['index']])
        rows = [json.loads(l) for l in (d / 'race.jsonl').read_text().splitlines() if l.strip()]
        self.assertEqual(len(rows), s['evaluations'])
        self.assertEqual(len({(r['config'], r['host'], r['seed']) for r in rows}), len(rows))
        self.assertEqual(len(json.loads((d / 'hosts.json').read_text())['tasks']), 32)
        self.assertEqual(len(json.loads((d / 'targets.json').read_text())['targets']), 32)
        self.assertEqual([r['round'] for r in s['rounds']], [0, 1, 2, 3, 4])


class RecordB20R90(unittest.TestCase):
    def test_the_labels_follow_from_the_rows(self):
        d = ROOT / 'evidence' / 'beat_the_champions_b20r90'
        s = json.loads((d / 'summary.json').read_text())
        rows = [json.loads(l) for l in (d / 'rows.jsonl').read_text().splitlines() if l.strip()]
        by = {f: [r for r in rows if r['family'] == f] for f in R90.FAMILIES}
        self.assertEqual({f: len(v) for f, v in by.items()}, {'P': 24, 'D': 12})
        self.assertEqual(len({r['task_id'] for r in rows}), 36)
        self.assertIsNone(R90.validity(by)[0])
        labels, fam = R90.analyse(by)
        self.assertEqual(labels, s['labels'])
        self.assertEqual(labels, {'champions_P': 'TFX_BEATS_EVERY_CHAMPION', 'vbs_P': 'TFX_BEATS_VBS',
                                  'champions_D': 'TFX_BEATS_EVERY_CHAMPION', 'vbs_D': 'TFX_BEATS_VBS',
                                  'long_budget': 'NO_CHAMPION_FINDS_MORE'})
        floor = sum(R90.R76.host_tts(r, 'tfx')[0] == R90.LADDER[0] for r in rows)
        self.assertEqual(floor, 33)                                          # the disclosed floor
        cfg = json.loads((ROOT / 'evidence' / 'configure_tfx_b20r89' / 'config.json').read_text())['config']
        self.assertEqual(s['tfx']['config'], cfg)


if __name__ == '__main__':
    unittest.main()
