"""B20_R96: the autonomy layer. The certified clique-packing bound, the quality-diversity archive, the adversary, the
generic quality-at-equal-time study (on tiny synthetic designs, end to end), the study generator and the loop's
preregistration, tfxw-v2's grammar, and the adaptation cell reading a study of quality at equal time."""
from itertools import combinations
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from genesis import bounds_large as B                                   # noqa: E402
from genesis.common import canonical                                     # noqa: E402
from genesis.autonomy import adversary as ADV, archive as AR, qet as Q, studygen as SG   # noqa: E402
from genesis.models_large import LargeGraphTask                          # noqa: E402

LARGE = 'triangle_free_large_v1'


def rand_task(n, p, seed, tid='t'):
    rng = random.Random(seed)
    E = tuple((u, v) for u, v in combinations(range(n), 2) if rng.random() < p)
    return LargeGraphTask(task_id=tid, n=n, edges=E, family='erdos:x')


def brute(task):
    best, E = 0, task.edges
    for mask in range(1 << len(E)):
        es = [E[i] for i in range(len(E)) if mask >> i & 1]
        if len(es) <= best:
            continue
        nb = [0] * task.n
        for a, b in es:
            nb[a] |= 1 << b
            nb[b] |= 1 << a
        if not any(nb[a] & nb[b] for a, b in es):
            best = len(es)
    return best


class Bound(unittest.TestCase):
    def test_valid_on_small_hosts_and_exact_on_cliques(self):
        for seed in range(10):
            t = rand_task(7, 0.7, seed)
            for lp in (True, False):
                c = B.clique_packing_bound(t, seconds=5, seed=seed, use_lp=lp)
                self.assertEqual(B.check(t, c), c['upper'])
                self.assertGreaterEqual(c['upper'], brute(t))
        for n in (5, 8, 12):
            k = LargeGraphTask(task_id='k', n=n, edges=tuple(combinations(range(n), 2)), family='f')
            self.assertEqual(B.clique_packing_bound(k, seconds=5)['upper'], n * n // 4)      # Mantel exactly

    def test_tighter_than_the_triangle_packing_on_dense_hosts(self):
        from genesis import graphs_large as GL
        t = rand_task(60, 0.5, 3)
        self.assertLess(B.clique_packing_bound(t, seconds=20)['upper'], GL.triangle_packing_bound(t)['upper'])
        best = B.best_bound(t, seconds=20)
        self.assertTrue(best['method'].startswith('mantel-clique-packing-lp-colgen'))
        self.assertEqual(B.check(t, best['certificate']), best['upper'])

    def test_tampering_is_refused(self):
        t = LargeGraphTask(task_id='k', n=5, edges=tuple(combinations(range(5), 2)), family='f')
        c = B.clique_packing_bound(t, seconds=5)
        for bad in (dict(c, weights=[w * 2 for w in c['weights']]), dict(c, cliques=[[0, 1]] + c['cliques'][1:]),
                    dict(c, weights=[-1] + c['weights'][1:]), dict(c, denominator=0)):
            with self.assertRaises(ValueError):
                B.check(t, bad)
        t2 = LargeGraphTask(task_id='p', n=4, edges=((0, 1), (0, 2), (1, 2), (2, 3)), family='f')
        with self.assertRaises(ValueError):
            B.check(t2, {'cliques': [[0, 2, 3]], 'weights': [1], 'denominator': 1})


class Archive(unittest.TestCase):
    def test_elites_pareto_parents_and_round_trip(self):
        a = AR.Archive()
        x = a.add('k', {'p': 1}, {AR.cell('erdos', 128, 10): 0.99, AR.cell('erdos', 256, 10): 0.95})
        y = a.add('k', {'p': 2}, {AR.cell('erdos', 128, 10): 0.98, AR.cell('erdos', 256, 10): 0.97}, parents=[x])
        z = a.add('k', {'p': 3}, {AR.cell('erdos', 128, 10): 0.90, AR.cell('erdos', 256, 10): 0.90}, parents=[x])
        self.assertEqual(a.elites[AR.cell('erdos', 128, 10)], x)
        self.assertEqual(a.elites[AR.cell('erdos', 256, 10)], y)
        self.assertEqual(a.pareto(), sorted([y, z]))       # x is dominated by y; z scales best
        self.assertNotIn(x, a.pareto())
        self.assertEqual(a.entries[x]['children'], 2)
        self.assertAlmostEqual(a.objectives(y)['scaling'], -0.01)
        rng = random.Random(1)
        picks = a.parents(500, rng)
        self.assertGreater(picks.count(y), picks.count(x))               # fewer children, similar quality
        self.assertIn(z, picks)                                          # stepping stones keep a chance
        with tempfile.TemporaryDirectory() as d:
            a.save(Path(d) / 'a.json')
            b = AR.Archive.load(Path(d) / 'a.json')
            self.assertEqual(b.elites, a.elites)

    def test_mutation_stays_in_the_space(self):
        space = {'a': (1, 2, 3), 'b': (0.1, 0.2)}
        rng = random.Random(2)
        for _ in range(50):
            c = AR.mutate({'a': 1, 'b': 0.1}, space, rng)
            self.assertTrue(all(c[k] in space[k] for k in space))
            self.assertNotEqual(c, {'a': 1, 'b': 0.1})


class Adversary(unittest.TestCase):
    def test_it_climbs_to_the_hard_region_within_the_space(self):
        space = {'erdos': {'n': (64, 512), 'p': (0.01, 0.95)}}
        hard = lambda pt: -abs(pt[1]['p'] - 0.7) - abs(pt[1]['n'] - 400) / 1000      # hardest at p 0.7, n 400
        res = ADV.search(space, [('erdos', {'n': 128, 'p': 0.2})], hard, generations=12, mu=3, lam=9, seed=3)
        best = res[0][1][1]
        self.assertLess(abs(best['p'] - 0.7), 0.25)
        for _, (f, p) in res:
            self.assertTrue(64 <= p['n'] <= 512 and 0.01 <= p['p'] <= 0.95)


def tiny_design(tmp_seed=91919101):
    from genesis.candidate_kinds import tfxw as TW
    return {'study': 'B20_R0', 'domain': LARGE, 'cells': [['erdos', {'n': 70, 'p': 0.3}],
                                                          ['planted_cluster', {'n': 70, 'p_in': 0.8, 'p_out': 0.06}]],
            'per_cell': 2, 'host_seed': tmp_seed, 'focal': {'arm': 'tfxw', 'kind': 'tfxw-v1', 'config': dict(TW.DEFAULT),
                                                             'from': 'test'},
            'extra': [{'arm': 'kp4', 'kind': 'tfxw-v1', 'config': dict(TW.DEFAULT, kpick=4), 'from': 'test'}],
            'champions': [['deepdist', 'deepdist'], ['pasmaxsat', 'pasmaxsat-c']], 'budget': 0.3,
            'focal_short': [0.05], 'probes': [{'arm': 'probe_deepdistc', 'solver': 'deepdist-c', 'budget': 0.3,
                                               'hosts': 1}],
            'looks': [2, 4], 'alpha': 0.1, 'delta': 0.002, 'boot': 200, 'boot_seed': 7, 'bound_seconds': 5,
            'later_budgets': [], 'asked_by': {}}


class QETStudy(unittest.TestCase):
    def test_a_tiny_study_end_to_end(self):
        d = tiny_design()
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as out:
            (Path(root) / 'evidence').mkdir()
            rc = Q.main(d, out, root, isolation='process', one_core=False)
            self.assertEqual(rc, 0)
            s = json.loads((Path(out) / 'summary.json').read_text())
            rows = [json.loads(l) for l in (Path(out) / 'rows.jsonl').read_text().splitlines()]
            self.assertIn(len(rows), (2, 4))
            self.assertEqual(set(s['labels']) >= {'qet_champions', 'qet_vbs', 'short_vs_vbs_0.05', 'extra_kp4',
                                                  'probe_deepdistc'}, True)
            for r in rows:
                self.assertLessEqual(r['best_value'], r['upper']['value'])
                self.assertEqual(set(r['runs']), {'tfxw', 'kp4', 'deepdist', 'pasmaxsat'})
            self.assertIn('probe_deepdistc', rows[0]['probes'])
            # the kept evidence re-checks from its data: witness and certificate
            hosts = [LargeGraphTask.model_validate_json(canonical(t))
                     for t in json.loads((Path(out) / 'hosts.json').read_text())['tasks']]
            for i, r in enumerate(rows):
                self.assertEqual(r['evidence']['file'], f'certificates/{i:03d}.json.gz')
                v, up = Q.check_host_evidence(hosts[i], r, Path(out) / r['evidence']['file'])
                self.assertEqual((v, up), (r['best_value'], r['upper']['value']))
            import gzip
            f = Path(out) / rows[0]['evidence']['file']
            ev = json.loads(gzip.decompress(f.read_bytes()))
            ev['witness']['value'] += 1
            f.write_bytes(gzip.compress(json.dumps(ev).encode()))
            with self.assertRaises(ValueError):
                Q.check_host_evidence(hosts[0], rows[0], f)
            with self.assertRaises(ValueError):                           # another host's evidence
                Q.check_host_evidence(hosts[1], rows[1], Path(out) / rows[0]['evidence']['file'])
            # resumes: a second call finds the rows and the summary unchanged in substance
            self.assertEqual(Q.main(d, out, root, isolation='process', one_core=False), 0)

    def test_pause_before_the_limit(self):
        d = tiny_design(91919111)
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as out:
            (Path(root) / 'evidence').mkdir()
            self.assertEqual(Q.main(d, out, root, isolation='process', slice_s=0, one_core=False), Q.PAUSED)
            self.assertFalse((Path(out) / 'summary.json').exists())

    def test_labels_on_synthetic_rows(self):
        d = dict(tiny_design(), champions=[['c1', 'deepdist'], ['c2', 'deepdist']], extra=[], probes=[],
                 focal_short=[], boot=400)
        rows = []
        for i in range(20):
            m = 1000
            rows.append({'edges': m, 'best_value': 600, 'runs': {'tfxw': {'0.3': {'value': 600}},
                                                                 'c1': {'0.3': {'value': 560 + i % 3}},
                                                                 'c2': {'0.3': {'value': 550}}}})
        for i, r in enumerate(rows):
            r.update(family='erdos' if i % 2 else 'planted_cluster', n=128)
        labels, det = Q.analyse(rows, d, 0.9)
        self.assertEqual(labels['qet_champions'], 'FOCAL_BETTER_THAN_EVERY_CHAMPION')
        self.assertEqual(labels['qet_vbs'], 'FOCAL_BETTER_THAN_VBS')
        self.assertTrue(det['decided'])
        self.assertEqual(set(det['by_cell']), {'erdos:n128', 'planted_cluster:n128'})
        self.assertEqual(det['by_cell']['erdos:n128']['hosts'], 10)
        self.assertEqual(det['by_cell']['erdos:n128']['tfxw@0.3'], 1.0)
        self.assertEqual(det['by_cell']['erdos:n128']['c2@0.3'], round(401 / 451, 6))
        for r in rows:
            r['runs']['c1']['0.3']['value'] = 600
        labels, _ = Q.analyse(rows, d, 0.9)
        self.assertEqual(labels['qet_vbs'], 'FOCAL_MATCHES_VBS')
        self.assertEqual(labels['qet_champions'], 'MIXED')               # equivalent to one, better than the other

    def test_decide_groups_govern_the_stop(self):
        d = dict(tiny_design(), champions=[['c1', 'deepdist']], probes=[], focal_short=[], boot=400,
                 extra=[{'arm': 'abl', 'kind': 'tfxw-v1', 'config': {}, 'from': 'test'}])
        rows = []
        for i in range(20):
            # the focal method beats the champion clearly; the ablation is noisy around it (unresolved)
            rows.append({'edges': 1000, 'best_value': 600,
                         'runs': {'tfxw': {'0.3': {'value': 600 - (i % 2) * 6}}, 'c1': {'0.3': {'value': 550}},
                                  'abl': {'0.3': {'value': 600 - ((i + 1) % 2) * 6 - (i % 5 == 0) * 3}}}})
        labels, det = Q.analyse(rows, d, 0.9)
        self.assertEqual(labels['qet_champions'], 'FOCAL_BETTER_THAN_EVERY_CHAMPION')
        self.assertEqual(labels['extra_abl'], 'UNRESOLVED')
        self.assertTrue(det['decided'])                                   # default: champions and vbs only
        _, det = Q.analyse(rows, dict(d, decide=['champions', 'vbs', 'extra']), 0.9)
        self.assertFalse(det['decided'])                                  # the ablation is not decided yet
        _, det = Q.analyse(rows, dict(d, decide=['champions']), 0.9)
        self.assertTrue(det['decided'])
        with self.assertRaises(ValueError):
            Q.analyse(rows, dict(d, decide=['champions', 'typo']), 0.9)


class StudyGen(unittest.TestCase):
    def test_fresh_seeds_and_a_script_that_embeds_its_design(self):
        base = SG.fresh_seed(ROOT, 97)
        self.assertFalse(set(range(base, base + 10)) & SG.used_seeds(ROOT))
        cell = {'sizes': [63, 128, 256], 'quality_at_equal_time': True, 'hosts': 54, 'long_budgets': [10.0, 60.0],
                'competitors': ['pasmaxsat-c', 'deepdist'], 'probes': {'deepdistc': {'budget_s': 60.0, 'hosts': 4}}}
        frozen = SG.frozen_configs(ROOT)
        if not any(k == 'tfxw-v1' for _, k, _ in frozen):
            self.skipTest('no frozen large-graph configuration in this tree yet')
        d = SG.qet_design(cell, {'chosen': {'SIZE_CAP@B20_R75': 'extend_domain'}}, ROOT, 97)
        self.assertEqual(len(d['cells']), 4)
        self.assertEqual(d['per_cell'], 14)
        self.assertEqual(d['budget'], 10.0)
        self.assertEqual(d['later_budgets'], [60.0])
        self.assertEqual(len(d['champions']), 13)
        self.assertEqual(d['probes'][0]['solver'], 'deepdist-c')
        self.assertEqual(d['looks'], [19, 38, 56])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'b20r97_qet_large.py'
            SG.write_script(d, path, title='t', why='w', expectation='e', disclosure='a rehearsal on 4 dev hosts')
            self.assertIn('**Disclosed before running.** a rehearsal on 4 dev hosts', path.read_text())
            r = subprocess.run([sys.executable, '-c', f'import runpy; m = runpy.run_path({str(path)!r}); '
                                'import json; print(json.dumps(m["DESIGN"], sort_keys=True))'],
                               capture_output=True, text=True, env={'PYTHONPATH': str(ROOT / 'src'), 'PATH': '/usr/bin:/bin'})
            self.assertEqual(json.loads(r.stdout), json.loads(json.dumps(d)), r.stderr[-500:])
        self.assertEqual(d['decide'], ['champions', 'vbs'])              # no ablation asked: no ablation arms
        self.assertTrue(all(e['arm'] == 'previous_generation' for e in d['extra']))

    def test_an_ablation_request_gives_ablation_arms_and_holds_the_stop(self):
        from genesis.candidate_kinds import tfxw as TW
        frozen = [x for x in SG.frozen_configs(ROOT) if x[1] == 'tfxw-v1']
        if not frozen:
            self.skipTest('no frozen large-graph configuration in this tree yet')
        cell = {'sizes': [128, 256], 'quality_at_equal_time': True, 'hosts': 54, 'long_budgets': [10.0, 60.0],
                'competitors': [], 'ablation': {'hosts': 48}}
        d = SG.qet_design(cell, {'chosen': {'COMPONENT_EFFECT_UNRESOLVED@B20_R92':
                                            'dedicated_ablation_with_more_power'}}, ROOT, 97)
        focal = d['focal']['config']
        arms = {e['arm']: e['config'] for e in d['extra']}
        for name, change in SG.ABLATIONS:
            if dict(focal, **change) == focal:
                self.assertIn(name, d['components_already_off'])
                self.assertNotIn(name, arms)
            else:
                self.assertEqual(arms[name], dict(focal, **change))       # exactly one component switched off
        if dict(TW.DEFAULT) != focal:
            self.assertEqual(arms['first_design'], dict(TW.DEFAULT))
        configs = [canonical(c) for c in arms.values()]
        self.assertEqual(len(configs), len(set(configs)))                # no two extra arms run the same thing
        self.assertEqual(d['decide'], ['champions', 'vbs', 'extra'])
        how = SG.implementation(d)
        self.assertIn('does not stop before', how['dedicated_ablation_with_more_power'])
        for a in arms:
            self.assertIn(a, how['dedicated_ablation_with_more_power'])

    def test_the_cost_estimate(self):
        d = tiny_design()
        e = SG.estimate_seconds(d)
        own = (0.3 + SG.RUN_OVERHEAD_S) * 2 + (0.05 + SG.RUN_OVERHEAD_S)
        champs = 2 * (0.3 + SG.ENCODING_S + SG.RUN_OVERHEAD_S)
        self.assertAlmostEqual(e['per_host_s'], round(own + champs + 5, 1))
        probe = 1 * (0.3 + SG.ENCODING_S + SG.RUN_OVERHEAD_S)
        self.assertEqual(e['all_hosts_s'], round((own + champs + 5) * 4 + probe))
        self.assertEqual(e['first_look_s'], round((own + champs + 5) * 2 + probe))


class Grammar(unittest.TestCase):
    def test_tfxw2_space_and_v1_equivalence(self):
        from genesis.candidate_kinds import tfxw as TW, tfxw2 as T2
        self.assertEqual(set(T2.SPACE), set(TW.SPACE) | set(T2.NEW_KEYS))
        self.assertIsNone(T2.check_config(T2.from_v1(dict(TW.DEFAULT))))
        self.assertEqual(T2.SPACE['acc'], (0, 1, 2, 3, 4))
        for k in T2.NEW_KEYS:
            self.assertEqual(T2.from_v1(dict(TW.DEFAULT))[k], T2.SPACE[k][0])   # first value: v1's search



class CellReadsQET(unittest.TestCase):
    """Cell v2: a study of quality at equal time is discovered and sensed, with the large domain's size cap."""

    def write(self, root, labels, better=False):
        d = Path(root) / 'evidence' / 'qet_b20r97'
        d.mkdir(parents=True)
        design = dict(tiny_design(), study='B20_R97', bound_seconds=5, looks=[4])
        rows = []
        for i in range(4):
            f = 600 if better else 590
            rows.append({'task_id': f'h{i}', 'family': 'erdos', 'n': 256, 'edges': 1000, 'best_value': 600,
                         'runs': {'tfxw': {'0.3': {'value': f, 'run': 'SUCCESS', 'cpu_ns': 3e8}},
                                  'kp4': {'0.3': {'value': f, 'run': 'SUCCESS', 'cpu_ns': 3e8}},
                                  'deepdist': {'0.3': {'value': 600, 'run': 'SUCCESS', 'cpu_ns': 3e8}},
                                  'pasmaxsat': {'0.3': {'value': 580, 'run': 'SUCCESS', 'cpu_ns': 3e8}}},
                         'probes': {}, 'upper': {'value': 640, 'method': 'm', 'cliques': 1, 'certificate_sha256': 'x'}})
        (d / 'rows.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows))
        (d / 'summary.json').write_text(json.dumps({'schema': 'genesis-qet-study-v1', 'design': design,
                                                    'labels': labels, 'detail': {'champions': {
                                                        'deepdist': {'verdict': 'B_BETTER', 'mean_difference': -0.01},
                                                        'pasmaxsat': {'verdict': 'A_BETTER', 'mean_difference': 0.02}}}}))
        (d / 'run.log').write_text('pinned to CPU 0\n[ 10.0s] x\n')

    def test_discovered_and_sensed(self):
        from genesis.adaptation.discovery import discover
        from genesis.adaptation.design import design_of
        from genesis.adaptation.receptors import Study, sense
        catalog = json.loads((ROOT / 'src/genesis/adaptation/baselines.json').read_text())
        with tempfile.TemporaryDirectory() as root:
            self.write(root, {'qet_champions': 'A_CHAMPION_BETTER', 'qet_vbs': 'VBS_BETTER',
                              'extra_kp4': 'NO_MEASURABLE_EFFECT', 'probe_deepdistc': 'NO_RESPONSE'})
            (p,) = discover(root)
            self.assertEqual((p.study, p.kind, p.focal), ('B20_R97', 'qet', 'tfxw'))
            st = Study.load(p, root)
            got = {c.lineage: c for c in sense(st, catalog)}
            self.assertIn('OUTPERFORMED', got)
            self.assertIn('UNCERTIFIED_TARGETS', got)
            self.assertIn('ARM_NOT_RESPONDING[deepdistc]', got)
            self.assertIn('COMPONENT_EFFECT_UNRESOLVED', got)
            self.assertIn('REGIME_GAP', got)                       # 0.3 s against a 60 s home regime
            self.assertNotIn('SIZE_CAP', got)                      # n 256 under the large domain's 1023
            self.assertNotIn('SATURATION', got)                    # the focal method ends below DeepDist
            d = design_of(st)
            self.assertTrue(d['quality_at_equal_time'] and d['upper_bounds'] and d['ablation'])
            self.assertEqual(d['competitors'], ['deepdist', 'pasmaxsat-c'])

    def test_a_planned_pause_is_not_an_interruption(self):
        from genesis.adaptation.discovery import discover
        from genesis.adaptation.receptors import Study, interruption
        with tempfile.TemporaryDirectory() as root:
            self.write(root, {'qet_champions': 'MIXED', 'qet_vbs': 'FOCAL_MATCHES_VBS'})
            log = Path(root) / 'evidence' / 'qet_b20r97' / 'run.log'
            paused = ('[   0.0s] pinned to CPU 0; design sha256 x\n[6601.0s] time slice used (6600 s): paused after '
                      '20 hosts\n')
            log.write_text(paused * 2 + '[   0.0s] pinned to CPU 0; design sha256 x\n[900.0s] labels {}\n')
            (p,) = discover(root)
            self.assertEqual(interruption(Study.load(p, root)), [])               # two planned pauses, three starts
            log.write_text(paused + '[   0.0s] pinned to CPU 0\n[ 50.0s] host 21\n[   0.0s] pinned to CPU 0\n')
            (c,) = interruption(Study.load(p, root))                             # a start after a kill, not a pause
            self.assertEqual(c.evidence, {'starts_in_run_log': 3, 'planned_pauses': 1})
            log.write_text('[   0.0s] pinned to CPU 0\n[ 50.0s] host 1\n[   0.0s] pinned to CPU 0\n')
            (c,) = interruption(Study.load(p, root))
            self.assertEqual(c.evidence, {'starts_in_run_log': 2})                # as before B20_R97

    def test_saturation_when_every_strong_method_ends_equal(self):
        from genesis.adaptation.discovery import discover
        from genesis.adaptation.receptors import Study, sense
        with tempfile.TemporaryDirectory() as root:
            self.write(root, {'qet_champions': 'MIXED', 'qet_vbs': 'FOCAL_MATCHES_VBS'}, better=True)
            (p,) = discover(root)
            got = {c.type for c in sense(Study.load(p, root), None)}
            self.assertIn('SATURATION', got)
            self.assertNotIn('OUTPERFORMED', got)


R97 = ROOT / 'evidence' / 'qet_large_b20r97'


@unittest.skipUnless((R97 / 'summary.json').exists(), 'B20_R97 has not run in this tree')
class ProspectiveB20R97(unittest.TestCase):
    """Preregistered with B20_R97 (before it ran): what the adaptation cell must conclude when it reads the loop's
    first study, and how well the study generator knew its cost. Items 1-3 and 6-7 follow from the design and the
    receptors; 4, 5 and 8 are empirical."""

    @classmethod
    def setUpClass(cls):
        from genesis.adaptation.discovery import discover
        from genesis.adaptation.receptors import Study, sense
        cls.catalog = json.loads((ROOT / 'src/genesis/adaptation/baselines.json').read_text())
        cls.profiles = discover(ROOT)
        cls.profile = next(p for p in cls.profiles if p.study == 'B20_R97')
        cls.study = Study.load(cls.profile, ROOT)
        cls.got = {c.type: c for c in sense(cls.study, cls.catalog)}

    def test_1_discovered_last_as_a_study_of_quality_at_equal_time(self):
        self.assertEqual(self.profiles[-1].study, 'B20_R97')
        self.assertEqual((self.profile.kind, self.profile.focal), ('qet', 'tfxw'))

    def test_2_planned_pauses_are_not_interruptions(self):
        log = self.study.run_log
        if log.count('pinned to CPU') - 1 > log.count('): paused after '):
            self.skipTest('a restart did not follow a planned pause: INTERRUPTED is then correct')
        self.assertNotIn('INTERRUPTED', self.got)

    def test_3_no_size_cap_under_the_large_domain(self):
        self.assertNotIn('SIZE_CAP', self.got)

    def test_4_values_separate_the_methods(self):
        self.assertNotIn('SATURATION', self.got)          # empirical: on more than 10% of hosts the values differ

    def test_5_targets_stay_uncertified_on_large_hosts(self):
        c = self.got.get('UNCERTIFIED_TARGETS')           # empirical: bounds above the best known value
        self.assertIsNotNone(c)
        self.assertGreater(c.evidence['mean_bound_gap'], 0.01)

    def test_6_the_home_regime_is_still_missing(self):
        self.assertIn('REGIME_GAP', self.got)             # 10 s here, the champions' home regime is 60 s

    def test_7_the_next_design_asks_for_the_staged_budget(self):
        from genesis.autonomy import loop
        design, _, chk, _ = loop._cell(str(ROOT), '2026-10-22')
        self.assertTrue(chk['pass'])
        self.assertIn(60.0, design['long_budgets'])

    def test_8_the_generator_knew_its_cost_within_a_quarter(self):
        from genesis.adaptation.metabolism import observed_wall_s
        s = json.loads((R97 / 'summary.json').read_text())
        e = SG.estimate_seconds(s['design'])
        probes = sum(p['hosts'] * (p['budget'] + SG.ENCODING_S + SG.RUN_OVERHEAD_S) for p in s['design']['probes'])
        predicted = e['per_host_s'] * s['hosts_run'] + probes
        observed = observed_wall_s(self.study.run_log)
        self.assertLess(abs(predicted - observed) / observed, 0.25, (predicted, observed))


@unittest.skipUnless((R97 / 'summary.json').exists(), 'B20_R97 has not run in this tree')
class RecordB20R97(unittest.TestCase):
    """The record of B20_R97 on its evidence: the preregistered script unchanged, the labels and the stop follow from
    the rows, validity, and every host's witness and bound re-check from the kept data."""

    @classmethod
    def setUpClass(cls):
        cls.s = json.loads((R97 / 'summary.json').read_text())
        cls.rows = [json.loads(l) for l in (R97 / 'rows.jsonl').read_text().splitlines() if l.strip()]
        cls.hosts = [LargeGraphTask.model_validate_json(canonical(t))
                     for t in json.loads((R97 / 'hosts.json').read_text())['tasks']]

    def test_the_preregistered_script_and_design(self):
        import hashlib
        import runpy
        script = ROOT / 'scripts' / 'b20r97_qet_large.py'
        digest = hashlib.sha256(script.read_bytes()).hexdigest()
        self.assertEqual(digest, '892b5a11c8f4ccc921e4548b3adb75314c931bd089dab4d231f54920c3407d58')
        self.assertIn(digest, (ROOT / 'docs' / 'PREREGISTRATIONS.md').read_text())
        design = runpy.run_path(str(script))['DESIGN']
        self.assertEqual(json.loads(json.dumps(design)), self.s['design'])

    def test_labels_and_the_stop_follow_from_the_rows(self):
        d = self.s['design']
        level = Q.AT.look_level(d['alpha'], len(d['looks']))
        self.assertEqual(self.s['stopped_at'], 19)
        self.assertEqual(len(self.rows), 19)
        labels, det = Q.analyse(self.rows, d, level)
        self.assertTrue(det['decided'])
        self.assertEqual(labels, self.s['labels'])
        self.assertEqual(labels['qet_champions'], 'FOCAL_BETTER_THAN_EVERY_CHAMPION')
        self.assertEqual(labels['qet_vbs'], 'FOCAL_BETTER_THAN_VBS')
        self.assertEqual(labels['short_vs_vbs_1'], 'FOCAL_BETTER_THAN_VBS')
        for e in d['extra']:
            self.assertEqual(labels[f"extra_{e['arm']}"], 'NO_MEASURABLE_EFFECT')
        self.assertEqual(labels['probe_deepdistc'], 'NO_RESPONSE')
        self.assertEqual(det['focal_strictly_best_hosts'], 17)
        looks = [json.loads(l) for l in (R97 / 'looks.jsonl').read_text().splitlines() if l.strip()]
        self.assertEqual([(x['hosts'], x['decided'], x['labels']) for x in looks], [(19, True, labels)])

    def test_validity(self):
        invalid, cpu, fail = Q.validity(self.rows, self.s['design'])
        self.assertIsNone(invalid)
        self.assertTrue(all(v >= 10.0 for v in cpu.values()))
        self.assertTrue(all(v == 0 for v in fail.values()))

    def test_every_witness_and_bound_rechecks(self):
        self.assertEqual([h.task_id for h in self.hosts[:19]], [r['task_id'] for r in self.rows])
        gaps = []
        for i, r in enumerate(self.rows):
            v, up = Q.check_host_evidence(self.hosts[i], r, R97 / r['evidence']['file'])
            self.assertEqual((v, up), (r['best_value'], r['upper']['value']))
            gaps.append((up - v) / up)
        self.assertAlmostEqual(sum(gaps) / len(gaps), 0.1081, places=3)

    def test_hosts_are_fresh(self):
        from genesis.domains import adapter
        a = adapter(LARGE)
        ident = lambda t: a.exposure_identity(t)['canonical']
        seen = set()
        for p in sorted((ROOT / 'evidence').glob('*/hosts.json')):
            if p.parent.name == R97.name:
                continue
            data = json.loads(p.read_text())
            for t in data.get('tasks', []) if isinstance(data, dict) else []:
                if isinstance(t, dict) and t.get('domain') == LARGE:
                    seen.add(ident(LargeGraphTask.model_validate_json(canonical(t))))
        self.assertEqual(len(seen), 16)                                  # B20_R95's training hosts
        mine = [ident(h) for h in self.hosts]
        self.assertEqual(len(set(mine)), 56)                             # distinct among themselves
        self.assertFalse(seen & set(mine))                              # and unseen before


if __name__ == '__main__':
    unittest.main()
