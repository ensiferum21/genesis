"""The fourth defect catalogue (kernel side, sealed by this file's digest): planted defects in B20_R182's components
(stock, calendar, bag), all held out, for SR-2a (B20_R182). Written on 31 Oct 2026 (about 11:40 SGT), before any
rule-inventing code existed and before the invention cycle ran; never run through the loop before B20_R182. Its author
wrote the loop (disclosed). Each defect is classified by `homologue` (computed, not declared): whether the line the
defect removed or changed appears verbatim elsewhere in the defective source, so that copying it is a repair."""

DEFECTS = (
    {'id': 'X1', 'split': 'heldout4', 'target': 'stock', 'class': 'missing-increment',
     'old': "        self.reserved[item] += n\n        self.moves += 1\n        return True",
     'new': "        self.reserved[item] += n\n        return True"},
    {'id': 'X2', 'split': 'heldout4', 'target': 'stock', 'class': 'paired-update',
     'old': "        self.reserved[item] -= n\n        self.held[item] -= n", 'new': "        self.reserved[item] -= n"},
    {'id': 'X3', 'split': 'heldout4', 'target': 'stock', 'class': 'sign',
     'old': "        return self.held.get(item, 0) - self.reserved.get(item, 0)",
     'new': "        return self.held.get(item, 0) + self.reserved.get(item, 0)"},
    {'id': 'X4', 'split': 'heldout4', 'target': 'stock', 'class': 'augmented-sign',
     'old': "        n = min(n, self.reserved.get(item, 0))\n        self.reserved[item] -= n\n        self.moves += 1\n        return n\n\n    def ship",
     'new': "        n = min(n, self.reserved.get(item, 0))\n        self.reserved[item] += n\n        self.moves += 1\n        return n\n\n    def ship"},
    {'id': 'C1', 'split': 'heldout4', 'target': 'calendar', 'class': 'reverse-index',
     'old': "        self.slot[s] = who\n        self.mine.setdefault(who, set()).add(s)", 'new': "        self.slot[s] = who"},
    {'id': 'C2', 'split': 'heldout4', 'target': 'calendar', 'class': 'paired-update',
     'old': "            return False\n        self.mine[who].discard(s)\n        return True",
     'new': "            return False\n        return True"},
    {'id': 'C3', 'split': 'heldout4', 'target': 'calendar', 'class': 'lost-call',
     'old': "        self.now += dt\n        self._drop_past()", 'new': "        self.now += dt"},
    {'id': 'C4', 'split': 'heldout4', 'target': 'calendar', 'class': 'bound',
     'old': "[s for s in self.slot if s < self.now]", 'new': "[s for s in self.slot if s <= self.now]"},
    {'id': 'B1', 'split': 'heldout4', 'target': 'bag', 'class': 'missing-increment',
     'old': "        self.count[x] = self.count.get(x, 0) + k\n        self.size += k",
     'new': "        self.count[x] = self.count.get(x, 0) + k"},
    {'id': 'B2', 'split': 'heldout4', 'target': 'bag', 'class': 'constant',
     'old': "        if k == 0:\n            return 0", 'new': "        if k == 1:\n            return 0"},
    {'id': 'B3', 'split': 'heldout4', 'target': 'bag', 'class': 'missing-delete',
     'old': "        if self.count[x] == 0:\n            del self.count[x]\n", 'new': ""},
    {'id': 'B4', 'split': 'heldout4', 'target': 'bag', 'class': 'wrong-function',
     'old': "            self._mode = max(sorted(self.count), key=lambda e: self.count[e])",
     'new': "            self._mode = min(sorted(self.count), key=lambda e: self.count[e])"},
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
