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


# ------------------------------------------------------------------------------------------- larger components
# Added 31 Oct 2026 for SR-1a2 (B20_R180): three larger components (60 to 80 lines), where a whole-file search no
# longer fits in the budget. The six components above are unchanged, and so are their workloads; SOURCES keeps only
# them (B20_R178's analysis counts its controls by it), and ALL_SOURCES has all nine.

SOURCES2 = {
    'ttl': '''"""A cache whose entries expire after a time to live; the least recently used is evicted when it is full."""
from collections import OrderedDict


class TTLCache:
    def __init__(self, capacity, ttl):
        self.capacity = capacity
        self.ttl = ttl
        self.now = 0
        self.d = OrderedDict()
        self.hits = 0
        self.misses = 0

    def tick(self, dt):
        self.now += dt
        self._expire()

    def _expire(self):
        for k in list(self.d):
            if self.d[k][1] <= self.now:
                del self.d[k]

    def put(self, k, v):
        if k in self.d:
            del self.d[k]
        self.d[k] = (v, self.now + self.ttl)
        while len(self.d) > self.capacity:
            self.d.popitem(last=False)

    def get(self, k, default=None):
        entry = self.d.get(k)
        if entry is None or entry[1] <= self.now:
            self.misses += 1
            return default
        self.hits += 1
        self.d.move_to_end(k)
        return entry[0]

    def counts(self):
        return (self.hits, self.misses)

    def keys(self):
        return list(self.d)

    def snapshot(self):
        return (list(self.d), self.hits, self.misses)
''',
    'pq': '''"""A priority queue of keys with a position index, so that a key's priority can change or the key be removed."""


class IndexedHeap:
    def __init__(self):
        self.heap = []
        self.pos = {}

    def size(self):
        return len(self.heap)

    def push(self, key, prio):
        if key in self.pos:
            self.update(key, prio)
            return
        self.heap.append([prio, key])
        self.pos[key] = len(self.heap) - 1
        self._up(len(self.heap) - 1)

    def peek(self):
        return self.heap[0][1] if self.heap else None

    def pop(self):
        if not self.heap:
            return None
        top = self.heap[0][1]
        self._swap(0, len(self.heap) - 1)
        self.heap.pop()
        del self.pos[top]
        if self.heap:
            self._down(0)
        return top

    def update(self, key, prio):
        i = self.pos[key]
        old = self.heap[i][0]
        self.heap[i][0] = prio
        if prio < old:
            self._up(i)
        else:
            self._down(i)

    def remove(self, key):
        i = self.pos[key]
        last = len(self.heap) - 1
        self._swap(i, last)
        self.heap.pop()
        del self.pos[key]
        if i < len(self.heap):
            self._up(i)
            self._down(i)

    def _swap(self, i, j):
        self.heap[i], self.heap[j] = self.heap[j], self.heap[i]
        self.pos[self.heap[i][1]] = i
        self.pos[self.heap[j][1]] = j

    def _up(self, i):
        while i > 0:
            p = (i - 1) // 2
            if self.heap[i] < self.heap[p]:
                self._swap(i, p)
                i = p
            else:
                break

    def _down(self, i):
        n = len(self.heap)
        while True:
            c = 2 * i + 1
            if c >= n:
                break
            if c + 1 < n and self.heap[c + 1] < self.heap[c]:
                c += 1
            if self.heap[c] < self.heap[i]:
                self._swap(i, c)
                i = c
            else:
                break

    def summary(self):
        return (self.peek(), len(self.heap))
''',
    'ledger': '''"""Accounts with balances, a transaction log that can be undone, a per-account history and a cached total."""


class Ledger:
    def __init__(self):
        self.balances = {}
        self.txs = []
        self.by_acct = {}
        self._total = None

    def open(self, acct):
        if acct not in self.balances:
            self.balances[acct] = 0
            self.by_acct[acct] = []

    def _apply(self, acct, amount):
        self.balances[acct] += amount
        self._total = None

    def deposit(self, acct, amount):
        self._apply(acct, amount)
        self.txs.append((acct, amount))
        self.by_acct[acct].append(len(self.txs) - 1)

    def withdraw(self, acct, amount):
        if self.balances[acct] < amount:
            raise ValueError('insufficient funds')
        self._apply(acct, -amount)
        self.txs.append((acct, -amount))
        self.by_acct[acct].append(len(self.txs) - 1)

    def undo(self):
        if not self.txs:
            return None
        acct, amount = self.txs.pop()
        self.by_acct[acct].pop()
        self._apply(acct, -amount)
        return acct

    def balance(self, acct):
        return self.balances[acct]

    def total(self):
        if self._total is None:
            self._total = sum(self.balances.values())
        return self._total

    def history(self, acct):
        return list(self.by_acct[acct])

    def snapshot(self):
        return (sorted(self.balances.items()), len(self.txs))
''',
}
ALL_SOURCES = dict(SOURCES, **SOURCES2)
CLASS.update({'ttl': 'TTLCache', 'pq': 'IndexedHeap', 'ledger': 'Ledger'})


class RefTTL:
    def __init__(self, capacity, ttl):
        self.capacity, self.ttl, self.now = capacity, ttl, 0
        self.order, self.vals, self.dead = [], {}, {}
        self.hits = self.misses = 0

    def _drop(self, k):
        self.order.remove(k)
        del self.vals[k], self.dead[k]

    def tick(self, dt):
        self.now += dt
        for k in list(self.order):
            if self.dead[k] <= self.now:
                self._drop(k)

    def put(self, k, v):
        if k in self.vals:
            self._drop(k)
        self.order.append(k)
        self.vals[k], self.dead[k] = v, self.now + self.ttl
        while len(self.order) > self.capacity:
            self._drop(self.order[0])

    def get(self, k, default=None):
        if k not in self.vals or self.dead[k] <= self.now:
            self.misses += 1
            return default
        self.hits += 1
        self.order.remove(k)
        self.order.append(k)
        return self.vals[k]

    def counts(self):
        return (self.hits, self.misses)

    def keys(self):
        return list(self.order)

    def snapshot(self):
        return (list(self.order), self.hits, self.misses)


class RefPQ:
    def __init__(self):
        self.prio = {}

    def size(self):
        return len(self.prio)

    def push(self, key, prio):
        self.prio[key] = prio

    def peek(self):
        return min(self.prio, key=lambda k: (self.prio[k], k)) if self.prio else None

    def pop(self):
        k = self.peek()
        if k is not None:
            del self.prio[k]
        return k

    def update(self, key, prio):
        if key not in self.prio:
            raise KeyError(key)
        self.prio[key] = prio

    def remove(self, key):
        del self.prio[key]

    def summary(self):
        return (self.peek(), len(self.prio))


class RefLedger:
    def __init__(self):
        self.balances, self.txs = {}, []

    def open(self, acct):
        self.balances.setdefault(acct, 0)

    def deposit(self, acct, amount):
        self.balances[acct] += amount
        self.txs.append((acct, amount))

    def withdraw(self, acct, amount):
        if self.balances[acct] < amount:
            raise ValueError('insufficient funds')
        self.balances[acct] -= amount
        self.txs.append((acct, -amount))

    def undo(self):
        if not self.txs:
            return None
        acct, amount = self.txs.pop()
        self.balances[acct] -= amount
        return acct

    def balance(self, acct):
        return self.balances[acct]

    def total(self):
        return sum(self.balances.values())

    def history(self, acct):
        if acct not in self.balances:
            raise KeyError(acct)
        return [i for i, (a, _) in enumerate(self.txs) if a == acct]

    def snapshot(self):
        return (sorted(self.balances.items()), len(self.txs))


REFERENCE.update({'ttl': RefTTL, 'pq': RefPQ, 'ledger': RefLedger})
OBSERVE.update({'ttl': 'snapshot', 'pq': 'summary', 'ledger': 'snapshot'})
COMPARE_OBSERVE.update({'ttl': True, 'pq': True, 'ledger': True})
_make_args_small, _ops_small = make_args, ops
ACCOUNTS = ('a', 'b', 'c', 'd', 'e')


def make_args(target, rng):                                                # noqa: F811 - extends the one above
    if target == 'ttl':
        return [rng.choice([4, 6])], {'ttl': rng.choice([5, 8])}
    return _make_args_small(target, rng)


def ops(target, rng, n, warm=0.4):                                         # noqa: F811 - extends the one above
    if target not in ('ttl', 'pq', 'ledger'):
        return _ops_small(target, rng, n, warm)
    out = []
    for t in range(n):
        warm_phase = t < warm * n
        r = rng.random()
        if target == 'ttl':
            if warm_phase:
                k = rng.randrange(3)
                out.append(('put', [k, rng.randrange(100)]) if r < 0.5 else ('get', [k]))
            else:
                k = rng.randrange(10)
                out.append(('put', [k, rng.randrange(100)]) if r < 0.35 else ('get', [k]) if r < 0.8
                           else ('tick', [rng.choice([1, 2, 3])]))
        elif target == 'pq':
            if warm_phase:
                out.append(('push', [rng.randrange(30), rng.randrange(50)]) if r < 0.7 else ('peek', []))
            else:
                key = rng.randrange(30)
                out.append(('push', [key, rng.randrange(50)]) if r < 0.35 else ('pop', []) if r < 0.55
                           else ('update', [key, rng.randrange(50)]) if r < 0.75 else ('remove', [key]) if r < 0.9
                           else ('peek', []))
        else:                                                               # ledger
            a = rng.choice(ACCOUNTS)
            if warm_phase:
                out.append(('open', [a]) if r < 0.25 else ('deposit', [a, rng.randrange(1, 50)]) if r < 0.8
                           else ('balance', [a]))
            else:
                out.append(('deposit', [a, rng.randrange(1, 50)]) if r < 0.3 else
                           ('withdraw', [a, rng.randrange(1, 60)]) if r < 0.55 else ('undo', []) if r < 0.7 else
                           ('balance', [a]) if r < 0.8 else ('total', []) if r < 0.9 else ('history', [a]))
        out.append(('observe', []))
    return out


VISIBLE_TESTS.update({
    'ttl': [('put then get, then expiry', '''
c = mod.TTLCache(2, ttl=3)
c.put('a', 1)
assert c.get('a') == 1
c.tick(5)
assert c.get('a') is None
''')],
    'pq': [('push and pop in order', '''
h = mod.IndexedHeap()
for k, p in ((1, 5), (2, 3), (3, 4)):
    h.push(k, p)
assert h.pop() == 2 and h.pop() == 3 and h.pop() == 1
''')],
    'ledger': [('deposit and balance', '''
g = mod.Ledger()
g.open('a')
g.deposit('a', 10)
assert g.balance('a') == 10 and g.total() == 10
''')],
})


# ------------------------------------------------------------------------------------------- B20_R181's components
# Added 31 Oct 2026 for SR-1a3 (B20_R181): a lease table with a clock, an undirected graph, a two-way map. SOURCES,
# SOURCES2 and ALL_SOURCES are unchanged (B20_R178's and B20_R180's analyses count their controls by them); the kernel
# looks components up in SOURCES_ANY, which has all twelve.

SOURCES3 = {
    'lease': '''"""Leases on named resources: a lease lasts a fixed term from when it is granted or renewed."""


class Leases:
    def __init__(self, term):
        self.term = term
        self.now = 0
        self.holder = {}
        self.until = {}
        self.granted = 0

    def advance(self, dt):
        self.now += dt
        self._sweep()

    def _sweep(self):
        for r in [r for r, t in self.until.items() if t <= self.now]:
            del self.until[r]
            del self.holder[r]

    def acquire(self, r, who):
        if r in self.holder and self.holder[r] != who:
            return False
        self.holder[r] = who
        self.until[r] = self.now + self.term
        self.granted += 1
        return True

    def renew(self, r, who):
        if self.holder.get(r) != who:
            return False
        self.until[r] = self.now + self.term
        return True

    def release(self, r, who):
        if self.holder.get(r) == who:
            del self.holder[r]
            del self.until[r]
            return True
        return False

    def owner(self, r):
        return self.holder.get(r)

    def snapshot(self):
        return (sorted(self.holder.items()), sorted(self.until.items()), self.granted)
''',
    'graph': '''"""An undirected graph: adjacency sets and an edge count."""


class Graph:
    def __init__(self):
        self.adj = {}
        self.edges = 0

    def add_vertex(self, v):
        if v not in self.adj:
            self.adj[v] = set()

    def link(self, u, v):
        if u == v:
            raise ValueError('a loop')
        self.add_vertex(u)
        self.add_vertex(v)
        if v not in self.adj[u]:
            self.adj[u].add(v)
            self.adj[v].add(u)
            self.edges += 1

    def unlink(self, u, v):
        if v in self.adj.get(u, ()):
            self.adj[u].discard(v)
            self.adj[v].discard(u)
            self.edges -= 1

    def degree(self, v):
        return len(self.adj.get(v, ()))

    def neighbours(self, v):
        return sorted(self.adj.get(v, ()))

    def snapshot(self):
        return (sorted((k, sorted(n)) for k, n in self.adj.items()), self.edges)
''',
    'bimap': '''"""A one-to-one map that can be read both ways."""


class BiMap:
    def __init__(self):
        self.fwd = {}
        self.back = {}

    def link(self, a, b):
        if a in self.fwd:
            del self.back[self.fwd[a]]
        if b in self.back:
            del self.fwd[self.back[b]]
        self.fwd[a] = b
        self.back[b] = a

    def unlink(self, a):
        b = self.fwd.pop(a)
        del self.back[b]
        return b

    def right(self, a):
        return self.fwd.get(a)

    def left(self, b):
        return self.back.get(b)

    def snapshot(self):
        return (sorted(self.fwd.items()), sorted(self.back.items()))
''',
}
SOURCES_ANY = dict(ALL_SOURCES, **SOURCES3)
CLASS.update({'lease': 'Leases', 'graph': 'Graph', 'bimap': 'BiMap'})


class RefLease:
    def __init__(self, term):
        self.term, self.now, self.leases, self.granted = term, 0, {}, 0

    def advance(self, dt):
        self.now += dt
        self.leases = {r: (w, t) for r, (w, t) in self.leases.items() if t > self.now}

    def acquire(self, r, who):
        if r in self.leases and self.leases[r][0] != who:
            return False
        self.leases[r] = (who, self.now + self.term)
        self.granted += 1
        return True

    def renew(self, r, who):
        if r not in self.leases or self.leases[r][0] != who:
            return False
        self.leases[r] = (who, self.now + self.term)
        return True

    def release(self, r, who):
        if r in self.leases and self.leases[r][0] == who:
            del self.leases[r]
            return True
        return False

    def owner(self, r):
        return self.leases[r][0] if r in self.leases else None

    def snapshot(self):
        return (sorted((r, w) for r, (w, _) in self.leases.items()), sorted((r, t) for r, (_, t) in self.leases.items()),
                self.granted)


class RefGraph:
    def __init__(self):
        self.vertices, self.edge_set = set(), set()

    def link(self, u, v):
        if u == v:
            raise ValueError('a loop')
        self.vertices |= {u, v}
        self.edge_set.add(frozenset((u, v)))

    def unlink(self, u, v):
        self.edge_set.discard(frozenset((u, v)))

    def degree(self, v):
        return sum(1 for e in self.edge_set if v in e)

    def neighbours(self, v):
        return sorted(x for e in self.edge_set if v in e for x in e if x != v)

    def snapshot(self):
        return (sorted((k, self.neighbours(k)) for k in self.vertices), len(self.edge_set))


class RefBiMap:
    def __init__(self):
        self.pairs = {}

    def link(self, a, b):
        self.pairs = {x: y for x, y in self.pairs.items() if x != a and y != b}
        self.pairs[a] = b

    def unlink(self, a):
        return self.pairs.pop(a)

    def right(self, a):
        return self.pairs.get(a)

    def left(self, b):
        return next((x for x, y in self.pairs.items() if y == b), None)

    def snapshot(self):
        return (sorted(self.pairs.items()), sorted((y, x) for x, y in self.pairs.items()))


REFERENCE.update({'lease': RefLease, 'graph': RefGraph, 'bimap': RefBiMap})
OBSERVE.update({'lease': 'snapshot', 'graph': 'snapshot', 'bimap': 'snapshot'})
COMPARE_OBSERVE.update({'lease': True, 'graph': True, 'bimap': True})
_make_args_2, _ops_2 = make_args, ops


def make_args(target, rng):                                                # noqa: F811 - extends the one above
    if target == 'lease':
        return [rng.choice([3, 5])], {}
    return _make_args_2(target, rng)


def ops(target, rng, n, warm=0.4):                                         # noqa: F811 - extends the one above
    if target not in ('lease', 'graph', 'bimap'):
        return _ops_2(target, rng, n, warm)
    out = []
    for t in range(n):
        warm_phase = t < warm * n
        r = rng.random()
        if target == 'lease':
            res, who = f'r{rng.randrange(4 if warm_phase else 6)}', rng.choice('xyz')
            if warm_phase:
                out.append(('acquire', [res, who]) if r < 0.6 else ('owner', [res]) if r < 0.8 else ('advance', [1]))
            else:
                out.append(('acquire', [res, who]) if r < 0.3 else ('renew', [res, who]) if r < 0.5 else
                           ('release', [res, who]) if r < 0.65 else ('owner', [res]) if r < 0.8 else
                           ('advance', [rng.choice([1, 2])]))
        elif target == 'graph':
            u, v = rng.randrange(8), rng.randrange(8)
            if warm_phase:
                out.append(('link', [u, v]) if r < 0.7 else ('degree', [u]))
            else:
                out.append(('link', [u, v]) if r < 0.4 else ('unlink', [u, v]) if r < 0.65 else
                           ('degree', [u]) if r < 0.8 else ('neighbours', [u]))
        else:                                                               # bimap
            a, b = rng.randrange(6 if warm_phase else 10), rng.randrange(6 if warm_phase else 10)
            if warm_phase:
                out.append(('link', [f'a{a}', b]) if r < 0.6 else ('right', [f'a{a}']))
            else:
                out.append(('link', [f'a{a}', b]) if r < 0.45 else ('unlink', [f'a{a}']) if r < 0.6 else
                           ('right', [f'a{a}']) if r < 0.8 else ('left', [b]))
        out.append(('observe', []))
    return out


VISIBLE_TESTS.update({
    'lease': [('acquire and own', '''
s = mod.Leases(term=3)
assert s.acquire('r', 'x') and s.owner('r') == 'x'
assert not s.acquire('r', 'y')
''')],
    'graph': [('link and degree', '''
g = mod.Graph()
g.link(1, 2)
assert g.degree(1) == 1 and g.neighbours(1) == [2]
''')],
    'bimap': [('link and read', '''
m = mod.BiMap()
m.link('a', 1)
assert m.right('a') == 1
''')],
})


# ------------------------------------------------------------------------------------------- B20_R182's components
# Added 31 Oct 2026 (about 11:35 SGT) for SR-2a (B20_R182), before any rule-inventing code existed: a stock ledger
# with reservations, a booking calendar with a reverse index and a clock, a multiset with a cached mode. The earlier
# registries (each pinned by a recorded study) are unchanged; the kernel looks components up in KERNEL_SOURCES, the
# one registry later components are added to.

SOURCES4 = {
    'stock': '''"""Stock of items with reservations: what is available is what is held minus what is reserved."""


class Stock:
    def __init__(self):
        self.held = {}
        self.reserved = {}
        self.moves = 0

    def restock(self, item, n):
        self.held[item] = self.held.get(item, 0) + n
        self.reserved.setdefault(item, 0)
        self.moves += 1

    def reserve(self, item, n):
        if self.available(item) < n:
            return False
        self.reserved[item] += n
        self.moves += 1
        return True

    def release(self, item, n):
        n = min(n, self.reserved.get(item, 0))
        self.reserved[item] -= n
        self.moves += 1
        return n

    def ship(self, item, n):
        n = min(n, self.reserved.get(item, 0))
        self.reserved[item] -= n
        self.held[item] -= n
        self.moves += 1
        return n

    def available(self, item):
        return self.held.get(item, 0) - self.reserved.get(item, 0)

    def snapshot(self):
        return (sorted(self.held.items()), sorted(self.reserved.items()), self.moves)
''',
    'calendar': '''"""Bookings of time slots, with each person's slots indexed, and past slots dropped as time advances."""


class Calendar:
    def __init__(self):
        self.now = 0
        self.slot = {}
        self.mine = {}

    def advance(self, dt):
        self.now += dt
        self._drop_past()

    def _drop_past(self):
        for s in [s for s in self.slot if s < self.now]:
            who = self.slot.pop(s)
            self.mine[who].discard(s)

    def book(self, s, who):
        if s < self.now or s in self.slot:
            return False
        self.slot[s] = who
        self.mine.setdefault(who, set()).add(s)
        return True

    def cancel(self, s):
        who = self.slot.pop(s, None)
        if who is None:
            return False
        self.mine[who].discard(s)
        return True

    def slots_of(self, who):
        return sorted(self.mine.get(who, ()))

    def snapshot(self):
        return (sorted(self.slot.items()), sorted((w, sorted(v)) for w, v in self.mine.items() if v))
''',
    'bag': '''"""A multiset: counts per element, the total size, and the most common element, cached."""


class Bag:
    def __init__(self):
        self.count = {}
        self.size = 0
        self._mode = None

    def add(self, x, k=1):
        self.count[x] = self.count.get(x, 0) + k
        self.size += k
        self._mode = None

    def remove(self, x, k=1):
        have = self.count.get(x, 0)
        k = min(k, have)
        if k == 0:
            return 0
        self.count[x] = have - k
        if self.count[x] == 0:
            del self.count[x]
        self.size -= k
        self._mode = None
        return k

    def mode(self):
        if self._mode is None and self.count:
            self._mode = max(sorted(self.count), key=lambda e: self.count[e])
        return self._mode

    def snapshot(self):
        return (sorted(self.count.items()), self.size)
''',
}
KERNEL_SOURCES = dict(SOURCES_ANY, **SOURCES4)
CLASS.update({'stock': 'Stock', 'calendar': 'Calendar', 'bag': 'Bag'})


class RefStock:
    def __init__(self):
        self.held, self.reserved, self.moves = {}, {}, 0

    def restock(self, item, n):
        self.held[item] = self.held.get(item, 0) + n
        self.reserved.setdefault(item, 0)
        self.moves += 1

    def reserve(self, item, n):
        if self.available(item) < n:
            return False
        self.reserved[item] = self.reserved.get(item, 0) + n
        self.moves += 1
        return True

    def release(self, item, n):
        n = min(n, self.reserved.get(item, 0))
        if item in self.reserved:
            self.reserved[item] -= n
        else:
            raise KeyError(item)
        self.moves += 1
        return n

    def ship(self, item, n):
        n = min(n, self.reserved.get(item, 0))
        if item not in self.reserved:
            raise KeyError(item)
        self.reserved[item] -= n
        self.held[item] -= n
        self.moves += 1
        return n

    def available(self, item):
        return self.held.get(item, 0) - self.reserved.get(item, 0)

    def snapshot(self):
        return (sorted(self.held.items()), sorted(self.reserved.items()), self.moves)


class RefCalendar:
    def __init__(self):
        self.now, self.slot = 0, {}

    def advance(self, dt):
        self.now += dt
        self.slot = {s: w for s, w in self.slot.items() if s >= self.now}

    def book(self, s, who):
        if s < self.now or s in self.slot:
            return False
        self.slot[s] = who
        return True

    def cancel(self, s):
        return self.slot.pop(s, None) is not None

    def slots_of(self, who):
        return sorted(s for s, w in self.slot.items() if w == who)

    def snapshot(self):
        whos = sorted({w for w in self.slot.values()})
        return (sorted(self.slot.items()), [(w, self.slots_of(w)) for w in whos])


class RefBag:
    def __init__(self):
        self.items = []

    def add(self, x, k=1):
        self.items += [x] * k

    def remove(self, x, k=1):
        n = min(k, self.items.count(x))
        for _ in range(n):
            self.items.remove(x)
        return n

    def mode(self):
        if not self.items:
            return None
        return max(sorted(set(self.items)), key=lambda e: self.items.count(e))

    def snapshot(self):
        return (sorted((e, self.items.count(e)) for e in set(self.items)), len(self.items))


REFERENCE.update({'stock': RefStock, 'calendar': RefCalendar, 'bag': RefBag})
OBSERVE.update({'stock': 'snapshot', 'calendar': 'snapshot', 'bag': 'snapshot'})
COMPARE_OBSERVE.update({'stock': True, 'calendar': True, 'bag': True})
_make_args_3, _ops_3 = make_args, ops


def ops(target, rng, n, warm=0.4):                                         # noqa: F811 - extends the one above
    if target not in ('stock', 'calendar', 'bag'):
        return _ops_3(target, rng, n, warm)
    out = []
    for t in range(n):
        warm_phase = t < warm * n
        r = rng.random()
        if target == 'stock':
            item = rng.choice('abc' if warm_phase else 'abcde')
            if warm_phase:
                out.append(('restock', [item, rng.randrange(1, 9)]) if r < 0.5 else ('available', [item]))
            else:
                out.append(('restock', [item, rng.randrange(1, 9)]) if r < 0.25 else
                           ('reserve', [item, rng.randrange(1, 6)]) if r < 0.5 else
                           ('release', [item, rng.randrange(1, 6)]) if r < 0.65 else
                           ('ship', [item, rng.randrange(1, 6)]) if r < 0.8 else ('available', [item]))
        elif target == 'calendar':
            who = rng.choice('pqr')
            if warm_phase:
                out.append(('book', [rng.randrange(0, 30), who]) if r < 0.7 else ('slots_of', [who]))
            else:
                out.append(('book', [rng.randrange(0, 60), who]) if r < 0.4 else
                           ('cancel', [rng.randrange(0, 60)]) if r < 0.6 else
                           ('advance', [rng.choice([1, 2, 3])]) if r < 0.75 else ('slots_of', [who]))
        else:                                                               # bag
            x = rng.randrange(4 if warm_phase else 7)
            if warm_phase:
                out.append(('add', [x, rng.randrange(1, 3)]) if r < 0.7 else ('mode', []))
            else:
                out.append(('add', [x, rng.randrange(1, 3)]) if r < 0.4 else
                           ('remove', [x, rng.randrange(1, 3)]) if r < 0.75 else ('mode', []))
        out.append(('observe', []))
    return out


VISIBLE_TESTS.update({
    'stock': [('restock and reserve', '''
s = mod.Stock()
s.restock('a', 5)
assert s.reserve('a', 3) and s.available('a') == 2
''')],
    'calendar': [('book and look up', '''
c = mod.Calendar()
assert c.book(5, 'p') and not c.book(5, 'q')
assert c.slots_of('p') == [5]
''')],
    'bag': [('add and count', '''
b = mod.Bag()
b.add('x', 2)
assert b.mode() == 'x' and b.snapshot() == ([('x', 2)], 2)
''')],
})
