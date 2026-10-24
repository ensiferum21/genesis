"""A persistent, resumable research queue (Daniel's directive of 24 Oct 2026, 15:35, item 12).

The queue holds research DIRECTIONS (studies, builds, analyses) with their dependencies and the capabilities they need
or provide. It is a JSON file (`research_queue.json` at the repository root), written atomically, with an append-only
event log, so that any agent can resume it after an interruption.

**States:** queued -> running -> done; a direction may also be `blocked` (by a dependency that failed or a missing
input), `dormant` (its line stagnated, or it waits for a capability) or `abandoned` (by a human decision only).

**Lines and stagnation.** Every direction belongs to a LINE of research (for example `engine-invention`). Each
finished direction records whether its outcome was positive (a preregistered verdict that showed something) or not.
When a line has STAGNATION_LIMIT negative outcomes in a row:
  * the line is marked stagnant, with the outcomes that made it so;
  * its queued directions that are not `committed` (preregistered commitments, which run as registered) become
    `dormant` with the failure kind `stagnated`, their artifacts kept;
  * a diagnosis direction is required before the line receives more compute: `diagnose(line, direction)` records
    which direction diagnoses it (its outcome is the bottleneck found).
Nothing is deleted.

**Capabilities and reactivation.** A direction may `require` capability tags and, when it finishes positively,
`unlock` tags. `reactivate(tag, fuel)` returns dormant directions that require that tag (or whose line's diagnosis
named it) to `queued`, at most `fuel` of them, best priority first, never twice for the same tag; the same rule as the
vault's cascade (`vault.py`), at the level of the research programme.

**Choosing the next direction:** `ready()` lists queued directions whose dependencies are done and whose required
tags are unlocked; `next()` is the ready one with the highest priority (ties by order of addition). Resources are
declared (`cpu0_hours`) so that an allocator can plan; the queue itself never runs anything.
"""
import copy
import datetime
import json
import os
from pathlib import Path

STATES = ('queued', 'running', 'done', 'blocked', 'dormant', 'abandoned')
STAGNATION_LIMIT = 3
FIELDS = ('id', 'title', 'kind', 'line', 'priority', 'depends_on', 'requires', 'unlocks', 'committed', 'resources',
          'script', 'output', 'preregistered', 'notes')


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')


class Queue:
    def __init__(self, path):
        self.path = Path(path)
        if self.path.exists():
            self.doc = json.loads(self.path.read_text())
        else:
            self.doc = {'schema': 'genesis-research-queue-v1', 'directions': {}, 'order': [], 'lines': {},
                        'unlocked': [], 'reactivated': {}, 'events': []}

    # ------------------------------------------------------------------ persistence
    def save(self):
        tmp = self.path.with_suffix(self.path.suffix + '.tmp')
        tmp.write_text(json.dumps(self.doc, indent=1, sort_keys=True) + '\n')
        os.replace(tmp, self.path)

    def _event(self, kind, **kw):
        self.doc['events'].append(dict(kw, kind=kind, time=_now()))

    # ------------------------------------------------------------------ directions
    def add(self, id, title, kind='study', line='general', priority=0, depends_on=(), requires=(), unlocks=(),
            committed=False, resources=None, script=None, output=None, preregistered=None, notes='', status='queued'):
        if id in self.doc['directions']:
            raise ValueError(f'direction {id} exists')
        for d in depends_on:
            if d not in self.doc['directions']:
                raise ValueError(f'unknown dependency {d}')
        if status not in STATES:
            raise ValueError(f'status must be one of {STATES}')
        self.doc['directions'][id] = {
            'id': id, 'title': title, 'kind': kind, 'line': line, 'priority': priority,
            'depends_on': list(depends_on), 'requires': list(requires), 'unlocks': list(unlocks),
            'committed': bool(committed), 'resources': resources or {}, 'script': script, 'output': output,
            'preregistered': preregistered, 'notes': notes, 'status': status, 'outcome': None, 'positive': None,
            'artifacts': [], 'failure': None}
        self.doc['order'].append(id)
        self.doc['lines'].setdefault(line, {'run': 0, 'stagnant': False, 'outcomes': [], 'diagnosis': None})
        self._event('add', id=id)
        return self.doc['directions'][id]

    def get(self, id):
        return copy.deepcopy(self.doc['directions'][id])

    def _set(self, id, **kw):
        self.doc['directions'][id].update(kw)

    def start(self, id):
        d = self.doc['directions'][id]
        if d['status'] != 'queued' or id not in [x['id'] for x in self.ready()]:
            raise ValueError(f'{id} is not ready')
        self._set(id, status='running')
        self._event('start', id=id)

    def finish(self, id, outcome, positive, artifacts=(), unlocks=None):
        """Record a finished direction; a positive outcome unlocks its tags; a negative one counts towards its line's
        stagnation."""
        d = self.doc['directions'][id]
        if d['status'] != 'running':
            raise ValueError(f'{id} is not running')
        self._set(id, status='done', outcome=outcome, positive=bool(positive), artifacts=list(artifacts))
        line = self.doc['lines'][d['line']]
        line['outcomes'].append([id, outcome, bool(positive)])
        line['run'] = 0 if positive else line['run'] + 1
        if positive:
            for t in (d['unlocks'] if unlocks is None else unlocks):
                if t not in self.doc['unlocked']:
                    self.doc['unlocked'].append(t)
        self._event('finish', id=id, outcome=outcome, positive=bool(positive))
        if line['run'] >= STAGNATION_LIMIT and not line['stagnant']:
            self._stagnate(d['line'])

    def record_past(self, line, id, outcome, positive):
        """A finished result from before the queue existed, counted on its line (history only)."""
        ln = self.doc['lines'].setdefault(line, {'run': 0, 'stagnant': False, 'outcomes': [], 'diagnosis': None})
        ln['outcomes'].append([id, outcome, bool(positive)])
        ln['run'] = 0 if positive else ln['run'] + 1
        self._event('past', id=id, line=line, outcome=outcome)
        if ln['run'] >= STAGNATION_LIMIT and not ln['stagnant']:
            self._stagnate(line)

    def _stagnate(self, line):
        ln = self.doc['lines'][line]
        ln['stagnant'] = True
        for id in self.doc['order']:
            d = self.doc['directions'][id]
            if d['line'] == line and d['status'] == 'queued' and not d['committed']:
                self._set(id, status='dormant', failure='stagnated')
        self._event('stagnant', line=line, outcomes=ln['outcomes'][-STAGNATION_LIMIT:])

    def diagnose(self, line, direction, bottleneck=None, tags=()):
        """Name the direction that diagnoses a stagnant line; once it is done, `bottleneck` and the tags whose unlocking
        should reactivate the line are recorded."""
        self.doc['lines'][line]['diagnosis'] = {'direction': direction, 'bottleneck': bottleneck, 'tags': list(tags)}
        self._event('diagnose', line=line, direction=direction, bottleneck=bottleneck)

    def block(self, id, why):
        self._set(id, status='blocked', failure=why)
        self._event('block', id=id, why=why)

    def unblock(self, id):
        if self.doc['directions'][id]['status'] != 'blocked':
            raise ValueError(f'{id} is not blocked')
        self._set(id, status='queued', failure=None)
        self._event('unblock', id=id)

    # ------------------------------------------------------------------ choice
    def ready(self):
        out = []
        for i, id in enumerate(self.doc['order']):
            d = self.doc['directions'][id]
            if d['status'] != 'queued':
                continue
            if any(self.doc['directions'][x]['status'] != 'done' for x in d['depends_on']):
                continue
            if any(t not in self.doc['unlocked'] for t in d['requires']):
                continue
            out.append((-d['priority'], i, d))
        return [copy.deepcopy(d) for _, _, d in sorted(out, key=lambda x: (x[0], x[1]))]

    def next(self):
        r = self.ready()
        return r[0] if r else None

    # ------------------------------------------------------------------ reactivation
    def reactivate(self, tag, fuel):
        """Dormant directions that require `tag`, or whose line's diagnosis names it, back to queued: at most `fuel`,
        best priority first, never twice for the same tag. Returns their ids."""
        if tag not in self.doc['unlocked']:
            raise ValueError(f'{tag} is not unlocked')
        seen = self.doc['reactivated'].setdefault(tag, [])
        cands = []
        for i, id in enumerate(self.doc['order']):
            d = self.doc['directions'][id]
            if d['status'] != 'dormant' or id in seen:
                continue
            diag = self.doc['lines'][d['line']].get('diagnosis') or {}
            if tag in d['requires'] or tag in diag.get('tags', []):
                cands.append((-d['priority'], i, id))
        out = [id for _, _, id in sorted(cands)[:fuel]]
        for id in out:
            self._set(id, status='queued', failure=None)
            seen.append(id)
            self._event('reactivate', id=id, tag=tag)
        return out

    def summary(self):
        by = {}
        for d in self.doc['directions'].values():
            by.setdefault(d['status'], []).append(d['id'])
        return {'by_status': by, 'stagnant_lines': sorted(k for k, v in self.doc['lines'].items() if v['stagnant']),
                'unlocked': list(self.doc['unlocked']), 'next': (self.next() or {}).get('id')}


__all__ = ['STATES', 'STAGNATION_LIMIT', 'Queue']
