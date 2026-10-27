"""The proving test's forbidden-concept audit (KERNEL SIDE; `docs/OMEGA_FRONTIER.md` §7b, "without specifying the
missing concept").

The hidden reference of the proving test's family A is a construction by equitable partitions (Damnjanovic, Ha and
Stevanovic 2026). The audit fails if that concept, or a close relative that would hand it over, is named or encoded
in what the research plane runs: identifiers (names, attributes, functions, classes, arguments) and string
constants in the code of the research-plane modules, and the manifest's description. Docstrings and comments are
not code and are not scanned: they say what the code does not contain, which is this audit's job to check.

The forbidden stems are listed here, kernel side, and never in the research plane.
"""
import ast
from pathlib import Path

FORBIDDEN = ('equitable', 'quotient', 'blowup', 'orbit', 'automorph', 'symmetr', 'partition', 'twin', 'lift',
             'cover', 'semiregular', 'biregular')


def _norm(text):
    """Lower case without separators, so that 'Blow-Up', 'blow_up' and 'blowup' match alike."""
    return ''.join(ch for ch in str(text).lower() if ch.isalnum())


def _docstring_nodes(tree):
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) \
                    and isinstance(first.value.value, str):
                out.add(id(first.value))
    return out


def code_tokens(path):
    """[(line, token)] of the identifiers and non-docstring string constants of a Python file."""
    tree = ast.parse(Path(path).read_text())
    docs = _docstring_nodes(tree)
    out = []
    for node in ast.walk(tree):
        line = getattr(node, 'lineno', 0)
        if isinstance(node, ast.Name):
            out.append((line, node.id))
        elif isinstance(node, ast.Attribute):
            out.append((line, node.attr))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.append((line, node.name))
        elif isinstance(node, ast.arg):
            out.append((line, node.arg))
        elif isinstance(node, ast.keyword) and node.arg:
            out.append((line, node.arg))
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docs:
            out.append((line, node.value))
    return out


def scan(paths, extra=()):
    """[(where, line, token, stem)] of every forbidden stem found."""
    hits = []
    for p in paths:
        for line, tok in code_tokens(p):
            low = _norm(tok)
            for stem in FORBIDDEN:
                if stem in low:
                    hits.append((str(p), line, tok, stem))
    for where, text in extra:
        low = _norm(text)
        for stem in FORBIDDEN:
            if stem in low:
                hits.append((where, 0, '', stem))
    return hits


def research_plane(root):
    """The research-plane modules the proving test runs."""
    root = Path(root)
    fr = [root / 'src/genesis/frontier' / m for m in ('__init__.py', 'direction.py', 'curves.py', 'converge.py',
                                                      'allocate.py', 'engine.py', 'manifest.py', 'procedure.py')]
    cj = [root / 'src/genesis/conjecture' / m for m in ('__init__.py', 'expr.py', 'graphs.py', 'attack.py',
                                                        'domain.py', 'abstraction.py', 'generate.py',
                                                        'invariants.py', 'statement.py', 'invariant_domain.py')]
    return fr + cj
