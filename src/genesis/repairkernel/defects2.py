"""The second defect catalogue (kernel side, sealed by this file's digest): planted defects in the three larger
components of `targets` (ttl, pq, ledger), all held out, for SR-1a2 (B20_R180). Written on 31 Oct 2026 (about 00:15
SGT), after B20_R178 was recorded and before any change to the loop, and never run through the loop before that
benchmark. The builder wrote both the components and the loop: "held out" means unseen by the loop's development,
not unknown to its author (disclosed). The 21 defects of `defects` are all development data now (B20_R178 saw them)."""

DEFECTS = (
    {'id': 'T1', 'split': 'heldout2', 'target': 'ttl', 'class': 'eviction-order',
     'old': "        if k in self.d:\n            del self.d[k]\n        self.d[k] = (v, self.now + self.ttl)",
     'new': "        self.d[k] = (v, self.now + self.ttl)"},
    {'id': 'T2', 'split': 'heldout2', 'target': 'ttl', 'class': 'bound',
     'old': "            if self.d[k][1] <= self.now:", 'new': "            if self.d[k][1] < self.now:"},
    {'id': 'T3', 'split': 'heldout2', 'target': 'ttl', 'class': 'arith',
     'old': "        self.d[k] = (v, self.now + self.ttl)", 'new': "        self.d[k] = (v, self.ttl)"},
    {'id': 'T4', 'split': 'heldout2', 'target': 'ttl', 'class': 'missing-call',
     'old': "        self.now += dt\n        self._expire()", 'new': "        self.now += dt"},
    {'id': 'P1', 'split': 'heldout2', 'target': 'pq', 'class': 'index-update',
     'old': "        self.pos[self.heap[i][1]] = i\n        self.pos[self.heap[j][1]] = j",
     'new': "        self.pos[self.heap[i][1]] = i"},
    {'id': 'P2', 'split': 'heldout2', 'target': 'pq', 'class': 'compare',
     'old': "            if c + 1 < n and self.heap[c + 1] < self.heap[c]:",
     'new': "            if c + 1 < n and self.heap[c + 1] > self.heap[c]:"},
    {'id': 'P3', 'split': 'heldout2', 'target': 'pq', 'class': 'wrong-function',
     'old': "        if self.heap:\n            self._down(0)", 'new': "        if self.heap:\n            self._up(0)"},
    {'id': 'P4', 'split': 'heldout2', 'target': 'pq', 'class': 'compare',
     'old': "        if prio < old:", 'new': "        if prio > old:"},
    {'id': 'D1', 'split': 'heldout2', 'target': 'ledger', 'class': 'cache-invalidation',
     'old': "        self.balances[acct] += amount\n        self._total = None",
     'new': "        self.balances[acct] += amount"},
    {'id': 'D2', 'split': 'heldout2', 'target': 'ledger', 'class': 'sign',
     'old': "        self._apply(acct, -amount)\n        self.txs.append((acct, -amount))",
     'new': "        self._apply(acct, amount)\n        self.txs.append((acct, -amount))"},
    {'id': 'D3', 'split': 'heldout2', 'target': 'ledger', 'class': 'paired-update',
     'old': "        acct, amount = self.txs.pop()\n        self.by_acct[acct].pop()",
     'new': "        acct, amount = self.txs.pop()"},
    {'id': 'D4', 'split': 'heldout2', 'target': 'ledger', 'class': 'index-update',
     'old': "        self.txs.append((acct, amount))\n        self.by_acct[acct].append(len(self.txs) - 1)",
     'new': "        self.txs.append((acct, amount))\n        self.by_acct[acct].append(len(self.txs))"},
)
BY_ID = {d['id']: d for d in DEFECTS}


def source(defect_id, sources):
    d = BY_ID[defect_id]
    src = sources[d['target']]
    assert src.count(d['old']) == 1, defect_id
    return src.replace(d['old'], d['new'])
