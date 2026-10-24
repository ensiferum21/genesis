"""The research-object layer (`src/genesis/objects/`; docs/OMEGA_RECURSIVE_INVENTION.md §3; fixtures): types and
kinds as data with lineage (new ones registered by composition, refused when unknown); validation; run with type
checks, pre- and postconditions under one fuel budget and a depth limit; a failed postcondition reported, never
repaired; adapters that give exactly what the existing languages give; a composition; an improver gated on unfamiliar
tasks; an improver of improvers (typed self-application); exact storage in the vault with a record of every run."""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.autonomy import process as P  # noqa: E402
from genesis.objects import core as O  # noqa: E402
from genesis.objects import kinds as KI  # noqa: E402
from genesis.objects import types as TY  # noqa: E402
from genesis.representation import relations as R  # noqa: E402

TRAIN = [r.to_json() for r in (R.clause([True, True, True]), R.parity(3, 1), R.and_gate(3), R.exactly(3, 1),
                               R.nae(3), R.clause([True, False]))]
GATE = [r.to_json() for r in (R.or_gate(3), R.parity(3, 0), R.at_least(3, 2), R.clause([False, False, True]),
                              R.at_most(3, 1))]
FINAL = [r.to_json() for r in (R.exactly(3, 2), R.from_predicate(3, lambda z: z[0] <= z[1] <= z[2]),
                               R.clause([True, False, False]), R.parity(3, 1).negate(0))]


def synthesizer(bound=1, max_ancillas=0):
    return O.make('Synthesizer', {'max_ancillas': max_ancillas, 'bound': bound, 'uniform': False,
                                  'space': {'max_ancillas': [0, 1, 2], 'bound': [1, 2, 3, 4, 6, 8]}},
                  'gadget-synth', {'relation': 'Relation'}, {'gadget': ['Option', 'Gadget']}, post=['exact_gadget'],
                  name='MILP gadget synthesiser')


MEASURE = O.make('Measure', {}, 'synth-yield', {'synthesizer': 'Object', 'relations': ['List', 'Relation']},
                 {'yield': 'Int'}, post=['nonnegative'], name='exact gadgets produced')


def improver(variants=6, step=2, slot='synthesizer', space=None):
    d = {'variants': variants, 'step': step, 'slot': slot, 'seed': 3, 'space': space}
    return O.make('Improver', d, 'improver', {'target': 'Object', 'measure': 'Object', 'train': 'Task',
                                              'unfamiliar': 'Task'},
                  {'object': 'Object', 'admitted': 'Bool', 'train_yield': 'Int'}, name='parameter improver')


class TypesAndKinds(unittest.TestCase):
    def test_types_as_data(self):
        reg = TY.register(TY.SEED, 'BitVector', ['List', 'Int'], refine=['binary', 'nonempty'], lineage={'by': 't'})
        self.assertEqual(reg['parent'], TY.SEED['version'])
        self.assertTrue(TY.check([0, 1, 1], 'BitVector', reg))
        self.assertFalse(TY.check([0, 2], 'BitVector', reg))
        self.assertFalse(TY.check([], 'BitVector', reg))
        with self.assertRaises(ValueError):
            TY.check([0], 'BitVector')                      # unknown to the earlier registry
        with self.assertRaises(ValueError):
            TY.register(reg, 'Bad', ['List', 'Nope'])
        with self.assertRaises(ValueError):
            TY.register(reg, 'BitVector', 'Int')
        self.assertTrue(TY.check({'a': [1, 0]}, ['Map', 'Str', 'BitVector'], reg))

    def test_kinds_beyond_the_seed_set(self):
        self.assertIn('Sense', KI.SEED['kinds'])
        reg = KI.register(KI.SEED, 'CertificateProducer', 'mathematics', 'accessibility', {'by': 'test'})
        self.assertEqual(reg['kinds']['CertificateProducer']['storage'], 'DiscoveryRecord')
        with self.assertRaises(ValueError):
            KI.register(reg, 'Sense', 'perception', 'accessibility')
        with self.assertRaises(ValueError):
            KI.register(reg, 'X', 'nowhere', 'accessibility')
        obj = O.make('CertificateProducer', {'expr': {'op': 'const', 'v': 1}}, 'expr', {}, {'value': 'Int'})
        self.assertIsNotNone(O.validate(obj))                # unknown to the seed registry
        self.assertIsNone(O.validate(obj, kinds=reg))


class Run(unittest.TestCase):
    def test_a_sense_in_the_expression_language(self):
        degree_mean = O.make('Sense', {'expr': {'op': 'mean', 'of': {'op': 'input', 'name': 'degrees'}},
                                       'output': 'value'}, 'expr', {'degrees': ['List', 'Int']}, {'value': 'Real'},
                             effect='accessibility', post=['nonnegative', 'finite'])
        res = O.run(degree_mean, {'degrees': [1, 2, 3]}, P.Fuel(10))
        self.assertTrue(res['ok'])
        self.assertEqual(res['outputs']['value'], 2)
        bad = O.run(degree_mean, {'degrees': ['x']}, P.Fuel(10))
        self.assertFalse(bad['ok'])
        self.assertIn('input', bad['violations'][0])
        neg = O.make('Sense', {'expr': {'op': '-', 'a': {'op': 'const', 'v': 0}, 'b': {'op': 'const', 'v': 3}}},
                     'expr', {}, {'value': 'Int'}, post=['nonnegative'])
        res = O.run(neg, {}, P.Fuel(5))
        self.assertFalse(res['ok'])
        self.assertEqual(res['violations'], ['postcondition nonnegative failed'])
        self.assertEqual(res['outputs']['value'], -3)          # reported, not repaired
        wrong = dict(degree_mean, effect='information')
        self.assertIn('contradicts', O.validate(wrong))

    def test_fuel_and_depth(self):
        loop = {'op': 'map', 'var': 'x', 'over': {'op': 'input', 'name': 'xs'},
                'body': {'op': 'map', 'var': 'y', 'over': {'op': 'input', 'name': 'xs'},
                         'body': {'op': '*', 'a': {'op': 'input', 'name': 'x'}, 'b': {'op': 'input', 'name': 'y'}}}}
        big = O.make('Sense', {'expr': loop}, 'expr', {'xs': ['List', 'Int']}, {'value': 'Any'})
        res = O.run(big, {'xs': list(range(200))}, P.Fuel(100))
        self.assertFalse(res['ok'])
        self.assertIn('node budget', res['violations'][0])
        with self.assertRaises(P.OutOfFuel):
            O.run(synthesizer(), {'relation': TRAIN[0]}, P.Fuel(1))

    def test_adapters_match_the_languages(self):
        from genesis.representation import gadgets as GD
        from genesis.science import acquire as Q
        rel = R.clause([True, True, True])
        res = O.run(synthesizer(bound=6, max_ancillas=1), {'relation': rel.to_json()}, P.Fuel(5))
        g, _ = GD.synthesize_milp(rel, max_ancillas=1, bound=6)
        self.assertEqual(res['outputs']['gadget'], g.to_json())
        ev = O.make('Gadget', g.to_json(), 'gadget-eval', {'x': 'Assignment'}, {'penalty': 'Int'})
        self.assertEqual(O.run(ev, {'x': [0, 0, 0]}, P.Fuel(3))['outputs']['penalty'], g.min_over_ancillas((0, 0, 0)))
        pairs = [[0, {f: 0.1 * (i + 1) for i, f in enumerate(('eig', 'dec', 'decf', 'eigall', 'decall', 'decfall',
                                                              'ent', 'maxp', 'pf', 'seen', 'left', 'one'))}]]
        acq = O.make('ExperimentDesign', Q.EIG, 'acquire', {'n_exp': 'Int', 'pairs': 'Any'},
                     {'scores': ['List', 'Real']})
        self.assertEqual(O.run(acq, {'n_exp': 2, 'pairs': pairs}, P.Fuel(3))['outputs']['scores'],
                         [float(x) for x in Q.scores(Q.EIG, 2, [(i, f) for i, f in pairs])])

    def test_a_composition(self):
        s1 = O.make('Sense', {'expr': {'op': 'len', 'of': {'op': 'input', 'name': 'xs'}}, 'output': 'n'}, 'expr',
                    {'xs': ['List', 'Int']}, {'n': 'Int'})
        s2 = O.make('Sense', {'expr': {'op': '/', 'a': {'op': 'sum', 'of': {'op': 'input', 'name': 'xs'}},
                                       'b': {'op': 'input', 'name': 'n'}}, 'output': 'avg'}, 'expr',
                    {'xs': ['List', 'Int'], 'n': 'Int'}, {'avg': 'Real'})
        seq = O.make('Composition', {'steps': [s1, s2], 'outputs': ['avg']}, 'sequence', {'xs': ['List', 'Int']},
                     {'avg': 'Real'})
        self.assertEqual(O.run(seq, {'xs': [2, 4, 6]}, P.Fuel(20))['outputs']['avg'], 4)


class Improvement(unittest.TestCase):
    def test_improver_gated_on_unfamiliar_tasks(self):
        weak = synthesizer(bound=1)
        res = O.run(improver(), {'target': weak, 'measure': MEASURE, 'train': {'relations': TRAIN},
                                 'unfamiliar': {'relations': GATE}}, P.Fuel(500))
        self.assertTrue(res['ok'], res['violations'])
        out = res['outputs']
        self.assertTrue(out['admitted'])
        self.assertGreater(out['unfamiliar']['candidate'], out['unfamiliar']['incumbent'])
        self.assertEqual(out['object']['lineage']['parent'], O.oid(weak))
        same = O.run(improver(variants=0), {'target': weak, 'measure': MEASURE, 'train': {'relations': TRAIN},
                                            'unfamiliar': {'relations': GATE}}, P.Fuel(200))
        self.assertFalse(same['outputs']['admitted'])
        self.assertEqual(same['outputs']['object'], weak)

    def test_an_improver_of_improvers(self):
        lvl2 = improver(variants=1, step=1)                    # no space of its own: it varies its target's
        imp_measure = O.make('Measure', {}, 'improver-yield',
                             {'improver': 'Object', 'base': 'Object', 'base_measure': 'Object', 'train': 'Task',
                              'gate': 'Task', 'final': 'Task'}, {'yield': 'Int'})
        task = {'base': synthesizer(bound=1), 'base_measure': MEASURE, 'train': {'relations': TRAIN},
                'gate': {'relations': GATE}, 'final': {'relations': FINAL}}
        lvl3 = improver(variants=3, step=2, slot='improver', space={'variants': [1, 2, 4, 6, 8], 'step': [1, 2, 3]})
        res = O.run(lvl3, {'target': lvl2, 'measure': imp_measure, 'train': task,
                           'unfamiliar': dict(task, final={'relations': GATE + FINAL})}, P.Fuel(5000))
        self.assertTrue(res['ok'], res['violations'])
        self.assertEqual(res['outputs']['object']['kind'], 'Improver')
        self.assertTrue(res['outputs']['tried'])


class Vault(unittest.TestCase):
    def test_storage_and_run_records(self):
        from genesis.vault import Vault as V
        with tempfile.TemporaryDirectory() as d:
            v = V(Path(d) / 'vault')
            s = O.make('Sense', {'expr': {'op': 'max', 'of': {'op': 'input', 'name': 'xs'}}}, 'expr',
                       {'xs': ['List', 'Int']}, {'value': 'Int'})
            res = O.run(s, {'xs': [3, 9, 1]}, P.Fuel(5), vault=v)
            aid, rid = res['record']['object'], res['record']['run']
            self.assertEqual(v.get(aid)['type'], 'ObservableSpec')
            self.assertEqual(v.get(aid)['content'], s)
            self.assertEqual(v.get(rid)['parents'], [aid])
            self.assertTrue(v.get(rid)['content']['ok'])
            raw = v.raw(aid)
            v.close()
            v2 = V(Path(d) / 'vault')
            self.assertEqual(v2.raw(aid), raw)
            v2.close()


if __name__ == '__main__':
    unittest.main()
