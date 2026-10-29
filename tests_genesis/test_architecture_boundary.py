"""ARA-1, boundaries (`docs/OMEGA_ARCHITECTURE_INVENTION.md` §2.2, §7.3, §15) and the architecture model (§3, §5.3):
the research-plane modules of `genesis.architecture` import neither the zoo nor the judge, nor any protected kernel
module, and never reach into a view's private state; the model is built from executed probes and recorded verdicts,
and a planted broken implementation is FAILED; generated assumptions never sit in the kernel, and every protected one
is refused."""
import ast
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.architecture import assumptions as AS  # noqa: E402
from genesis.architecture import model as M  # noqa: E402
from genesis.architecture import zoo as Z  # noqa: E402

ARCH = ROOT / 'src' / 'genesis' / 'architecture'
RESEARCH_PLANE = ('graph.py', 'policies.py', 'model.py', 'assumptions.py', 'diagnose.py', 'rewrite.py', 'ara.py',
                  'meta.py', '__init__.py')
KERNEL_SIDE = ('zoo.py', 'judge.py')
PRIVATE = ('_draw', '_graphs', '_units', '_envs', '_seed', '_env', '__closure__', '__self__', '__globals__')


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
        self.assertEqual({p.name for p in ARCH.glob('*.py')}, set(RESEARCH_PLANE) | set(KERNEL_SIDE))

    def test_research_plane_imports_no_kernel_side(self):
        bad = []
        for name in RESEARCH_PLANE:
            for m in imports(ARCH / name):
                parts = [x for x in m.replace('genesis.', '.').split('.') if x]
                if any(x in ('zoo', 'judge', 'kernel', 'custodian', 'verification', 'release_bundle') for x in parts):
                    bad.append(f'{name}: {m}')
        self.assertEqual(bad, [])

    def test_research_plane_never_reaches_private_state(self):
        bad = []
        for name in RESEARCH_PLANE:
            for node in ast.walk(ast.parse((ARCH / name).read_text())):
                if isinstance(node, ast.Attribute) and node.attr in PRIVATE:
                    bad.append(f'{name}: .{node.attr}')
                if isinstance(node, ast.Call) and getattr(node.func, 'id', '') in ('getattr', 'vars', 'eval', 'exec'):
                    bad.append(f'{name}: {node.func.id}()')
        self.assertEqual(bad, [])

    def test_the_scan_sees_a_planted_reach(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / 'x.py'
            f.write_text('from . import judge\nview._draw.__self__.cls\n')
            self.assertTrue(any('judge' in m for m in imports(f)))
            attrs = [n.attr for n in ast.walk(ast.parse(f.read_text())) if isinstance(n, ast.Attribute)]
            self.assertTrue(set(attrs) & set(PRIVATE))


class Model(unittest.TestCase):
    def test_capabilities_are_probed(self):
        caps = M.capabilities()
        self.assertTrue(caps)
        self.assertTrue(all(c['status'] == 'OBSERVED_OK' for c in caps.values()), caps)

    def test_a_planted_broken_implementation_fails(self):
        status, why = M.probe('Policy', 'threshold', impl={'apply': lambda fam, p, X: [9] * len(X)})
        self.assertEqual(status, 'FAILED')
        self.assertIn('outside', why)

    def test_evidence_and_failure_patterns(self):
        ev = M.evidence()
        self.assertIn('engine-invention', ev['lines'])
        self.assertTrue(any(p['line'] == 'engine-invention' and p['stagnant'] for p in ev['failure_patterns']))


class Assumptions(unittest.TestCase):
    def test_generated_assumptions_are_outside_the_kernel_and_challengeable(self):
        ag = Z.Environment(3, 4, 'GLOBAL_ONLY').incumbent
        gen = AS.generated(ag)
        self.assertTrue(gen)
        self.assertTrue(all(a['location'] != 'out' for a in gen))
        for a in gen:
            self.assertIsNotNone(AS.challenge(a, ag))

    def test_every_protected_assumption_is_refused(self):
        prot = AS.protected()
        self.assertEqual(len(prot), len(AS.PROTECTED))
        for a in prot:
            with self.assertRaises(AS.Refused):
                AS.challenge(a)
        ag = Z.Environment(3, 4, 'GLOBAL_ONLY').incumbent
        with self.assertRaises(AS.Refused):
            AS.challenge({'kind': 'generated', 'location': 'out', 'fixed': 'Output.reattempt'}, ag)

    def test_recorded_assumptions_name_their_studies(self):
        for r in AS.recorded():
            self.assertTrue(r['tested_by'])
            self.assertTrue(all(s.startswith('B20_R') for s in r['tested_by']))


if __name__ == '__main__':
    unittest.main()
