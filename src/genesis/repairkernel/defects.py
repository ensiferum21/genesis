"""The testbed's planted defects (kernel side; sealed). Each is an exact edit of a correct component's source, of a
class the first version supports (cache eviction and ordering, invalidation, aliasing, iteration over a mutated
container, a missing paired update) or, for honesty, one it is not expected to reach (R2: a whole loop missing).

`split`: 'dev' defects were used while the loop was built. 'heldout' ones were never run by the loop before the
benchmark; this file's digest is recorded in the benchmark report. The builder wrote both, so 'held out' means unseen
by the loop's development, not unknown to its author (disclosed).

History (disclosed): the first catalogue (30 Oct 2026, file created 23:14 SGT) had 4 dev and 12 held-out defects. During
development the loop was run, by mistake, on L3, R1 (law mining only), S2 and G2; those four were moved to 'dev' at
23:24 SGT, and five new held-out defects (G3, L5, W3, R5, S4) were written then, before any further development."""
DEFECTS = (
    # ---- development defects
    {'id': 'M1', 'split': 'dev', 'target': 'memo', 'class': 'ordering',
     'old': """            if len(self._seen) >= self.limit:
                self._seen.clear()
            self._seen[key] = v""",
     'new': """            self._seen[key] = v
            if len(self._seen) >= self.limit:
                self._seen.clear()"""},
    {'id': 'L2', 'split': 'dev', 'target': 'lru', 'class': 'eviction-order',
     'old': """            return default
        self.d.move_to_end(k)
        return self.d[k]""",
     'new': """            return default
        return self.d[k]"""},
    {'id': 'S1', 'split': 'dev', 'target': 'stats', 'class': 'invalidation',
     'old': """        self.values.append(v)
        self._total = None
        self._top = None""",
     'new': """        self.values.append(v)
        self._top = None"""},
    {'id': 'W2', 'split': 'dev', 'target': 'window', 'class': 'eviction-order',
     'old': "            self.buf.pop(0)", 'new': "            self.buf.pop()"},
    # ---- held-out defects
    {'id': 'M2', 'split': 'heldout', 'target': 'memo', 'class': 'guard',
     'old': "        if key not in self._seen:", 'new': "        if key in self._seen:"},
    {'id': 'L1', 'split': 'heldout', 'target': 'lru', 'class': 'eviction-order',
     'old': "            self.d.popitem(last=False)", 'new': "            self.d.popitem(last=True)"},
    {'id': 'L3', 'split': 'dev', 'target': 'lru', 'class': 'bound',
     'old': "        if len(self.d) > self.capacity:", 'new': "        if len(self.d) >= self.capacity:"},
    {'id': 'L4', 'split': 'heldout', 'target': 'lru', 'class': 'eviction-order',
     'old': """        if k in self.d:
            self.d.move_to_end(k)
        self.d[k] = v""",
     'new': """        self.d[k] = v"""},
    {'id': 'R1', 'split': 'dev', 'target': 'registry', 'class': 'index-update',
     'old': "                self.index[k] = j - 1", 'new': "                self.index[k] = j + 1"},
    {'id': 'R2', 'split': 'heldout', 'target': 'registry', 'class': 'missing-block',
     'old': """        self.items.pop(i)
        for k, j in list(self.index.items()):
            if j > i:
                self.index[k] = j - 1""",
     'new': """        self.items.pop(i)"""},
    {'id': 'R4', 'split': 'heldout', 'target': 'registry', 'class': 'ordering',
     'old': """        self.index[name] = len(self.items)
        self.items.append(value)""",
     'new': """        self.items.append(value)
        self.index[name] = len(self.items)"""},
    {'id': 'S2', 'split': 'dev', 'target': 'stats', 'class': 'invalidation',
     'old': """        v = self.values.pop()
        self._total = None
        self._top = None""",
     'new': """        v = self.values.pop()
        self._total = None"""},
    {'id': 'S3', 'split': 'heldout', 'target': 'stats', 'class': 'wrong-function',
     'old': "            self._top = max(self.values) if self.values else None",
     'new': "            self._top = min(self.values) if self.values else None"},
    {'id': 'W1', 'split': 'heldout', 'target': 'window', 'class': 'aliasing',
     'old': "        return {'size': self.size, 'buf': list(self.buf)}",
     'new': "        return {'size': self.size, 'buf': self.buf}"},
    {'id': 'G1', 'split': 'heldout', 'target': 'log', 'class': 'iteration',
     'old': "        for e in list(self.events):", 'new': "        for e in self.events:"},
    {'id': 'G2', 'split': 'dev', 'target': 'log', 'class': 'paired-update',
     'old': """                self.events.remove(e)
                self.seen.discard(e)""",
     'new': """                self.events.remove(e)"""},
    # ---- held-out defects added at 23:24 SGT (see the history above)
    {'id': 'G3', 'split': 'heldout', 'target': 'log', 'class': 'paired-update',
     'old': "        self.seen.add(e)\n        self.events.append(e)",
     'new': "        self.events.append(e)"},
    {'id': 'L5', 'split': 'heldout', 'target': 'lru', 'class': 'eviction-order',
     'old': "            return default\n        self.d.move_to_end(k)",
     'new': "            return default\n        self.d.move_to_end(k, last=False)"},
    {'id': 'W3', 'split': 'heldout', 'target': 'window', 'class': 'bound',
     'old': "        if len(self.buf) > self.size:", 'new': "        if len(self.buf) > self.size + 1:"},
    {'id': 'R5', 'split': 'heldout', 'target': 'registry', 'class': 'index-update',
     'old': "        return self.items[self.index[name]]", 'new': "        return self.items[self.index[name] - 1]"},
    {'id': 'S4', 'split': 'heldout', 'target': 'stats', 'class': 'eviction-order',
     'old': "        v = self.values.pop()", 'new': "        v = self.values.pop(0)"},
)
BY_ID = {d['id']: d for d in DEFECTS}


def source(defect_id, sources):
    d = BY_ID[defect_id]
    src = sources[d['target']]
    if src.count(d['old']) != 1:
        raise ValueError(f'{defect_id}: the edit does not apply exactly once')
    return src.replace(d['old'], d['new'])
