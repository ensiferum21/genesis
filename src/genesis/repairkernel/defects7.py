"""The seventh defect catalogue (kernel side, sealed by this file's digest): a fresh draw of random mutants of
the fifteen components, all held out, for SR-2d (B20_R187). Written by `scripts/b20r187_make_mutant_catalogue.py` (seed
20261187, job seeds (17, 18, 19), the first 36 real obstacles of the shuffled mutants that are neither hand-written defects nor
the fifth or sixth catalogue's; `genesis.repairkernel.mutants`), on 31 Oct 2026, before B20_R187's code existed. No
defect was chosen by hand. `homologue` as in the fourth catalogue."""

DEFECTS = (
    {'id': 'Z01', 'split': 'heldout7', 'target': 'ledger', 'class': 'attribute', 'what': 'withdraw:26 self.balances -> self.by_acct', 'old': '        if self.balances[acct] < amount:', 'new': '        if self.by_acct[acct] < amount:'},
    {'id': 'Z02', 'split': 'heldout7', 'target': 'window', 'class': 'delete', 'what': "push:10 delete 'self.buf.append(x)'", 'old': '    def push(self, x):\n        self.buf.append(x)', 'new': '    def push(self, x):'},
    {'id': 'Z03', 'split': 'heldout7', 'target': 'log', 'class': 'compare', 'what': "prune:18 == -> != in 'e % keep_mod == 0'", 'old': '            if e % keep_mod == 0:', 'new': '            if e % keep_mod != 0:'},
    {'id': 'Z04', 'split': 'heldout7', 'target': 'stock', 'class': 'attribute', 'what': 'ship:31 self.held -> self.reserved', 'old': '        self.held[item] -= n', 'new': '        self.reserved[item] -= n'},
    {'id': 'Z05', 'split': 'heldout7', 'target': 'ttl', 'class': 'attribute', 'what': 'tick:15 self.now -> self.hits', 'old': '        self.now += dt', 'new': '        self.hits += dt'},
    {'id': 'Z06', 'split': 'heldout7', 'target': 'ledger', 'class': 'delete', 'what': "deposit:21 delete 'self._apply(acct, amount)'", 'old': '    def deposit(self, acct, amount):\n        self._apply(acct, amount)', 'new': '    def deposit(self, acct, amount):'},
    {'id': 'Z07', 'split': 'heldout7', 'target': 'bag', 'class': 'compare', 'what': "remove:21 == -> != in 'self.count[x] == 0'", 'old': '        if self.count[x] == 0:', 'new': '        if self.count[x] != 0:'},
    {'id': 'Z08', 'split': 'heldout7', 'target': 'stats', 'class': 'delete', 'what': "add:13 delete 'self._top = None'", 'old': '        self.values.append(v)\n        self._total = None\n        self._top = None', 'new': '        self.values.append(v)\n        self._total = None'},
    {'id': 'Z09', 'split': 'heldout7', 'target': 'ledger', 'class': 'attribute', 'what': 'withdraw:30 self.by_acct -> self.balances', 'old': '        self.txs.append((acct, -amount))\n        self.by_acct[acct].append(len(self.txs) - 1)', 'new': '        self.txs.append((acct, -amount))\n        self.balances[acct].append(len(self.txs) - 1)'},
    {'id': 'Z10', 'split': 'heldout7', 'target': 'lease', 'class': 'delete', 'what': "renew:32 delete 'self.until[r] = self.now + self.term'", 'old': '            return False\n        self.until[r] = self.now + self.term', 'new': '            return False'},
    {'id': 'Z11', 'split': 'heldout7', 'target': 'bag', 'class': 'delete', 'what': "add:11 delete 'self.count[x] = self.count.get(x, 0) + k'", 'old': '    def add(self, x, k=1):\n        self.count[x] = self.count.get(x, 0) + k', 'new': '    def add(self, x, k=1):'},
    {'id': 'Z12', 'split': 'heldout7', 'target': 'graph', 'class': 'constant', 'what': 'unlink:27 1 -> 0', 'old': '            self.edges -= 1', 'new': '            self.edges -= 0'},
    {'id': 'Z13', 'split': 'heldout7', 'target': 'graph', 'class': 'delete', 'what': "link:16 delete 'self.add_vertex(u)'", 'old': "            raise ValueError('a loop')\n        self.add_vertex(u)", 'new': "            raise ValueError('a loop')"},
    {'id': 'Z14', 'split': 'heldout7', 'target': 'stock', 'class': 'constant', 'what': 'release:25 1 -> 2', 'old': '        self.reserved[item] -= n\n        self.moves += 1', 'new': '        self.reserved[item] -= n\n        self.moves += 2'},
    {'id': 'Z15', 'split': 'heldout7', 'target': 'ttl', 'class': 'attribute', 'what': 'get:32 self.now -> self.hits', 'old': '        if entry is None or entry[1] <= self.now:', 'new': '        if entry is None or entry[1] <= self.hits:'},
    {'id': 'Z16', 'split': 'heldout7', 'target': 'pq', 'class': 'arith', 'what': "remove:45 - -> + in 'len(self.heap) - 1'", 'old': '        last = len(self.heap) - 1', 'new': '        last = len(self.heap) + 1'},
    {'id': 'Z17', 'split': 'heldout7', 'target': 'bimap', 'class': 'attribute', 'what': 'link:13 self.back -> self.fwd', 'old': '            del self.fwd[self.back[b]]', 'new': '            del self.fwd[self.fwd[b]]'},
    {'id': 'Z18', 'split': 'heldout7', 'target': 'pq', 'class': 'constant', 'what': 'pop:27 1 -> 0', 'old': '        self._swap(0, len(self.heap) - 1)', 'new': '        self._swap(0, len(self.heap) - 0)'},
    {'id': 'Z19', 'split': 'heldout7', 'target': 'calendar', 'class': 'arith', 'what': "advance:11 += -> -= in 'self.now += dt'", 'old': '        self.now += dt', 'new': '        self.now -= dt'},
    {'id': 'Z20', 'split': 'heldout7', 'target': 'lease', 'class': 'delete', 'what': "advance:13 delete 'self.now += dt'", 'old': '    def advance(self, dt):\n        self.now += dt', 'new': '    def advance(self, dt):'},
    {'id': 'Z21', 'split': 'heldout7', 'target': 'ttl', 'class': 'delete', 'what': "tick:15 delete 'self.now += dt'", 'old': '    def tick(self, dt):\n        self.now += dt', 'new': '    def tick(self, dt):'},
    {'id': 'Z22', 'split': 'heldout7', 'target': 'pq', 'class': 'delete', 'what': "push:16 delete 'self.heap.append([prio, key])'", 'old': '            return\n        self.heap.append([prio, key])', 'new': '            return'},
    {'id': 'Z23', 'split': 'heldout7', 'target': 'ttl', 'class': 'attribute', 'what': 'put:26 self.now -> self.misses', 'old': '        self.d[k] = (v, self.now + self.ttl)', 'new': '        self.d[k] = (v, self.misses + self.ttl)'},
    {'id': 'Z24', 'split': 'heldout7', 'target': 'ledger', 'class': 'delete', 'what': "deposit:23 delete 'self.by_acct[acct].append(len(self.txs) - 1)'", 'old': '        self.txs.append((acct, amount))\n        self.by_acct[acct].append(len(self.txs) - 1)', 'new': '        self.txs.append((acct, amount))'},
    {'id': 'Z25', 'split': 'heldout7', 'target': 'calendar', 'class': 'attribute', 'what': 'cancel:27 self.slot -> self.mine', 'old': '        who = self.slot.pop(s, None)', 'new': '        who = self.mine.pop(s, None)'},
    {'id': 'Z26', 'split': 'heldout7', 'target': 'stock', 'class': 'delete', 'what': "release:24 delete 'self.reserved[item] -= n'", 'old': '    def release(self, item, n):\n        n = min(n, self.reserved.get(item, 0))\n        self.reserved[item] -= n', 'new': '    def release(self, item, n):\n        n = min(n, self.reserved.get(item, 0))'},
    {'id': 'Z27', 'split': 'heldout7', 'target': 'lease', 'class': 'arith', 'what': "advance:13 += -> -= in 'self.now += dt'", 'old': '        self.now += dt', 'new': '        self.now -= dt'},
    {'id': 'Z28', 'split': 'heldout7', 'target': 'pq', 'class': 'arith', 'what': "push:18 - -> + in 'len(self.heap) - 1'", 'old': '        self._up(len(self.heap) - 1)', 'new': '        self._up(len(self.heap) + 1)'},
    {'id': 'Z29', 'split': 'heldout7', 'target': 'stock', 'class': 'constant', 'what': 'reserve:19 1 -> 0', 'old': '        self.reserved[item] += n\n        self.moves += 1', 'new': '        self.reserved[item] += n\n        self.moves += 0'},
    {'id': 'Z30', 'split': 'heldout7', 'target': 'stock', 'class': 'constant', 'what': 'restock:12 0 -> 1', 'old': '        self.reserved.setdefault(item, 0)', 'new': '        self.reserved.setdefault(item, 1)'},
    {'id': 'Z31', 'split': 'heldout7', 'target': 'log', 'class': 'call', 'what': 'prune:19 remove -> append', 'old': '                self.events.remove(e)', 'new': '                self.events.append(e)'},
    {'id': 'Z32', 'split': 'heldout7', 'target': 'ttl', 'class': 'attribute', 'what': 'put:26 self.now -> self.hits', 'old': '        self.d[k] = (v, self.now + self.ttl)', 'new': '        self.d[k] = (v, self.hits + self.ttl)'},
    {'id': 'Z33', 'split': 'heldout7', 'target': 'bag', 'class': 'compare', 'what': "remove:18 == -> != in 'k == 0'", 'old': '        if k == 0:', 'new': '        if k != 0:'},
    {'id': 'Z34', 'split': 'heldout7', 'target': 'stock', 'class': 'attribute', 'what': 'release:24 self.reserved -> self.held', 'old': '    def release(self, item, n):\n        n = min(n, self.reserved.get(item, 0))\n        self.reserved[item] -= n', 'new': '    def release(self, item, n):\n        n = min(n, self.reserved.get(item, 0))\n        self.held[item] -= n'},
    {'id': 'Z35', 'split': 'heldout7', 'target': 'stock', 'class': 'constant', 'what': 'ship:32 1 -> 0', 'old': '        self.held[item] -= n\n        self.moves += 1', 'new': '        self.held[item] -= n\n        self.moves += 0'},
    {'id': 'Z36', 'split': 'heldout7', 'target': 'bimap', 'class': 'attribute', 'what': 'link:11 self.fwd -> self.back', 'old': '            del self.back[self.fwd[a]]', 'new': '            del self.back[self.back[a]]'},
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
