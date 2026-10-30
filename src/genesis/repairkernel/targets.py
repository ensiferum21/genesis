"""The testbed's components (kernel side): small state-management classes of the kinds Genesis's research code
uses (a bounded score memo, an LRU cache, a name registry, a cached derived value, a sliding window with save and
load, a deduplicating event log). Each has its correct source, a reference model the kernel checks it against, a
workload generator, and the tests visible to the repairer (which, as in real code, do not catch every defect)."""

SOURCES = {
    'memo': '''"""A bounded memo of an expensive score."""


class Scorer:
    def __init__(self, f, limit=64):
        self.f = f
        self.limit = limit
        self._seen = {}

    def score(self, x):
        key = tuple(x)
        if key not in self._seen:
            v = self.f(key)
            if len(self._seen) >= self.limit:
                self._seen.clear()
            self._seen[key] = v
        return self._seen[key]

    def size(self):
        return len(self._seen)
''',
    'lru': '''"""A least-recently-used cache."""
from collections import OrderedDict


class LRU:
    def __init__(self, capacity):
        self.capacity = capacity
        self.d = OrderedDict()

    def get(self, k, default=None):
        if k not in self.d:
            return default
        self.d.move_to_end(k)
        return self.d[k]

    def put(self, k, v):
        if k in self.d:
            self.d.move_to_end(k)
        self.d[k] = v
        if len(self.d) > self.capacity:
            self.d.popitem(last=False)

    def keys(self):
        return list(self.d)
''',
    'registry': '''"""Names mapped to positions in a list."""


class Registry:
    def __init__(self):
        self.items = []
        self.index = {}

    def add(self, name, value):
        if name in self.index:
            self.items[self.index[name]] = value
            return self.index[name]
        self.index[name] = len(self.items)
        self.items.append(value)
        return self.index[name]

    def remove(self, name):
        i = self.index.pop(name)
        self.items.pop(i)
        for k, j in list(self.index.items()):
            if j > i:
                self.index[k] = j - 1

    def get(self, name):
        return self.items[self.index[name]]

    def names(self):
        return sorted(self.index)
''',
    'stats': '''"""Values with a cached total and a cached maximum."""


class Stats:
    def __init__(self):
        self.values = []
        self._total = None
        self._top = None

    def add(self, v):
        self.values.append(v)
        self._total = None
        self._top = None

    def drop_last(self):
        v = self.values.pop()
        self._total = None
        self._top = None
        return v

    def total(self):
        if self._total is None:
            self._total = sum(self.values)
        return self._total

    def top(self):
        if self._top is None:
            self._top = max(self.values) if self.values else None
        return self._top
''',
    'window': '''"""A sliding window that can be saved and restored."""


class Window:
    def __init__(self, size):
        self.size = size
        self.buf = []

    def push(self, x):
        self.buf.append(x)
        if len(self.buf) > self.size:
            self.buf.pop(0)

    def mean(self):
        return sum(self.buf) / len(self.buf) if self.buf else 0.0

    def state(self):
        return {'size': self.size, 'buf': list(self.buf)}

    @classmethod
    def load(cls, st):
        w = cls(st['size'])
        w.buf = list(st['buf'])
        return w
''',
    'log': '''"""An event log that records each event once and can be pruned."""


class Log:
    def __init__(self):
        self.events = []
        self.seen = set()

    def record(self, e):
        if e in self.seen:
            return False
        self.seen.add(e)
        self.events.append(e)
        return True

    def prune(self, keep_mod):
        for e in list(self.events):
            if e % keep_mod == 0:
                self.events.remove(e)
                self.seen.discard(e)

    def count(self):
        return len(self.events)
''',
}
CLASS = {'memo': 'Scorer', 'lru': 'LRU', 'registry': 'Registry', 'stats': 'Stats', 'window': 'Window', 'log': 'Log'}


def _f(key):
    return sum((i + 1) * v for i, v in enumerate(key)) % 97


# ------------------------------------------------------------------------------------------- reference models

class RefScorer:
    def __init__(self, f, limit=64):
        self.f = f

    def score(self, x):
        return self.f(tuple(x))


class RefLRU:
    def __init__(self, capacity):
        self.capacity, self.order, self.vals = capacity, [], {}

    def get(self, k, default=None):
        if k not in self.vals:
            return default
        self.order.remove(k)
        self.order.append(k)
        return self.vals[k]

    def put(self, k, v):
        if k in self.vals:
            self.order.remove(k)
        self.order.append(k)
        self.vals[k] = v
        if len(self.order) > self.capacity:
            old = self.order.pop(0)
            del self.vals[old]

    def keys(self):
        return list(self.order)


class RefRegistry:
    def __init__(self):
        self.d = {}

    def add(self, name, value):
        self.d[name] = value
        return None                          # positions are the component's business; not compared

    def remove(self, name):
        del self.d[name]

    def get(self, name):
        return self.d[name]

    def names(self):
        return sorted(self.d)


class RefStats:
    def __init__(self):
        self.values = []

    def add(self, v):
        self.values.append(v)

    def drop_last(self):
        return self.values.pop()

    def total(self):
        return sum(self.values)

    def top(self):
        return max(self.values) if self.values else None


class RefWindow:
    def __init__(self, size):
        self.size, self.buf, self.snap = size, [], None

    def save(self):
        self.snap = list(self.buf)

    def restore(self):
        if self.snap is not None:
            self.buf = list(self.snap)

    def push(self, x):
        self.buf = (self.buf + [x])[-self.size:]

    def mean(self):
        return sum(self.buf) / len(self.buf) if self.buf else 0.0


class RefLog:
    def __init__(self):
        self.events = []

    def record(self, e):
        if e in self.events:
            return False
        self.events.append(e)
        return True

    def prune(self, keep_mod):
        self.events = [e for e in self.events if e % keep_mod != 0]

    def count(self):
        return len(self.events)


REFERENCE = {'memo': RefScorer, 'lru': RefLRU, 'registry': RefRegistry, 'stats': RefStats, 'window': RefWindow,
             'log': RefLog}


# ------------------------------------------------------------------------------------------- workloads

def make_args(target, rng):
    """The constructor's arguments for an instance."""
    if target == 'memo':
        return [_f], {'limit': rng.choice([16, 24, 32])}
    if target == 'lru':
        return [rng.choice([4, 6, 8])], {}
    if target == 'window':
        return [rng.choice([3, 5, 7])], {}
    return [], {}


def ops(target, rng, n, warm=0.4):
    """A workload: n operations [(method, args)], each followed by an observation, checked against the reference.
    The first `warm` share is a warm-up phase that uses only the component's basic operations and a small key space
    (no eviction, no removal, no save and restore), as a long run's early phase would; the rest is the full mix. So
    some defects show at once and others only after several checkpoints."""
    out = []
    for t in range(n):
        warm_phase = t < warm * n
        if target == 'memo':
            k = 3 if warm_phase else 6
            out.append(('score', [[rng.randrange(k) for _ in range(2 if warm_phase else rng.choice([2, 3]))]]))
        elif target == 'lru':
            if warm_phase:
                out.append(('put', [t % 3, rng.randrange(100)]))
            else:
                k = rng.randrange(12)
                out.append(('get', [k]) if rng.random() < 0.5 else ('put', [k, rng.randrange(100)]))
        elif target == 'registry':
            r = rng.random()
            if warm_phase:
                name = f'n{rng.randrange(10)}'
                out.append(('add', [name, rng.randrange(100)]) if r < 0.6 else ('get', [name]))
            else:
                name = f'n{rng.randrange(10)}'
                out.append(('add', [name, rng.randrange(100)]) if r < 0.5 else ('remove', [name]) if r < 0.7
                           else ('get', [name]))
        elif target == 'stats':
            r = rng.random()
            if warm_phase:
                out.append(('add', [rng.randrange(-50, 50)]) if r < 0.1 else ('total', []) if r < 0.55
                           else ('top', []))
            else:
                out.append(('add', [rng.randrange(-50, 50)]) if r < 0.3 else ('drop_last', []) if r < 0.75
                           else ('total', []) if r < 0.85 else ('top', []))
        elif target == 'window':
            r = rng.random()
            if warm_phase:
                out.append(('push', [rng.randrange(100)]) if r < 0.75 else ('mean', []))
            else:
                out.append(('push', [rng.randrange(100)]) if r < 0.7 else ('mean', []) if r < 0.85 else
                           ('save', []) if r < 0.93 else ('restore', []))
        elif target == 'log':
            r = rng.random()
            if warm_phase:
                out.append(('record', [rng.randrange(40)]))
            else:
                out.append(('record', [rng.randrange(40)]) if r < 0.85 else ('prune', [rng.choice([3, 4, 5])]))
        out.append(('observe', []))
    return out


OBSERVE = {'memo': 'size', 'lru': 'keys', 'registry': 'names', 'stats': 'total', 'window': 'mean', 'log': 'count'}
COMPARE_OBSERVE = {'memo': False, 'lru': True, 'registry': True, 'stats': True, 'window': True, 'log': True}

VISIBLE_TESTS = {
    'memo': [('a repeated score is the same', '''
s = mod.Scorer(lambda k: sum(k), limit=4)
assert s.score([1, 2]) == 3
assert s.score([1, 2]) == 3
''')],
    'lru': [('get after put', '''
c = mod.LRU(2)
c.put(1, 'a')
assert c.get(1) == 'a'
assert c.get(9) is None
''')],
    'registry': [('add then get', '''
r = mod.Registry()
r.add('a', 1)
r.add('b', 2)
assert r.get('b') == 2
''')],
    'stats': [('total and top', '''
s = mod.Stats()
s.add(3)
s.add(5)
assert s.total() == 8 and s.top() == 5
''')],
    'window': [('mean of a short window', '''
w = mod.Window(2)
w.push(1)
w.push(3)
assert w.mean() == 2
''')],
    'log': [('record once', '''
g = mod.Log()
assert g.record(1) and not g.record(1)
assert g.count() == 1
''')],
}
