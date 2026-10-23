"""B20_R111: the invention test (design): the prior-art library is in the language and complete as declared; the
structural signature drops numbers and representations and expands macros; the novelty rule is conservative (a reduced
template is known); statement deletion; tuning and the champion; the sign test and the verdict; fresh seed; the
registered output."""
import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r111_invention_test as M  # noqa: E402
from genesis.candidate_kinds import solver_program as KP  # noqa: E402
from genesis.invention import solver_library as SL  # noqa: E402
from genesis.invention import solver_programs as SP  # noqa: E402

LICENSED = KP.licensed_reps('triangle_free_host_v1')


class Design(unittest.TestCase):
    def test_seed_is_fresh(self):
        for path in (ROOT / 'scripts').glob('*.py'):
            if path.name != 'b20r111_invention_test.py':
                self.assertIsNone(re.search(rf'\b{M.HOST_SEED}\b', path.read_text()), path.name)

    def test_library(self):
        self.assertEqual(list(M.LIBRARY), [f'T{i}' for i in range(1, 9)])
        self.assertEqual(sum(len(v) for v in M.LIBRARY.values()), 68)
        self.assertEqual(set(M.REPS), set(LICENSED))
        names = [n for vs in M.LIBRARY.values() for n, _ in vs]
        self.assertEqual(len(set(names)), len(names))
        for vs in M.LIBRARY.values():
            for n, p in vs:
                self.assertEqual(SP.problems(p, LICENSED), [], n)
        self.assertEqual(len(set(M.TEMPLATE_SIGNATURES.values())), 8)

    def test_signature_and_novelty_rule(self):
        a = {'rep': 'cross_2', 'body': [['split', 0.5, [M.ANNEAL], [['descent']]]]}
        b = {'rep': 'ordered_2', 'body': [['split', 0.9, [['relabel', 'random', 'anneal', 10]], [['descent']]]]}
        self.assertEqual(M.signature(a), M.signature(b))
        self.assertEqual(M.core_label(M.signature(a)), ('KNOWN_CORE', ['T4', 'T8']))
        lib = {'rep': 'cross_2', 'library': [[['descent']]], 'body': [['init'], ['macro', 0]]}
        self.assertEqual(M.signature(lib), M.signature(M.LIBRARY['T1'][0][1]))       # macros expand in place
        reduced = {'rep': 'cross_2', 'body': [['descent']]}
        self.assertEqual(M.core_label(M.signature(reduced))[0], 'KNOWN_CORE')     # a reduced template is known
        new = {'rep': 'cross_2', 'body': [['loop', [['edges', 'drop', 'anneal', 10], ['relabel', 'best', 'sideways', 1]]]]}
        self.assertEqual(M.core_label(M.signature(new)), ('NOVEL_CORE', []))       # a combination no template has

    def test_the_candidates_load_and_sign(self):
        c = M.candidates()
        self.assertEqual(set(c), {'gen1', 'gen2', 'gen3', 'control'})
        for arm, (p, _) in c.items():
            self.assertEqual((SL.problems(p, LICENSED) if 'library' in p else SP.problems(p, LICENSED)), [], arm)
            M.signature(p)
        self.assertEqual(M.core_label(M.signature(c['gen1'][0]))[0], 'KNOWN_CORE')   # gen1 uses T8's statements only

    def test_deletions(self):
        p = {'rep': 'cross_2', 'body': [['descent'], ['loop', [['relabel', 'random', 'always', 10], ['descent']]]]}
        ds = M.deletions(p)
        self.assertEqual(len(ds), 4)                    # either top statement, either loop statement
        for d in ds:
            self.assertEqual(SP.problems(d, LICENSED), [])
        lib = json.loads(json.dumps(M.candidates()['gen2'][0]))
        self.assertTrue(any(d['library'] != lib['library'] for d in M.deletions(lib)))

    def test_tune_and_verdict(self):
        hosts = ['h1', 'h2']
        values = {n: {h: 100 for h in hosts} for vs in M.LIBRARY.values() for n, _ in vs}
        values['T6|adjacent_2|-'] = {h: 105 for h in hosts}
        tuned, champion, _ = M.tune(values, hosts)
        self.assertEqual((champion, tuned['T6']), ('T6', 'T6|adjacent_2|-'))
        self.assertEqual(tuned['T1'], 'T1|cross_2|-')   # ties: the first variant
        r = M.sign([101] * 24, [100] * 24)
        self.assertEqual(r['label'], 'BEATS_PRIOR_ART')
        self.assertEqual(M.sign([100] * 24, [100] * 24)['label'], 'NOT_DISTINGUISHABLE')
        t1 = {'gen1': r, 'gen2': M.sign([99] * 24, [100] * 24)}
        self.assertEqual(M.verdict(t1, {'gen1': {'label': 'NOVEL_CORE'}}), 'INVENTION_DEMONSTRATED')
        self.assertEqual(M.verdict(t1, {'gen1': {'label': 'KNOWN_CORE'}}), 'BETTER_BUT_KNOWN')
        self.assertEqual(M.verdict({'gen2': t1['gen2']}, {}), 'NOT_DEMONSTRATED')

    def test_refuses_another_output(self):
        with self.assertRaises(SystemExit):
            M.main([str(ROOT / 'evidence' / 'elsewhere')])


if __name__ == '__main__':
    unittest.main()
