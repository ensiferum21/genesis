"""X2 (B20_R154): boundaries of `genesis.expressive` (`docs/OMEGA_EXPRESSIVE_LANGUAGE.md` §3). The research-plane
modules import neither the language judge nor the fixture (the kernel side), nor any protected module, and never
reach into the judge's state; the judge shows only `submit` and `ledger`; it records the digests of the
research-plane code it runs."""
import ast
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.expressive import fixture as F  # noqa: E402
from genesis.expressive import judge as J  # noqa: E402

PKG = ROOT / 'src' / 'genesis' / 'expressive'
RESEARCH_PLANE = ('__init__.py', 'lambda1.py', 'operators.py', 'library.py', 'consolidate.py', 'workflow.py',
                  'pipeline.py')
KERNEL_SIDE = ('judge.py', 'fixture.py', 'maxcut_domain.py')
PRIVATE = ('_train', '_truth', '_runs', '_ledger', '_domain', '_seed', '_replicates', '_search', '_run', '_ref',
           '_truth_gains', '_control', '_close', '__closure__', '__self__', '__globals__')


def imports(path):
    out = []
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.ImportFrom):
            mod = ('.' * node.level) + (node.module or '')
            out += [mod] + [f'{mod}.{a.name}' for a in node.names]
        elif isinstance(node, ast.Import):
            out += [a.name for a in node.names]
    return out


class Boundary(unittest.TestCase):
    def test_the_split_covers_the_package(self):
        self.assertEqual({p.name for p in PKG.glob('*.py')}, set(RESEARCH_PLANE) | set(KERNEL_SIDE))

    def test_the_research_plane_imports_no_kernel_side(self):
        bad = []
        for name in RESEARCH_PLANE:
            for m in imports(PKG / name):
                parts = [x for x in m.replace('genesis.', '.').split('.') if x]
                if any(x in ('judge', 'fixture', 'maxcut_domain', 'kernel', 'custodian', 'verification',
                             'release_bundle', 'zoo')
                       for x in parts):
                    bad.append(f'{name}: {m}')
        self.assertEqual(bad, [])

    def test_the_research_plane_never_reaches_the_judge(self):
        bad = []
        for name in RESEARCH_PLANE:
            for node in ast.walk(ast.parse((PKG / name).read_text())):
                if isinstance(node, ast.Attribute) and node.attr in PRIVATE:
                    bad.append(f'{name}: .{node.attr}')
                if isinstance(node, ast.Call) and getattr(node.func, 'id', '') in ('getattr', 'vars', 'eval', 'exec'):
                    bad.append(f'{name}: {node.func.id}()')
        self.assertEqual(bad, [])

    def test_the_scan_sees_a_planted_reach(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / 'x.py'
            f.write_text('from . import judge\njudge_obj._truth[0]\n')
            self.assertTrue(any('judge' in m for m in imports(f)))
            attrs = {n.attr for n in ast.walk(ast.parse(f.read_text())) if isinstance(n, ast.Attribute)}
            self.assertTrue(attrs & set(PRIVATE))

    def test_the_judge_shows_only_its_verdicts_and_ledger(self):
        j = J.LanguageJudge(F.FixtureDomain(), sealed_seed=1)
        self.assertEqual({a for a in dir(j) if not a.startswith('_')}, {'submit', 'ledger'})
        self.assertEqual(set(J.code_digests()), set(J.CODE))
        self.assertIn('expressive/operators.py', J.CODE)


if __name__ == '__main__':
    unittest.main()
