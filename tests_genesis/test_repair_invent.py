"""Genesis inventing repair rules (`genesis.repair.invent`, `docs/OMEGA_RULE_INVENTION.md`), on development data only:
the vocabulary and the dream grammar (it holds the repairs of development defects no earlier operator reached); the
anti-unification lattice and rule application (a rule lifted from one development defect's repair transfers to
another's, the mirror rule of N1 and N2); free metavariables; the library's admission rule (another family's verified
repair) and rejection; the inventor's posterior over its levels; and one isolated dream episode that lifts rules."""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.repair import invent as IV  # noqa: E402
from genesis.repairkernel import defects3 as DF3  # noqa: E402
from genesis.repairkernel import targets as TG  # noqa: E402

SRC = TG.KERNEL_SOURCES


def fixed(did):
    return SRC[DF3.BY_ID[did]['target']]


class Dream(unittest.TestCase):
    def test_the_grammar_holds_repairs_no_earlier_operator_made(self):
        for did in ('N1', 'N4', 'K1', 'E3'):                 # B20_R181: no arm repaired these
            with self.subTest(did=did):
                ed = IV.dream_edits(DF3.source(did, SRC))
                self.assertTrue(any(s.replace(' ', '') == fixed(did).replace(' ', '') for _, s in ed))

    def test_the_vocabulary_knows_what_each_attribute_holds(self):
        v = IV.vocabulary(SRC['graph'])
        self.assertEqual(v['kinds'], {'adj': 'dict', 'edges': 'int'})
        self.assertEqual(v['values']['adj'], 'set')
        self.assertIn('_sweep', IV.vocabulary(SRC['lease'])['private'])


class Abstraction(unittest.TestCase):
    def test_the_lattice_and_a_rule_that_transfers(self):
        rules = IV.abstract(DF3.source('N1', SRC), fixed('N1'), {'episode': 'n1', 'family': 'N1'})
        levels = [r['level'] for r in rules]
        self.assertEqual(levels[0], 'concrete')
        general = next(r for r in rules if r['level'] == 'names+attrs+ops')
        got = [s for _, s in IV.apply_rule(general, DF3.source('N2', SRC))]
        self.assertIn(fixed('N2').replace(' ', ''), [s.replace(' ', '') for s in got])
        concrete = rules[0]
        self.assertEqual(IV.apply_rule(concrete, DF3.source('N2', SRC)), [])

    def test_free_metavariables_bind_to_attributes_of_the_same_kind(self):
        rules = IV.abstract(DF3.source('K1', SRC), fixed('K1'), {'episode': 'k1', 'family': 'K1'})
        free = next(r for r in rules if r['level'] == 'free')
        self.assertEqual(list(free['free'].values()), ['dict'])
        self.assertTrue(IV.apply_rule(free, DF3.source('K1', SRC)))


class LibraryAndInventor(unittest.TestCase):
    def test_admission_needs_another_familys_verified_repair_and_the_inventor_learns(self):
        with tempfile.TemporaryDirectory() as d:
            lib = IV.Library(Path(d) / 'rules.jsonl')
            new = lib.add(IV.abstract(DF3.source('N1', SRC), fixed('N1'), {'episode': 'n1', 'family': 'N1'}))
            self.assertEqual(lib.add(new), [])                           # no duplicates
            rid = new[-1]['id']
            lib.record(rid, True, 'N1')
            self.assertEqual(lib.get(rid)['status'], 'candidate')         # its own family does not admit it
            lib.record(rid, True, 'N2')
            self.assertEqual(lib.get(rid)['status'], 'admitted')
            self.assertEqual([r['id'] for r in IV.Library(Path(d) / 'rules.jsonl').admitted()], [rid])
            other = new[0]['id']
            lib.record(other, False, 'K1', false_repair=True)
            self.assertEqual(lib.get(other)['status'], 'rejected')
            inv = IV.Inventor(Path(d) / 'inventor.json')
            m0 = inv.mean('free')
            inv.learn('free', True)
            self.assertGreater(IV.Inventor(Path(d) / 'inventor.json').mean('free'), m0)


if __name__ == '__main__':
    unittest.main()
