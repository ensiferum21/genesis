"""B20_R92 (design): tfx against the 2026 and 2024 MaxSAT champions with a finer ladder and ablations. Seeds are fresh,
every arm builds under one profile per part, each ablation changes only what it says, short-budget runs without an
assignment are unsuccessful but not failures, and the labels say what the preregistration says on synthetic rows."""
import importlib.util
import json
import math
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / f'{name}.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


R92 = load('b20r92_vs_mse2026')


def earlier_seeds():
    seen = set()
    for p in (ROOT / 'scripts').glob('*.py'):
        if p.name.startswith('b20r92'):
            continue
        seen |= {int(x) for x in re.findall(r'\b(2026\d{4})\b', p.read_text())}
    return seen


def row(task_id, tts, family='P', target=10, long=None, fail_short=()):
    """A synthetic row whose ladder runs give each arm the requested TTS* (inf: never reached)."""
    runs = {}
    for a in R92.ARMS[family]:
        runs[a] = {}
        for t in R92.LADDER:
            hit = not math.isinf(tts[a]) and t >= tts[a]
            x = {'value': target if hit else target - 1, 'run': 'SUCCESS', 'cpu_ns': int(t * 1e9)}
            if a in fail_short and t < R92.SHORT:
                x = {'value': 0, 'run': 'FAILED', 'cpu_ns': 0}
            runs[a][str(t)] = [x] * 3
    long = long or {}
    return {'task_id': task_id, 'family': family, 'runs': runs, 'target': target, 'target_certified': True,
            'edges': 400, 'cpu_ns': {a: {'0.5': int(0.6e9)} for a in R92.ARMS[family]},
            'long': {a: {'value': long.get(a, target), 'run': 'SUCCESS', 'cpu_ns': 1} for a in R92.LONG_ARMS},
            'exact': {'cpsat': {'claims_optimal': False, 'value': target - 1}}}


def rows(n, fn, family='P', **kw):
    return [row(f'{family}{i}', fn(i), family, **kw) for i in range(n)]


class Design(unittest.TestCase):
    def test_seeds_ladder_and_arms(self):
        seeds = {R92.FAMILIES[f]['seed'] for f in R92.FAMILIES} | {R92.BOOT_SEED}
        self.assertEqual(len(seeds), 3)
        self.assertFalse(seeds & earlier_seeds())
        self.assertEqual(R92.LADDER, (0.005, 0.01, 0.02, 0.05, 0.1, 0.25, 0.5, 2.0))
        self.assertEqual(R92.CH2026, ('pasmaxsat', 'sgat', 'aperture_gbg', 'nuwls26ub', 'aperture_kbg',
                                      'aperture_ibi', 'deepdistc', 'nuwls26'))
        self.assertEqual(len(R92.CHAMPIONS), 13)
        from genesis.candidate_kinds import maxsat2026 as M26
        self.assertEqual({R92.FIXED[c][1]['solver'] for c in R92.CH2026}, set(M26.SOLVERS))
        self.assertEqual(set(R92.ARMS['D']), {'tfx', *R92.CHAMPIONS})

    def test_every_arm_builds_and_ablations_change_only_what_they_say(self):
        from genesis.candidate_kinds import tfx as T
        cfg = json.loads((ROOT / 'evidence' / 'configure_tfx_b20r89' / 'config.json').read_text())['config']
        D = R92.arm_descriptors(cfg)
        self.assertEqual(len(D), len(R92.ARMS['P']) * len(R92.LADDER) + len(R92.LONG_ARMS))
        for a, change in R92.ABLATIONS.items():
            got = R92.tfx_config(a, cfg)
            if change is None:
                self.assertEqual(got, T.DEFAULT)
            else:
                self.assertEqual({k for k in cfg if cfg[k] != got[k]}, set(change), a)
        self.assertEqual(R92.tfx_config('tfx', cfg), cfg)

    def test_labels_and_the_ablations(self):
        inf = math.inf
        base = {a: 0.005 for a in R92.ARMS['P']}
        rs = rows(24, lambda i: {**base, **{c: 0.5 for c in R92.CHAMPIONS}, 'no_dsb': 0.005, 'no_pt': 0.05,
                                 'no_cross': inf, 'first_design': 0.01, 'no_relink_restart': 0.01 if i % 2 else 0.005})
        rd = rows(12, lambda i: {**{a: 0.005 for a in R92.ARMS['D']}, **{c: 2.0 for c in R92.CHAMPIONS}}, 'D')
        labels, fam = R92.analyse({'P': rs, 'D': rd})
        self.assertEqual(labels['champions_P'], 'TFX_BEATS_EVERY_CHAMPION')
        self.assertEqual(labels['vbs_P'], 'TFX_BEATS_VBS')
        self.assertEqual(labels['champions2026_D'], 'TFX_BEATS_EVERY_CHAMPION')
        self.assertEqual(labels['ablation_no_dsb'], 'NO_MEASURABLE_EFFECT')
        self.assertEqual(labels['ablation_no_pt'], 'HELPS')
        self.assertEqual(labels['ablation_no_cross'], 'HELPS')
        # exactly twice as slow everywhere: the interval's lower end sits on 1, so not "more than twice"
        self.assertEqual(labels['ablation_first_design'], 'UNRESOLVED')
        self.assertEqual(labels['long_budget'], 'NO_CHAMPION_FINDS_MORE')
        self.assertEqual(fam['P']['arms']['tfx']['at_floor'], 24)
        # one 2026 champion as fast as tfx: not every champion is beaten; the VBS is matched
        rs = rows(24, lambda i: {**base, **{c: 0.5 for c in R92.CHAMPIONS}, 'pasmaxsat': 0.005})
        labels, _ = R92.analyse({'P': rs, 'D': rd})
        self.assertEqual((labels['champions_P'], labels['champions2026_P'], labels['vbs_P']),
                         ('MIXED', 'MIXED', 'TFX_MATCHES_VBS'))
        # an ablated engine faster than tfx: HURTS
        rs = rows(24, lambda i: {**base, 'tfx': 0.05, **{c: 2.0 for c in R92.CHAMPIONS}})
        labels, _ = R92.analyse({'P': rs, 'D': rd})
        self.assertEqual(labels['ablation_no_dsb'], 'HURTS')

    def test_long_budget(self):
        base = {a: 0.005 for a in R92.ARMS['P']}
        rs = [row('a', base, long={'pasmaxsat': 11}), row('b', base)]
        self.assertEqual([(x['task_id'], x['champions_10s']) for x in R92.long_budget(rs)], [('a', {'pasmaxsat': 11})])

    def test_short_budget_runs_without_an_assignment_are_not_failures(self):
        rs = rows(24, lambda i: {a: 0.5 for a in R92.ARMS['P']}, fail_short=('sgat', 'aperture'))
        rd = rows(12, lambda i: {a: 0.5 for a in R92.ARMS['D']}, 'D', fail_short=('sgat',))
        self.assertIsNone(R92.validity({'P': rs, 'D': rd})[0])
        self.assertEqual(R92.host_tts(rs[0], 'sgat'), 0.5)                  # unsuccessful below 0.5, then hits
        rs[0]['runs']['sgat']['0.5'] = [{'value': 0, 'run': 'FAILED', 'cpu_ns': 0}] * 3
        self.assertEqual(R92.validity({'P': rs, 'D': rd})[0], 'INVALID_FAILURES')     # 3 of 144 + 24 at >= 0.5



class RecordB20R92(unittest.TestCase):
    def test_the_labels_follow_from_the_rows(self):
        d = ROOT / 'evidence' / 'vs_mse2026_b20r92'
        s = json.loads((d / 'summary.json').read_text())
        rs = [json.loads(l) for l in (d / 'rows.jsonl').read_text().splitlines() if l.strip()]
        by = {f: [r for r in rs if r['family'] == f] for f in R92.FAMILIES}
        self.assertEqual({f: len(v) for f, v in by.items()}, {'P': 24, 'D': 12})
        self.assertEqual(len({r['task_id'] for r in rs}), 36)
        self.assertIsNone(R92.validity(by)[0])
        labels, fam = R92.analyse(by)
        self.assertEqual(labels, s['labels'])
        self.assertEqual(labels, {
            'champions_P': 'TFX_BEATS_EVERY_CHAMPION', 'champions2026_P': 'TFX_BEATS_EVERY_CHAMPION',
            'vbs_P': 'UNRESOLVED', 'champions_D': 'TFX_BEATS_EVERY_CHAMPION',
            'champions2026_D': 'TFX_BEATS_EVERY_CHAMPION', 'vbs_D': 'TFX_BEATS_VBS',
            'long_budget': 'NO_CHAMPION_FINDS_MORE',
            **{f'ablation_{a}': 'UNRESOLVED' for a in R92.ABLATIONS}})
        # the floor B20_R90 had is gone: tfx at the shortest run time on 3 of 24 and 2 of 12 hosts
        self.assertEqual((fam['P']['arms']['tfx']['at_floor'], fam['D']['arms']['tfx']['at_floor']), (3, 2))
        # no run of any arm above its host's target, and tfx's 10 s value is the target everywhere
        for r in rs:
            vals = [x['value'] for a in r['runs'] for xs in r['runs'][a].values() for x in xs if x['run'] == 'SUCCESS']
            vals += [x['value'] for x in r['long'].values() if x['run'] == 'SUCCESS']
            self.assertLessEqual(max(vals), r['target'])
            self.assertEqual(r['long']['tfx']['value'], r['target'])
        cfg = json.loads((ROOT / 'evidence' / 'configure_tfx_b20r89' / 'config.json').read_text())['config']
        self.assertEqual(s['tfx']['config'], cfg)


if __name__ == '__main__':
    unittest.main()
