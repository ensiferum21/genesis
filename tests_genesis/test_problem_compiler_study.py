"""B20_R133: the Problem Compiler study (design): fresh seeds, the instance plan, the sign tests, Holm and the verdict,
validity, the registered output."""
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
import b20r133_problem_compiler as M  # noqa: E402


def rows_with(score):
    rows = []
    for spec in M.instances():
        for b in M.BUDGETS:
            for a in M.ARMS:
                rows.append({'family': spec['family'], 'seed': spec['seed'], 'arm': a, 'budget': b, 'valid': True,
                             'score': score(spec, a, b), 'info': {'violations_before_repair': 0}})
    return rows


class Design(unittest.TestCase):
    def test_seed_and_plan(self):
        for path in (ROOT / 'scripts').glob('*.py'):
            if path.name != 'b20r133_problem_compiler.py':
                self.assertIsNone(re.search(rf'\b{M.SEED}\b', path.read_text()), path.name)
        ins = M.instances()
        self.assertEqual(len(ins), 80)
        self.assertEqual(len({i['seed'] for i in ins}), 80)
        self.assertEqual({i['family'] for i in ins}, set(M.FAMILIES))

    def test_verdicts(self):
        def tie(spec, a, b):
            return 100 + spec['seed'] % 7 + (0 if a != 'milp' else -50) * (1 if spec['family'] != 'coloring' else -1)
        a = M.analyse(rows_with(tie))
        self.assertEqual(a['verdict'], 'COMPETITIVE_WITH_SPECIALISTS')
        self.assertEqual(set(a['tests']), {'mis', 'coloring', 'max2sat'})

        def behind(spec, a, b):
            s = 100 + spec['seed'] % 7
            if spec['family'] == 'coloring' and a == 'genesis':
                return s + 5                                  # more conflicts: worse
            return s
        self.assertEqual(M.analyse(rows_with(behind))['verdict'], 'BEHIND_SPECIALISTS_ON coloring')

        def beyond(spec, a, b):
            s = 100 + spec['seed'] % 7
            return s + 3 if spec['family'] == 'mis' and a == 'genesis' else s
        self.assertEqual(M.analyse(rows_with(beyond))['verdict'],
                         'COMPETITIVE_WITH_SPECIALISTS; BEYOND_SPECIALISTS_ON mis')

    def test_checks_and_holm(self):
        rows = rows_with(lambda s, a, b: 1)
        self.assertTrue(M.checks(rows))
        self.assertFalse(M.checks(rows[:-1]))
        self.assertEqual(M.holm({'a': 0.01, 'b': 0.04}), {'a': True, 'b': True})
        self.assertEqual(M.holm({'a': 0.03, 'b': 0.04}), {'a': False, 'b': False})

    def test_refuses_another_output(self):
        with self.assertRaises(SystemExit):
            M.main([str(ROOT / 'evidence' / 'elsewhere')])


def independent_score(family, inst, x):
    """A second checker written apart from `compiler.families` (numpy and networkx), from the instance and the raw
    BQP assignment: (valid, score). It decodes the compiler's variable layout itself."""
    import networkx as nx
    import numpy as np
    if x is None:
        return False, None
    z = np.asarray(x, dtype=np.int64)
    if family == 'mis':
        S = [i for i in range(inst['n']) if z[i] == 1]
        G = nx.Graph()
        G.add_nodes_from(range(inst['n']))
        G.add_edges_from(map(tuple, inst['edges']))
        return G.subgraph(S).number_of_edges() == 0, len(S)
    if family == 'coloring':
        n, k = inst['n'], inst['k']
        Z = z[:n * k].reshape(n, k)
        if not (Z.sum(axis=1) == 1).all():
            return False, None
        col = Z.argmax(axis=1)
        E = np.asarray(inst['edges'])
        return True, int((col[E[:, 0]] == col[E[:, 1]]).sum())
    if family == 'max2sat':
        C = np.asarray(inst['clauses'])
        val = z[np.abs(C) - 1] == (C > 0)
        return True, int(val.any(axis=1).sum())
    if family == 'maxcut':
        E = np.asarray(inst['edges'])
        return True, int((z[E[:, 0]] != z[E[:, 1]]).sum())
    raise ValueError(family)


class RecordB20R133(unittest.TestCase):
    """B20_R133's record: every run's answer re-checked by the family's verifier AND by an independent second checker
    on the regenerated instance; the run set complete; the analysis, the Holm family and the verdict recompute; the
    code identity is the run tree's. The reductions executed are the builder's (`compiler.families.compile`):
    nothing here is an invented reduction."""
    IDENTITY = '130db5ccdb57555a2b75d48ba9a04cb90438adc40974d006b96b5630a308a13c'   # the run tree, 8bdebad

    @classmethod
    def setUpClass(cls):
        import json
        cls.ev = ROOT / 'evidence' / 'problem_compiler_b20r133'
        cls.s = json.loads((cls.ev / 'summary.json').read_text())
        cls.rows = [json.loads(line) for line in (cls.ev / 'runs.jsonl').read_text().splitlines() if line.strip()]

    def test_every_answer_checked_twice(self):
        from genesis.compiler import families as FM
        insts = {}
        for r in self.rows:
            key = (r['family'], r['seed'])
            if key not in insts:
                insts[key] = FM.generate(r['family'], r['seed'], r['params'])
            inst = insts[key]
            if r['valid']:
                ok, score, _ = FM.verify(r['family'], inst, FM.decode(r['family'], inst, r['assignment']))
                self.assertTrue(ok)
                self.assertEqual(score, r['score'])
                ok2, score2 = independent_score(r['family'], inst, r['assignment'])
                self.assertTrue(ok2, (r['family'], r['seed'], r['arm']))
                self.assertEqual(score2, r['score'], (r['family'], r['seed'], r['arm']))
            else:
                self.assertEqual(r['score'], M.worst(r['family'], inst))

    def test_analysis_recomputes(self):
        import json
        self.assertTrue(M.checks(self.rows))
        a = json.loads(json.dumps(M.analyse(self.rows)))
        for k in ('tests', 'secondary', 'means', 'failures', 'holm', 'verdict'):
            self.assertEqual(a[k], self.s[k], k)
        self.assertTrue(self.s['valid'])
        self.assertEqual(self.s['code_identity'], self.IDENTITY)


if __name__ == '__main__':
    unittest.main()
