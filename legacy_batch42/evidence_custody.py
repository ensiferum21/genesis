"""Descriptor-relative no-follow evidence reader for local receipt validation.

Requires a trusted, non-writable-by-attacker evidence root. This does not
establish independence or prevent modifications by privileged processes.
"""
import os
import stat
from pathlib import Path


def _regular_beneath(root, *parts, max_bytes=1024*1024):
    if type(max_bytes) is not int or max_bytes < 0 or max_bytes > 8*1024*1024:
        raise ValueError('invalid evidence size bound')
    if not parts or any(not isinstance(p,str) or p in ('','.','..') or '/' in p or '\\' in p or '\x00' in p for p in parts):
        raise ValueError('invalid evidence path component')
    base=Path(root).absolute()
    if not base.is_absolute():
        raise ValueError('invalid evidence root')
    flags=os.O_RDONLY | getattr(os,'O_CLOEXEC',0) | getattr(os,'O_NOFOLLOW',0)
    directory_flags=flags | getattr(os,'O_DIRECTORY',0)
    # Walk from filesystem root: even ancestors of the evidence root may not
    # be symlinks. No string-path stat/read race between traversal and open.
    components=base.parts[1:]
    fd=os.open('/',directory_flags)
    try:
        for component in components:
            new=os.open(component,directory_flags,dir_fd=fd)
            os.close(fd); fd=new
        for component in parts[:-1]:
            new=os.open(component,directory_flags,dir_fd=fd)
            os.close(fd); fd=new
        file_fd=os.open(parts[-1],flags | getattr(os,'O_NONBLOCK',0),dir_fd=fd)
        try:
            metadata=os.fstat(file_fd)
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > max_bytes:
                raise ValueError('evidence not regular or oversized')
            with os.fdopen(file_fd,'rb',closefd=False) as stream:
                data=stream.read(max_bytes+1)
            if len(data)>max_bytes:
                raise ValueError('oversized evidence')
            return data
        finally:
            os.close(file_fd)
    finally:
        os.close(fd)


def regular_beneath(root, *parts, max_bytes=1024*1024):
    try:
        return _regular_beneath(root, *parts, max_bytes=max_bytes)
    except OSError as exc:
        raise ValueError("unsafe or unavailable evidence path") from exc
