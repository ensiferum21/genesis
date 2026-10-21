"""Discovery: the adaptation cell finds the studies to read and how to read them, from the evidence alone.

No study has to be registered by hand. A time-to-solution study is any `evidence/<name>/` with a `summary.json` that
has a `ladder` and a `rows.jsonl` whose rows have `runs` and a `target`. Its batch is the `b20rNN` suffix of the
directory name (studies are read in batch order); its date is the commit date of its summary (or, before it is
committed, the file's modification date); its focal arm is the system's own method, recognised by name in the order
of `NATIVE` (the arm names the system's own kinds have had in these studies: the native engine first); the other arms
are its competitors, and which published solvers they were is read from the pinned binaries the summary records.
"""
import datetime
import json
from pathlib import Path
import re
import subprocess

from .receptors import Profile

NATIVE = ('tfx', 'found', 'engine', 'system', 'candidate')


def _date(root, path):
    try:
        out = subprocess.run(['git', '-C', str(root), 'log', '--diff-filter=A', '--format=%cs', '--', str(path)],
                             capture_output=True, text=True, timeout=30).stdout.split()
        if out:
            return out[-1]
    except (OSError, subprocess.SubprocessError):
        pass
    return datetime.date.fromtimestamp(Path(root, path).stat().st_mtime).isoformat()


def is_tts_study(d):
    s, r = d / 'summary.json', d / 'rows.jsonl'
    if not (s.exists() and r.exists()):
        return False
    try:
        summary = json.loads(s.read_text())
        first = json.loads(next(l for l in r.read_text().splitlines() if l.strip()))
    except (ValueError, StopIteration):
        return False
    return bool(summary.get('ladder')) and 'runs' in first and 'target' in first


def is_qet_study(d):
    s = d / 'summary.json'
    if not (s.exists() and (d / 'rows.jsonl').exists()):
        return False
    try:
        return json.loads(s.read_text()).get('schema') == 'genesis-qet-study-v1'
    except ValueError:
        return False


def discover(root, include_unfinished=False):
    """Profiles of every time-to-solution study under `root/evidence`, in batch order."""
    out = []
    for d in sorted(Path(root, 'evidence').iterdir()):
        m = re.search(r'b20r(\d+)$', d.name)
        if not m or not d.is_dir():
            continue
        finished = (d / 'summary.json').exists()
        if not finished and not include_unfinished:
            continue
        if finished and is_qet_study(d):
            s = json.loads((d / 'summary.json').read_text())
            arms = [s['design']['focal']['arm']] + [a for a, _ in s['design']['champions']] + \
                [e['arm'] for e in s['design'].get('extra', ())]
            rel = d.relative_to(root)
            out.append((int(m.group(1)), Profile(f'B20_R{m.group(1)}', str(rel), arms[0], tuple(arms[1:]),
                                                 _date(root, rel / 'summary.json'), kind='qet')))
            continue
        if finished and not is_tts_study(d):
            continue
        rows = [json.loads(l) for l in (d / 'rows.jsonl').read_text().splitlines() if l.strip()] \
            if (d / 'rows.jsonl').exists() else []
        if not rows:
            continue
        arms = list(rows[0]['runs'])
        focal = next((a for a in NATIVE if a in arms), None)
        if focal is None:
            continue
        rel = d.relative_to(root)
        date = _date(root, rel / ('summary.json' if finished else 'rows.jsonl'))
        out.append((int(m.group(1)), Profile(f'B20_R{m.group(1)}', str(rel), focal,
                                             tuple(a for a in arms if a != focal), date)))
    return [p for _, p in sorted(out)]
