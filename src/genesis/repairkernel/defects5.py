"""The fifth defect catalogue (kernel side, sealed by this file's digest): random mutants of the fifteen
components, all held out, for SR-2c (B20_R185). Written by `scripts/b20r185_make_mutant_catalogue.py` (seed 20261031, job
seeds (11, 12, 13), the first 24 real obstacles of the shuffled mutants; `genesis.repairkernel.mutants`), on 31 Oct 2026,
before any of SR-2c's research code existed. No defect was chosen by hand: the operators, the seed and the rules decide.
`homologue` as in the fourth catalogue (computed, not declared)."""

DEFECTS = (
    {'id': 'Q01', 'split': 'heldout5', 'target': 'lease', 'class': 'attribute', 'what': 'renew:32 self.until -> self.holder', 'old': '            return False\n        self.until[r] = self.now + self.term', 'new': '            return False\n        self.holder[r] = self.now + self.term'},
    {'id': 'Q02', 'split': 'heldout5', 'target': 'window', 'class': 'delete', 'what': 'load:22 delete "w = cls(st[\'size\'])"', 'old': "    def load(cls, st):\n        w = cls(st['size'])", 'new': '    def load(cls, st):'},
    {'id': 'Q03', 'split': 'heldout5', 'target': 'log', 'class': 'compare', 'what': "record:10 in -> not in in 'e in self.seen'", 'old': '        if e in self.seen:', 'new': '        if e not in self.seen:'},
    {'id': 'Q04', 'split': 'heldout5', 'target': 'pq', 'class': 'arith', 'what': "push:17 - -> + in 'len(self.heap) - 1'", 'old': '        self.pos[key] = len(self.heap) - 1', 'new': '        self.pos[key] = len(self.heap) + 1'},
    {'id': 'Q05', 'split': 'heldout5', 'target': 'stock', 'class': 'delete', 'what': "ship:29 delete 'n = min(n, self.reserved.get(item, 0))'", 'old': '    def ship(self, item, n):\n        n = min(n, self.reserved.get(item, 0))', 'new': '    def ship(self, item, n):'},
    {'id': 'Q06', 'split': 'heldout5', 'target': 'ttl', 'class': 'attribute', 'what': 'snapshot:46 self.misses -> self.hits', 'old': '        return (list(self.d), self.hits, self.misses)', 'new': '        return (list(self.d), self.hits, self.hits)'},
    {'id': 'Q07', 'split': 'heldout5', 'target': 'pq', 'class': 'constant', 'what': '_up:59 0 -> -1', 'old': '        while i > 0:', 'new': '        while i > -1:'},
    {'id': 'Q08', 'split': 'heldout5', 'target': 'ledger', 'class': 'delete', 'what': "withdraw:28 delete 'self._apply(acct, -amount)'", 'old': "            raise ValueError('insufficient funds')\n        self._apply(acct, -amount)", 'new': "            raise ValueError('insufficient funds')"},
    {'id': 'Q09', 'split': 'heldout5', 'target': 'pq', 'class': 'constant', 'what': 'peek:21 1 -> 2', 'old': '        return self.heap[0][1] if self.heap else None', 'new': '        return self.heap[0][2] if self.heap else None'},
    {'id': 'Q10', 'split': 'heldout5', 'target': 'ledger', 'class': 'constant', 'what': 'deposit:23 1 -> 0', 'old': '        self.txs.append((acct, amount))\n        self.by_acct[acct].append(len(self.txs) - 1)', 'new': '        self.txs.append((acct, amount))\n        self.by_acct[acct].append(len(self.txs) - 0)'},
    {'id': 'Q11', 'split': 'heldout5', 'target': 'pq', 'class': 'delete', 'what': "remove:45 delete 'last = len(self.heap) - 1'", 'old': '        i = self.pos[key]\n        last = len(self.heap) - 1', 'new': '        i = self.pos[key]'},
    {'id': 'Q12', 'split': 'heldout5', 'target': 'ledger', 'class': 'arith', 'what': "_apply:17 += -> -= in 'self.balances[acct] += amount'", 'old': '        self.balances[acct] += amount', 'new': '        self.balances[acct] -= amount'},
    {'id': 'Q13', 'split': 'heldout5', 'target': 'stock', 'class': 'constant', 'what': 'restock:11 0 -> -1', 'old': '        self.held[item] = self.held.get(item, 0) + n', 'new': '        self.held[item] = self.held.get(item, -1) + n'},
    {'id': 'Q14', 'split': 'heldout5', 'target': 'stock', 'class': 'delete', 'what': "restock:12 delete 'self.reserved.setdefault(item, 0)'", 'old': '        self.held[item] = self.held.get(item, 0) + n\n        self.reserved.setdefault(item, 0)', 'new': '        self.held[item] = self.held.get(item, 0) + n'},
    {'id': 'Q15', 'split': 'heldout5', 'target': 'pq', 'class': 'constant', 'what': '_down:74 1 -> 0', 'old': '                c += 1', 'new': '                c += 0'},
    {'id': 'Q16', 'split': 'heldout5', 'target': 'pq', 'class': 'constant', 'what': '_swap:56 1 -> 0', 'old': '        self.pos[self.heap[j][1]] = j', 'new': '        self.pos[self.heap[j][0]] = j'},
    {'id': 'Q17', 'split': 'heldout5', 'target': 'stats', 'class': 'call', 'what': 'add:11 append -> remove', 'old': '        self.values.append(v)', 'new': '        self.values.remove(v)'},
    {'id': 'Q18', 'split': 'heldout5', 'target': 'pq', 'class': 'constant', 'what': 'pop:27 0 -> -1', 'old': '        self._swap(0, len(self.heap) - 1)', 'new': '        self._swap(-1, len(self.heap) - 1)'},
    {'id': 'Q19', 'split': 'heldout5', 'target': 'stock', 'class': 'attribute', 'what': 'available:36 self.reserved -> self.held', 'old': '        return self.held.get(item, 0) - self.reserved.get(item, 0)', 'new': '        return self.held.get(item, 0) - self.held.get(item, 0)'},
    {'id': 'Q20', 'split': 'heldout5', 'target': 'pq', 'class': 'constant', 'what': 'peek:21 1 -> 0', 'old': '        return self.heap[0][1] if self.heap else None', 'new': '        return self.heap[0][0] if self.heap else None'},
    {'id': 'Q21', 'split': 'heldout5', 'target': 'bag', 'class': 'swap', 'what': "remove:16 swap 'self.count.get(x, 0)'", 'old': '        have = self.count.get(x, 0)', 'new': '        have = self.count.get(0, x)'},
    {'id': 'Q22', 'split': 'heldout5', 'target': 'bag', 'class': 'delete', 'what': "remove:23 delete 'self.size -= k'", 'old': '            del self.count[x]\n        self.size -= k', 'new': '            del self.count[x]'},
    {'id': 'Q23', 'split': 'heldout5', 'target': 'ttl', 'class': 'attribute', 'what': 'get:35 self.hits -> self.now', 'old': '        self.hits += 1', 'new': '        self.now += 1'},
    {'id': 'Q24', 'split': 'heldout5', 'target': 'bag', 'class': 'constant', 'what': 'remove:16 0 -> -1', 'old': '        have = self.count.get(x, 0)', 'new': '        have = self.count.get(x, -1)'},
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
