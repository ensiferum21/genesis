"""B20_R157 (F4)'s design (`scripts/b20r157_laplacian_bounds.py`), checked before it runs, without attacking any
sealed bound: a fresh sealed seed; the posed set (56 bounds: 21 proved, 33 refuted, 2 open; the proving test's
family A and the duplicate left out; opaque ids); the pins; the exact McNemar test, Holm and the verdict rules; the
double check; and end to end on INVENTED bounds at a small budget, with pauses, to the same result."""
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r157_laplacian_bounds as S  # noqa: E402
from genesis.conjecture import sealed as SD  # noqa: E402

INVENTED = {'t1': ('d + 1', 'vertex', 'refuted-test'), 't2': ('2*d', 'vertex', 'proved'),
            't3': ('di + dj - 1', 'edge', 'refuted-test'), 't4': ('d + m', 'vertex', 'proved'),
            't5': ('(d + m)/2 + 1', 'vertex', 'refuted-test')}


def digest_at(commit, rel):
    """The SHA-256 of a file as committed at `commit` (None without git): the pins are checked against the
    preregistration commit, because the branch head may move on after a study is preregistered (the study itself
    runs from a clean worktree of that commit, where its own run-time pin check applies)."""
    import hashlib
    import subprocess
    try:
        out = subprocess.run(['git', '-C', str(ROOT), 'show', f'{commit}:{rel}'], capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return hashlib.sha256(out.stdout).hexdigest() if out.returncode == 0 else None


class Design(unittest.TestCase):
    def test_constants_and_the_posed_set(self):
        others = [p for p in (ROOT / 'scripts').glob('*.py') if p.name != 'b20r157_laplacian_bounds.py']
        self.assertFalse(any(re.search(rf'\b{S.SEALED_SEED}\b', p.read_text()) for p in others))
        at = {m: digest_at('HEAD', 'src/genesis/' + m) for m in S.PINNED}          # the amendment commit (its hash next)
        if all(v is not None for v in at.values()):
            self.assertEqual(at, S.PINNED)
        problems, number_of = S.posed()
        self.assertEqual(len(problems), 56)
        statuses = [SD.status(k) for k in number_of.values()]
        self.assertEqual(sum(s == 'proved' for s in statuses), 21)
        self.assertEqual(sum(s.startswith('refuted') for s in statuses), 33)
        self.assertEqual(sorted(k for k in number_of.values() if SD.status(k) == 'open'), [44, 46])
        self.assertFalse(set(number_of.values()) & (set(SD.PROVING_TEST_HOLDOUT) | {23}))
        self.assertTrue(all(re.fullmatch(r'B[0-9a-f]{10}', p) for p in problems))
        for p, (f, kind) in problems.items():
            self.assertEqual((f, kind), (SD.BOUNDS[number_of[p]][0], SD.kind(number_of[p])))


class Analysis(unittest.TestCase):
    def test_mcnemar_holm_and_verdicts(self):
        self.assertAlmostEqual(S.mcnemar_one_sided(5, 0), 1 / 32)
        self.assertEqual(S.mcnemar_one_sided(0, 0), 1.0)
        self.assertGreater(S.mcnemar_one_sided(3, 3), 0.5)
        ids = [f'p{i}' for i in range(30)]
        status = {p: 'refuted-2024' for p in ids}
        numbers = {p: 100 + i for i, p in enumerate(ids)}
        strong = {a: set(ids[:10]) for a in S.ARMS}
        strong['FRONTIER'] = set(ids[:25])
        res = S.analyse(strong, status, numbers)
        self.assertEqual(S.verdict(True, res)[0], 'FRONTIER_BETTER')
        self.assertEqual(S.verdict(False, res)[0], 'INVALID')
        tie = S.analyse({a: set(ids[:10]) for a in S.ARMS}, status, numbers)
        self.assertEqual(S.verdict(True, tie)[0], 'NOT_SHOWN')
        part = {a: set(ids[:10]) for a in S.ARMS}
        part['FRONTIER'] = set(ids[:20])
        part['GBFS'] = set(ids[:20])
        self.assertEqual(S.verdict(True, S.analyse(part, status, numbers)), ('PARTIAL', ['UCB', 'UNIFORM', 'NRPA',
                                                                                         'CEM']))

    def test_the_double_check(self):
        C4 = {'n': 4, 'edges': [[0, 1], [1, 2], [2, 3], [0, 3]], 'x': ['1', '-1', '1', '-1']}
        self.assertEqual(S.double_check('d + 1', 'vertex', C4), 'CONFIRMED')
        self.assertEqual(S.double_check('d + m', 'vertex', C4), 'REJECTED')
        self.assertEqual(S.double_check('d + 1', 'vertex', {'n': 4}), 'REJECTED')


class EndToEnd(unittest.TestCase):
    def test_runs_pauses_and_resumes_to_the_same_result(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            with mock.patch.object(S, 'CHUNK', 5):
                self.assertEqual(S.main([a], registered=False, b_per=3000, test_problems=INVENTED), 0)
                codes = []
                with mock.patch.object(S, 'SLICE_S', -1):          # every slice: one unit of progress, then a pause
                    while not codes or codes[-1] != 0:
                        codes.append(S.main([b], registered=False, b_per=3000, test_problems=INVENTED))
                        self.assertLess(len(codes), 200)
            self.assertIn(S.PAUSED, codes)
            sa, sb = (json.loads((Path(d) / 'summary.json').read_text()) for d in (a, b))
            strip = lambda s: {k: v for k, v in s.items() if k != 'code_identity'}
            self.assertEqual(strip(sa), strip(sb))
            self.assertTrue(sa['valid'], sa)
            self.assertEqual(sa['proved_bounds_refuted'], [])
            self.assertIn('t1', sa['refuted']['FRONTIER'])


if __name__ == '__main__':
    unittest.main()
