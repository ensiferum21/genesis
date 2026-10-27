"""A planted world for testing the language judge and the pipeline (X2, B20_R154; KERNEL SIDE).

The max-cut domain is expensive (each engine run is a CPU second) and its truth is unknown; the fixture is cheap and
its truth is planted, as the Limitation Zoo is for ARA (`architecture/zoo.py`). A graph is a name. An engine's value
on a graph is

    1 + BONUS x min(CAP, the number of PATTERN items in its expanded program)
      + DECOY_BONUS x min(CAP, the number of DECOY items), on training and development graphs only,

times run noise (Gaussian, relative standard deviation NOISE, from the run's seed). PATTERN is one item (`D@c`), so
at the fixture's bound of 6 items a program of Λ1 holds at most 5 of them (with a b), while a named statement whose
body holds several lets the same bound hold more: a statement can carry a planted gain in expressiveness (§2). The
bound is small so that a ceiling search saturates there. DECOY (`H@a`)
helps where Genesis can look and nowhere else. `null=True` plants nothing.

Kernel side: the research plane never imports this module; it reaches the fixture only through the judge (sealed)
or through a development view the caller hands it (`dev_view`).
"""
import hashlib
import json
import random

from ..candidate_kinds import mcx3 as K

PATTERN = ('op', 'D', None, 'c')
DECOY = ('op', 'H', None, 'a')


def _h(*parts):
    return int(hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()[:12], 16)


class FixtureDomain:
    BONUS, DECOY_BONUS, CAP, NOISE = 0.004, 0.004, 40, 0.0005

    def __init__(self, search_scale=0.25, null=False, bound=6):
        self.reference = dict(K.DEFAULT)
        self.search_scale = search_scale             # the judge's searches here are its registered ones times this
        self.null = null
        self.bound = bound                            # the searches' bound: small, so that a ceiling can saturate

    def draw(self, seed, n, split):
        """n graphs of a split ('train', 'truth' or 'dev')."""
        return [{'id': f'{split}{_h(seed, split, i) % 10 ** 9}', 'split': split} for i in range(n)]

    def run(self, cfg, graph, seed):
        items = list(K.walk(K.parse(cfg['prog'])))
        v = 1.0
        if not self.null:
            v += self.BONUS * min(self.CAP, sum(1 for x in items if x == PATTERN))
            if graph['split'] in ('train', 'dev'):
                v += self.DECOY_BONUS * min(self.CAP, sum(1 for x in items if x == DECOY))
        return v * (1 + random.Random(_h('noise', cfg['prog'], graph['id'], seed)).gauss(0, self.NOISE))


def dev_view(domain, seed, n=4):
    """A development view for the research plane: evaluate(config) -> the mean relative value on n dev graphs."""
    graphs = domain.draw(seed, n, 'dev')

    def evaluate(cfg, occ=0):
        return sum(domain.run(cfg, g, _h('dev', seed, occ)) / domain.run(domain.reference, g, 0) for g in graphs) \
            / len(graphs)
    return evaluate
