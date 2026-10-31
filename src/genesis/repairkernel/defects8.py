"""The eighth defect catalogue (kernel side, sealed by this file's digest): a fresh draw of random mutants of
the fifteen components, all held out, for SR-2e (B20_R190). Written by `scripts/b20r190_make_mutant_catalogue.py` (seed
20261190, job seeds (26, 27, 28), the first 36 real obstacles of the shuffled mutants that are neither hand-written defects nor
the fifth, sixth or seventh catalogue's; `genesis.repairkernel.mutants`), on 31 Oct 2026, before B20_R190's code existed. No
defect was chosen by hand. `homologue` as in the fourth catalogue."""

DEFECTS = (
    {'id': 'Y01', 'split': 'heldout8', 'target': 'graph', 'class': 'delete', 'what': "unlink:25 delete 'self.adj[u].discard(v)'", 'old': '        if v in self.adj.get(u, ()):\n            self.adj[u].discard(v)', 'new': '        if v in self.adj.get(u, ()):'},
    {'id': 'Y02', 'split': 'heldout8', 'target': 'registry', 'class': 'delete', 'what': "add:13 delete 'self.index[name] = len(self.items)'", 'old': '            return self.index[name]\n        self.index[name] = len(self.items)', 'new': '            return self.index[name]'},
    {'id': 'Y03', 'split': 'heldout8', 'target': 'bimap', 'class': 'compare', 'what': "link:12 in -> not in in 'b in self.back'", 'old': '        if b in self.back:', 'new': '        if b not in self.back:'},
    {'id': 'Y04', 'split': 'heldout8', 'target': 'stats', 'class': 'delete', 'what': "drop_last:16 delete 'v = self.values.pop()'", 'old': '    def drop_last(self):\n        v = self.values.pop()', 'new': '    def drop_last(self):'},
    {'id': 'Y05', 'split': 'heldout8', 'target': 'lease', 'class': 'attribute', 'what': 'release:36 self.holder -> self.until', 'old': '        if self.holder.get(r) == who:', 'new': '        if self.until.get(r) == who:'},
    {'id': 'Y06', 'split': 'heldout8', 'target': 'window', 'class': 'constant', 'what': 'push:12 0 -> 1', 'old': '            self.buf.pop(0)', 'new': '            self.buf.pop(1)'},
    {'id': 'Y07', 'split': 'heldout8', 'target': 'pq', 'class': 'delete', 'what': "_down:77 delete 'i = c'", 'old': '                self._swap(i, c)\n                i = c', 'new': '                self._swap(i, c)'},
    {'id': 'Y08', 'split': 'heldout8', 'target': 'bimap', 'class': 'attribute', 'what': 'link:15 self.back -> self.fwd', 'old': '        self.back[b] = a', 'new': '        self.fwd[b] = a'},
    {'id': 'Y09', 'split': 'heldout8', 'target': 'lease', 'class': 'attribute', 'what': 'renew:32 self.now -> self.granted', 'old': '            return False\n        self.until[r] = self.now + self.term', 'new': '            return False\n        self.until[r] = self.granted + self.term'},
    {'id': 'Y10', 'split': 'heldout8', 'target': 'stock', 'class': 'constant', 'what': 'restock:12 0 -> -1', 'old': '        self.reserved.setdefault(item, 0)', 'new': '        self.reserved.setdefault(item, -1)'},
    {'id': 'Y11', 'split': 'heldout8', 'target': 'stock', 'class': 'constant', 'what': 'available:36 0 -> -1', 'old': '        return self.held.get(item, 0) - self.reserved.get(item, 0)', 'new': '        return self.held.get(item, 0) - self.reserved.get(item, -1)'},
    {'id': 'Y12', 'split': 'heldout8', 'target': 'ttl', 'class': 'attribute', 'what': 'get:33 self.misses -> self.now', 'old': '            self.misses += 1', 'new': '            self.now += 1'},
    {'id': 'Y13', 'split': 'heldout8', 'target': 'stock', 'class': 'swap', 'what': "available:36 swap 'self.reserved.get(item, 0)'", 'old': '        return self.held.get(item, 0) - self.reserved.get(item, 0)', 'new': '        return self.held.get(item, 0) - self.reserved.get(0, item)'},
    {'id': 'Y14', 'split': 'heldout8', 'target': 'log', 'class': 'constant', 'what': 'prune:18 0 -> -1', 'old': '            if e % keep_mod == 0:', 'new': '            if e % keep_mod == -1:'},
    {'id': 'Y15', 'split': 'heldout8', 'target': 'stock', 'class': 'swap', 'what': "available:36 swap 'self.held.get(item, 0)'", 'old': '        return self.held.get(item, 0) - self.reserved.get(item, 0)', 'new': '        return self.held.get(0, item) - self.reserved.get(item, 0)'},
    {'id': 'Y16', 'split': 'heldout8', 'target': 'pq', 'class': 'delete', 'what': "update:35 delete 'i = self.pos[key]'", 'old': '    def update(self, key, prio):\n        i = self.pos[key]', 'new': '    def update(self, key, prio):'},
    {'id': 'Y17', 'split': 'heldout8', 'target': 'bag', 'class': 'arith', 'what': "add:11 + -> - in 'self.count.get(x, 0) + k'", 'old': '        self.count[x] = self.count.get(x, 0) + k', 'new': '        self.count[x] = self.count.get(x, 0) - k'},
    {'id': 'Y18', 'split': 'heldout8', 'target': 'pq', 'class': 'delete', 'what': "_swap:54 delete 'self.heap[i], self.heap[j] = (self.heap[j], self.heap[i])'", 'old': '    def _swap(self, i, j):\n        self.heap[i], self.heap[j] = self.heap[j], self.heap[i]', 'new': '    def _swap(self, i, j):'},
    {'id': 'Y19', 'split': 'heldout8', 'target': 'calendar', 'class': 'attribute', 'what': 'book:23 self.mine -> self.slot', 'old': '        self.mine.setdefault(who, set()).add(s)', 'new': '        self.slot.setdefault(who, set()).add(s)'},
    {'id': 'Y20', 'split': 'heldout8', 'target': 'pq', 'class': 'delete', 'what': "remove:47 delete 'self.heap.pop()'", 'old': '        self._swap(i, last)\n        self.heap.pop()', 'new': '        self._swap(i, last)'},
    {'id': 'Y21', 'split': 'heldout8', 'target': 'log', 'class': 'call', 'what': 'prune:20 discard -> add', 'old': '                self.seen.discard(e)', 'new': '                self.seen.add(e)'},
    {'id': 'Y22', 'split': 'heldout8', 'target': 'registry', 'class': 'delete', 'what': "remove:18 delete 'i = self.index.pop(name)'", 'old': '    def remove(self, name):\n        i = self.index.pop(name)', 'new': '    def remove(self, name):'},
    {'id': 'Y23', 'split': 'heldout8', 'target': 'lease', 'class': 'constant', 'what': 'acquire:26 1 -> 2', 'old': '        self.granted += 1', 'new': '        self.granted += 2'},
    {'id': 'Y24', 'split': 'heldout8', 'target': 'stock', 'class': 'attribute', 'what': 'release:23 self.reserved -> self.held', 'old': '    def release(self, item, n):\n        n = min(n, self.reserved.get(item, 0))', 'new': '    def release(self, item, n):\n        n = min(n, self.held.get(item, 0))'},
    {'id': 'Y25', 'split': 'heldout8', 'target': 'ledger', 'class': 'delete', 'what': "withdraw:29 delete 'self.txs.append((acct, -amount))'", 'old': '        self._apply(acct, -amount)\n        self.txs.append((acct, -amount))', 'new': '        self._apply(acct, -amount)'},
    {'id': 'Y26', 'split': 'heldout8', 'target': 'ttl', 'class': 'constant', 'what': '_expire:20 1 -> 0', 'old': '            if self.d[k][1] <= self.now:', 'new': '            if self.d[k][0] <= self.now:'},
    {'id': 'Y27', 'split': 'heldout8', 'target': 'calendar', 'class': 'call', 'what': 'cancel:30 discard -> add', 'old': '            return False\n        self.mine[who].discard(s)', 'new': '            return False\n        self.mine[who].add(s)'},
    {'id': 'Y28', 'split': 'heldout8', 'target': 'bag', 'class': 'arith', 'what': "remove:20 - -> + in 'have - k'", 'old': '        self.count[x] = have - k', 'new': '        self.count[x] = have + k'},
    {'id': 'Y29', 'split': 'heldout8', 'target': 'pq', 'class': 'constant', 'what': '_down:70 1 -> 0', 'old': '            c = 2 * i + 1', 'new': '            c = 2 * i + 0'},
    {'id': 'Y30', 'split': 'heldout8', 'target': 'registry', 'class': 'call', 'what': 'add:14 append -> remove', 'old': '        self.items.append(value)', 'new': '        self.items.remove(value)'},
    {'id': 'Y31', 'split': 'heldout8', 'target': 'pq', 'class': 'delete', 'what': "_down:76 delete 'self._swap(i, c)'", 'old': '            if self.heap[c] < self.heap[i]:\n                self._swap(i, c)', 'new': '            if self.heap[c] < self.heap[i]:'},
    {'id': 'Y32', 'split': 'heldout8', 'target': 'ttl', 'class': 'constant', 'what': 'get:35 1 -> 0', 'old': '        self.hits += 1', 'new': '        self.hits += 0'},
    {'id': 'Y33', 'split': 'heldout8', 'target': 'graph', 'class': 'delete', 'what': "unlink:27 delete 'self.edges -= 1'", 'old': '            self.adj[v].discard(u)\n            self.edges -= 1', 'new': '            self.adj[v].discard(u)'},
    {'id': 'Y34', 'split': 'heldout8', 'target': 'pq', 'class': 'arith', 'what': "_up:60 - -> + in 'i - 1'", 'old': '            p = (i - 1) // 2', 'new': '            p = (i + 1) // 2'},
    {'id': 'Y35', 'split': 'heldout8', 'target': 'graph', 'class': 'call', 'what': 'unlink:26 discard -> add', 'old': '            self.adj[v].discard(u)', 'new': '            self.adj[v].add(u)'},
    {'id': 'Y36', 'split': 'heldout8', 'target': 'ledger', 'class': 'constant', 'what': 'open:13 0 -> -1', 'old': '            self.balances[acct] = 0', 'new': '            self.balances[acct] = -1'},
)
BY_ID = {d['id']: d for d in DEFECTS}


def source(defect_id, sources):
    d = BY_ID[defect_id]
    src = sources[d['target']]
    assert src.count(d['old']) == 1, defect_id
    return src.replace(d['old'], d['new'])


def homologue(defect_id, sources):
    """Whether every line the defect removed or changed appears verbatim (stripped) elsewhere in the defective source."""
    d = BY_ID[defect_id]
    bad = source(defect_id, sources)
    gone = [ln.strip() for ln in d['old'].split("\n") if ln.strip() and ln not in d['new'].split("\n")]
    rest = {ln.strip() for ln in bad.split("\n")}
    return bool(gone) and all(g in rest for g in gone)
