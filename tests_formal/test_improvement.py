"""B21: generation controller (W21), primitives (W22), fault-tolerant routes and expert
questions (W23)."""
import json
from pathlib import Path
import random
import unittest

from genesis.fol import parse
from genesis.learning import equational as Q
from genesis.learning import faults as FT
from genesis.learning import generations as GEN
from genesis.learning import primitives as PR
from genesis.verification.tools import ToolUnavailable, tool

EVIDENCE = Path(__file__).resolve().parents[1] / 'evidence' / 'improvement_b21'


def eq(text):
    f = parse(text)
    while f[0] == 'all':
        f = f[2]
    return Q.canon((f[1], f[2]))


def _ready():
    try:
        tool('eprover')
        from genesis import sandbox
        from genesis.formal_research import workspace as W
        W.environment()
        return sandbox.available()
    except (ToolUnavailable, Exception):
        return False


READY = _ready()


class Generations(unittest.TestCase):
    def test_decision_rule(self):
        self.assertEqual(GEN.decide({'P1': 5}, {'P1': 6})['decision'], 'ACCEPTED')
        self.assertEqual(GEN.decide({'P1': 5}, {'P1': 5})['decision'], 'ROLLED_BACK')
        r = GEN.decide({'P1': 8, 'P2': 4}, {'P1': 6, 'P2': 9})
        self.assertEqual((r['decision'], r['reason']), ('ROLLED_BACK', 'regression on an earlier panel'))
        self.assertEqual(GEN.decide({'P1': 8, 'P2': 4}, {'P1': 7, 'P2': 9})['decision'], 'ACCEPTED')

    def test_freeze_is_content_addressed(self):
        lib = [{'id': 'L0', 'text': 'a', 'proof': 'p'}]
        a, b = GEN.freeze(lib, [0.1], [0]), GEN.freeze(lib, [0.1], [0])
        self.assertEqual(a['sha256'], b['sha256'])
        self.assertNotEqual(a['sha256'], GEN.freeze(lib, [0.2], [0])['sha256'])


class Primitives(unittest.TestCase):
    def test_adversary_skips_renamings_and_counts_patterns(self):
        es = [eq('![X,Y]: s(s(X,X),Y) = s(Y,s(X,X))'), eq('![X]: s(s(X,X),s(X,X)) = X')]
        props = PR.propose(es, top=3, min_size=1, max_size=2)
        pats = [p for p, _ in props]
        self.assertIn(('fn', 's', (('var', 'P0'), ('var', 'P0'))), pats)
        self.assertNotIn(('fn', 's', (('var', 'P0'), ('var', 'P1'))), pats)

    def test_fold_unfold_extend_migrate(self):
        prim = PR.primitive(('fn', 's', (('var', 'P0'), ('var', 'P0'))), name='tnot')
        ext = PR.extend('ba_sheffer', prim)
        self.assertEqual(Q.SYSTEMS[ext]['ops']['tnot'], 1)
        self.assertTrue(Q.holds(eq('![X]: tnot(tnot(X)) = X'), 'nand'))
        self.assertFalse(Q.holds(eq('![X]: tnot(X) = X'), 'nand'))
        pool = Q.true_equations('ba_sheffer', 4, per_bucket=3)
        self.assertEqual(PR.round_trip(prim, pool)['failures'], 0)
        lib = [{'id': f'L{i}', 'eq': e, 'text': Q.text(e)} for i, e in enumerate(pool[:10])]
        back = PR.rollback(PR.migrate(lib, prim), prim)
        self.assertEqual([b['eq'] for b in back], [Q.canon(l['eq']) for l in lib])
        with self.assertRaises(ValueError):
            PR.extend('ba_sheffer', PR.primitive(('fn', 's', (('var', 'P0'), ('fn', 's', (('var', 'P0'),
                                                                                         ('var', 'P0'))))), 's'))


class Diagnosis(unittest.TestCase):
    def r(self, **kw):
        base = {'claim': 'c', 'decider': True, 'prover': 'GAVE_UP', 'kernel': 'NO_PROOF', 'countermodel': 'NONE_UP_TO_SIZE'}
        return dict(base, **kw)

    def test_verdicts(self):
        self.assertEqual(FT.diagnose(self.r(prover='THEOREM', kernel='THEOREM_CHECKED'))['verdict'], 'ACCEPTED')
        self.assertEqual(FT.diagnose(self.r(prover='THEOREM'))['verdict'], 'UNVERIFIED')        # prover alone
        self.assertEqual(FT.diagnose(self.r(decider=False, countermodel='FOUND'))['verdict'], 'REJECTED_FALSE')
        d = FT.diagnose(self.r(decider=False, prover='OFFERED', kernel='THEOREM_CHECKED'))
        self.assertEqual((d['verdict'], d['suspect']), ('DISAGREEMENT', 'decider'))
        d = FT.diagnose(self.r(decider=True, countermodel='FOUND'))
        self.assertEqual(d['verdict'], 'DISAGREEMENT')
        d = FT.diagnose(self.r(decider=False, prover='THEOREM', countermodel='FOUND'))
        self.assertEqual(d['suspect'], 'prover')

    def test_corruption_touches_a_derived_clause(self):
        proof = ("fof(ax0, axiom, a, file('p', ax0)).\n"
                 "cnf(c_0_1, plain, (s(X1,X2)=s(X2,X1)), inference(spm,[status(thm)],[ax0])).\n")
        bad = FT.corrupt_proof(proof, random.Random(0))
        self.assertIn('s(X1,X2)!=s(X2,X1)', bad)
        self.assertTrue(bad.startswith("fof(ax0, axiom, a, file('p', ax0))."))

    def test_simulated_expert_is_labelled(self):
        ex = FT.SimulatedExpert('ba_sheffer', 0.0, 1)
        q = ex.answer(FT.question('c', 'r'), eq('![X,Y]: s(X,Y) = s(Y,X)'))
        self.assertEqual((q['answer'], q['answered_by']), (True, 'SIMULATED_EXPERT'))


class Hints(unittest.TestCase):
    """The B21 ground-hint repair, on a step from a Wolfram lemma chain:
    c_0_56 = rw(rw(rw(rw(spm(c_0_51, c_0_52), c_0_53), c_0_44), c_0_54), c_0_44), where
    c_0_44 is commutativity. Before the repair no hints were found and Lean failed."""

    def test_rewrite_after_superposition_modulo_commutativity(self):
        from genesis.formal_research import fof_lean as F
        cl = lambda t: F._shape(parse(t), 'fof')
        parents = [cl('![X1,X2,X3]: s(s(s(X1,X2),X3),s(X1,s(s(X1,X2),s(X3,s(X1,X2))))) = s(s(X1,X2),s(X3,s(X1,X2)))'),
                   cl('![X1,X2,X3]: s(s(s(X1,s(X1,X1)),X2),s(X3,X2)) = X2'),
                   cl('![X1,X2,X3]: s(s(X1,X2),s(s(X3,s(X3,X3)),X2)) = X2'),
                   cl('![X1,X2]: s(X1,X2) = s(X2,X1)'),
                   cl('![X1,X2]: s(X1,s(X2,s(X1,X2))) = s(X1,X1)')]
        mine = cl('![X1,X2]: s(X1,s(X2,X2)) = s(X1,s(X2,X1))')
        hints = F.ground_hints(parents, mine, [])
        self.assertTrue(hints)
        self.assertIn(3, {i for i, _ in hints})                  # a commutativity instance is among them

    def test_commutativity_matching_records_swaps(self):
        from genesis.formal_research import fof_lean as F
        s = lambda a, b: ('fn', 's', (a, b))
        X, Y, a, b = ('var', 'X'), ('var', 'Y'), ('fn', 'a', ()), ('fn', 'b', ())
        m, swaps = next(F._match_c(s(X, s(Y, Y)), s(s(b, b), a), {}, {'s': (0, 'X1', 'X2')}))
        self.assertEqual(m, {'X': a, 'Y': b})
        self.assertEqual(swaps, (s(s(b, b), a),))
        self.assertIsNone(next(F._match_c(s(X, X), s(a, b), {}, {'s': (0, 'X1', 'X2')}), None))


@unittest.skipUnless(READY, 'E prover or formal workspace unavailable')
class Routes(unittest.TestCase):
    def test_clean_and_faulty_claims(self):
        from genesis.verification.eprover import prove
        ax = Q.axioms('ba_sheffer')
        good = eq('![X,Y]: s(X,Y) = s(Y,X)')
        proof = prove(ax, Q.closed(good), seconds=5)['proof']
        self.assertEqual(FT.diagnose(FT.routes('ba_sheffer', good, proof=proof))['verdict'], 'ACCEPTED')
        bad = eq('![X]: s(X,X) = X')
        v = FT.diagnose(FT.routes('ba_sheffer', bad, proof=proof))['verdict']          # a proof of something else
        self.assertEqual(v, 'REJECTED_FALSE')
        corrupt = FT.corrupt_proof(proof, random.Random(1))
        if corrupt:
            self.assertNotEqual(FT.diagnose(FT.routes('ba_sheffer', good, proof=corrupt))['verdict'], 'ACCEPTED')

    def test_definitional_extension_is_bound_to_the_base_statement(self):
        from genesis.formal_research import fof_lean as F
        from genesis.verification.eprover import prove
        prim = PR.primitive(('fn', 's', (('var', 'P0'), ('var', 'P0'))), name='tnot')
        ext = PR.extend('ba_sheffer', prim)
        target = eq('![X,Y]: s(X,s(Y,s(Y,Y))) = s(X,X)')        # a Sheffer axiom: provable at once
        r = prove(Q.axioms(ext), Q.closed(target), seconds=5)
        rec = F.replay('t-b21-def', Q.axioms('ba_sheffer'), Q.closed(target), r['proof'],
                       definitions=[PR.lean_definition(prim)])
        self.assertEqual(rec['status'], 'THEOREM_CHECKED', rec)


@unittest.skipUnless((EVIDENCE / 'summary.json').exists(), 'B21 evidence not generated')
class Evidence(unittest.TestCase):
    def test_recorded(self):
        s = json.loads((EVIDENCE / 'summary.json').read_text())
        self.assertEqual(s['w23']['false_acceptances'], 0)
        self.assertIn('NOT ESTABLISHED', s['e4']['claim'])
        self.assertIn('SIMULATED', s['w23']['expert']['expert'])
        t = json.loads((EVIDENCE / 'e4' / 'transitions.json').read_text())
        for r in t['records']:
            self.assertEqual(r['decision'], GEN.decide(r['parent_scores'], r['child_scores'])['decision'])
            self.assertEqual(r['human_interventions'], 0)

    def test_followups(self):
        w22 = json.loads((EVIDENCE / 'w22_lean_followup.json').read_text())
        self.assertTrue(w22['panel_matches_main_run_targets'])
        for arm in ('primitive', 'base'):
            self.assertEqual(w22['rows'][arm]['checked'], w22['rows'][arm]['attempted'])
        w23 = json.loads((EVIDENCE / 'w23_followup.json').read_text())
        flagged = [r for r in w23['rows'] if r['false_acceptance']]
        # the recorded strict count stands; no false claim was ever accepted
        self.assertEqual(len(flagged), w23['false_acceptances'])
        self.assertTrue(all(r['truth'] and r['routes']['kernel'] == 'THEOREM_CHECKED' for r in flagged))
        self.assertFalse([r for r in w23['rows'] if r['verdict'] == 'ACCEPTED' and not r['truth']])
        self.assertIn('SIMULATED', w23['expert']['label'])


if __name__ == '__main__':
    unittest.main()
