"""Gset (B20_R101): the public max-cut benchmark as pinned `maxcut_v1` tasks, with published best-known values.

Data (`data/gset/`):
  * `set1.zip`: G1-G54 in `.rud` format (Helmberg and Rendl 2000; OPTSICOM's set 1), Daniel's download of 22 Oct 2026.
    `MANIFEST.json` pins the archive and every member by SHA-256; `tasks()` refuses anything else.
  * `best_known.json`: for each instance, the highest value among the sources held (OPTSICOM's 2009 table; breakout
    local search's published improvements, Benlic and Hao 2013), every source's value, and the policy: a result is a
    fraction of this value, never a record claim, until checked against the paper that set it.

Families (Helmberg and Rendl's construction, read from the instance numbers; weights read from the file):
random (G1-G10, G22-G31, G43-G47), toroidal 2D grids (G11-G13, G32-G34, G48-G50), planar (G14-G21, G35-G42, G51-G54).
"""
import hashlib
import json
from pathlib import Path
import zipfile

DATA = Path(__file__).resolve().parents[2] / 'data' / 'gset'
FAMILY = {**{k: 'random' for k in list(range(1, 11)) + list(range(22, 32)) + list(range(43, 48))},
          **{k: 'toroidal' for k in list(range(11, 14)) + list(range(32, 35)) + list(range(48, 51))},
          **{k: 'planar' for k in list(range(14, 22)) + list(range(35, 43)) + list(range(51, 55))}}


def manifest():
    return json.loads((DATA / 'MANIFEST.json').read_text())


def best_known():
    """{'G1': value, ...}."""
    doc = json.loads((DATA / 'best_known.json').read_text())
    return {g: v['best_known'] for g, v in doc['instances'].items()}


def tasks(numbers=None):
    """The pinned Gset instances as `MaxCutTask`s (task_id 'gset-G<k>', family 'gset-<family>-<weights>')."""
    from .graphs_maxcut import parse_rud
    from .models_maxcut import MaxCutTask
    if numbers is not None and not set(numbers) <= set(FAMILY):
        raise ValueError(f'Gset set 1 holds G1-G54, not {sorted(set(numbers) - set(FAMILY))}')
    man = manifest()
    raw = (DATA / man['archive']).read_bytes()
    if hashlib.sha256(raw).hexdigest() != man['archive_sha256']:
        raise ValueError('the Gset archive is not the pinned one')
    out = []
    with zipfile.ZipFile(DATA / man['archive']) as z:
        names = sorted(i.filename for i in z.infolist())
        if names != sorted(man['members']):
            raise ValueError('the Gset archive members differ from the manifest')
        for k in sorted(numbers or FAMILY):
            name = f'g{k}.rud'
            data = z.read(name)
            if hashlib.sha256(data).hexdigest() != man['members'][name]:
                raise ValueError(f'{name} is not the pinned file')
            n, edges = parse_rud(data.decode('ascii'))
            weights = 'pm1' if any(w < 0 for _, _, w in edges) else '1'
            out.append(MaxCutTask(task_id=f'gset-G{k}', n=n, edges=edges, family=f'gset-{FAMILY[k]}-{weights}'))
    return out
