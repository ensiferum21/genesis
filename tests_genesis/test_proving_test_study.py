"""PT-1's draft study (`scripts/b20r159_proving_test.py`), checked before it is preregistered, on invented families
only (never A, B or C):
  * the draft refuses a registered run;
  * families A and B are posed under opaque ids, statuses kept back; C withholds published bounds;
  * the two statistics of parts 4 and 5, and the verdict rules on synthetic summaries;
  * end to end on invented families at tiny budgets:
    - the inadequacy gate stops the test when the predecessor certifies something in A;
    - with the predecessor's certificates on A withheld (a plumbing check of the later stages only), every stage
      runs, and a run paused after every chunk resumes to the same summary."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r159_proving_test as S  # noqa: E402

A_TEST = {'a1': ('d + 1', 'vertex'), 'a2': ('2*d', 'vertex')}
B_TEST = {'s1': 'alpha <= max_degree', 's2': 'radius <= diameter'}
C_TEST = {'c1': ('d + 1', 'vertex'), 'c2': ('2*d', 'vertex'), 'c3': ('di + dj - 1', 'edge')}


def verify_b(pid, art):
    from genesis.conjecture import invariants as I
    from genesis.conjecture import statement as ST
    G = I.Graph(art['n'], [tuple(x) for x in art['edges']])
    return 1.0 if G.connected() and ST.Statement(B_TEST[pid]).check(G)['violated'] else 0.0


FAMILIES = {'A': (A_TEST, {p: p for p in A_TEST}), 'B': (B_TEST, verify_b), 'C': C_TEST}


class Design(unittest.TestCase):
    def test_the_draft_refuses_a_registered_run(self):
        self.assertFalse(S.PREREGISTERED)
        with tempfile.TemporaryDirectory() as d, self.assertRaises(SystemExit):
            S.main([d])

    def test_the_families_are_posed_opaquely(self):
        from genesis.conjecture import sealed as SD
        from genesis.conjecture import wowii as W
        pa, na = S.posed_a(424242)
        self.assertEqual(sorted(na.values()), sorted(SD.PROVING_TEST_HOLDOUT))
        self.assertTrue(all(p.startswith('A') and str(na[p]) not in p for p in pa))
        self.assertEqual(pa, S.posed_a(424242)[0])
        self.assertNotEqual(set(pa), set(S.posed_a(424243)[0]))
        pb, nb = S.posed_b(424242)
        self.assertEqual(len(pb), len(W.DISPROVED) + len(W.OPEN))
        self.assertFalse(set(nb.values()) & set(W.PROVED))
        self.assertEqual({nb[p]: t for p, t in pb.items()}, {k: W.TEXT[k] for k in nb.values()})

    def test_c_pools_draws_without_repeats(self):
        from genesis.conjecture import generate as GN
        one, _, w1 = S.posed_c(7, (991001,), count=60)
        two, _, w2 = S.posed_c(7, (991001, 991002), count=60)
        self.assertTrue(set(one) <= set(two))
        fs = [f for f, _ in two.values()]
        self.assertFalse(any(GN.equivalent(a, b) for i, a in enumerate(fs) for b in fs[i + 1:]))
        self.assertTrue(all(p.startswith('C') and k == 'vertex' for p, (f, k) in two.items()))

    def test_c_withholds_published_bounds(self):
        self.assertTrue(S.c_label('d + m')[0])                       # Merris
        self.assertTrue(S.c_label('sqrt(2*m^3/d + 2*d^2)')[0])       # bound 18, a bound of A
        self.assertEqual(S.c_label('d + 1'), (False, None))

    def test_the_two_statistics(self):
        imp = {'certified': ['p1', 'p2', 'p3', 'p4', 'p5', 'p6', 'p7'],
               'first': {f'p{i}': 10 * i for i in range(1, 8)}}
        pre = {'certified': ['p1', 'p2', 'p3', 'p4', 'p5', 'p6', 'p7'],
               'first': {f'p{i}': 100 * i for i in range(1, 8)}}
        s = S.compare(imp, pre, [f'p{i}' for i in range(1, 9)])
        self.assertEqual((s['improved_only'], s['predecessor_only'], s['shared']), (0, 0, 7))
        self.assertAlmostEqual(s['p_first'], 1 / 128)
        self.assertTrue(s['pass'])                                    # faster on all 7 shared: 2 x 1/128 < 0.05
        s = S.compare(imp, dict(pre, first={k: v / 10 for k, v in imp['first'].items()}), ['p1', 'p2'])
        self.assertFalse(s['pass'])                                   # the predecessor faster: nothing
        few = {'certified': ['p1', 'p2', 'p3', 'p4', 'p5'], 'first': {f'p{i}': 1 for i in range(1, 6)}}
        none = {'certified': [], 'first': {}}
        s = S.compare(few, none, ['p1', 'p2', 'p3', 'p4', 'p5'])
        self.assertEqual(s['improved_only'], 5)
        self.assertAlmostEqual(s['p_mcnemar'], 1 / 32)
        self.assertFalse(s['pass'])                                   # 1/32 x 2 (Holm) is not below 0.05

    def test_the_verdict_rules(self):
        parts = {'gate': True, 'part1': True, 'part2': True, 'part3': True, 'part4': True, 'part5': True}
        self.assertEqual(S.verdict({'valid': True, 'parts': parts}), ('PROVED_OUT', []))
        self.assertEqual(S.verdict({'valid': False, 'parts': parts}), ('INVALID', []))
        self.assertEqual(S.verdict({'valid': True, 'parts': dict(parts, gate=False)}), ('INADEQUACY_GATE_FAILED', []))
        self.assertEqual(S.verdict({'valid': True, 'parts': dict(parts, part1=False, part5=False)}),
                         ('NOT_PROVED_OUT', ['part1', 'part5']))


def p0_blind(record):
    """A plumbing check only: the predecessor's certificates on A are withheld, so the later stages run."""
    def wrapped(e, problems):
        rec = record(e, problems)
        if e.m.description.get('stage') == 'A_P0':
            rec['claimed'] = []
        return rec
    return wrapped


class EndToEnd(unittest.TestCase):
    def run_study(self, d, blind, slice_s=None):
        patches = [mock.patch.object(S, 'QUANTUM', 100), mock.patch.object(S, 'CHUNK', 5),
                   mock.patch.object(S, 'K_ABLATION', 2)]
        if blind:
            patches.append(mock.patch.object(S, 'record', p0_blind(S.record)))
        if slice_s is not None:
            patches.append(mock.patch.object(S, 'SLICE_S', slice_s))
        for p in patches:
            p.start()
        try:
            return S.main([d], registered=False, families=FAMILIES, budgets=(1500, 1500, 1500), seed=7)
        finally:
            for p in reversed(patches):
                p.stop()

    def test_the_gate_stops_an_adequate_family(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(self.run_study(d, blind=False), 0)
            s = json.loads((Path(d) / 'summary.json').read_text())
        self.assertIn('a1', s['certified_A']['P0'])                   # 'd + 1' is false, and P0 refutes it
        self.assertEqual(s['verdict'], 'INADEQUACY_GATE_FAILED')
        self.assertTrue(s['valid'])

    def test_every_stage_runs_and_a_paused_run_resumes_to_the_same_summary(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            self.assertEqual(self.run_study(a, blind=True), 0)
            codes = []
            while not codes or codes[-1] != 0:
                codes.append(self.run_study(b, blind=True, slice_s=-1))
                self.assertLess(len(codes), 200)
            self.assertIn(S.PAUSED, codes)
            sa, sb = (json.loads((Path(x) / 'summary.json').read_text()) for x in (a, b))
            stages = json.loads((Path(a) / 'stages.json').read_text())
        for key in ('A_P0', 'A_G', 'part1', 'part3_procedure', 'part3_replay', 'B_improved', 'B_predecessor',
                    'C_improved', 'C_predecessor'):
            self.assertIn(key, stages)
        self.assertTrue(sa['parts']['gate'] and sa['parts']['part2'])
        self.assertEqual(sa['discovery'], 'a1')
        self.assertTrue(sa['valid'])
        self.assertIn(sa['verdict'], ('PROVED_OUT', 'NOT_PROVED_OUT'))
        self.assertEqual(stages['C_improved']['budget'], 3 * 1500 - stages['C_improved']['charge'])
        self.assertEqual(stages['C_predecessor']['budget'], 3 * 1500)
        strip = lambda s: {k: v for k, v in s.items() if k != 'code_identity'}
        self.maxDiff = None
        self.assertEqual(strip(sa), strip(sb))



class RegisteredPath(unittest.TestCase):
    """The path B20_R141's tests never ran, run here for PT-1: `main` as a registered run, with the preregistration
    flag set, the output and the pins redirected, and the posing functions returning invented families (the sealed
    ones are never touched). Its validity must hold, and any other registered output is refused."""

    def test_a_registered_run_is_valid(self):
        with tempfile.TemporaryDirectory() as d:
            patches = [mock.patch.object(S, 'PREREGISTERED', True), mock.patch.object(S, 'OUTPUT', Path(d)),
                       mock.patch.object(S, 'PINNED', S.pins()), mock.patch.object(S, 'QUANTUM', 100),
                       mock.patch.object(S, 'CHUNK', 5), mock.patch.object(S, 'K_ABLATION', 2),
                       mock.patch.object(S, 'posed_a', lambda seed: (A_TEST, {p: p for p in A_TEST})),
                       mock.patch.object(S, 'posed_b', lambda seed: (B_TEST, {p: p for p in B_TEST})),
                       mock.patch.object(S, 'b_verifier', lambda numbers: verify_b),
                       mock.patch.object(S, 'posed_c', lambda seed, seeds: (C_TEST, {p: None for p in C_TEST}, [])),
                       mock.patch.object(S, 'record', p0_blind(S.record))]
            for p in patches:
                p.start()
            try:
                self.assertEqual(S.main([d], budgets=(1500, 1500, 1500), seed=7), 0)
                s = json.loads((Path(d) / 'summary.json').read_text())
                with self.assertRaises(SystemExit):
                    S.main([str(Path(d) / 'elsewhere')], budgets=(1500, 1500, 1500), seed=7)
            finally:
                for p in reversed(patches):
                    p.stop()
        self.assertTrue(s['pins_ok'] and s['spent_ok'] and s['valid'], s)
        self.assertEqual(s['audit_hits'], [])
        self.assertTrue(s['preregistered'])
        self.assertIn(s['verdict'], ('PROVED_OUT', 'NOT_PROVED_OUT'))


if __name__ == '__main__':
    unittest.main()
