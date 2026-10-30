"""PT-2 (`scripts/b20r177_proving_test_2.py`), PT-1 with the inadequacy gate judged bound by bound, checked on invented
families only (never A, B or C):
  * it is PT-1's code except stage 1 and the analysis: every shared function's source is PT-1's, and the pins are
    PT-1's;
  * the per-bound gate: A' is what no predecessor run certified, the discovery must be in A', and the gate fails only
    when A' is empty;
  * a registered run refuses another output and other pins; the fixed constants (fresh seeds, the strict part 1);
  * families A and B are posed under opaque ids, statuses kept back; C withholds published bounds;
  * the two statistics of parts 4 and 5, and the verdict rules on synthetic summaries;
  * end to end on invented families at tiny budgets:
    - the inadequacy gate stops the test when the predecessor certifies something in A;
    - with the predecessor's certificates on A withheld (a plumbing check of the later stages only), every stage
      runs, and a run paused after every chunk resumes to the same summary;
    - and through the REGISTERED path, with the output and the pins redirected (B20_R141's lesson)."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r177_proving_test_2 as S  # noqa: E402
import b20r159_proving_test as P1  # noqa: E402

PREREGISTRATION = '25eadb7'         # the amendment's commit, the study's run tree (preregistered at a7303de)
SHA256 = '9da64f5e8da1a61d52eea0ba0d29129c43bbaa279a0bd0a75af0ff10d546b557'

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
    def test_a_registered_run_refuses_another_output_and_other_pins(self):
        self.assertTrue(S.PREREGISTERED)
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(SystemExit):
                S.main([d])                                            # not the registered output
            with self.assertRaises(SystemExit):
                S.main([d], output=d, pinned={'frontier/engine.py': 'x'})

    def test_the_fixed_constants(self):
        import re
        self.assertEqual(S.PART1_MECHANISMS, ('derivation', 'library'))     # the strict reading (item 8)
        self.assertEqual(len(S.C_SEEDS), 10)
        self.assertEqual((S.B_A, S.B_B, S.B_C, S.P_DERIVE, S.PROGRAM_MAX_N, S.K_ABLATION),
                         (100_000, 50_000, 100_000, 0.2, 400, 5))
        self.assertEqual((S.K_GATE, S.STUDY), (3, 'b20r177'))
        for name in ('QUANTUM', 'CHUNK', 'RHO', 'C_COUNT', 'ALPHA'):
            self.assertEqual(getattr(S, name), getattr(P1, name), name)
        self.assertNotEqual(S.SEALED_SEED, P1.SEALED_SEED)
        self.assertFalse(set(S.C_SEEDS) & set(P1.C_SEEDS))
        others = [x for x in (ROOT / 'scripts').glob('*.py') if x.name != 'b20r177_proving_test_2.py']
        for seed in (S.SEALED_SEED,) + S.C_SEEDS:
            self.assertFalse(any(re.search(rf'\b{seed}\b', x.read_text()) for x in others), seed)
        self.assertEqual(S.pins(), S.PINNED)
        if PREREGISTRATION is not None:
            import hashlib
            import subprocess
            rel = 'scripts/b20r177_proving_test_2.py'
            out = subprocess.run(['git', '-C', str(ROOT), 'show', f'{PREREGISTRATION}:{rel}'],
                                 capture_output=True, timeout=60)
            if out.returncode == 0:
                self.assertEqual(hashlib.sha256(out.stdout).hexdigest(), SHA256)

    def test_it_is_pt1_apart_from_the_gate_and_the_amendment(self):
        import inspect
        self.assertEqual(S.MODULES, P1.MODULES)
        differ = sorted(m for m in S.MODULES if S.PINNED[m] != P1.PINNED[m])
        self.assertEqual(differ, ['conjecture/library.py'])            # the amendment (B20R177-LIBRARY) only
        for name in ('posed_a', 'posed_b', 'b_verifier', 'posed_c', 'c_label', 'double_check', 'mcnemar_one_sided',
                     'wilcoxon_less', 'holm', 'compare', 'conjecture_domain', 'invariant_domain', 'settings',
                     'run_engine', 'record', 'check_facts', 'give', 'spent_ok', 'beats', '_proved_equivalent',
                     'verdict', 'pins', 'h'):
            self.assertEqual(inspect.getsource(getattr(S, name)), inspect.getsource(getattr(P1, name)), name)
        for name in ('B_A', 'B_B', 'B_C', 'P_DERIVE', 'PROGRAM_MAX_N', 'K_ABLATION', 'PART1_MECHANISMS',
                     'PART5_REQUIRES_CONTROLS', 'ARMS_LATER', 'CLASSICAL_PROVED', 'SLICE_S', 'PAUSED'):
            self.assertEqual(getattr(S, name), getattr(P1, name), name)

    def test_the_per_bound_gate(self):
        pa = {'a1': ('d', 'vertex'), 'a2': ('d', 'vertex'), 'a3': ('d', 'vertex')}
        na = {'a1': 18, 'a2': 21, 'a3': 40}
        g = {'certified': ['a1', 'a2'], 'first': {'a1': 5, 'a2': 10}}
        p0 = [{'certified': ['a1']}, {'certified': []}, {'certified': ['a1']}]
        done = dict({f'A_P0_{k}': r for k, r in enumerate(p0)}, A_G=g)
        s = S.analyse(done, pa, {}, {}, na, {}, {}, [], False)
        self.assertTrue(s['parts']['gate'] and s['parts']['part2'])
        self.assertEqual((s['discovery'], s['discovery_bound'], s['beyond_p0']), ('a2', 21, [21, 40]))
        self.assertEqual(s['certified_A'], {'P0_0': [18], 'P0_1': [], 'P0_2': [18], 'G': [18, 21]})
        only_outside = dict(done, A_G={'certified': ['a1'], 'first': {'a1': 5}})
        s = S.analyse(only_outside, pa, {}, {}, na, {}, {}, [], False)
        self.assertTrue(s['parts']['gate'])
        self.assertFalse(s['parts']['part2'])                       # a certificate outside A' does not count
        self.assertIsNone(s['discovery'])
        everything = dict(done, A_P0_1={'certified': ['a2', 'a3']})
        s = S.analyse(everything, pa, {}, {}, na, {}, {}, [], False)
        self.assertFalse(s['parts']['gate'])
        self.assertEqual(S.verdict(dict(s, valid=True))[0], 'INADEQUACY_GATE_FAILED')

    def test_a_template_discovery_does_not_pass_part1(self):
        base = {f'A_P0_{k}': {'certified': []} for k in range(S.K_GATE)}
        base['A_G'] = {'certified': ['a'], 'first': {'a': 5}}
        for mech, ok in (('template', False), ('derivation', True), ('library', True)):
            s = S.analyse(dict(base, part1={'useful': True, 'mechanism': mech}), {'a': ('d', 'vertex')}, {}, {},
                          {'a': 18}, {}, {}, [], False)
            self.assertEqual(s['parts']['part1'], ok, mech)

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

    def test_part5_must_beat_both_controls(self):
        win = {'pass': True}
        lose = {'pass': False}
        skipped = {'skipped': 'the discovery used a starting representation'}
        self.assertTrue(S.PART5_REQUIRES_CONTROLS)
        self.assertTrue(S.beats(dict(win, vs_notebook=win, vs_given_rep=win), 'notebook'))
        self.assertFalse(S.beats(dict(win, vs_notebook=lose), 'notebook'))
        self.assertTrue(S.beats(dict(win, vs_given_rep=skipped), 'given_rep'))     # the predecessor itself
        self.assertFalse(S.beats(dict(lose, vs_given_rep=skipped), 'given_rep'))
        self.assertFalse(S.beats(dict(win, vs_notebook={'skipped': 'not run'}), 'notebook'))

    def test_the_notebook_checks_every_fact_on_every_task(self):
        facts = [{'id': 1}, {'id': 2}]
        found, units = S.check_facts({'p': 0, 'q': 0, 'r': 0}, lambda p, a: (p, a['id']) in {('q', 2), ('r', 1)}, facts)
        self.assertEqual(units, 6)
        self.assertEqual(found, {'q': 4, 'r': 5})

    def test_the_given_representation_is_copied_without_a_procedure(self):
        from genesis.conjecture.domain import ConjectureDomain
        src = ConjectureDomain(A_TEST, n_values=(6, 8))
        src.derived['derived3'] = {'ops': {'r9': 9}, 'from': 'gamma'}
        dom = S.give(ConjectureDomain(C_TEST, n_values=(6, 8)), src, 'derived3')
        self.assertEqual(dom.derived, {'derived0': {'ops': {'r9': 9}, 'from': 'given'}})
        self.assertIn('derived0', dom.approaches('c1')['representation'])

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
        if e.m.description.get('stage', '').startswith('A_P0'):
            rec['claimed'] = []
        return rec
    return wrapped


class EndToEnd(unittest.TestCase):
    def run_study(self, d, blind, slice_s=None, registered=False):
        patches = [mock.patch.object(S, 'QUANTUM', 100), mock.patch.object(S, 'CHUNK', 5),
                   mock.patch.object(S, 'K_ABLATION', 2)]
        if blind:
            patches.append(mock.patch.object(S, 'record', p0_blind(S.record)))
        if slice_s is not None:
            patches.append(mock.patch.object(S, 'SLICE_S', slice_s))
        for p in patches:
            p.start()
        try:
            kw = dict(output=d, pinned=S.pins()) if registered else {}
            return S.main([d], registered=registered, families=FAMILIES, budgets=(1500, 1500, 1500), seed=7, **kw)
        finally:
            for p in reversed(patches):
                p.stop()

    def test_the_gate_stops_a_family_wholly_within_the_predecessor(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.dict(FAMILIES, {'A': ({'a1': A_TEST['a1']}, {'a1': 'a1'})}):
                self.assertEqual(self.run_study(d, blind=False), 0)
            s = json.loads((Path(d) / 'summary.json').read_text())
        for k in range(S.K_GATE):
            self.assertIn('a1', s['certified_A'][f'P0_{k}'])       # 'd + 1' is false, and every P0 run refutes it
        self.assertEqual(s['beyond_p0'], [])
        self.assertEqual(s['verdict'], 'INADEQUACY_GATE_FAILED')
        self.assertTrue(s['valid'])

    def test_a_bound_beyond_the_predecessor_keeps_the_gate_open(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(self.run_study(d, blind=False), 0)
            s = json.loads((Path(d) / 'summary.json').read_text())
        self.assertEqual(s['beyond_p0'], ['a2'])                   # '2*d' is a proved bound: nobody refutes it
        self.assertTrue(s['parts']['gate'])
        self.assertFalse(s['parts']['part2'])                       # G's certificate on a1 is outside A'
        self.assertEqual(s['verdict'], 'NOT_PROVED_OUT')

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
        gate = tuple(f'A_P0_{k}' for k in range(S.K_GATE))
        for key in gate + ('A_G', 'part1', 'part3_procedure', 'part3_replay') + tuple(
                f'{f}_{a}' for f in 'BC' for a in S.ARMS_LATER):
            self.assertIn(key, stages)
        nb = stages['C_notebook']                                      # the facts were checked first, and charged
        self.assertEqual(nb['fact_units'], len(stages['A_G']['certified']) * len(C_TEST))
        self.assertEqual(nb['budget'], 3 * 1500 - nb['charge'])
        self.assertIn('vs_notebook', sa['stats']['C'])
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
    """The path B20_R141's tests never ran, run here for PT-2: `main` as a registered run, with the preregistration
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
