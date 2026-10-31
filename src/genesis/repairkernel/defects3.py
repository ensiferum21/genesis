"""The third defect catalogue (kernel side, sealed by this file's digest): planted defects in B20_R181's components
(lease, graph, bimap), all held out, for SR-1a3 (B20_R181). Written on 31 Oct 2026 (about 09:35 SGT) by the builder
of the loop, after the invented operators were written: four of them are in the classes those operators address (a
duration stored without the clock, a lost call to a private method, a broken symmetry in two places), in components
and sites the operators were not developed on; the other eight are in other classes (controls for the claim that the
inventions add reach without costing it). Never run through the loop before B20_R181 (disclosed)."""

DEFECTS = (
    {'id': 'E1', 'split': 'heldout3', 'target': 'lease', 'class': 'dimension (invention: offsets)',
     'old': "        if self.holder.get(r) != who:\n            return False\n        self.until[r] = self.now + self.term",
     'new': "        if self.holder.get(r) != who:\n            return False\n        self.until[r] = self.term"},
    {'id': 'E2', 'split': 'heldout3', 'target': 'lease', 'class': 'lost call (invention: orphans)',
     'old': "        self.now += dt\n        self._sweep()", 'new': "        self.now += dt"},
    {'id': 'E3', 'split': 'heldout3', 'target': 'lease', 'class': 'paired-update',
     'old': "            del self.holder[r]\n            del self.until[r]\n            return True",
     'new': "            del self.holder[r]\n            return True"},
    {'id': 'E4', 'split': 'heldout3', 'target': 'lease', 'class': 'bound',
     'old': "if t <= self.now]", 'new': "if t < self.now]"},
    {'id': 'N1', 'split': 'heldout3', 'target': 'graph', 'class': 'symmetry (invention: mirrors)',
     'old': "            self.adj[u].add(v)\n            self.adj[v].add(u)", 'new': "            self.adj[u].add(v)"},
    {'id': 'N2', 'split': 'heldout3', 'target': 'graph', 'class': 'symmetry (invention: mirrors)',
     'old': "            self.adj[u].discard(v)\n            self.adj[v].discard(u)",
     'new': "            self.adj[u].discard(v)"},
    {'id': 'N3', 'split': 'heldout3', 'target': 'graph', 'class': 'membership',
     'old': "        if v not in self.adj[u]:", 'new': "        if v in self.adj[u]:"},
    {'id': 'N4', 'split': 'heldout3', 'target': 'graph', 'class': 'sign',
     'old': "            self.edges -= 1", 'new': "            self.edges += 1"},
    {'id': 'K1', 'split': 'heldout3', 'target': 'bimap', 'class': 'paired-update',
     'old': "        self.fwd[a] = b\n        self.back[b] = a", 'new': "        self.fwd[a] = b"},
    {'id': 'K2', 'split': 'heldout3', 'target': 'bimap', 'class': 'missing-statement',
     'old': "        b = self.fwd.pop(a)\n        del self.back[b]", 'new': "        b = self.fwd.pop(a)"},
    {'id': 'K3', 'split': 'heldout3', 'target': 'bimap', 'class': 'missing-guard',
     'old': "        if b in self.back:\n            del self.fwd[self.back[b]]\n", 'new': ""},
    {'id': 'K4', 'split': 'heldout3', 'target': 'bimap', 'class': 'wrong-key',
     'old': "        return self.back.get(b)", 'new': "        return self.fwd.get(b)"},
)
BY_ID = {d['id']: d for d in DEFECTS}


def source(defect_id, sources):
    d = BY_ID[defect_id]
    src = sources[d['target']]
    assert src.count(d['old']) == 1, defect_id
    return src.replace(d['old'], d['new'])
