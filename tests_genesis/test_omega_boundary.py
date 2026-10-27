"""Genesis Ω contract §2: the research plane cannot reach the protected kernel's write paths.

The Ω research modules (the scientist, its languages, the causal adapters and estimators, the Problem Compiler, the
vault and its CLI) import nothing from `genesis.kernel`, `genesis.judge`, `genesis.custodian`, `genesis.verification`
or the release and custody modules; they read data and propose. A study promotes nothing: promotion goes through
recorded evidence (the vault refuses `verified` and `promoted` without it, `test_vault`).
"""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ['src/genesis/science', 'src/genesis/compiler', 'src/genesis/causal/active3.py',
            'src/genesis/causal/instruments.py', 'src/genesis/causal/joint.py', 'src/genesis/causal/global_ml.py',
            'src/genesis/vault.py', 'src/genesis/discovery_cli.py', 'src/genesis/interpret.py',
            'src/genesis/autonomy/process.py', 'src/genesis/replayers.py',
            'src/genesis/autonomy/contract_v3.py', 'src/genesis/autonomy/queue.py', 'src/genesis/representation',
            'src/genesis/objects', 'src/genesis/senses', 'src/genesis/expressive'] + \
    [f'src/genesis/architecture/{m}' for m in ('graph.py', 'policies.py', 'model.py', 'assumptions.py', 'diagnose.py',
                                             'rewrite.py', 'ara.py')]
PROTECTED = ('kernel', 'judge', 'custodian', 'custody_records', 'verification', 'release_bundle', 'eligibility',
             'exposure', 'decision_record')


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
    def test_research_plane_imports_no_protected_module(self):
        bad = []
        for spec in RESEARCH:
            p = ROOT / spec
            files = sorted(p.rglob('*.py')) if p.is_dir() else [p]
            for f in files:
                for m in imports(f):
                    parts = [x for x in m.replace('genesis.', '.').split('.') if x]
                    if any(x in PROTECTED for x in parts):
                        bad.append(f'{f.relative_to(ROOT)}: {m}')
        self.assertEqual(bad, [])

    def test_the_scan_sees_a_planted_import(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / 'x.py'
            f.write_text('from ..kernel import evidence\nfrom genesis.judge import recompute\n')
            ms = imports(f)
            self.assertTrue(any('kernel' in m for m in ms) and any('judge' in m for m in ms))


if __name__ == '__main__':
    unittest.main()
