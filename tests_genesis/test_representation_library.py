"""The representation language, stage A continued (fixtures): the library admits only exact gadgets (two checkers),
only improvements, keeps lineage and a parent chain, and serves a whole orbit by transport; compiling constraint
problems through the library is exact (satisfiability, Max-CSP with uniform gadgets, constrained optimisation),
checked by brute force against the problem itself; missing relations are reported, parked in the vault as dormant
problems, and reactivated once (bounded, never twice by a trigger, never by a null trigger) when a verified gadget is
announced; archived representations are byte-exact across a restart."""
from itertools import product
from pathlib import Path
import random
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.representation import compile as C  # noqa: E402
from genesis.representation import gadgets as GD  # noqa: E402
from genesis.representation import library as LB  # noqa: E402
from genesis.representation import relations as R  # noqa: E402
from genesis.vault import Vault  # noqa: E402


def lib_with(*rels, uniform=False):
    lib = LB.EMPTY
    for r in rels:
        g, rep = GD.synthesize_milp(r, max_ancillas=2, bound=6, uniform=uniform)
        lib = LB.register(lib, r, g, {'synthesizer': 'milp', 'params': {'uniform': uniform}, 'tried': rep['tried']})
    return lib


def random_csp(rng, n, m, rel_of):
    cons = []
    for _ in range(m):
        vs = rng.sample(range(n), 3)
        cons.append({'relation': rel_of(rng).to_json(), 'vars': vs, 'weight': rng.randint(1, 3)})
    return {'n': n, 'constraints': cons, 'objective': None}


def best_direct(problem, score):
    return min(score(x) for x in product((0, 1), repeat=problem['n']))


class Library(unittest.TestCase):
    def test_admission_lineage_and_orbit(self):
        c3 = R.clause([True, True, True])
        g, rep = GD.synthesize_milp(c3, max_ancillas=1, bound=6)
        lib = LB.register(LB.EMPTY, c3, g, {'synthesizer': 'milp'})
        self.assertEqual(lib['parent'], LB.version(LB.EMPTY))
        self.assertEqual(lib['entries'][c3.id()]['lineage'], {'synthesizer': 'milp'})
        with self.assertRaises(ValueError):                 # not an improvement
            LB.register(lib, c3, g, {'synthesizer': 'again'})
        bad = GD.Gadget(3, 0, 1, [-1, -1, -1], {})
        with self.assertRaises(ValueError):
            LB.register(LB.EMPTY, c3, bad, {})
        other = R.clause([False, True, False])               # the same orbit
        self.assertTrue(LB.supports(lib, other))
        self.assertTrue(GD.check(LB.lookup(lib, other), other)['exact'])
        self.assertIsNone(LB.lookup(lib, R.exactly(3, 1)))
        self.assertEqual(LB.register(LB.EMPTY, c3, g, {'synthesizer': 'milp'}), lib)   # values, not state

    def test_inverse(self):
        rng = random.Random(3)
        for _ in range(30):
            r = R.random_relation(4, rng)
            perm = list(range(4))
            rng.shuffle(perm)
            flips = rng.randrange(16)
            self.assertEqual(r.transform(perm, flips).transform(*LB.inverse(perm, flips, 4)), r)


class Compile(unittest.TestCase):
    def test_satisfiability_is_exact(self):
        lib = lib_with(R.exactly(3, 1))
        rng = random.Random(11)
        for _ in range(12):
            p = random_csp(rng, 7, 4, lambda r: R.exactly(3, 1))
            for c in p['constraints']:
                c['weight'] = 1
            bqp, info = C.compile(p, lib, 'satisfy')
            v, z = C.brute_force(bqp)
            sat = best_direct(p, lambda x: C.verify(p, x)[0]) == 0
            self.assertEqual(v == 0, sat)
            if v == 0:
                self.assertEqual(C.verify(p, C.decode(z, info))[0], 0)

    def test_max_csp_is_exact_with_uniform_gadgets(self):
        rels = [R.clause([True, True, True]), R.nae(3)]
        lib = lib_with(*rels, uniform=True)
        rng = random.Random(12)
        for _ in range(10):
            def rel_of(r):
                base = r.choice(rels)
                return base.transform(list(range(3)), r.randrange(8))
            p = random_csp(rng, 6, 5, rel_of)
            bqp, info = C.compile(p, lib, 'max_csp')
            v, z = C.brute_force(bqp)
            self.assertEqual(v, best_direct(p, lambda x: C.verify(p, x)[0]))
            self.assertEqual(C.verify(p, C.decode(z, info))[0], v)
        with self.assertRaises(ValueError):                  # a non-uniform gadget is refused for Max-CSP
            C.compile(random_csp(rng, 5, 2, lambda r: R.exactly(3, 1)), lib_with(R.exactly(3, 1)), 'max_csp')

    def test_constrained_optimum_is_exact(self):
        lib = lib_with(R.clause([True, True]), R.exactly(3, 1))
        rng = random.Random(13)
        for _ in range(8):
            n = 6
            cons = [{'relation': R.clause([True, True]).transform([0, 1], rng.randrange(4)).to_json(),
                     'vars': rng.sample(range(n), 2)} for _ in range(3)]
            cons.append({'relation': R.exactly(3, 1).to_json(), 'vars': rng.sample(range(n), 3)})
            obj = {'constant': 0, 'linear': [[i, rng.randint(-5, 5)] for i in range(n)],
                   'quadratic': [[0, 1, rng.randint(-3, 3)], [2, 4, rng.randint(-3, 3)]]}
            p = {'n': n, 'constraints': cons, 'objective': obj}
            bqp, info = C.compile(p, lib, 'optimize')
            v, z = C.brute_force(bqp)
            feas = [C.verify(p, x)[1] for x in product((0, 1), repeat=n) if C.verify(p, x)[0] == 0]
            if feas:
                x = C.decode(z, info)
                self.assertEqual(C.verify(p, x), (0, min(feas)))

    def test_missing_relations_are_reported(self):
        p = random_csp(random.Random(1), 5, 2, lambda r: R.parity(3, 1))
        self.assertEqual([r.id() for r in C.missing(p, LB.EMPTY)], [R.parity(3, 1).id()])
        with self.assertRaises(KeyError):
            C.compile(p, LB.EMPTY)


class VaultCascade(unittest.TestCase):
    def test_park_announce_reactivate_once(self):
        with tempfile.TemporaryDirectory() as d:
            v = Vault(Path(d) / 'vault')
            xor = R.parity(3, 1)
            p = random_csp(random.Random(5), 6, 3, lambda r: xor)
            for c in p['constraints']:
                c['weight'] = 1
            lib = LB.EMPTY
            miss = C.missing(p, lib)
            pid = LB.park(v, p, miss, creator='test', score=1.0)
            self.assertEqual(v.status(pid)['status'], 'dormant')
            g, rep = GD.synthesize_milp(xor, max_ancillas=1, bound=6)
            lib = LB.register(lib, xor, g, {'synthesizer': 'milp', 'tried': rep['tried']})
            rid = LB.archive(v, lib, xor, creator='test')
            self.assertEqual(v.status(rid)['status'], 'reproducible')
            cap = LB.announce(v, xor, rid)
            null = v.put(v.record('CapabilityRecord', {'name': 'nothing', 'unlocks': []}, domain='t', creator='t'))
            self.assertEqual(LB.cascade(v, [null], lambda a, t: [], fuel=5), [])
            seen = []

            def retest(aid, trigger):
                prob = v.get(aid)['content']
                bqp, info = C.compile(prob, lib, 'satisfy')
                val, z = C.brute_force(bqp)
                seen.append((aid, val, C.verify(prob, C.decode(z, info))[0]))
                return []
            log = LB.cascade(v, [cap], retest, fuel=5)
            self.assertEqual([a for _, _, a in log], [pid])
            self.assertEqual(seen[0][1] == 0, seen[0][2] == 0)
            self.assertEqual(LB.cascade(v, [cap], retest, fuel=5), [])      # never twice by the same trigger
            raw = v.raw(rid)
            v.close()
            v2 = Vault(Path(d) / 'vault')
            self.assertEqual(v2.raw(rid), raw)
            self.assertEqual(v2.get(rid)['content']['entry']['gadget'], g.to_json())
            self.assertEqual(v2.status(rid)['explanation'], 'unknown')
            v2.close()


if __name__ == '__main__':
    unittest.main()
