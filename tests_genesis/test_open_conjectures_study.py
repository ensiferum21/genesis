"""B20_R158 (F5)'s design (`scripts/b20r158_open_conjectures.py`), checked before it runs, without generating its
data: a fresh data seed; the kernel's labels (a proving-test bound is withheld, a published one labelled); the double
check for small and large graphs; McNemar; and end to end on ANOTHER data seed at a tiny budget, two generations,
paused after every arm and resumed to the same result."""
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
import b20r158_open_conjectures as S  # noqa: E402

AMENDMENT = None                # the second amendment's commit (set after it; the first was ff9eada)


def digest_at(commit, rel):
    """The SHA-256 of a file as committed at `commit` (None without git): pins are checked against the
    preregistration commit, because the branch head moves on; the study runs from a worktree of that commit."""
    import hashlib
    import subprocess
    try:
        out = subprocess.run(['git', '-C', str(ROOT), 'show', f'{commit}:{rel}'], capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return hashlib.sha256(out.stdout).hexdigest() if out.returncode == 0 else None


class Design(unittest.TestCase):
    def test_constants_and_labels(self):
        others = [p for p in (ROOT / 'scripts').glob('*.py') if p.name != 'b20r158_open_conjectures.py']
        self.assertFalse(any(re.search(rf'\b{S.DATA_SEED}\b', p.read_text()) for p in others))
        if AMENDMENT is not None:
            at = {m: digest_at(AMENDMENT, 'src/genesis/' + m) for m in S.PINNED}     # the second amendment commit
            if all(v is not None for v in at.values()):
                self.assertEqual(at, S.PINNED)
        self.assertEqual(S.labels('sqrt(2*m^3/d + 2*d^2)')[0], True)                 # bound 18: withheld
        self.assertEqual(S.labels('sqrt(d^2 + 3*d*m)'), (False, 'rediscovery of bound 10 (proved)'))
        self.assertEqual(S.labels('(2*d + 2*m)/2'), (False, 'rediscovery of Merris 1998 (proved)'))
        self.assertTrue(S.proved_equivalent('d + m'))
        self.assertFalse(S.proved_equivalent('d + 1'))
        self.assertEqual(S.mcnemar_one_sided(4, 0), 1 / 16)

    def test_the_double_check(self):
        C4 = {'n': 4, 'edges': [[0, 1], [1, 2], [2, 3], [0, 3]], 'x': ['1', '-1', '1', '-1']}
        self.assertEqual(S.double_check('d + 1', 'vertex', C4), 'CONFIRMED')
        self.assertEqual(S.double_check('d + m', 'vertex', C4), 'REJECTED')
        n = 44                                                     # above the Sturm limit: the matrix-form check
        edges = [[i, (i + 1) % n] for i in range(n)]
        x = [str(1 if i % 2 == 0 else -1) for i in range(n)]       # C44: mu = 4 > 'd + 1' = 3
        self.assertEqual(S.double_check('d + 1', 'vertex', {'n': n, 'edges': edges, 'x': x}), 'CONFIRMED')


class EndToEnd(unittest.TestCase):
    def test_two_generations_pause_and_resume(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b, \
                mock.patch.object(S, 'DATA_SEED', 991001), mock.patch.object(S, 'CHUNK', 10):
            kw = dict(registered=False, b_per=1500, generations=2, data_count=60)
            self.assertEqual(S.main([a], **kw), 0)
            codes = []
            with mock.patch.object(S, 'SLICE_S', -1):
                while not codes or codes[-1] != 0:
                    codes.append(S.main([b], **kw))
                    self.assertLess(len(codes), 100)
            sa, sb = (json.loads((Path(d) / 'summary.json').read_text()) for d in (a, b))
            def strip(s):                                          # CPU differs between a run and its resumption
                s = {k: v for k, v in s.items() if k != 'code_identity'}
                s['generations'] = [{k: v for k, v in g.items() if k != 'cpu'} for g in s['generations']]
                return s
            self.maxDiff = None
            self.assertEqual(strip(sa), strip(sb))
            self.assertTrue(sa['valid'], sa)
            self.assertEqual(len(sa['generations']), 2)
            self.assertGreater(sa['generations'][0]['posed'], 0)


if __name__ == '__main__':
    unittest.main()
