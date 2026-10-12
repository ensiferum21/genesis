"""CRPD-1: one soundness-mode record for abstractions, transports and bounds.

Modes are derived from checked obligations, never taken from the proposer; HEURISTIC and
REJECTED never admit a proof; an optimum needs matching checked bounds. The modes of the
existing B18 representations and world transports and of the B20_R1 certificate bundles
are derived from their recorded, checked evidence.
"""
import json
from itertools import combinations, permutations
from pathlib import Path
import unittest

from genesis.invention import soundness as S

ROOT = Path(__file__).resolve().parents[1]


class Derivation(unittest.TestCase):
    def test_truth_table(self):
        C, D = S.CHECKED, S.DISPROVED
        self.assertEqual(S.derive(C, C), 'EQ')
        self.assertEqual(S.derive(C, None), 'SUFF')
        self.assertEqual(S.derive(C, D), 'SUFF')
        self.assertEqual(S.derive(None, C), 'NEC')
        self.assertEqual(S.derive(D, C), 'NEC')
        self.assertEqual(S.derive(None, None), 'HEURISTIC')
        self.assertEqual(S.derive('UNRESOLVED', 'TIMEOUT'), 'HEURISTIC')       # not evidence either way
        self.assertEqual(S.derive(D, None), 'REJECTED')
        self.assertEqual(S.derive(S.VACUOUS, None), 'REJECTED')

    def test_established_never_exceeds_request_or_evidence(self):
        r = S.establish('x', requested='EQ', forward=S.CHECKED, evidence=['p1'])
        self.assertEqual((r['derived'], r['established'], r['downgraded']), ('SUFF', 'SUFF', True))
        r = S.establish('x', requested='SUFF', forward=S.CHECKED, backward=S.CHECKED, evidence=['p1', 'p2'])
        self.assertEqual(r['established'], 'SUFF')
        r = S.establish('x', requested='NEC', forward=S.CHECKED, evidence=['p1'])
        self.assertEqual(r['established'], 'HEURISTIC')
        with self.assertRaises(ValueError):
            S.establish('x', requested='BOUND')


class Licensing(unittest.TestCase):
    def test_heuristic_and_rejected_never_admit_a_proof(self):
        h = S.heuristic('learned research policy')
        self.assertEqual(S.problems(h, 'order'), [])
        for use in ('lift_positive', 'lift_negative', 'prune', 'bound_lower', 'bound_upper'):
            with self.assertRaises(S.SoundnessError):
                S.admit(h, use)
        rej = S.establish('x', requested='EQ', forward=S.DISPROVED)
        for use in S.USES:
            self.assertTrue(S.problems(rej, use), use)

    def test_one_directional_modes(self):
        suff = S.establish('x', requested='EQ', forward=S.CHECKED, evidence=['p'])
        nec = S.establish('x', requested='EQ', backward=S.CHECKED, evidence=['p'])
        self.assertTrue(S.admit(suff, 'lift_positive'))
        for use in ('prune', 'lift_negative'):
            self.assertTrue(S.problems(suff, use))
        self.assertTrue(S.admit(nec, 'prune') and S.admit(nec, 'lift_negative'))
        self.assertTrue(S.problems(nec, 'lift_positive'))
        eq = S.establish('x', requested='EQ', forward=S.CHECKED, backward=S.CHECKED, evidence=['p', 'q'])
        for use in ('order', 'lift_positive', 'lift_negative', 'prune'):
            self.assertTrue(S.admit(eq, use))

    def test_tampered_or_unsupported_records(self):
        suff = S.establish('x', requested='EQ', forward=S.CHECKED, evidence=['p'])
        forged = dict(suff, established='EQ')
        self.assertIn('record identity mismatch', S.problems(forged, 'prune'))
        forged = {k: v for k, v in dict(suff, established='EQ', derived='EQ').items() if k != 'record_id'}
        forged['record_id'] = S.digest(forged)
        self.assertIn('derived mode does not follow from the recorded obligations', S.problems(forged, 'prune'))
        bare = S.establish('x', requested='SUFF', forward=S.CHECKED)
        self.assertIn('SUFF without evidence identities', S.problems(bare, 'lift_positive'))
        self.assertEqual(S.problems({'schema': 'other'}, 'order'), ['not a soundness-mode record'])

    def test_bounds_and_optimum(self):
        lo = S.bound_record('w', side='lower', status='VALID', task_sha256='t', value=7, objective='o', evidence=['w'])
        up = S.bound_record('c', side='upper', status='VALID', task_sha256='t', value=7, objective='o', evidence=['c'])
        self.assertEqual(S.problems(lo, 'bound_lower'), [])
        self.assertTrue(S.problems(lo, 'bound_upper'))
        self.assertTrue(S.problems(lo, 'lift_positive'))
        self.assertEqual(S.optimum_problems(lo, up), [])
        up8 = S.bound_record('c', side='upper', status='VALID', task_sha256='t', value=8, objective='o', evidence=['c'])
        self.assertIn('bounds do not meet', S.optimum_problems(lo, up8))
        other = S.bound_record('c', side='upper', status='VALID', task_sha256='u', value=7, objective='o',
                               evidence=['c'])
        self.assertIn('bounds are for different tasks or objectives', S.optimum_problems(lo, other))
        bad = S.bound_record('c', side='upper', status='REJECTED', task_sha256='t', value=7, objective='o',
                             evidence=['c'])
        self.assertTrue(S.optimum_problems(lo, bad))


def _c4(n, edges):
    E = {frozenset(e) for e in edges}
    for a, b, c, d in permutations(range(n), 4):
        if all(frozenset(p) in E for p in ((a, b), (b, c), (c, d), (d, a))):
            return True
    return False


class Aliasing(unittest.TestCase):
    """CRPD-4's trigger: same abstract state, different checked outcomes, refutes one direction."""

    def test_degree_sequence_cannot_decide_c4_freeness(self):
        c7 = [(i, (i + 1) % 7) for i in range(7)]
        c4_c3 = [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 4)]
        deg = lambda E: sorted(sum(v in e for e in E) for v in range(7))
        self.assertEqual(deg(c7), deg(c4_c3))                       # same abstract state
        self.assertNotEqual(_c4(7, c7), _c4(7, c4_c3))              # different Goal (C4-free)
        abs_value = max(deg(c7)) <= 2                               # Abs: "max degree <= 2"
        ref = S.aliasing_refutation(abs_value)
        self.assertEqual(ref, {'forward': S.DISPROVED})             # max degree <= 2 does not imply C4-free
        r = S.establish('max-degree<=2 for C4-free', requested='SUFF', **ref)
        self.assertEqual(r['established'], 'REJECTED')

    def test_codegree_has_no_aliasing_pair_on_small_graphs(self):
        """Exhaustive over labelled graphs on 5 vertices: (max codegree <= 1) and C4-freeness
        never disagree, so no aliasing pair exists for this abstract predicate here (finite
        evidence, not a proof; CRPD-2 is the Lean proof)."""
        n = 5
        pairs = list(combinations(range(n), 2))
        for mask in range(1 << len(pairs)):
            E = [pairs[i] for i in range(len(pairs)) if mask >> i & 1]
            adj = {v: {w for e in E for w in e if v in e and w != v} for v in range(n)}
            codeg_ok = all(len(adj[u] & adj[v]) <= 1 for u, v in pairs)
            self.assertEqual(codeg_ok, not _c4(n, E))


class ExistingArtifacts(unittest.TestCase):
    def test_b18_representations(self):
        pkg = json.loads((ROOT / 'evidence' / 'invention_b18' / 'representations' / 'package.json').read_text())
        modes = S.representation_modes(pkg)
        by_dom = {}
        for (rid, dom), r in modes.items():
            by_dom.setdefault(dom, {}).setdefault(r['established'], []).append(rid)
        self.assertEqual(set(by_dom['c4_host_v2']), {'REJECTED'})               # every decoder refuted for C4
        self.assertEqual(len(by_dom['triangle_free_host_v1']['SUFF']), 4)
        self.assertNotIn('EQ', by_dom['triangle_free_host_v1'])                 # lossy: never exact
        suff = modes[('cross_2', 'triangle_free_host_v1')]
        self.assertEqual(suff['obligations']['backward'], S.DISPROVED)          # the checked loss witness
        self.assertTrue(S.admit(suff, 'lift_positive'))                         # decodings are valid witnesses
        self.assertTrue(S.problems(suff, 'prune'))                              # but cannot prune candidates

    def test_b18_world_transports(self):
        v = json.loads((ROOT / 'evidence' / 'invention_b18' / 'worlds' / 'package.json').read_text())['verdict']
        got = {(d['from'], d['to']): S.transport_mode(d, v['worlds'])['established'] for d in v['transports']}
        self.assertEqual(got, {('W_tf', 'W_bip'): 'SUFF', ('W_tf', 'W_deg1'): 'HEURISTIC',
                               ('W_tf', 'W_conflict'): 'REJECTED'})

    def test_b20r_certificate_bundles_give_optima(self):
        from genesis.verification import certificates as CB
        d = ROOT / 'evidence' / 'obstruction_custody_b20r'
        bundles = sorted((d / 'bundles').glob('*.json'))
        self.assertEqual(len(bundles), 12)
        for b in bundles:
            bundle = json.loads(b.read_bytes())
            r = CB.replay(bundle, lambda h: (d / 'objects' / h).read_bytes())
            lo, up = S.certificate_bound_modes(bundle, r)
            self.assertEqual(S.optimum_problems(lo, up), [], b.name)


class Wiring(unittest.TestCase):
    """The mode travels with the results that move between abstractions."""

    def test_world_judge_reproduces_b18_and_adds_modes(self):
        from genesis.invention import worlds as WD
        pkg = json.loads((ROOT / 'evidence' / 'invention_b18' / 'worlds' / 'package.json').read_text())
        v = pkg['verdict']
        claims = [{'id': c['id'], 'world': c['world']} for c in v['claims']]
        out = WD.judge(pkg['worlds'], [(d['from'], d['to']) for d in v['transports']], claims, pkg['statements'])
        strip = lambda ds: [{k: x for k, x in d.items() if k != 'soundness'} for d in ds]
        self.assertEqual(strip(out['transports']), v['transports'])          # B18 verdicts unchanged
        modes = {(d['from'], d['to']): d['soundness']['established'] for d in out['transports']}
        self.assertEqual(modes[('W_tf', 'W_bip')], 'SUFF')
        self.assertEqual(modes[('W_tf', 'W_conflict')], 'REJECTED')
        for d in out['transports']:
            if d['verdict'] != 'TRANSPORTED':
                self.assertTrue(S.problems(d['soundness'], 'lift_positive'))

    def test_research_guidance_is_heuristic(self):
        from genesis.learning import equational as Q
        from genesis.learning import research as RS
        from genesis.learning.budget import Account, StudyBudget

        def fake(axioms, goal, *, res, label):
            return {'status': 'RESOURCE_OUT', 'proof': None,
                    'resource': {'termination': 'EXITED', 'exit_code': 0, 'cpu_ns': 1000, 'wall_ns': 1000,
                                 'meter': {'kind': 'fake', 'lower_bound': False}}}
        r = RS.run('ba_sheffer', RS.Fixed(), Q.true_equations('ba_sheffer', 3, per_bucket=2),
                   account=Account(StudyBudget.from_seconds(3.0, attempt_s=1), label='g'), prover=fake)
        self.assertEqual(r['guidance']['established'], 'HEURISTIC')
        with self.assertRaises(S.SoundnessError):
            S.admit(r['guidance'], 'lift_positive')


if __name__ == "__main__":
    unittest.main()
