"""Legacy retention and negative transfer under a frozen protocol (handoff H08, s20.6).

"Measure legacy retention and negative transfer under a frozen protocol. Repeated evaluation on
the same public retention tasks can itself become training; maintain protected retention
confirmation material where the claim requires it."

A campaign freezes ONE retention protocol in its store (entity ``retention_protocol``, id
``protocol``; write-once) before any measurement:

  panels       named panels of tasks, typically ``legacy`` (the campaign's own domain and earlier,
               easier families) and ``transfer`` (another domain or family the research never
               targeted). The record keeps, per panel, a commitment to its task list.
  material     DEV_PUBLIC: the tasks are in the record (anyone, research included, can see them).
               PROTECTED: the tasks and a salt live only in a private root (0700, outside the
               campaign and its exports); the record holds the salted commitment and the task count.
               Research that reads the campaign store or its export never sees protected tasks.
  rule         per panel, paired differences child − parent over the same tasks and seeds; a
               percentile bootstrap interval (``resamples``, ``level``); with margin m:
                 NEGATIVE_TRANSFER  mean <= −m and upper bound < 0
                 RETAINED           lower bound > −m
                 INCONCLUSIVE       otherwise
  budget       the number of measurements the protocol allows in total. Each (from, to) pair is
               measured at most once (entity ``retention_measurement``, id = digest of the pair), so
               the retention material is not re-used until a lucky pass appears and cannot become a
               training signal by repetition.

``measure(store, from_version, to_version, ...)`` runs both versions' frozen solver programs
(``execution.execute``, the campaign's limits) on every panel task with seeds fixed by the protocol,
and records the result. Versions are read from the store's ``system_version`` entities (content
digests). A NEGATIVE_TRANSFER verdict is evidence for a rollback decision (``versions.rollback``);
nothing here moves the pointer.
"""
import json
import os
from pathlib import Path
import random
import statistics

from .common import atomic_write, canonical, digest

PROTOCOL_SCHEMA = 'genesis-retention-protocol-v1'
MEASUREMENT_SCHEMA = 'genesis-retention-measurement-v1'
MATERIALS = ('DEV_PUBLIC', 'PROTECTED')
VERDICTS = ('RETAINED', 'NEGATIVE_TRANSFER', 'INCONCLUSIVE')


class RetentionError(ValueError):
    pass


def _tasks_digest(tasks):
    return digest([t.model_dump(mode='json') for t in tasks])


def freeze(store, panels, *, limits, margin=0.5, level=0.9, resamples=2000, budget=4, material='DEV_PUBLIC',
           private_root=None, seed=0):
    """Freeze the campaign's retention protocol (write-once). ``panels``: {name: [GraphTask]}."""
    from .models import Limits
    if material not in MATERIALS:
        raise RetentionError(f'material must be one of {MATERIALS}')
    if not isinstance(panels, dict) or not panels or any(not isinstance(v, list) or not v for v in panels.values()):
        raise RetentionError('at least one non-empty panel')
    if not (0 < margin and 0.5 < level < 1 and resamples >= 200 and type(budget) is int and budget >= 1):
        raise RetentionError('margin > 0, level in (0.5, 1), resamples >= 200, budget >= 1')
    Limits.model_validate_json(canonical(limits.model_dump(mode='json')))
    if store.db.execute("SELECT 1 FROM entities WHERE kind='retention_protocol' AND id='protocol'").fetchone():
        raise RetentionError('the campaign already has a frozen retention protocol')
    record = {'schema': PROTOCOL_SCHEMA, 'material': material, 'margin': margin, 'level': level,
              'resamples': resamples, 'budget': budget, 'seed': seed, 'limits': limits.model_dump(mode='json'),
              'panels': {}}
    if material == 'PROTECTED':
        if private_root is None:
            raise RetentionError('protected material needs a private root')
        root = Path(private_root)
        root.mkdir(parents=True, exist_ok=True)
        root.chmod(0o700)
        salt = os.urandom(32).hex()
        for name, tasks in sorted(panels.items()):
            record['panels'][name] = {'tasks': len(tasks),
                                      'commitment': digest({'tasks': _tasks_digest(tasks), 'salt': salt})}
        atomic_write(root / 'retention_material.json',
                     canonical({'salt': salt, 'panels': {n: [t.model_dump(mode='json') for t in ts]
                                                         for n, ts in panels.items()}}), mode=0o600)
    else:
        for name, tasks in sorted(panels.items()):
            record['panels'][name] = {'tasks': len(tasks), 'commitment': _tasks_digest(tasks),
                                      'task_list': [t.model_dump(mode='json') for t in tasks]}
    store.save('retention_protocol', 'protocol', record)
    return record


def protocol(store):
    row = store.db.execute("SELECT object_hash FROM entities WHERE kind='retention_protocol' AND id='protocol'").fetchone()
    if row is None:
        raise RetentionError('no frozen retention protocol in this campaign')
    return store.get(row[0])


def panels(record, private_root=None):
    """The protocol's tasks, checked against its commitments."""
    from .models import GraphTask
    out = {}
    if record['material'] == 'PROTECTED':
        if private_root is None:
            raise RetentionError('protected retention material needs the private root')
        path = Path(private_root) / 'retention_material.json'
        st = path.stat()
        if path.is_symlink() or st.st_mode & 0o077:
            raise RetentionError('the retention material must be a private, non-symlinked file')
        data = json.loads(path.read_text())
        for name, spec in record['panels'].items():
            tasks = [GraphTask.model_validate_json(canonical(t)) for t in data['panels'].get(name, [])]
            if digest({'tasks': _tasks_digest(tasks), 'salt': data['salt']}) != spec['commitment']:
                raise RetentionError(f'panel {name} differs from its commitment')
            out[name] = tasks
    else:
        for name, spec in record['panels'].items():
            tasks = [GraphTask.model_validate_json(canonical(t)) for t in spec['task_list']]
            if _tasks_digest(tasks) != spec['commitment']:
                raise RetentionError(f'panel {name} differs from its commitment')
            out[name] = tasks
    return out


def _program(store, vid):
    from .models import SolverProgram
    row = store.db.execute("SELECT object_hash FROM entities WHERE kind='system_version' AND id=?", (vid,)).fetchone()
    if row is None:
        raise RetentionError(f'version {vid[:12]} is not a stored system version')
    doc = store.get(row[0])
    if digest(doc) != vid:
        raise RetentionError(f'version {vid[:12]} does not hash to its id')
    return SolverProgram.model_validate_json(canonical(doc['solver']))


def _value(receipt):
    return (receipt.get('result') or {}).get('value', 0) if receipt.get('status') == 'SUCCESS' else 0


def verdict(diffs, record, rng_seed):
    mean = statistics.fmean(diffs)
    rng = random.Random(rng_seed)
    n, sims = len(diffs), []
    for _ in range(record['resamples']):
        sims.append(statistics.fmean(diffs[rng.randrange(n)] for _ in range(n)))
    sims.sort()
    tail = (1 - record['level']) / 2
    lo, hi = sims[int(tail * len(sims))], sims[min(len(sims) - 1, int((1 - tail) * len(sims)))]
    m = record['margin']
    v = 'NEGATIVE_TRANSFER' if mean <= -m and hi < 0 else 'RETAINED' if lo > -m else 'INCONCLUSIVE'
    return {'mean': round(mean, 4), 'interval': [round(lo, 4), round(hi, 4)], 'verdict': v,
            'wins_ties_losses': [sum(d > 0 for d in diffs), sum(d == 0 for d in diffs), sum(d < 0 for d in diffs)]}


def measure(store, from_version, to_version, *, private_root=None):
    """Measure one (parent, child) pair once, within the protocol's budget, and record it."""
    from .execution import execute
    from .models import Limits
    record = protocol(store)
    if from_version == to_version:
        raise RetentionError('a measurement compares two different versions')
    a, b = _program(store, from_version), _program(store, to_version)
    pair = digest({'from': from_version, 'to': to_version})
    done = [i for (i,) in store.db.execute("SELECT id FROM entities WHERE kind='retention_measurement'")]
    if pair in done:
        raise RetentionError('this pair was already measured: the retention material is not re-used')
    if len(done) >= record['budget']:
        raise RetentionError(f'the protocol allows {record["budget"]} measurements; all are used')
    limits = Limits.model_validate_json(canonical(record['limits']))
    pid = digest(record)
    results, rows = {}, []
    for name, tasks in sorted(panels(record, private_root).items()):
        diffs = []
        for t in tasks:
            seed = int(digest({'retention': pid, 'task': t.task_id})[:12], 16)
            va, vb = _value(execute(t, a, limits, seed)), _value(execute(t, b, limits, seed))
            diffs.append(vb - va)
            rows.append({'panel': name, 'task_sha256': digest(t.model_dump(mode='json')), 'from': va, 'to': vb}
                        if record['material'] == 'PROTECTED' else
                        {'panel': name, 'task_id': t.task_id, 'from': va, 'to': vb})
        results[name] = verdict(diffs, record, int(digest({'boot': pid, 'pair': pair, 'panel': name})[:12], 16))
    overall = ('NEGATIVE_TRANSFER' if any(r['verdict'] == 'NEGATIVE_TRANSFER' for r in results.values()) else
               'RETAINED' if all(r['verdict'] == 'RETAINED' for r in results.values()) else 'INCONCLUSIVE')
    out = {'schema': MEASUREMENT_SCHEMA, 'protocol_sha256': pid, 'from_version': from_version,
           'to_version': to_version, 'panels': results, 'verdict': overall, 'rows': rows,
           'sequence': len(done), 'note': 'a NEGATIVE_TRANSFER verdict supports a rollback decision; it moves nothing'}
    store.save('retention_measurement', pair, out)
    return out


def measurements(store):
    rows = store.db.execute("SELECT object_hash FROM entities WHERE kind='retention_measurement'").fetchall()
    return sorted((store.get(h) for (h,) in rows), key=lambda m: m['sequence'])


__all__ = ['freeze', 'protocol', 'panels', 'measure', 'measurements', 'verdict', 'RetentionError', 'MATERIALS',
           'VERDICTS']
