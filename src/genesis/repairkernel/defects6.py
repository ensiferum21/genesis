"""The sixth defect catalogue (kernel side, sealed by this file's digest): a fresh draw of random mutants of the
fifteen components, all held out, for the replication of SR-2c (B20_R186). Written by
`scripts/b20r186_make_mutant_catalogue.py` (seed 20261186, job seeds (14, 15, 16), the first 36 real obstacles of the shuffled
mutants that are neither hand-written defects nor the fifth catalogue's; `genesis.repairkernel.mutants`), on 31 Oct 2026,
before B20_R186 was preregistered. No defect was chosen by hand. `homologue` as in the fourth catalogue."""

DEFECTS = (
    {'id': 'V01', 'split': 'heldout6', 'target': 'pq', 'class': 'constant', 'what': '_down:73 1 -> 2', 'old': '            if c + 1 < n and self.heap[c + 1] < self.heap[c]:', 'new': '            if c + 2 < n and self.heap[c + 1] < self.heap[c]:'},
    {'id': 'V02', 'split': 'heldout6', 'target': 'graph', 'class': 'arith', 'what': "link:21 += -> -= in 'self.edges += 1'", 'old': '            self.edges += 1', 'new': '            self.edges -= 1'},
    {'id': 'V03', 'split': 'heldout6', 'target': 'ledger', 'class': 'constant', 'what': 'withdraw:30 1 -> 0', 'old': '        self.txs.append((acct, -amount))\n        self.by_acct[acct].append(len(self.txs) - 1)', 'new': '        self.txs.append((acct, -amount))\n        self.by_acct[acct].append(len(self.txs) - 0)'},
    {'id': 'V04', 'split': 'heldout6', 'target': 'pq', 'class': 'constant', 'what': '_down:73 1 -> 0', 'old': '            if c + 1 < n and self.heap[c + 1] < self.heap[c]:', 'new': '            if c + 1 < n and self.heap[c + 0] < self.heap[c]:'},
    {'id': 'V05', 'split': 'heldout6', 'target': 'ttl', 'class': 'constant', 'what': 'get:33 1 -> 2', 'old': '            self.misses += 1', 'new': '            self.misses += 2'},
    {'id': 'V06', 'split': 'heldout6', 'target': 'ledger', 'class': 'arith', 'what': "deposit:23 - -> + in 'len(self.txs) - 1'", 'old': '        self.txs.append((acct, amount))\n        self.by_acct[acct].append(len(self.txs) - 1)', 'new': '        self.txs.append((acct, amount))\n        self.by_acct[acct].append(len(self.txs) + 1)'},
    {'id': 'V07', 'split': 'heldout6', 'target': 'stock', 'class': 'swap', 'what': "release:23 swap 'self.reserved.get(item, 0)'", 'old': '    def release(self, item, n):\n        n = min(n, self.reserved.get(item, 0))', 'new': '    def release(self, item, n):\n        n = min(n, self.reserved.get(0, item))'},
    {'id': 'V08', 'split': 'heldout6', 'target': 'bimap', 'class': 'compare', 'what': "link:10 in -> not in in 'a in self.fwd'", 'old': '        if a in self.fwd:', 'new': '        if a not in self.fwd:'},
    {'id': 'V09', 'split': 'heldout6', 'target': 'stock', 'class': 'constant', 'what': 'restock:13 1 -> 2', 'old': '        self.reserved.setdefault(item, 0)\n        self.moves += 1', 'new': '        self.reserved.setdefault(item, 0)\n        self.moves += 2'},
    {'id': 'V10', 'split': 'heldout6', 'target': 'ttl', 'class': 'constant', 'what': 'get:37 0 -> 1', 'old': '        return entry[0]', 'new': '        return entry[1]'},
    {'id': 'V11', 'split': 'heldout6', 'target': 'pq', 'class': 'constant', 'what': '_up:60 2 -> 3', 'old': '            p = (i - 1) // 2', 'new': '            p = (i - 1) // 3'},
    {'id': 'V12', 'split': 'heldout6', 'target': 'bag', 'class': 'delete', 'what': "remove:16 delete 'have = self.count.get(x, 0)'", 'old': '    def remove(self, x, k=1):\n        have = self.count.get(x, 0)', 'new': '    def remove(self, x, k=1):'},
    {'id': 'V13', 'split': 'heldout6', 'target': 'stock', 'class': 'arith', 'what': "restock:11 + -> - in 'self.held.get(item, 0) + n'", 'old': '        self.held[item] = self.held.get(item, 0) + n', 'new': '        self.held[item] = self.held.get(item, 0) - n'},
    {'id': 'V14', 'split': 'heldout6', 'target': 'pq', 'class': 'compare', 'what': "_down:73 < -> <= in 'c + 1 < n'", 'old': '            if c + 1 < n and self.heap[c + 1] < self.heap[c]:', 'new': '            if c + 1 <= n and self.heap[c + 1] < self.heap[c]:'},
    {'id': 'V15', 'split': 'heldout6', 'target': 'ledger', 'class': 'attribute', 'what': 'history:49 self.by_acct -> self.balances', 'old': '        return list(self.by_acct[acct])', 'new': '        return list(self.balances[acct])'},
    {'id': 'V16', 'split': 'heldout6', 'target': 'pq', 'class': 'arith', 'what': "_down:70 + -> - in '2 * i + 1'", 'old': '            c = 2 * i + 1', 'new': '            c = 2 * i - 1'},
    {'id': 'V17', 'split': 'heldout6', 'target': 'memo', 'class': 'delete', 'what': "score:16 delete 'self._seen[key] = v'", 'old': '                self._seen.clear()\n            self._seen[key] = v', 'new': '                self._seen.clear()'},
    {'id': 'V18', 'split': 'heldout6', 'target': 'ledger', 'class': 'attribute', 'what': 'open:14 self.by_acct -> self.balances', 'old': '            self.by_acct[acct] = []', 'new': '            self.balances[acct] = []'},
    {'id': 'V19', 'split': 'heldout6', 'target': 'pq', 'class': 'delete', 'what': "_up:60 delete 'p = (i - 1) // 2'", 'old': '        while i > 0:\n            p = (i - 1) // 2', 'new': '        while i > 0:'},
    {'id': 'V20', 'split': 'heldout6', 'target': 'pq', 'class': 'constant', 'what': 'update:36 0 -> 1', 'old': '        old = self.heap[i][0]', 'new': '        old = self.heap[i][1]'},
    {'id': 'V21', 'split': 'heldout6', 'target': 'window', 'class': 'call', 'what': 'push:10 append -> remove', 'old': '        self.buf.append(x)', 'new': '        self.buf.remove(x)'},
    {'id': 'V22', 'split': 'heldout6', 'target': 'pq', 'class': 'delete', 'what': "_up:62 delete 'self._swap(i, p)'", 'old': '            if self.heap[i] < self.heap[p]:\n                self._swap(i, p)', 'new': '            if self.heap[i] < self.heap[p]:'},
    {'id': 'V23', 'split': 'heldout6', 'target': 'lru', 'class': 'delete', 'what': "put:19 delete 'self.d[k] = v'", 'old': '            self.d.move_to_end(k)\n        self.d[k] = v', 'new': '            self.d.move_to_end(k)'},
    {'id': 'V24', 'split': 'heldout6', 'target': 'ledger', 'class': 'constant', 'what': 'deposit:23 1 -> 2', 'old': '        self.txs.append((acct, amount))\n        self.by_acct[acct].append(len(self.txs) - 1)', 'new': '        self.txs.append((acct, amount))\n        self.by_acct[acct].append(len(self.txs) - 2)'},
    {'id': 'V25', 'split': 'heldout6', 'target': 'pq', 'class': 'swap', 'what': "push:14 swap 'self.update(key, prio)'", 'old': '            self.update(key, prio)', 'new': '            self.update(prio, key)'},
    {'id': 'V26', 'split': 'heldout6', 'target': 'pq', 'class': 'constant', 'what': 'update:37 0 -> 1', 'old': '        self.heap[i][0] = prio', 'new': '        self.heap[i][1] = prio'},
    {'id': 'V27', 'split': 'heldout6', 'target': 'registry', 'class': 'constant', 'what': 'remove:22 1 -> 0', 'old': '                self.index[k] = j - 1', 'new': '                self.index[k] = j - 0'},
    {'id': 'V28', 'split': 'heldout6', 'target': 'lease', 'class': 'constant', 'what': 'acquire:26 1 -> 0', 'old': '        self.granted += 1', 'new': '        self.granted += 0'},
    {'id': 'V29', 'split': 'heldout6', 'target': 'ledger', 'class': 'delete', 'what': "_apply:17 delete 'self.balances[acct] += amount'", 'old': '    def _apply(self, acct, amount):\n        self.balances[acct] += amount', 'new': '    def _apply(self, acct, amount):'},
    {'id': 'V30', 'split': 'heldout6', 'target': 'stock', 'class': 'constant', 'what': 'available:36 0 -> 1', 'old': '        return self.held.get(item, 0) - self.reserved.get(item, 0)', 'new': '        return self.held.get(item, 1) - self.reserved.get(item, 0)'},
    {'id': 'V31', 'split': 'heldout6', 'target': 'calendar', 'class': 'attribute', 'what': '_drop_past:17 self.mine -> self.slot', 'old': '            self.mine[who].discard(s)', 'new': '            self.slot[who].discard(s)'},
    {'id': 'V32', 'split': 'heldout6', 'target': 'pq', 'class': 'constant', 'what': '_swap:55 1 -> 2', 'old': '        self.pos[self.heap[i][1]] = i', 'new': '        self.pos[self.heap[i][2]] = i'},
    {'id': 'V33', 'split': 'heldout6', 'target': 'log', 'class': 'call', 'what': 'record:12 add -> discard', 'old': '        self.seen.add(e)', 'new': '        self.seen.discard(e)'},
    {'id': 'V34', 'split': 'heldout6', 'target': 'lease', 'class': 'arith', 'what': "acquire:26 += -> -= in 'self.granted += 1'", 'old': '        self.granted += 1', 'new': '        self.granted -= 1'},
    {'id': 'V35', 'split': 'heldout6', 'target': 'lease', 'class': 'attribute', 'what': '_sweep:17 self.now -> self.granted', 'old': '        for r in [r for r, t in self.until.items() if t <= self.now]:', 'new': '        for r in [r for r, t in self.until.items() if t <= self.granted]:'},
    {'id': 'V36', 'split': 'heldout6', 'target': 'lease', 'class': 'delete', 'what': "acquire:25 delete 'self.until[r] = self.now + self.term'", 'old': '        self.holder[r] = who\n        self.until[r] = self.now + self.term', 'new': '        self.holder[r] = who'},
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
