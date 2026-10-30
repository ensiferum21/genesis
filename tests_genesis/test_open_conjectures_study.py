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

AMENDMENT = 'f7803e3'             # the second amendment's commit (the first was ff9eada)


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



R158 = ROOT / 'evidence' / 'open_conjectures_b20r158'


@unittest.skipUnless((R158 / 'summary.json').exists(), 'B20_R158 has not been recorded')
class RecordB20R158(unittest.TestCase):
    """The record of B20_R158 (F5) on its evidence: the script; validity recomputed (the budgets, no proved bound
    refuted, the audit of the research plane at the preregistration commit); every certified refutation
    double-checked again; the analysis and the verdict recomputed; generation 1's posed set regenerated from the
    data seed; the survivors' small exhaustive check repeated."""

    @classmethod
    def setUpClass(cls):
        cls.s = json.loads((R158 / 'summary.json').read_text())
        cls.gens = [json.loads(x) for x in (R158 / 'generations.jsonl').read_text().splitlines() if x.strip()]

    def test_the_script(self):
        import hashlib
        self.assertEqual(hashlib.sha256((ROOT / 'scripts' / 'b20r158_open_conjectures.py').read_bytes()).hexdigest(),
                         'f44333c3355607da31fd54d10bf6444ecc3a753d8d431b12d7dd9ea15f85c06c')

    def test_validity(self):
        self.assertEqual(len(self.gens), S.G)
        spent = all(g[a]['spent'] >= g[a]['budget'] - S.QUANTUM - 1 for g in self.gens for a in ('FULL', 'PLAIN'))
        self.assertEqual(spent, self.s['spent_ok'])
        hits = sorted({g['posed'][p][0] for g in self.gens for a in ('FULL', 'PLAIN') for p in g['confirmed'][a]
                       if S.proved_equivalent(g['posed'][p][0])})
        self.assertEqual(hits, self.s['proved_equivalents_refuted'])
        self.assertEqual(self.s['audit_hits'], [])
        self.assertTrue(self.s['pins_ok'])
        self.assertEqual(self.s['valid'], spent and not hits and self.s['pins_ok'] and not self.s['audit_hits'])

    def test_the_audit_at_the_preregistration_commit(self):
        import subprocess
        import tempfile
        from genesis.conjecture import audit as AU
        with tempfile.TemporaryDirectory() as tmp:
            files = []
            for path in AU.research_plane(Path(tmp)):
                rel = path.relative_to(tmp).as_posix()
                out = subprocess.run(['git', '-C', str(ROOT), 'show', f'{AMENDMENT}:{rel}'], capture_output=True)
                if out.returncode != 0:                          # a module that did not exist then
                    continue
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(out.stdout)
                files.append(path)
            self.assertTrue(files)
            self.assertEqual(AU.scan(files), [])

    def test_every_refutation_double_checks_again(self):
        for g in self.gens:
            for arm in ('FULL', 'PLAIN'):
                got = [p for p, art in sorted(g[arm]['artifacts'].items())
                       if p in g[arm]['refuted'] and S.double_check(g['posed'][p][0], 'vertex', art) == 'CONFIRMED']
                self.assertEqual(got, g['confirmed'][arm], (g['k'], arm))

    def test_the_analysis_recomputes(self):
        both = {a: set().union(*[set(g['confirmed'][a]) for g in self.gens]) for a in ('FULL', 'PLAIN')}
        b, c = len(both['FULL'] - both['PLAIN']), len(both['PLAIN'] - both['FULL'])
        self.assertEqual((self.s['P1']['full_only'], self.s['P1']['plain_only']), (b, c))
        self.assertAlmostEqual(self.s['P1']['p'], S.mcnemar_one_sided(b, c))
        want = 'INVALID' if not self.s['valid'] else ('FULL_BETTER' if S.mcnemar_one_sided(b, c) < S.ALPHA
                                                      else 'NOT_SHOWN')
        self.assertEqual(self.s['verdict'], want)
        for g in self.gens:
            surv = sorted(p for p in g['posed'] if p not in g['confirmed']['FULL'] and p not in g['confirmed']['PLAIN'])
            self.assertEqual(surv, g['survivors'])

    def test_generation_one_is_posed_again_from_the_data_seed(self):
        import numpy as np
        from genesis.conjecture import generate as GN
        data = GN.data(np.random.default_rng(S.DATA_SEED), count=S.DATA_COUNT)
        kept = [f for f, _ in GN.conjectures(data)]
        g1 = self.gens[0]
        self.assertEqual(len(kept), g1['kept'])
        posed = sorted(f for f, _ in g1['posed'].values())
        self.assertEqual(sorted(f for f in kept if not S.labels(f)[0]), posed)
        self.assertEqual(sorted(f for f in kept if S.labels(f)[0]), sorted(g1['withheld']))

    def test_the_survivors_small_check_repeats(self):
        for g in self.gens:
            for p in g['survivors']:
                self.assertEqual(S.survives_small(g['posed'][p][0], 'vertex'), g['survivors_small_exhaustive'][p])


if __name__ == '__main__':
    unittest.main()
