"""X2 (B20_R154): the language judge (kernel side, `genesis.expressive.judge`) on the planted fixture
(`genesis.expressive.fixture`).

Each correctness check refuses what it should; a planted statement is admitted under both claims; in a null world it
is not; the decoy (helpful only where Genesis looks) is refused; a statement worth nothing is refused, including
when a parent search sticks (the replicate test and the margin); a one-item statement cannot claim expressiveness
(structural); an unsaturated ceiling refuses an expressiveness claim; the verdict carries no number, the ledger does,
with the digests of the code the judge ran; the judge is deterministic; its digest is pinned."""
import hashlib
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.candidate_kinds import mcx3 as K  # noqa: E402
from genesis.expressive import fixture as F  # noqa: E402
from genesis.expressive import judge as J  # noqa: E402
from genesis.expressive import lambda1 as L1  # noqa: E402

P4 = 'D@c D@c D@c D@c'                                    # the planted statement's body


def submit(judge, body, claim, parent=L1.EMPTY, name='st'):
    cand = parent.extend(name, body)
    return judge.submit(parent.to_json(), cand.to_json(), [name], claim), judge.ledger()[-1]


class Correctness(unittest.TestCase):
    def setUp(self):
        self.j = J.LanguageJudge(F.FixtureDomain(), sealed_seed=3)
        self.cand = L1.EMPTY.extend('st', P4)

    def test_each_check_refuses(self):
        e, c = L1.EMPTY.to_json(), self.cand.to_json()
        bad = self.cand.to_json()
        bad['defs'][0]['body'] = 'D@c'                     # the JSON no longer rebuilds to its version
        other = L1.EMPTY.extend('zz', 'X I').to_json()
        for args in ((e, bad, ['st'], 'search'), (e, c, ['xx'], 'search'), (e, c, [], 'search'),
                     (e, c, ['st'], 'speed'), (other, c, ['st'], 'search'),
                     (e, c, ['st'], 'search', [dict(K.DEFAULT, prog='b1 nope(3)')])):
            self.assertEqual(self.j.submit(*args), {'admitted': False, 'failed': 'correctness'}, args[2:4])

    def test_a_one_item_statement_cannot_claim_expressiveness(self):
        v, rec = submit(self.j, 'D@c', 'expressiveness')
        self.assertEqual(v, {'admitted': False, 'failed': 'structural'})
        v, _ = submit(self.j, '?f>$1', 'expressiveness', name='late')
        self.assertEqual(v['failed'], 'structural')


class Decisions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.j = J.LanguageJudge(F.FixtureDomain(search_scale=0.5), sealed_seed=7)
        cls.planted = submit(cls.j, P4, 'search')
        cls.worthless = submit(cls.j, 'X I', 'search')
        cls.decoy = submit(cls.j, 'H@a H@a H@a H@a', 'search')
        cls.unsaturated = submit(cls.j, P4, 'expressiveness')
        null = J.LanguageJudge(F.FixtureDomain(search_scale=0.5, null=True), sealed_seed=7)
        cls.null = submit(null, P4, 'search')

    def test_planted_admitted_and_the_rest_refused(self):
        self.assertEqual(self.planted[0], {'admitted': True, 'failed': None})
        for v, _ in (self.worthless, self.decoy, self.null):
            self.assertEqual(v, {'admitted': False, 'failed': 'sealed'})
        rec = self.planted[1]
        self.assertGreater(rec['tests']['parent']['mean'], 0.01)
        self.assertEqual(rec['tests']['parent']['replicates'], 0.05)       # every candidate search beat every other

    def test_an_unsaturated_ceiling_cannot_admit_expressiveness(self):
        v, rec = self.unsaturated
        self.assertEqual(v, {'admitted': False, 'failed': 'not_saturated'})
        self.assertLess(rec['saturation']['p'], J.ALPHA)

    def test_the_verdict_has_no_numbers_the_ledger_does(self):
        for v, rec in (self.planted, self.worthless):
            self.assertEqual(set(v), {'admitted', 'failed'})
            self.assertIn('tests', rec)
            self.assertEqual(rec['code'], J.code_digests())
            self.assertTrue(rec['control'])
        self.assertNotEqual(self.planted[1]['control'], self.worthless[1]['control'])   # drawn per submission

    def test_deterministic(self):
        again = J.LanguageJudge(F.FixtureDomain(search_scale=0.5), sealed_seed=7)
        self.assertEqual(submit(again, P4, 'search')[1], self.planted[1])


class Expressiveness(unittest.TestCase):
    """A ceiling long enough to saturate in the fixture's bound: the planted statement is admitted as expressive, a
    worthless one is not, though a parent search sticks."""

    @classmethod
    def setUpClass(cls):
        cls.j = J.LanguageJudge(F.FixtureDomain(search_scale=2.0), sealed_seed=7)
        cls.planted = submit(cls.j, P4, 'expressiveness')
        cls.worthless = submit(cls.j, 'X I', 'expressiveness')

    def test_expressiveness(self):
        self.assertEqual(self.planted[0], {'admitted': True, 'failed': None})
        self.assertGreater(self.planted[1]['tests']['parent']['margin'], 0.03)
        self.assertEqual(self.worthless[0], {'admitted': False, 'failed': 'sealed'})
        self.assertLess(min(t['margin'] for t in self.worthless[1]['tests'].values()), J.MATERIAL)


class Pin(unittest.TestCase):
    def test_the_judge_is_pinned(self):
        got = hashlib.sha256((ROOT / 'src' / 'genesis' / 'expressive' / 'judge.py').read_bytes()).hexdigest()
        self.assertEqual(got, PINNED)


PINNED = '8390b1998e4dcb91ff282b955d1940cda3508d9be99cd384ad150d21188d5d05'     # judge.py; a change is a human-gated amendment

if __name__ == '__main__':
    unittest.main()
