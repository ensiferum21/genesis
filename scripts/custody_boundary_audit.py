"""Fail-closed audit of the legacy in-process sealed-data boundary."""
from pathlib import Path
import ast
import json
import sys

def inspect(root: Path) -> dict:
    path = root / 'src/gap_engine/kernel/sealed.py'
    tree = ast.parse(path.read_text())
    classes = [x for x in tree.body if isinstance(x, ast.ClassDef) and x.name == 'SealedStore']
    if len(classes) != 1:
        return {'status':'BLOCK','independent_custody_proven':False,'reasons':['missing/ambiguous SealedStore']}
    cls = classes[0]
    methods = {x.name for x in cls.body if isinstance(x, ast.FunctionDef)}
    fields = {x.target.id for x in cls.body if isinstance(x, ast.AnnAssign) and isinstance(x.target, ast.Name)}
    reasons = []
    if '_items' in fields:
        reasons.append('sealed task payloads reside in same-process mutable memory')
    if 'judge' in methods:
        reasons.append('same-process solver callback receives sealed task payloads')
    if 'screen' in methods:
        reasons.append('adaptive sealed near-duplicate oracle is exposed')
    return {'status':'BLOCK' if reasons else 'REVIEW_REQUIRED','independent_custody_proven':False,'reasons':reasons}

if __name__ == '__main__':
    print(json.dumps(inspect(Path(sys.argv[1]) if len(sys.argv)>1 else Path('.')),indent=2))
    sys.exit(2)
