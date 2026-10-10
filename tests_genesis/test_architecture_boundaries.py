"""Microkernel / cognitive kernel / phenotype boundaries are explicit in code (spec §31).

The evidence microkernel (genesis.kernel) must not import the research,
campaign, DSL, IR or representation modules whose outputs it judges.
"""
import ast
from pathlib import Path
import unittest

SRC = Path(__file__).resolve().parents[1] / 'src' / 'genesis'
FORBIDDEN_FOR_KERNEL = {'research', 'campaign', 'dsl', 'ir', 'mrdl', 'ladder', 'execution', 'macros', 'market'}


def imported_modules(path):
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ''
            if node.level >= 2 or module.startswith('genesis.'):
                parts = module.replace('genesis.', '').split('.')
                yield parts[0] if parts[0] else (node.names[0].name)
            elif node.level == 1:
                yield module.split('.')[0] if module else node.names[0].name
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith('genesis.'):
                    yield alias.name.split('.')[1]


class Boundaries(unittest.TestCase):
    def test_kernel_does_not_import_research_components(self):
        offenders = []
        for path in (SRC / 'kernel').rglob('*.py'):
            for module in imported_modules(path):
                if module in FORBIDDEN_FOR_KERNEL:
                    offenders.append(f'{path.name} imports {module}')
        self.assertEqual(offenders, [])

    def test_research_code_cannot_import_custodian_private_paths(self):
        # Research-side modules may build requests but never call evaluate/adjudicate.
        for name in ('research.py', 'campaign.py', 'dsl.py', 'ir.py', 'mrdl.py'):
            text = (SRC / name).read_text()
            self.assertNotIn('custodian import evaluate', text, name)
            self.assertNotIn('adjudicate', text, name)


if __name__ == '__main__':
    unittest.main()
