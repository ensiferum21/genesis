"""B18 / W09–W12: representation grammar, worlds and transport, concept recovery.

Pure tests need no Lean. The evidence tests read `evidence/invention_b18/`, check its
contract, and replay the packages from their sources. They need the formal workspace
and the sandbox, and the formal suite accepts no skips.
"""
import copy
import json
from pathlib import Path
import random
import unittest

from genesis import sandbox
from genesis.formal_research import theory_package as TP
from genesis.formal_research import triangle_theory as T
from genesis.formal_research import workspace as W
from genesis.formal_research import loop as L
from genesis.invention import recovery as RV
from genesis.invention import recovery_experiment as RX
from genesis.invention import representations as R
from genesis.invention import worlds as WD

EVIDENCE = Path(__file__).resolve().parents[1] / 'evidence' / 'invention_b18'


def _ready():
    try:
        W.environment()
        return sandbox.available()
    except Exception:
        return False


READY = _ready()


class Representations(unittest.TestCase):
    def test_grammar_typechecks_and_bounds_every_proposal(self):
        reps = R.proposals()
        self.assertEqual(len(reps), 8)
        for bad in ({'decoder': 'teleport', 'k': 2}, {'decoder': 'cross', 'k': 4}, {'decoder': 'cross', 'k': '2'},
                    {'decoder': 'cross', 'k': 2, 'extra': 1}):
            with self.assertRaises(R.ProposalError):
                R.typecheck(bad)
        for r in reps:
            for field in ('semantics', 'retained', 'lost', 'cost', 'failure_conditions', 'kind', 'encoder'):
                self.assertTrue(r[field], (r['id'], field))
            self.assertEqual(r['kind'], 'conservative-definition')

    def test_screening_matches_the_known_soundness(self):
        conjs = {c['id']: c for c in R.conjectures(R.proposals())}
        sound_tf = {cid.split('_sound')[0] for cid, c in conjs.items() if cid.endswith('_sound_tf')
                    and L.screen(c)[0] is None}
        self.assertEqual(sound_tf, {'cross_2', 'ordered_2', 'adjacent_2', 'adjacent_3'})
        self.assertTrue(all(L.screen(c)[0] is not None for cid, c in conjs.items() if cid.endswith('_sound_c4')))

    def test_loss_witnesses(self):
        reps = {r['id']: r for r in R.proposals()}
        n, S = R.loss_witness(reps['cross_2'])
        self.assertEqual((n, len(S)), (5, 5))                    # the 5-cycle: triangle-free, not bipartite
        self.assertTrue(T.tf(frozenset(map(tuple, S))))
        self.assertLess(R.loss_witness(reps['ordered_2'])[0], 5)

    def test_method_returns_valid_witnesses(self):
        cross = next(r for r in R.proposals() if r['id'] == 'cross_2')
        rng = random.Random(3)
        for _ in range(20):
            n = rng.randrange(4, 12)
            edges = sorted({(u, v) for u in range(n) for v in range(u + 1, n) if rng.random() < 0.5})
            out = R.represent_and_repair(n, edges, cross, R.tf_add_ok, cpu_seconds=0.02, seed=1)
            S = frozenset(map(tuple, out['witness']))
            self.assertTrue(S <= set(edges))
            self.assertTrue(T.tf(S))
            self.assertGreaterEqual(out['value'], out['decoded_before_repair'])


class Worlds(unittest.TestCase):
    def test_world_records_and_interventions(self):
        w = WD.world('A', ['bipartite'], solver='keep-all')
        v = WD.intervene(w, 'B', add=['has_triangle'])
        self.assertEqual(v['assumptions'], ['bipartite', 'has_triangle'])
        self.assertEqual(v['lineage'], {'parent': 'A', 'intervention': {'add': ['has_triangle'], 'remove': []}})
        with self.assertRaises(ValueError):
            WD.world('C', ['flat_earth'], solver='x')
        self.assertIsNone(WD.find_model(['bipartite', 'has_triangle'], tries=3000))
        self.assertIsNotNone(WD.find_model(['has_triangle']))

    def test_judgement_rules(self):
        worlds = [WD.world('A', ['triangle_free'], solver='s'), WD.world('B', ['bipartite'], solver='s'),
                  WD.world('C', ['bipartite', 'has_triangle'], solver='s'), WD.world('D', ['max_deg_1'], solver='s')]
        st = [{'id': 'model_A', 'status': 'CHECKED', 'proof_const': 'p1'},
              {'id': 'model_B', 'status': 'CHECKED', 'proof_const': 'p2'},
              {'id': 'incons_C', 'status': 'CHECKED', 'proof_const': 'p3'},
              {'id': 'model_D', 'status': 'UNRESOLVED'},
              {'id': 'imp_bipartite__triangle_free', 'status': 'CHECKED', 'proof_const': 'p4'},
              {'id': 'imp_max_deg_1__triangle_free', 'status': 'UNRESOLVED'}]
        claims = [{'id': 'k', 'world': 'A'}, {'id': 'v', 'world': 'C'}]
        out = WD.judge(worlds, [('A', 'B'), ('A', 'D'), ('A', 'C'), ('C', 'A')], claims, st)
        self.assertEqual({k: v['status'] for k, v in out['worlds'].items()},
                         {'A': 'CONSISTENT', 'B': 'CONSISTENT', 'C': 'INCONSISTENT', 'D': 'UNKNOWN'})
        self.assertEqual([t['verdict'] for t in out['transports']],
                         ['TRANSPORTED', 'REFUSED_UNPROVED_CONDITIONS', 'REFUSED_INCONSISTENT_TARGET',
                          'REFUSED_VACUOUS_SOURCE'])
        self.assertEqual(out['transports'][0]['implication_proofs'], ['p4'])
        self.assertEqual({c['id']: c['status'] for c in out['claims']}, {'k': 'WORLD_RELATIVE', 'v': 'VACUOUS'})
        self.assertEqual(WD.equivalence('CHECKED', 'DISPROVED'), 'DISTINCT')
        self.assertEqual(WD.equivalence('CHECKED', 'UNRESOLVED'), 'UNKNOWN')
        self.assertEqual(WD.equivalence('CHECKED', 'CHECKED'), 'EQUIVALENT')


class Recovery(unittest.TestCase):
    TF = ['const', 'GT.TriangleFree']
    SIMPLE = ['const', 'HS.Simple']

    def down(self, pred):
        sub = ['app', ['app', ['app', ['app', ['const', 'HasSubset.Subset'], ['const', 'GT.Edges']],
                               ['const', 'Finset.instHasSubset']], ['bvar', 0]], ['bvar', 1]]
        return ['pi', ['const', 'GT.Edges'], ['pi', ['const', 'GT.Edges'],
                                              ['pi', sub, ['pi', ['app', pred, ['bvar', 2]], ['app', pred, ['bvar', 2]]]]]]

    def types(self, t):
        return {'GT.TriangleFree': 'GT.Edges → Prop', 'HS.Simple': 'GT.Edges → Prop',
                'Nat': 'Type'}.get(t[1]) if t[0] == 'const' else None

    def test_typed_anti_unification(self):
        g, holes = RV.anti_unify([self.down(self.TF), self.down(self.SIMPLE)], self.types)
        self.assertEqual(len(holes), 1)
        self.assertEqual(holes[0]['type'], 'GT.Edges → Prop')
        self.assertEqual(holes[0]['fillers'], [self.TF, self.SIMPLE])
        # differently typed fillers are never merged into one hole
        self.assertEqual(RV.anti_unify([self.down(self.TF), self.down(['const', 'Nat'])], self.types), (None, None))
        # subterms with loose bound variables are not abstracted (first order only)
        self.assertEqual(RV.anti_unify([['app', self.TF, ['bvar', 0]], ['app', self.TF, ['bvar', 1]]], self.types),
                         (None, None))

    def test_reification_and_leakage_check(self):
        cands = RV.candidates({'HSConj.down_tf': self.down(self.TF), 'HSConj.down_simple': self.down(self.SIMPLE)},
                              self.types)
        self.assertEqual(cands[0]['members'], ['HSConj.down_simple', 'HSConj.down_tf'])
        r = RV.reify(cands[0], 'C0')
        self.assertTrue(r['definition'].startswith('def C0 (P0 : GT.Edges → Prop) : Prop := (∀ (x0 : @GT.Edges)'))
        self.assertEqual(r['uses_hidden'], [])
        self.assertIn('= @RC.C0 @GT.TriangleFree := rfl', r['checks'][1]['lean'])
        leaky = dict(cands[0], constants=['Antitone'])
        self.assertEqual(RV.reify(leaky, 'C1')['uses_hidden'], ['Antitone'])

    def test_fresh_families_are_screened_honestly(self):
        conjs = RX.fresh_conjectures('x')
        refuted = {c['id'] for c in conjs if L.screen(c)[0] is not None}
        self.assertEqual(refuted, {f'x_nonempty_{op}' for op in RX.OPS})
        inst = RX.screen_instances(RX.instance_conjectures('RC.C0', 'concept'), 'RC.C0')
        self.assertEqual([c['id'] for c in inst if c.get('preset_counterexample')], ['inst_concept_nonempty'])


@unittest.skipUnless(READY, 'formal workspace or sandbox unavailable')
class Evidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = json.loads((EVIDENCE / 'summary.json').read_text())
        cls.pkgs = {p.parent.relative_to(EVIDENCE).as_posix(): json.loads(p.read_text())
                    for p in EVIDENCE.rglob('package.json')}

    def test_every_package_is_intact_and_was_replayed(self):
        replay = json.loads((EVIDENCE / 'replay.json').read_text())
        self.assertEqual(len(replay), len(self.pkgs))
        for name, pkg in self.pkgs.items():
            self.assertEqual(TP.integrity_problems(pkg), [], name)
            self.assertEqual(replay[f'{name}/package.json']['verdict'], 'REPLAYED', name)

    def test_representations(self):
        st = self.summary['representations']['statements']
        self.assertEqual(st['cross_2_sound_tf'], 'CHECKED')
        self.assertEqual(st['cross_3_sound_tf'], 'DISPROVED')
        self.assertTrue(all(v == 'DISPROVED' for k, v in st.items() if k.endswith('_sound_c4')))
        self.assertEqual(st['cross_2_loses_tf'], 'CHECKED')
        ev = json.loads((EVIDENCE / 'representations' / 'dev_evaluation.json').read_text())
        self.assertTrue(ev['summary']['all_witnesses_valid'])
        self.assertEqual(ev['split'], 'DEV')
        chosen = ev['chosen_representation']
        self.assertEqual(st[f'{chosen}_sound_tf'], 'CHECKED')    # the method uses only a checked representation

    def test_worlds(self):
        v = self.summary['worlds']['verdict']
        self.assertEqual(v['worlds']['W_conflict']['status'], 'INCONSISTENT')
        self.assertEqual(v['worlds']['W_bip']['status'], 'CONSISTENT')
        t = {(x['from'], x['to']): x['verdict'] for x in v['transports']}
        self.assertEqual(t[('W_tf', 'W_bip')], 'TRANSPORTED')
        self.assertEqual(t[('W_tf', 'W_conflict')], 'REFUSED_INCONSISTENT_TARGET')
        self.assertEqual(v['equivalence']['W_tf~W_bip'], 'DISTINCT')
        self.assertIn('VACUOUS', {c['status'] for c in v['claims']})

    def test_recovery(self):
        comp = json.loads((EVIDENCE / 'recovery' / 'comparison.json').read_text())
        chosen = comp['recovery']['chosen']
        self.assertEqual(chosen['uses_hidden'], [])
        self.assertGreaterEqual(len(chosen['members']), 2)
        arms = comp['arms']
        self.assertGreater(arms['concept']['proved'], arms['none']['proved'])
        self.assertGreaterEqual(arms['concept']['proved'], arms['retrieval']['proved'])
        self.assertTrue(all(a['cache_hits'] == 0 for a in arms.values()))
        concept = self.pkgs['recovery/concept']
        self.assertTrue(all(s['status'] == 'CHECKED' for s in concept['statements'] if s['id'].startswith('instance_')))

    def test_a_package_replays_from_its_sources(self):
        r = TP.replay(self.pkgs['worlds'])
        self.assertEqual(r['verdict'], 'REPLAYED', r['differences'])
        tampered = copy.deepcopy(self.pkgs['worlds'])
        tampered['statements'][0]['status'] = 'CHECKED' if tampered['statements'][0]['status'] != 'CHECKED' \
            else 'DISPROVED'
        self.assertEqual(TP.replay(tampered)['verdict'], 'DIFFERS')


if __name__ == '__main__':
    unittest.main()
