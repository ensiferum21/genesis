"""B20_R56: the exact checker for sum-free tree certificates and its producer.

* the registry comes only from CHECKED pattern statements of B20_R55's intact package with the trusted SFDefs, and
  every statement parses to the generator's relations; another SFDefs is refused;
* on small hosts both routes (with the rows; with Schur rows only) certify the brute-force optimum, and every
  certificate checks VALID against its own registry and is REJECTED against the other's digest;
* alterations are refused: a lower claimed bound, a row naming a non-host element, a pattern map breaking a
  relation, a dropped leaf weight, a branch on a fixed element, a wrong right side, an infeasible leaf that is not;
* separation keeps every Schur row and only pattern rows; the producer's copies equal brute force.
"""
import copy
import itertools
import json
import unittest

from genesis.common import digest
from genesis.discovery import generated_bnb_sf as GB
from genesis.formal_research import loop as L
from genesis.invention import cuts_sf as SF
from genesis.verification import lp_dual_tree_sf as VT


def task(elements, tid='t'):
    return {'domain': VT.DOMAIN, 'task_id': tid, 'elements': sorted(elements)}


def brute(A):
    for k in range(len(A), -1, -1):
        for s in itertools.combinations(A, k):
            if SF.sumfree(s):
                return k, list(s)


SMALL = [list(range(1, 13)), [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 14, 15], [2, 3, 4, 5, 6, 7, 9, 10, 11, 13, 14, 16]]


class Registry(unittest.TestCase):
    def test_registry_from_the_package(self):
        reg = GB.load_registry()
        pats = SF.generate()
        self.assertEqual(len(reg['patterns']), 17)
        for p, c in zip(pats, SF.conjectures(pats)[3:]):
            r = reg['patterns'][c['id']]
            self.assertEqual((r['k'], r['ex']), (len(p['elements']), p['ex']))
            self.assertEqual([tuple(x) for x in r['relations']], [tuple(t) for t in SF._index_triples(p['elements'])])
            self.assertEqual(VT.parse_pattern_statement(L.statement(c))[1], [tuple(x) for x in r['relations']])
        pkg = json.loads(GB.PACKAGE.read_text())
        with self.assertRaises(ValueError):
            VT.registry_from_package(pkg, sf_source=SF.SOURCE.replace('a + b ∉ S', 'a + b ∈ S'))
        self.assertIsNone(VT.parse_pattern_statement('∀ (S : Finset ℕ) (hS : SF.SumFree S) (v0 : ℕ) (r0 : v0 + v0 = v0), '
                                                     'SF.ind S v0 ≤ 0 ∧ True'))
        bad = copy.deepcopy(pkg)
        st = next(s for s in bad['statements'] if s.get('role') == 'pattern')
        st['lean'] = st['lean'].replace('≤ 2', '≤ 1')
        with self.assertRaises(ValueError):
            VT.registry_from_package(bad, sf_source=SF.SOURCE)


class Certify(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reg = GB.load_registry()
        cls.abl = GB.empty_registry(cls.reg)
        cls.out = {}
        for i, A in enumerate(SMALL):
            t = task(A, f's{i}')
            opt, wit = brute(A)
            w = wit[:-1]                                     # start one below the optimum
            for name, reg, sep in (('rows', cls.reg, {}), ('schur', cls.abl, None)):
                cls.out[(i, name)] = (t, opt, reg, GB.certify_with_tree(t, w, reg, seconds=60, separation=sep))

    def test_both_routes_certify_the_optimum_and_check(self):
        for (i, name), (t, opt, reg, rec) in self.out.items():
            self.assertEqual((rec['lower'], rec['upper']), (opt, opt), (i, name))
            v = VT.check_certificate(t, rec['certificate'], reg)
            self.assertEqual((v['verdict'], v['bound']), ('VALID', opt), (i, name, v))
            other = self.abl if reg is self.reg else self.reg
            self.assertEqual(VT.check_certificate(t, rec['certificate'], other)['verdict'], 'REJECTED')
            self.assertEqual(VT.check_witness(t, rec['witness']), opt)

    def test_alterations_are_refused(self):
        t, opt, reg, rec = self.out[(0, 'rows')]
        cert = rec['certificate']
        lied = dict(cert, upper=opt - 1)
        self.assertEqual(VT.check_certificate(t, lied, reg)['verdict'], 'REJECTED')
        self.assertEqual(VT.check_certificate(task(t['elements'][:-1], 'other'), cert, reg)['verdict'], 'REJECTED')

        def leaves(node, out):
            if 'leaf' in node:
                out.append(node['leaf'])
            else:
                leaves(node['zero'], out); leaves(node['one'], out)
            return out
        found = {}
        for (i, name), (tt, _, rr, rc) in self.out.items():
            for lf in leaves(rc['certificate']['tree'], []):
                for q in lf.get('inequalities', []):
                    found.setdefault(q['kind'], (tt, rr, rc['certificate'], q))
        self.assertTrue({'schur', 'pattern'} <= set(found), sorted(found))
        for kind, mutate in (('schur', lambda q: q.update(triple=[q['triple'][0], q['triple'][1], 10 ** 6])),
                             ('schur', lambda q: q.update(rhs=3)),
                             ('pattern', lambda q: q.update(map=list(reversed(q['map'])))),
                             ('pattern', lambda q: q.update(weight='0'))):
            tt, rr, cc, q0 = found[kind]
            bad = copy.deepcopy(cc)
            hit = []

            def walk(node):
                if 'leaf' in node:
                    for q in node['leaf'].get('inequalities', []):
                        if not hit and q == q0:
                            mutate(q); hit.append(1)
                else:
                    walk(node['zero']); walk(node['one'])
            walk(bad['tree'])
            self.assertTrue(hit)
            self.assertEqual(VT.check_certificate(tt, bad, rr)['verdict'], 'REJECTED', kind)
        # a branch on an element that is already fixed, and a fake infeasible leaf
        bad = {'schema': VT.SCHEMA, 'task_sha256': digest(t), 'domain': VT.DOMAIN, 'registry_sha256': digest(reg),
               'upper': 0, 'tree': {'branch': 1, 'zero': {'branch': 1, 'zero': {'leaf': {'kind': 'dual'}},
                                                          'one': {'leaf': {'kind': 'dual'}}}, 'one': {'leaf': {'kind': 'dual'}}}}
        self.assertEqual(VT.check_certificate(t, bad, reg)['verdict'], 'REJECTED')
        bad['tree'] = {'leaf': {'kind': 'infeasible', 'row': {'kind': 'schur', 'triple': [1, 2, 3], 'rhs': 2}}}
        self.assertEqual(VT.check_certificate(t, bad, reg)['verdict'], 'REJECTED')


class Producer(unittest.TestCase):
    def test_copies_and_separation(self):
        reg = GB.load_registry()
        A = list(range(1, 15))
        for pid, pat in list(reg['patterns'].items())[:4]:
            got = {frozenset(c) for c in GB.copies(pat['k'], pat['relations'], A)}
            brute_set = set()
            for phi in itertools.permutations(A, pat['k']):
                if all(phi[a] + phi[b] == phi[c] for a, b, c in pat['relations']):
                    brute_set.add(frozenset(phi))
            self.assertEqual(got, brute_set, pid)
        t = task(list(range(1, 25)))
        R = GB.rows(t, reg)
        W, k, _ = GB.separate(t, list(R))
        schur = [r for r in R if r[0]['kind'] != 'pattern']
        self.assertTrue(all(r in W for r in schur))
        self.assertTrue(all(r[0]['kind'] == 'pattern' for r in W[len(schur):]))
        self.assertGreater(len(W), len(schur))
        self.assertGreaterEqual(k, 1)


if __name__ == '__main__':
    unittest.main()
