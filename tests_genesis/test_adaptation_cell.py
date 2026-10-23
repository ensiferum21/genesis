"""B20_R93: the adaptation cell. Synthetic studies test each part (discovery, receptors, doses and noise bands, the
ledger's inference of attempts and outcomes, composition, triage, work orders, the checkpoint and membrane, the cost
model); the record tests run the cell on the real evidence and check it against what the builder found by hand."""
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from genesis.adaptation import capabilities, metabolism                                   # noqa: E402
from genesis.adaptation.checkpoint import check, membrane                                 # noqa: E402
from genesis.adaptation.design import (arm_keys, compose, design_of, vbs_contributors,    # noqa: E402
                                       MIN_RUN_S)
from genesis.adaptation.discovery import discover                                         # noqa: E402
from genesis.adaptation.ledger import Ledger, rebuild, RETIRE_AFTER                       # noqa: E402
from genesis.adaptation.receptors import (Profile, Study, sense, stale_knowledge,           # noqa: E402
                                          arm_not_responding, outperformed, floor_effect, magnitude,
                                          focal_identity)
from genesis.adaptation.responses import RESPONSES                                        # noqa: E402

CATALOG = json.loads((ROOT / 'src/genesis/adaptation/baselines.json').read_text())
LADDER = (0.01, 0.05, 0.25, 2.0)
TINY_CATALOG = {'problem_classes': {'unweighted_partial_maxsat_anytime': {
    'source': 'test', 'as_of': '2026-10-20', 'refresh': {'month': 7, 'day': 1}, 'home_budgets_s': [60, 300],
    'entries': [{'name': 'A', 'published': '2024-07', 'leading': True, 'solver_key': 'alpha'},
                {'name': 'B', 'published': '2026-07', 'leading': True, 'solver_key': 'beta'},
                {'name': 'C', 'published': '2030-01', 'leading': True, 'solver_key': 'gamma'},
                {'name': 'D', 'published': '2024-07', 'leading': False, 'solver_key': 'delta'}]}}}


def hit_at(t0, target, miss=5):
    """An arm that reaches the target from run time t0 on (inf: never)."""
    return lambda t: target if t >= t0 else target - miss


def flat(v):
    return lambda t: v


def mkrow(i, arms, target=100, n=40, certified=True, family='P', ladder=LADDER, reps=3, long=None, ref_s=30.0,
          upper=True):
    runs = {a: {str(t): [{'value': f(t), 'run': 'SUCCESS', 'cpu_ns': int(t * 1e9)} for _ in range(reps)]
                for t in ladder} for a, f in arms.items()}
    r = {'task_id': f'h{i}', 'n': n, 'family': family, 'target': target, 'target_certified': certified, 'runs': runs,
         'reference': {'wall_s': ref_s, **({'upper': target} if upper else {})}}
    if long:
        r['long'] = long
    return r


def write_study(root, name, rows, summary=None, log=None):
    d = Path(root) / 'evidence' / name
    d.mkdir(parents=True)
    s = {'ladder': list(LADDER), 'reps': 3, 'labels': {}}
    s.update(summary or {})
    (d / 'summary.json').write_text(json.dumps(s))
    (d / 'rows.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows))
    (d / 'run.log').write_text(log if log is not None else 'pinned to CPU 0\n[   100.0s] host done\n')
    return d


def study(root, name, rows, summary=None, log=None, focal='tfx', date='2026-10-20'):
    write_study(root, name, rows, summary, log)
    arms = list(rows[0]['runs'])
    p = Profile(name.upper(), f'evidence/{name}', focal, tuple(a for a in arms if a != focal), date)
    return Study.load(p, root)


def entry(type_, evidence, severity='medium', status='OPEN', retired=()):
    return {'type': type_, 'study': 'S', 'status': status, 'severity': severity, 'evidence': evidence,
            'retired': list(retired)}


class Discovery(unittest.TestCase):
    def test_finds_tts_studies_in_batch_order_and_their_focal_arm(self):
        with tempfile.TemporaryDirectory() as tmp:
            rows = [mkrow(0, {'tfx': hit_at(0.01, 100), 'spb': hit_at(0.25, 100)})]
            write_study(tmp, 'late_b20r10', rows)
            write_study(tmp, 'early_b20r9', [mkrow(0, {'engine': hit_at(0.01, 100), 'dsb': hit_at(2.0, 100)})])
            other = Path(tmp) / 'evidence' / 'not_tts_b20r11'
            other.mkdir()
            (other / 'summary.json').write_text('{"verdict": "X"}')
            (other / 'rows.jsonl').write_text('{"a": 1}\n')
            half = Path(tmp) / 'evidence' / 'running_b20r12'
            half.mkdir()
            (half / 'rows.jsonl').write_text(json.dumps(rows[0]) + '\n')
            got = discover(tmp)
            self.assertEqual([p.study for p in got], ['B20_R9', 'B20_R10'])
            self.assertEqual([p.focal for p in got], ['engine', 'tfx'])
            self.assertEqual(got[1].competitors, ('spb',))
            self.assertEqual([p.study for p in discover(tmp, include_unfinished=True)],
                             ['B20_R9', 'B20_R10', 'B20_R12'])


class Receptors(unittest.TestCase):
    def test_floor_effect_needs_half_the_hosts_at_the_shortest_run_time(self):
        with tempfile.TemporaryDirectory() as tmp:
            at = [mkrow(i, {'tfx': hit_at(0.01, 100), 'x': hit_at(2.0, 100)}) for i in range(2)]
            above = [mkrow(i, {'tfx': hit_at(0.05, 100), 'x': hit_at(2.0, 100)}) for i in range(3)]
            self.assertEqual(len(floor_effect(study(tmp, 'a', at + above))), 0)
            c = floor_effect(study(tmp, 'b', at + above[:2]))
            self.assertEqual(c[0].evidence['hosts_at_floor'], 2)

    def test_saturation_uncertified_regime_and_size_cap(self):
        with tempfile.TemporaryDirectory() as tmp:
            rows = [mkrow(i, {'tfx': hit_at(0.01, 100), 'x': hit_at(0.05, 100)}, n=63, certified=i < 6)
                    for i in range(10)]
            types = {c.type for c in sense(study(tmp, 'a', rows), TINY_CATALOG, 63)}
            self.assertLessEqual({'SATURATION', 'UNCERTIFIED_TARGETS', 'REGIME_GAP', 'SIZE_CAP', 'MISSING_BASELINE'},
                                 types)
            rows = [mkrow(i, {'tfx': hit_at(0.01, 100), 'x': flat(90)}, n=40) for i in range(10)]
            types = {c.type for c in sense(study(tmp, 'b', rows, {'long_seconds': 60}), TINY_CATALOG, 63)}
            self.assertNotIn('SATURATION', types)
            self.assertNotIn('REGIME_GAP', types)
            self.assertNotIn('SIZE_CAP', types)

    def test_missing_baseline_only_counts_what_was_published_by_the_study_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            rows = [mkrow(0, {'tfx': hit_at(0.01, 100), 'x': hit_at(2.0, 100)})]
            st = study(tmp, 'a', rows, {'champions': {'alpha': 'sha'}}, date='2026-08-01')
            c = [c for c in sense(st, TINY_CATALOG, 63) if c.type == 'MISSING_BASELINE'][0]
            self.assertEqual(c.evidence['missing_keys'], ['beta'])         # gamma is later, delta not leading
            st = study(tmp, 'b', rows, {'champions': {'alpha': 'sha'}}, date='2025-01-01')
            self.assertFalse([c for c in sense(st, TINY_CATALOG, 63) if c.type == 'MISSING_BASELINE'])

    def test_labels_invalid_unresolved_null_ablation_and_interruption(self):
        with tempfile.TemporaryDirectory() as tmp:
            rows = [mkrow(0, {'tfx': hit_at(0.01, 100), 'no_x': hit_at(0.01, 100), 'y': hit_at(2.0, 100)})]
            st = study(tmp, 'a', rows, {'labels': {'main': 'UNRESOLVED', 'v': 'INVALID_CPU_DELIVERY',
                                                   'ablation_no_x': 'NO_MEASURABLE_EFFECT'}},
                       log='pinned to CPU 0\n[ 5.0s] a\npinned to CPU 0\n[ 7.0s] b\n')
            got = {c.type: c for c in sense(st, None, 63)}
            self.assertEqual(got['UNRESOLVED_VERDICT'].evidence['labels'], {'main': 'UNRESOLVED'})
            self.assertEqual(got['INVALID_RUN'].evidence, {'labels': ['INVALID_CPU_DELIVERY'], 'focal': 'tfx'})
            self.assertEqual(got['COMPONENT_EFFECT_UNRESOLVED'].evidence['components'],
                             {'no_x': 'NO_MEASURABLE_EFFECT'})
            self.assertEqual(got['INTERRUPTED'].evidence['starts_in_run_log'], 2)

    def test_a_flat_arm_is_flagged_an_improving_one_and_ablations_are_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            rows = [mkrow(i, {'tfx': hit_at(0.01, 100), 'stuck': flat(70), 'slow': hit_at(2.0, 100, miss=20),
                              'no_dsb': flat(70)}) for i in range(4)]
            c = arm_not_responding(study(tmp, 'a', rows, {'labels': {'ablation_no_dsb': 'HELPS'}}))
            self.assertEqual([x.evidence['subject'] for x in c], ['stuck'])
            self.assertEqual(c[0].lineage, 'ARM_NOT_RESPONDING[stuck]')
            self.assertAlmostEqual(c[0].evidence['detail']['median_share_of_target'], 0.7)
            near = [mkrow(i, {'tfx': hit_at(0.01, 100), 'near': flat(99)}) for i in range(4)]
            self.assertEqual(arm_not_responding(study(tmp, 'b', near)), [])       # within 95% of the target

    def test_a_probe_at_the_home_budget_explains_or_confirms_a_flat_arm(self):
        with tempfile.TemporaryDirectory() as tmp:
            def rows(value):
                out = [mkrow(i, {'tfx': hit_at(0.01, 100), 'stuck': flat(70)}) for i in range(4)]
                for r in out[:2]:
                    r['probes'] = {'stuck': {'budget_s': 60.0, 'value': value, 'run': 'SUCCESS'}}
                return out
            self.assertEqual(arm_not_responding(study(tmp, 'a', rows(100))), [])      # responds, only later
            c = arm_not_responding(study(tmp, 'b', rows(71)))[0]
            self.assertIn('no response at the home budget on 2 of 2', c.evidence['detail']['probe'])

    def test_outperformed_reads_the_rows_and_marks_native_arms(self):
        with tempfile.TemporaryDirectory() as tmp:
            rows = [mkrow(i, {'tfx': hit_at(2.0, 100), 'fast': hit_at(0.05, 100), 'engine': hit_at(0.25, 100),
                              'peer': hit_at(2.0, 100)}, family='D' if i else 'P') for i in range(4)]
            c = outperformed(study(tmp, 'a', rows))[0]
            self.assertEqual(sorted(c.evidence['arms']), ['engine', 'fast'])
            self.assertTrue(c.evidence['arms']['engine']['native'])
            self.assertEqual(c.evidence['arms']['fast']['families'], {'P': 1, 'D': 3})
            self.assertEqual(magnitude(c), 1.0)
            tie = [mkrow(i, {'tfx': hit_at(0.05, 100), 'fast': hit_at(0.05, 100)}) for i in range(4)]
            self.assertEqual(outperformed(study(tmp, 'b', tie)), [])

    def test_the_autoreceptor_senses_a_stale_catalog(self):
        self.assertEqual(stale_knowledge(TINY_CATALOG, '2027-06-30'), [])
        c = stale_knowledge(TINY_CATALOG, '2027-07-01')[0]
        self.assertEqual((c.type, c.evidence['due']), ('STALE_KNOWLEDGE', '2027-07-01'))
        bare = {'problem_classes': {'x': {'entries': []}}}
        self.assertEqual(stale_knowledge(bare, '2026-01-01')[0].evidence['reason'], 'no as-of date')
        self.assertEqual(stale_knowledge(CATALOG, '2026-10-20'), [])


class Doses(unittest.TestCase):
    def prog(self, type_, name, design, evidence):
        return next(r for r in RESPONSES[type_] if r.name == name).progress(design, evidence)

    def test_noise_bands(self):
        e = {'certification_s': 121, 'uncertified': 3, 'hosts': 10}
        self.assertEqual(self.prog('UNCERTIFIED_TARGETS', 'longer_certification', {'certification_s': 122}, e), 0)
        self.assertEqual(self.prog('UNCERTIFIED_TARGETS', 'longer_certification', {'certification_s': 182}, e), 1)
        self.assertEqual(self.prog('SATURATION', 'quality_at_equal_time_on_larger_instances', {'sizes': [63]},
                                   {'largest_n': 60}), 0)
        self.assertEqual(self.prog('FLOOR_EFFECT', 'extend_ladder_down', {'ladder': [0.048]}, {'floor_s': 0.05}), 0)

    def test_partial_doses(self):
        e = {'missing_keys': ['a', 'b', 'c', 'd']}
        self.assertEqual(self.prog('MISSING_BASELINE', 'acquire_baseline', {'competitors': ['a', 'z']}, e), 0.25)
        e = {'longest_budget_s': 2.0, 'competitors_home_budgets_s': [60, 300]}
        p = self.prog('REGIME_GAP', 'add_home_budgets', {'ladder': [2.0], 'long_budgets': [10.0]}, e)
        self.assertAlmostEqual(p, math.log(5) / math.log(30))
        self.assertEqual(self.prog('REGIME_GAP', 'add_home_budgets', {'ladder': [2.0], 'long_budgets': [60]}, e), 1)


def series(tmp, specs):
    """Studies from (name, rows, summary) and a ledger that observed them in order."""
    led, sts = Ledger(), []
    for i, (name, rows, summary) in enumerate(specs):
        st = study(tmp, name, rows, summary)
        led.observe(st, sense(st, TINY_CATALOG, 63))
        sts.append(st)
    return led, sts


def sat_rows(k, n=40, cert=True):
    return [mkrow(i, {'tfx': hit_at(0.05, 100), 'x': hit_at(0.25, 100)}, n=n, certified=cert) for i in range(k)]


class LedgerInference(unittest.TestCase):
    def test_an_attempt_is_a_change_not_a_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            led, _ = series(tmp, [('a', sat_rows(4), {}), ('b', sat_rows(4), {}), ('c', sat_rows(4), {})])
            lin = led.lineages['SATURATION']
            self.assertEqual((lin['status'], lin['attempts']), ('CHRONIC', []))
            self.assertEqual(lin['severity'], 'high')                     # raised once, from medium
            self.assertEqual(lin['unanswered_recurrences'], 2)

    def test_partial_dose_with_a_drop_is_improving_without_one_underdosed(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = sat_rows(2)
            led, _ = series(tmp, [('a', r, {}), ('b', r, {'champions': {'alpha': 's'}})])
            lin = led.lineages['MISSING_BASELINE']                       # alpha and beta were missing
            self.assertEqual(lin['attempts'][-1]['outcome'], 'IMPROVING')
            self.assertEqual(lin['attempts'][-1]['dose'], 0.5)
            r2 = [mkrow(i, {'tfx': hit_at(0.05, 100), 'x': hit_at(0.25, 100)}) for i in range(2)]
            led, _ = series(tmp, [('c', r2, {'long_seconds': 2.0}), ('d', r2, {'long_seconds': 10.0})])
            lin = led.lineages['REGIME_GAP']
            self.assertEqual(lin['attempts'][-1]['outcome'], 'IMPROVING')   # 60/2 -> 60/10

    def test_resolution_relapse_and_the_resolver_is_charged(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = sat_rows(2)
            led, _ = series(tmp, [('a', bad, {'labels': {'v': 'INVALID_X'}}), ('b', bad, {}),
                                  ('c', bad, {'labels': {'v': 'INVALID_Y'}})])
            lin = led.lineages['INVALID_RUN']
            self.assertEqual(lin['attempts'][0]['outcome'], 'RESOLVED')
            self.assertEqual(lin['status'], 'RELAPSE')
            self.assertEqual(led.outcomes['fix_harness_then_rerun']['RELAPSED'], 1)
            self.assertIn('INVALID_RUN@A', led.open())                    # open again, under its first sighting

    def test_full_doses_without_effect_retire_a_response(self):
        with tempfile.TemporaryDirectory() as tmp:
            specs = [(f's{i}', [mkrow(j, {'tfx': hit_at(0.05, 100), 'x': hit_at(0.25, 100)})
                                for j in range(4 * 2 ** i)], {'labels': {'m': 'UNRESOLVED'}}) for i in range(3)]
            led, _ = series(tmp, specs)
            lin = led.lineages['UNRESOLVED_VERDICT']
            self.assertEqual([a['outcome'] for a in lin['attempts']], ['PERSISTENT'] * RETIRE_AFTER)
            self.assertEqual(lin['retired'], ['more_hosts'])
            e = led.open()['UNRESOLVED_VERDICT@S0']
            self.assertEqual(led.ranked_responses(e), ['finer_ladder'])

    def test_quiet_in_studies_that_could_show_it_clears(self):
        with tempfile.TemporaryDirectory() as tmp:
            stuck = [mkrow(i, {'tfx': hit_at(0.01, 100), 'w': flat(60)}) for i in range(3)]
            fine = [mkrow(i, {'tfx': hit_at(0.01, 100), 'w': hit_at(0.25, 100)}) for i in range(3)]
            gone = [mkrow(i, {'tfx': hit_at(0.01, 100), 'v': hit_at(0.25, 100)}) for i in range(3)]
            led, _ = series(tmp, [('a', stuck, {}), ('b', fine, {}), ('c', fine, {})])
            self.assertEqual(led.lineages['ARM_NOT_RESPONDING[w]']['status'], 'CLEARED')
            led, _ = series(tmp, [('d', stuck, {}), ('e', gone, {})])
            lin = led.lineages['ARM_NOT_RESPONDING[w]']
            self.assertEqual((lin['status'], lin['resolved_by']), ('RESOLVED', 'exclude_with_disclosure'))

    def test_a_method_is_itself_by_its_configuration_and_binary(self):
        with tempfile.TemporaryDirectory() as tmp:
            rows = sat_rows(2)
            a = study(tmp, 'a', rows, {'tfx': {'config': {'K': 12}, 'binary_sha256': 'b'}})
            b = study(tmp, 'b', rows, {'tfx': {'config': {'K': 12}, 'binary_sha256': 'b', 'ablations': {'x': 1}}})
            c = study(tmp, 'c', rows, {'tfx': {'config': {'K': 13}, 'binary_sha256': 'b'}})
            self.assertEqual(focal_identity(a), focal_identity(b))
            self.assertNotEqual(focal_identity(a), focal_identity(c))

    def test_new_weaknesses_appearing_with_an_attempt_are_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = sat_rows(2)
            log2 = 'pinned to CPU 0\n[ 1.0s] a\npinned to CPU 0\n[ 2.0s] b\n'
            led = Ledger()
            for name, summary, log in (('a', {}, None), ('b', {'champions': {'alpha': 's'}}, log2)):
                st = study(tmp, name, r, summary, log)
                led.observe(st, sense(st, TINY_CATALOG, 63))
            att = led.lineages['MISSING_BASELINE']['attempts'][-1]
            self.assertEqual(att['new_alongside'], ['INTERRUPTED'])

    def test_diagnose_before_excising(self):
        led = Ledger()
        led.outcomes['exclude_with_disclosure'] = {'RESOLVED': 5, 'IMPROVING': 0, 'PERSISTENT': 0, 'UNDERDOSED': 0,
                                                   'RELAPSED': 0}
        e = entry('ARM_NOT_RESPONDING', {'arms': ['x']})
        self.assertEqual(led.ranked_responses(e), ['probe_at_home_budget', 'fix_arm_harness',
                                                   'exclude_with_disclosure'])

    def test_rebuild_is_deterministic(self):
        a, _, _ = rebuild(discover(ROOT), ROOT, CATALOG, 63)
        b, _, _ = rebuild(discover(ROOT), ROOT, CATALOG, 63)
        self.assertEqual(json.dumps(a.record(), sort_keys=True, default=str),
                         json.dumps(b.record(), sort_keys=True, default=str))


class Composition(unittest.TestCase):
    def setup(self, tmp, summary=None, rows=None):
        rows = rows or [mkrow(i, {'tfx': hit_at(0.01, 100), 'spb': hit_at(0.25, 100), 'mq': hit_at(0.25, 100)},
                              certified=i < 2) for i in range(6)]
        st = study(tmp, 'a', rows, dict({'champions': {'spb-maxsat-c-fps': 's'}}, **(summary or {})),
                   date='2026-10-20')
        led = Ledger()
        led.observe(st, sense(st, CATALOG, 63))
        return st, led

    def test_composed_design_answers_every_open_caveat_and_passes_the_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            st, led = self.setup(tmp)
            base = design_of(st)
            d, plan = compose(led, base, CATALOG, budget_s=1e9, contributors=vbs_contributors(st))
            self.assertTrue(check(d, led)['pass'])
            self.assertFalse(check(base, led)['pass'])
            self.assertLess(min(d['ladder']), 0.01)
            self.assertIn('pasmaxsat-c', d['competitors'])
            self.assertIn(60.0, d['long_budgets'])
            self.assertIn('tfx', d['long_arm_names'])
            self.assertIn('spb', d['long_arm_names'])                    # stands for a leading solver
            self.assertNotIn('mq', d['long_arm_names'])                  # not a published solver here
            self.assertEqual(plan['chosen']['UNCERTIFIED_TARGETS@A'], 'longer_certification')   # upper bounds on
            self.assertIn('upper_bounds: already in the design', plan['skipped']['UNCERTIFIED_TARGETS@A'])

    def test_a_ladder_at_the_harness_resolution_escalates_to_internal_timing(self):
        led = Ledger()
        led.lineages['FLOOR_EFFECT'] = {'type': 'FLOOR_EFFECT', 'first_seen': 'S', 'severity': 'medium',
                                        'status': 'OPEN', 'occurrences': [{'study': 'S', 'magnitude': 0.001,
                                        'evidence': {'floor_s': MIN_RUN_S, 'hosts_at_floor': 4, 'hosts': 4}}],
                                        'attempts': [], 'retired': [], 'unanswered_recurrences': 0}
        led.studies, led.designs['S'] = ['S'], {}
        base = {'study': 'S', 'focal': 'tfx', 'ladder': [MIN_RUN_S, 0.01], 'competitors': [], 'sizes': [40],
                'hosts': 4, 'arms': 2, 'long_budgets': []}
        d, plan = compose(led, base, budget_s=1e9)
        self.assertTrue(d['internal_tts'])
        self.assertIn('below the harness resolution', plan['skipped']['FLOOR_EFFECT@S'][0])

    def test_triage_defers_only_what_the_membrane_allows(self):
        with tempfile.TemporaryDirectory() as tmp:
            st, led = self.setup(tmp)
            base = design_of(st)
            full, plan = compose(led, base, CATALOG, budget_s=1e9)
            marg = plan['marginal_cost_s']
            excess = 50
            fit = compose(led, base, CATALOG, budget_s=full['estimated_runtime_s'] - excess)
            deferred = fit[1]['deferred']
            self.assertEqual(len(deferred), 1)                            # one deferral is enough here ...
            (key, why), = deferred.items()
            self.assertIn(key, ('FLOOR_EFFECT@A', 'UNCERTIFIED_TARGETS@A'))   # ... of a medium, acute caveat ...
            self.assertEqual(marg[key], min(v for k, v in marg.items()    # ... the smallest one that fits
                                            if k in ('FLOOR_EFFECT@A', 'UNCERTIFIED_TARGETS@A') and v >= excess))
            self.assertTrue(why.startswith('cost:'))
            self.assertLessEqual(fit[0]['estimated_runtime_s'], full['estimated_runtime_s'] - excess)
            self.assertTrue(check(fit[0], led)['pass'])
            tiny = compose(led, base, CATALOG, budget_s=10)
            self.assertNotIn('MISSING_BASELINE@A', tiny[1]['deferred'])   # high: never deferred to save time
            self.assertIn('over_budget', tiny[1])

    def test_anticipation_and_work_orders(self):
        with tempfile.TemporaryDirectory() as tmp:
            rows = [mkrow(i, {'tfx': hit_at(0.05, 100), 'spb': hit_at(0.25, 100)}, n=63) for i in range(24)]
            st, led = self.setup(tmp, rows=rows)
            caps = capabilities.scan([design_of(st)])
            d, plan = compose(led, design_of(st), CATALOG, budget_s=1e9, caps=caps)
            self.assertTrue(d['sequential_stopping'])                     # 60 s budgets: longer than a window
            needs = {w['need'] for w in plan['work_orders']}
            self.assertLessEqual({'extend_domain', 'quality_at_equal_time', 'sequential_stopping', 'long_budgets'},
                                 needs)

    def test_arm_names_map_to_solver_keys(self):
        keys = ['spb-maxsat-c-fps', 'nuwls-c-2026', 'nuwls-c-2026-ub', 'aperture-gbg', 'aperture-kbg', 'deepdist',
                'deepdist-c', 'pasmaxsat-c']
        got = arm_keys(['spb', 'nuwls26', 'nuwls26ub', 'aperture_gbg', 'deepdist', 'deepdistc', 'pasmaxsat', 'mq1',
                        'tfx'], keys)
        self.assertEqual(got, {'spb': 'spb-maxsat-c-fps', 'nuwls26': 'nuwls-c-2026', 'nuwls26ub': 'nuwls-c-2026-ub',
                               'aperture_gbg': 'aperture-gbg', 'deepdist': 'deepdist', 'deepdistc': 'deepdist-c',
                               'pasmaxsat': 'pasmaxsat-c'})


class CheckpointAndMembrane(unittest.TestCase):
    def test_membrane_rules(self):
        ok = {'validity': {'min_cpu_at_half': 0.45, 'max_fail_share': 0.01}, 'fresh_hosts': True}
        self.assertEqual(membrane(ok), [])
        self.assertEqual(len(membrane(dict(ok, validity={'min_cpu_at_half': 0.3}))), 1)
        self.assertEqual(len(membrane(dict(ok, validity={'max_fail_share': 0.05}))), 1)
        self.assertEqual(len(membrane(dict(ok, fresh_hosts=False))), 1)
        hi = {'K': {'type': 'SIZE_CAP', 'severity': 'high', 'status': 'CHRONIC'}}
        self.assertEqual(len(membrane(dict(ok, deferred={'K': 'cost: later'}), hi)), 1)
        self.assertEqual(membrane(dict(ok, deferred={'K': 'blocked: work order extend_domain'}), hi), [])

    def test_stale_catalog_blocks_until_refreshed(self):
        led = Ledger()
        d = {'validity': {}, 'fresh_hosts': True, 'catalog_as_of': '2026-10-20'}
        self.assertTrue(check(d, led, catalog=TINY_CATALOG, today='2027-01-01')['pass'])
        r = check(d, led, catalog=TINY_CATALOG, today='2027-07-02')
        self.assertIn('STALE_KNOWLEDGE@unweighted_partial_maxsat_anytime', r['unaddressed'])
        self.assertTrue(check(dict(d, catalog_as_of='2027-07-05'), led, catalog=TINY_CATALOG,
                              today='2027-07-06')['pass'])


class Metabolism(unittest.TestCase):
    def test_wall_time_sums_resumed_segments_and_the_fit_recovers_the_overhead(self):
        log = 'pinned to CPU 0\n[  10.0s] a\n[  40.0s] b\npinned to CPU 0\n[   5.0s] c\n[  25.0s] d\n'
        self.assertEqual(metabolism.observed_wall_s(log), 65.0)
        with tempfile.TemporaryDirectory() as tmp:
            sts = []
            for k, hosts in enumerate((4, 8)):
                rows = [mkrow(i, {'tfx': hit_at(0.01, 100), 'x': hit_at(0.25, 100)}, ref_s=10.0) for i in range(hosts)]
                d = {'arms': 2, 'reps': 3, 'ladder': list(LADDER), 'certification_mean_s': 10.0}
                runs, budget, cert = metabolism.demand(d)
                wall = hosts * (budget + 0.4 * runs + cert)
                sts.append(study(tmp, f's{k}', rows, log=f'pinned to CPU 0\n[ {wall:.3f}s] end\n'))
            m = metabolism.fit(sts)
            self.assertAlmostEqual(m['overhead_s'], 0.4, places=3)
            for v in metabolism.residuals(sts, m).values():
                self.assertAlmostEqual(v['observed_s'], v['predicted_s'], delta=1)


class Command(unittest.TestCase):
    def test_the_cell_runs_and_its_check_mode_gates(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as out:
            rows = [mkrow(i, {'tfx': hit_at(0.01, 100), 'spb': hit_at(0.25, 100)}) for i in range(4)]
            write_study(tmp, 'one_b20r1', rows)
            cmd = [sys.executable, str(ROOT / 'scripts/b20r93_cell.py'), tmp, out, '--today', '2026-10-20']
            self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 0)
            for f in ('caveats.json', 'ledger.json', 'cost_model.json', 'capabilities.json', 'next_design.json',
                      'plan.json', 'checkpoint.json', 'CAVEATS.md'):
                self.assertTrue((Path(out) / f).exists(), f)
            base = Path(out) / 'base.json'
            base.write_text(json.dumps(json.loads((Path(tmp) / 'evidence/one_b20r1/summary.json').read_text())))
            self.assertEqual(subprocess.run(cmd + ['--check', str(Path(out) / 'next_design.json')],
                                            capture_output=True).returncode, 0)
            self.assertEqual(subprocess.run(cmd + ['--check', str(base)], capture_output=True).returncode, 1)


# Studies preregistered under an earlier number but run after later records were written: study -> the first record
# written after it ran. B20_R86 ran on 23 Oct 2026, after B20_R93's records (and B20_R97's); a record's corpus is
# the evidence that existed when it was written, so it is left out of theirs.
RAN_AFTER = {'B20_R86': 98}


def real_until(batch, record=None):
    record = batch if record is None else record
    return [p for p in discover(ROOT) if int(p.study.split('_R')[1]) <= batch and RAN_AFTER.get(p.study, 0) <= record]


class RecordB20R93(unittest.TestCase):
    """The cell on the real evidence, up to B20_R90, against what the builder found by hand."""

    @classmethod
    def setUpClass(cls):
        cls.profiles = real_until(90, record=93)
        cls.led, cls.seen, cls.studies = rebuild(cls.profiles, ROOT, CATALOG, 63)

    def test_it_finds_the_studies_by_itself(self):
        self.assertEqual([p.study for p in self.profiles],
                         ['B20_R70', 'B20_R75', 'B20_R76', 'B20_R77', 'B20_R81', 'B20_R90'])
        self.assertEqual([p.focal for p in self.profiles], ['candidate', 'system', 'system', 'engine', 'found', 'tfx'])

    def test_on_b20r90_it_senses_exactly_the_caveats_found_by_hand(self):
        # B20_R90 record and Daniel's caveats: floor at 0.05 s, saturation, best-known targets, the interruption, the
        # 2026 champions left out, 10 s below the 60 s regime, n = 63 at the model's cap
        got = {c.type for c in self.seen['B20_R90']['caveats']}
        self.assertEqual(got, {'FLOOR_EFFECT', 'SATURATION', 'UNCERTIFIED_TARGETS', 'INTERRUPTED', 'MISSING_BASELINE',
                               'REGIME_GAP', 'SIZE_CAP'})
        floor = next(c for c in self.seen['B20_R90']['caveats'] if c.type == 'FLOOR_EFFECT')
        self.assertEqual((floor.evidence['floor_s'], floor.evidence['hosts_at_floor']), (0.05, 33))

    def test_it_infers_the_history_without_being_told(self):
        lin = self.led.lineages
        self.assertEqual(lin['INVALID_RUN']['attempts'][0]['study'], 'B20_R76')
        self.assertEqual(lin['INVALID_RUN']['status'], 'RESOLVED')
        self.assertEqual([(a['study'], a['outcome']) for a in lin['OUTPERFORMED']['attempts']],
                         [('B20_R75', 'PERSISTENT'), ('B20_R77', 'RESOLVED'), ('B20_R90', 'RESOLVED')])
        self.assertEqual(lin['ARM_NOT_RESPONDING[highs]']['resolved_by'], 'exclude_with_disclosure')
        mb = lin['MISSING_BASELINE']['attempts'][-1]
        self.assertEqual((mb['study'], mb['dose'], mb['outcome']), ('B20_R90', 0.444, 'IMPROVING'))
        self.assertEqual(lin['UNCERTIFIED_TARGETS']['status'], 'CHRONIC')   # certification never got longer
        self.assertEqual(lin['UNCERTIFIED_TARGETS']['attempts'], [])

    def test_from_b20r90_it_proposes_what_b20r92_did_by_hand_and_more(self):
        model = metabolism.fit(self.studies)
        caps = capabilities.scan([v['design'] for v in self.seen.values()])
        base = self.seen['B20_R90']['design']
        d, plan = compose(self.led, base, CATALOG, model, contributors=vbs_contributors(self.studies[-1]), caps=caps,
                          today='2026-10-20')
        self.assertEqual(min(d['ladder']), 0.005)                         # B20_R92 starts its ladder at 0.005 s
        self.assertLessEqual({'pasmaxsat-c', 'aperture-kbg', 'sgat-nuwls-c', 'aperture-gbg', 'nuwls-c-2026-ub'},
                             set(d['competitors']))                       # the five 2026 leaders, as B20_R92
        self.assertIn(60.0, d['long_budgets'])                            # beyond B20_R92: the 60 s regime
        self.assertGreater(max(d['sizes']), 63)                           # and the large-graph milestone
        self.assertTrue(check(d, self.led, catalog=CATALOG, today='2026-10-20')['pass'])
        self.assertFalse(check(base, self.led, catalog=CATALOG, today='2026-10-20')['pass'])
        self.assertIn('extend_domain', {w['need'] for w in plan['work_orders']})

    def test_it_knows_its_own_costs(self):
        model = metabolism.fit(self.studies)
        for k, v in metabolism.residuals(self.studies, model).items():
            self.assertLess(abs(v['predicted_s'] - v['observed_s']) / v['observed_s'], 0.15, k)



R92 = ROOT / 'evidence' / 'vs_mse2026_b20r92' / 'summary.json'


@unittest.skipUnless(R92.exists(), 'B20_R92 has not finished')
class ProspectiveB20R92(unittest.TestCase):
    """B20_R93's preregistered prospective check: what the cell, committed while B20_R92 ran, concludes from it."""

    @classmethod
    def setUpClass(cls):
        cls.profiles = real_until(92, record=93)
        cls.led, cls.seen, cls.studies = rebuild(cls.profiles, ROOT, CATALOG, 63)
        cls.lin = cls.led.lineages

    def last_attempt(self, key):
        return self.lin[key]['attempts'][-1] if self.lin[key]['attempts'] else {}

    def test_1_floor_resolved_by_the_lower_ladder(self):
        self.assertEqual(self.lin['FLOOR_EFFECT']['status'], 'RESOLVED')
        self.assertEqual(self.lin['FLOOR_EFFECT']['resolved_by'], 'extend_ladder_down')

    def test_2_missing_baselines_resolved(self):
        self.assertEqual((self.lin['MISSING_BASELINE']['status'], self.lin['MISSING_BASELINE']['resolved_by']),
                         ('RESOLVED', 'acquire_baseline'))

    def test_3_regime_gap_recurs_without_an_attempt(self):
        self.assertEqual(self.lin['REGIME_GAP']['occurrences'][-1]['study'], 'B20_R92')
        self.assertNotEqual(self.last_attempt('REGIME_GAP').get('study'), 'B20_R92')

    def test_4_chronic_ones_stay_chronic(self):
        for k in ('SATURATION', 'UNCERTIFIED_TARGETS', 'SIZE_CAP'):
            self.assertEqual(self.lin[k]['occurrences'][-1]['study'], 'B20_R92', k)
            self.assertEqual(self.lin[k]['status'], 'CHRONIC', k)

    def test_5_interruption_becomes_chronic(self):
        self.assertEqual(self.lin['INTERRUPTED']['status'], 'CHRONIC')

    def test_6_deepdist_c_does_not_respond(self):
        self.assertEqual(self.lin['ARM_NOT_RESPONDING[deepdistc]']['first_seen'], 'B20_R92')

    def test_7_not_outperformed(self):
        self.assertNotIn('OUTPERFORMED', {c.type for c in self.seen['B20_R92']['caveats']})

    def test_8_the_next_proposal(self):
        model = metabolism.fit(self.studies)
        caps = capabilities.scan([v['design'] for v in self.seen.values()])
        base = self.seen['B20_R92']['design']
        d, plan = compose(self.led, base, CATALOG, model, contributors=vbs_contributors(self.studies[-1]), caps=caps,
                          today='2026-10-20')
        self.assertTrue(check(d, self.led, catalog=CATALOG, today='2026-10-20')['pass'])
        self.assertFalse(check(base, self.led, catalog=CATALOG, today='2026-10-20')['pass'])
        self.assertIn(60.0, d['long_budgets'])
        self.assertGreater(max(d['sizes']), 63)
        self.assertIn('deepdistc', d['probes'])

    def test_9_the_cost_model_predicted_b20r92(self):
        st = next(s for s in self.studies if s.profile.study == 'B20_R92')
        observed = metabolism.observed_wall_s(st.run_log)
        self.assertLess(abs(18763 - observed) / observed, 0.15, observed)


if __name__ == '__main__':
    unittest.main()
