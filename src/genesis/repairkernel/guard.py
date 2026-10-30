"""The static guard on proposed sources (kernel side): a candidate may only re-arrange what the component already
does. It is checked before the kernel executes a candidate (the trial executor, the verifier).

A candidate is refused if it
  * does not parse;
  * adds, removes or changes an import;
  * uses a name, attribute or keyword the original does not use, unless it is in ALLOW_NEW (the containers' own
    methods and a few pure builtins a repair may need: `discard` for a missing paired update, `list` for a copy);
  * uses anything in DENY (input/output, reflection, code execution), or a dunder the original does not use, or a
    `global`/`nonlocal` statement.
With line-preserving edits of the component (`genesis.repair.synth`), nothing in a candidate can open a file, import a
module or reach the interpreter's internals: defence in depth behind the process isolation of `foundry`."""
import ast

DENY = frozenset({
    'open', 'exec', 'eval', 'compile', '__import__', 'getattr', 'setattr', 'delattr', 'globals', 'locals', 'vars',
    'breakpoint', 'input', 'print', 'exit', 'quit', 'memoryview', 'object', 'type', 'super', 'help', 'dir', 'id',
    'os', 'sys', 'subprocess', 'builtins', 'importlib', 'pickle', 'marshal', 'ctypes', 'socket', 'shutil', 'pathlib',
})
ALLOW_NEW = frozenset({
    # pure builtins
    'list', 'dict', 'set', 'tuple', 'len', 'sum', 'min', 'max', 'any', 'all', 'sorted', 'range', 'enumerate',
    'reversed', 'abs', 'int', 'bool',
    # container methods
    'append', 'pop', 'remove', 'discard', 'add', 'insert', 'clear', 'copy', 'update', 'get', 'setdefault',
    'move_to_end', 'popitem', 'keys', 'values', 'items', 'index', 'count', 'extend', 'sort', 'reverse',
    # keywords of those
    'last', 'key', 'default',
})


def identifiers(tree):
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Name):
            out.add(n.id)
        elif isinstance(n, ast.Attribute):
            out.add(n.attr)
        elif isinstance(n, ast.keyword) and n.arg:
            out.add(n.arg)
        elif isinstance(n, (ast.FunctionDef, ast.ClassDef)):
            out.add(n.name)
        elif isinstance(n, ast.arg):
            out.add(n.arg)
    return out


def imports(tree):
    return sorted(ast.dump(n) for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom)))


def check(original, candidate):
    """None if the candidate may be executed, else the reason it may not."""
    try:
        new = ast.parse(candidate)
    except SyntaxError as e:
        return f'syntax: {e.msg}'
    old = ast.parse(original)
    if imports(new) != imports(old):
        return 'imports changed'
    if any(isinstance(n, (ast.Global, ast.Nonlocal)) for n in ast.walk(new)):
        return 'global or nonlocal'
    known = identifiers(old)
    for name in sorted(identifiers(new)):
        if name in DENY:
            return f'denied: {name}'
        if name.startswith('__') and name not in known:
            return f'new dunder: {name}'
        if name not in known and name not in ALLOW_NEW:
            return f'new identifier: {name}'
    return None
