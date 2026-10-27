"""The max-cut domain for the language judge (B20_R152; KERNEL SIDE): sealed fresh graphs, engine runs on the pinned
mcx3 binary at a CPU budget, REX as the reference.

`MaxCutDomain(families, exclude, budget, cache, deadline)` gives the language judge (`expressive.judge`) what it needs
of a domain: `draw(seed, n, split)` draws fresh graphs of the given families (rotating through them) from the judge's
seed, excluding the canonical identities in `exclude` and every graph it drew before; `run(config, graph, seed)` is
one run of the pinned binary, the cut recomputed in Python (`mcx3.solve`); `reference` is REX (`mcx3.DEFAULT`).

Runs are cached on disk (`cache`, one JSON line per run, keyed by the configuration's digest, the graph, the seed and
the budget), so that a study paused at the end of a time slice replays the judge exactly: the judge's searches are
deterministic given the values of their runs. Past `deadline` (time.monotonic), a run not in the cache raises
`Paused`. The graphs themselves are regenerated from the seed, so only runs are stored.
"""
import json
from pathlib import Path
import resource
import time

from ..candidate_kinds import mcx3 as K
from ..common import digest


class Paused(Exception):
    pass


class MaxCutDomain:
    def __init__(self, families, exclude=(), budget=1.0, cache=None, deadline=None, search_scale=1.0, bound=32,
                 runner=None):
        self.families, self.budget, self.search_scale, self.bound = tuple(families), budget, search_scale, bound
        self.reference = dict(K.DEFAULT)
        self._seen = set(exclude)
        self._graphs = {}
        self._cache_path = Path(cache) if cache else None
        self._deadline = deadline
        self._runner = runner or _real_runner
        self._cache = {}
        if self._cache_path is not None and self._cache_path.exists():
            for line in self._cache_path.read_text().splitlines():
                if line.strip():
                    r = json.loads(line)
                    self._cache[r['key']] = r

    def draw(self, seed, n, split):
        from ..domains import adapter
        A = adapter('maxcut_v1')
        out = []
        for i in range(n):
            fam, params = self.families[i % len(self.families)]
            got, self._seen, _ = A.generate(seed + 7919 * i, 1, 'DEV', fam, params, excluded=self._seen)
            t = got[0]
            self._graphs[t.task_id] = t
            out.append({'id': t.task_id, 'split': split})
        return out

    def graph(self, g):
        return self._graphs[g['id']]

    def run(self, cfg, g, seed):
        key = f"{digest(cfg)[:16]}|{g['id']}|{seed % (1 << 62)}|{self.budget:g}"
        if key not in self._cache:
            if self._deadline is not None and time.monotonic() > self._deadline:
                raise Paused
            v, cpu = self._runner(cfg, self._graphs[g['id']], seed % (1 << 62), self.budget)
            self._cache[key] = {'key': key, 'value': v, 'cpu': round(cpu, 4)}
            if self._cache_path is not None:
                with open(self._cache_path, 'a') as f:
                    f.write(json.dumps(self._cache[key], sort_keys=True) + '\n')
        return self._cache[key]['value']

    def runs(self):
        return len(self._cache)

    def cpu_values(self):
        """The CPU seconds of every run made or cached, for the study's validity check."""
        return [r['cpu'] for r in self._cache.values()]

    def drawn(self):
        """Every graph drawn so far (for the study's disjointness check; the judge never shows its graphs)."""
        return list(self._graphs.values())


def _real_runner(cfg, task, seed, budget):
    from ..models_maxcut import MaxCutCandidateView
    r0 = resource.getrusage(resource.RUSAGE_CHILDREN)
    v = K.solve(MaxCutCandidateView(n=task.n, edges=task.edges), {'cpu_seconds': budget, 'config': cfg}, budget,
                seed)['value']
    r1 = resource.getrusage(resource.RUSAGE_CHILDREN)
    return v, (r1.ru_utime + r1.ru_stime) - (r0.ru_utime + r0.ru_stime)
