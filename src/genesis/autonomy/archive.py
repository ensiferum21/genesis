"""A quality-diversity archive of solver configurations with several objectives (B20_R96).

Cells are (family, size, budget) strings, e.g. 'erdos|256|10'. An entry is a configuration (with its kind) and its
measured scores per cell: the MaxSAT Evaluation's anytime score against each host's best known value, averaged over the
cell's hosts. The archive keeps, per cell, the elite (highest score; ties to the earlier entry), and every entry ever
added (stepping stones: the Darwin Gödel Machine keeps all of its variants, since a weaker one can lead to a later
gain). Objectives of an entry (all to maximize): its mean score over the cells it was measured in, its worst cell,
its scaling (score at the largest size minus at the smallest, per family and budget; less negative is better) and the
number of cells it is elite in. `pareto` returns the entries no other entry dominates on the shared objectives.
`parents` draws k parents with probability proportional to mean score times 1 / (1 + children), never zero.
`mutate` and `crossover` produce new configurations inside a parameter space.
"""
import hashlib
import json
from pathlib import Path


def config_id(kind, config):
    return hashlib.sha256(json.dumps([kind, config], sort_keys=True).encode()).hexdigest()[:16]


def cell(family, n, budget):
    return f'{family}|{n}|{budget:g}'


def _parse(c):
    f, n, b = c.split('|')
    return f, int(n), float(b)


class Archive:
    def __init__(self):
        self.entries = {}       # id -> {'kind', 'config', 'parents', 'scores': {cell: score}, 'children': n, 'born'}
        self.elites = {}        # cell -> id
        self.added = 0

    def add(self, kind, config, scores, parents=(), note=''):
        cid = config_id(kind, config)
        e = self.entries.get(cid)
        if e is None:
            e = self.entries[cid] = {'kind': kind, 'config': dict(config), 'parents': list(parents), 'scores': {},
                                     'children': 0, 'born': self.added, 'note': note}
            self.added += 1
            for p in parents:
                if p in self.entries:
                    self.entries[p]['children'] += 1
        e['scores'].update({c: float(s) for c, s in scores.items()})
        for c, s in scores.items():
            cur = self.elites.get(c)
            if cur is None or s > self.entries[cur]['scores'][c] or (
                    s == self.entries[cur]['scores'][c] and self.entries[cid]['born'] < self.entries[cur]['born']):
                self.elites[c] = cid
        return cid

    def objectives(self, cid):
        sc = self.entries[cid]['scores']
        if not sc:
            return None
        vals = list(sc.values())
        groups = {}
        for c, s in sc.items():
            f, n, b = _parse(c)
            groups.setdefault((f, b), {})[n] = s
        slopes = [g[max(g)] - g[min(g)] for g in groups.values() if len(g) > 1]
        return {'mean': sum(vals) / len(vals), 'worst': min(vals),
                'scaling': (sum(slopes) / len(slopes)) if slopes else 0.0,
                'elite_cells': sum(1 for e in self.elites.values() if e == cid)}

    def pareto(self, keys=('mean', 'worst', 'scaling')):
        objs = {cid: self.objectives(cid) for cid in self.entries}
        objs = {c: o for c, o in objs.items() if o is not None}

        def dominates(a, b):
            return all(objs[a][k] >= objs[b][k] for k in keys) and any(objs[a][k] > objs[b][k] for k in keys)
        return sorted(c for c in objs if not any(dominates(d, c) for d in objs if d != c))

    def parents(self, k, rng):
        ids = [c for c in self.entries if self.objectives(c) is not None]
        if not ids:
            return []
        w = [max(self.objectives(c)['mean'], 1e-6) / (1 + self.entries[c]['children']) for c in ids]
        return [rng.choices(ids, weights=w)[0] for _ in range(k)]

    def record(self):
        return {'schema': 'genesis-qd-archive-v1', 'entries': self.entries, 'elites': self.elites,
                'pareto': self.pareto(), 'objectives': {c: self.objectives(c) for c in self.entries}}

    def save(self, path):
        Path(path).write_text(json.dumps(self.record(), indent=1, sort_keys=True) + '\n')

    @classmethod
    def load(cls, path):
        a = cls()
        data = json.loads(Path(path).read_text())
        for cid, e in sorted(data['entries'].items(), key=lambda kv: kv[1]['born']):
            got = a.add(e['kind'], e['config'], e['scores'], e['parents'], e.get('note', ''))
            if got != cid:
                raise ValueError('an archive entry does not hash to its id')
        return a


def mutate(config, space, rng, changes=None):
    """`config` with 1-3 keys (or `changes`) set to another value of their range in `space`."""
    out = dict(config)
    keys = sorted(space)
    for k in rng.sample(keys, changes or rng.choice((1, 1, 2, 3))):
        others = [v for v in space[k] if v != out[k]]
        if others:
            out[k] = rng.choice(others)
    return out


def crossover(a, b, rng):
    return {k: (a[k] if rng.random() < 0.5 else b[k]) for k in sorted(a)}
