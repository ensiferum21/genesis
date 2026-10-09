"""Local evidence-path custody checks. Does not authenticate an independent prover."""
from pathlib import Path


def regular_beneath(root, *parts, max_bytes=1024*1024):
    """Read only regular files under a non-symlinked directory tree.

    Rejects symlinks at *any* path component, traversal, special files and oversized
    evidence before reading. Not race-free against concurrent hostile mutations;
    use a protected immutable snapshot for adversarial custody.
    """
    base=Path(root).absolute()
    if not base.is_dir() or base.is_symlink():
        raise ValueError('invalid evidence root')
    current=base
    for part in parts:
        if not isinstance(part,str) or part in ('','.','..') or '/' in part or '\\' in part:
            raise ValueError('invalid path component')
        current=current/part
        if current.is_symlink():
            raise ValueError('symlinked evidence component')
    if not current.is_file() or current.is_symlink():
        raise ValueError('evidence not a regular file')
    if current.stat().st_size>max_bytes:
        raise ValueError('oversized evidence')
    with current.open('rb') as stream:
        data=stream.read(max_bytes+1)
    if len(data)>max_bytes:
        raise ValueError('oversized evidence')
    return data
