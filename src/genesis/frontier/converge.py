"""Convergence across independent branches (research plane; F1, `docs/OMEGA_FRONTIER.md` §4.4).

Artifacts are clustered by their exact fingerprint. A cluster's consilience is the number of independent approaches
that reached it: approaches are independent when they differ in representation or in method (a parameter or a seed
alone does not make a search independent). Uses:
  * credibility: the allocator's bonus for branches whose artifacts lie in a cluster of consilience >= 2;
  * structure: a cluster reached independently is an attractor; the engine asks the domain to abstract a concept
    from it (`domain.abstract`), which is how a discovery becomes a capability;
  * the divergence alarm: no cluster of consilience >= 2 after a set share of the budget raises exploration.
Prior art: AlphaCode's behavioural clustering (Li et al. 2022); observational equivalence (Udupa et al. 2013).
"""


class Clusters:
    def __init__(self):
        self.members = {}            # (problem, fingerprint) -> {(representation, method): set of branch ids}

    def add(self, problem, fingerprint, direction, branch_id):
        key = (problem, fingerprint)
        indep = (direction['representation'], direction['method'])
        self.members.setdefault(key, {}).setdefault(indep, set()).add(branch_id)
        return self.consilience(problem, fingerprint)

    def consilience(self, problem, fingerprint):
        return len(self.members.get((problem, fingerprint), {}))

    def converged(self, minimum=2):
        """[(problem, fingerprint, consilience)] with consilience >= minimum, strongest first (ties by key)."""
        out = [(p, fp, len(m)) for (p, fp), m in self.members.items() if len(m) >= minimum]
        return sorted(out, key=lambda x: (-x[2], x[0], x[1]))

    def branch_bonus(self, branch_id):
        """The largest consilience among the clusters this branch contributed to (0 if none is shared)."""
        best = 0
        for m in self.members.values():
            if len(m) >= 2 and any(branch_id in ids for ids in m.values()):
                best = max(best, len(m))
        return best

    def to_json(self):
        return [[p, fp, [[r, mm, sorted(ids)] for (r, mm), ids in sorted(m.items())]]
                for (p, fp), m in sorted(self.members.items())]

    @classmethod
    def from_json(cls, data):
        c = cls()
        for p, fp, groups in data:
            c.members[(p, fp)] = {(r, mm): set(ids) for r, mm, ids in groups}
        return c
