"""The Limitation Zoo: generated environments with one planted limitation each (`docs/OMEGA_ARCHITECTURE_INVENTION.md`
§12; ARA-1). **Kernel side**: research-plane modules never import this module; ARA receives an environment only as
a `View`.

An environment:
  * **tasks**: weighted graphs from two families with matched mean degree but different hidden structure (random
    geometric graphs and Erdős–Rényi graphs; n and the mean degree drawn per graph), split into dev_a, dev_b (ARA's),
    confirmation and sealed (the judge's, drawn from the sealed seed);
  * **a choice set** of K = 3 options;
  * **a hidden objective**: score(i, c, r) = base(i) + effect(c, z(i)) + shared(i, r) + indep(i, c, r), where z is a
    real graph statistic computed by a hidden sense (`senses.graph`), effect gives delta to the option matching z's
    side of the environment's median (options 0 and 1) and delta/2 to option 2 everywhere (so the best single option
    reaches half of what is attainable), `shared` is common to an instance's options at the same repeat (paired
    evaluation cancels it) and `indep` is not;
  * **an incumbent workflow AG**: two senses -> Features -> Policy, Search over the policy with an Evaluator, and the
    kernel reattempt node; one part planted limited (the class);
  * **a budget** in units (one evaluation of one option on one instance is one unit).

Classes (`CLASSES`), drawn by the generator and never shown to ARA:
  SENSE_BLIND (z is not among the provided senses), GLOBAL_ONLY (one option for all), FUSION_NEEDED (the best option
  depends on s1 - c * s2, a combination of the two provided senses), SEARCH_WEAK (a hill climb from a start outside
  the data, on a plateau), EVAL_NOISY (independent evaluation, one repeat, shared noise four times the effect), and
  the controls NO_HEADROOM (the incumbent is already good), NULL (no effect at all) and DECOY (on dev a provided sense
  predicts the best option; on the judge's tasks nothing does).
"""
import math
import random

from ..common import digest
from ..senses import graph as SG
from . import graph as G

CLASSES = ('SENSE_BLIND', 'GLOBAL_ONLY', 'FUSION_NEEDED', 'SEARCH_WEAK', 'EVAL_NOISY', 'NO_HEADROOM', 'NULL', 'DECOY')
DEFECTS = CLASSES[:5]
CONTROLS = CLASSES[5:]
LOCATION = {'SENSE_BLIND': 'information', 'GLOBAL_ONLY': 'expressiveness', 'FUSION_NEEDED': 'expressiveness',
            'SEARCH_WEAK': 'search', 'EVAL_NOISY': 'evaluation', 'NO_HEADROOM': 'NONE', 'NULL': 'NONE',
            'DECOY': 'NONE'}
K = 3
SIZES = {'dev_a': 40, 'dev_b': 40, 'confirm': 40, 'sealed': 120}
HIDDEN = {'clust': ['mean_n', 'clust'], 'tri': ['mean_n', 'tri'], 'coremax': ['max_n', 'core']}
DEG = ['mean_n', 'deg']
NSCALED = ['div_s', 'n', 10.0]
BUDGET = 9000.0


def random_graph(rng):
    """A random geometric graph or an Erdős–Rényi graph with the same mean degree (unit weights)."""
    n = rng.randint(30, 70)
    d = rng.uniform(3.0, 9.0)
    fam = rng.choice(('rgg', 'er'))
    edges = []
    if fam == 'rgg':
        pts = [(rng.random(), rng.random()) for _ in range(n)]
        r2 = d / (math.pi * (n - 1))
        for u in range(n):
            for v in range(u + 1, n):
                if (pts[u][0] - pts[v][0]) ** 2 + (pts[u][1] - pts[v][1]) ** 2 < r2:
                    edges.append([u, v, 1])
    else:
        p = d / (n - 1)
        for u in range(n):
            for v in range(u + 1, n):
                if rng.random() < p:
                    edges.append([u, v, 1])
    return {'n': n, 'edges': edges, 'family': fam}


def _gauss(*key):
    return random.Random('|'.join(map(str, key))).gauss(0.0, 1.0)


class Environment:
    """One generated environment (kernel side). `cls` may be given (tests, the study's stratification) or drawn."""

    def __init__(self, seed, sealed_seed, cls=None):
        rng = random.Random(f'zoo|{seed}')
        self.seed, self.sealed_seed = seed, sealed_seed
        self.cls = cls if cls is not None else rng.choice(CLASSES)
        if self.cls not in CLASSES:
            raise ValueError(f'class in {CLASSES}')
        self.delta = rng.uniform(1.0, 2.0)
        self.sigma_shared = 4.0 * self.delta if self.cls == 'EVAL_NOISY' else rng.uniform(0.5, 1.0)
        self.sigma_indep = rng.uniform(0.15, 0.3) * self.delta
        hid = rng.choice(sorted(HIDDEN))
        self.scale = rng.choice((1.0, 2.0))
        if self.cls == 'FUSION_NEEDED':
            self.z_expr = ['sub_s', DEG, NSCALED if self.scale == 1.0 else ['mul_s', self.scale, NSCALED]]
        else:
            self.z_expr = HIDDEN[hid]
        self.graphs = {}
        for split, n in SIZES.items():
            r = random.Random(f'zoo|{seed}|{split}' if split in ('dev_a', 'dev_b') else
                              f'zoo-sealed|{sealed_seed}|{seed}|{split}')
            self.graphs[split] = [random_graph(r) for _ in range(n)]
        self.z = {s: [SG.evaluate(self.z_expr, g) for g in gs] for s, gs in self.graphs.items()}
        ref = sorted(self.z['dev_a'] + self.z['dev_b'])
        self.cut = ref[len(ref) // 2]
        if self.cls == 'DECOY':
            self.decoy_expr = DEG
            dv = {s: [SG.evaluate(DEG, g) for g in self.graphs[s]] for s in ('dev_a', 'dev_b')}
            dz = sorted(dv['dev_a'] + dv['dev_b'])
            self.decoy_cut = dz[len(dz) // 2]
            self.decoy_side = {s: [int(v > self.decoy_cut) for v in vs] for s, vs in dv.items()}
        self.incumbent = self._incumbent(rng, hid)

    # -------------------------------------------------------------------------------------------- objective

    def effect(self, split, i, c):
        if self.cls == 'NULL':
            return 0.0
        if self.cls == 'DECOY':
            if split not in ('dev_a', 'dev_b'):
                return 0.0
            side = self.decoy_side[split][i]
        else:
            side = int(self.z[split][i] > self.cut)
        if c == 2:
            return self.delta / 2
        return self.delta if c == side else 0.0

    def draw(self, split, i, c, r):
        base = _gauss('base', self.seed, split, i)
        return (base + self.effect(split, i, c) + self.sigma_shared * _gauss('shared', self.seed, split, i, r) +
                self.sigma_indep * _gauss('indep', self.seed, split, i, c, r))

    def value(self, split, choices):
        """The noise-free mean effect of the choices on the split's instances."""
        return sum(self.effect(split, i, c) for i, c in enumerate(choices)) / max(1, len(choices))

    def oracle(self, split):
        return sum(max(self.effect(split, i, c) for c in range(K)) for i in range(len(self.graphs[split]))) / \
            max(1, len(self.graphs[split]))

    # -------------------------------------------------------------------------------------------- the incumbent

    def _incumbent(self, rng, hid):
        z_sense = self.z_expr if self.cls not in ('SENSE_BLIND', 'FUSION_NEEDED', 'DECOY') else None
        if self.cls == 'SENSE_BLIND':
            senses = [DEG, 'n']
        elif self.cls == 'FUSION_NEEDED':
            senses = [DEG, NSCALED]
        elif self.cls == 'DECOY':
            senses = [DEG, 'n']
        else:
            senses = [z_sense, DEG] if rng.random() < 0.5 else [DEG, z_sense]
        policy, pparams = ('global', {}) if self.cls in ('GLOBAL_ONLY', 'DECOY') else ('threshold', {'n_cuts': 1})
        search, sparams = 'exhaustive', {}
        if self.cls == 'SEARCH_WEAK':
            search = 'hill_climb'
            sparams = {'steps': 30, 'step': 0.001, 'start': {'f': 0, 'cuts': [1.0e3], 'choices': [2, 2]}}
        evaluator, eparams = ('independent', {'repeats': 1}) if self.cls == 'EVAL_NOISY' else \
            ('paired', {'repeats': 2})
        nodes = {'s1': G.node('Sense', 'expr', {'expr': senses[0]}), 's2': G.node('Sense', 'expr', {'expr': senses[1]}),
                 'feat': G.node('Features', 'stack'), 'pol': G.node('Policy', policy, pparams),
                 'ev': G.node('Evaluator', evaluator, eparams), 'search': G.node('Search', search, sparams),
                 'out': G.node('Output', 'reattempt', kernel=True)}
        edges = [['s1', 'feat', 'senses'], ['s2', 'feat', 'senses'], ['feat', 'search', 'features'],
                 ['pol', 'search', 'family'], ['ev', 'search', 'scheme'], ['search', 'out', 'policy']]
        return G.make(nodes, edges, BUDGET, {'search': 0.9})

    def remedy(self):
        """The oracle-key arm's AG: the incumbent with the planted remedy applied (an upper reference; labelled)."""
        ag = G.make(self.incumbent['nodes'], self.incumbent['edges'], self.incumbent['budget']['total'],
                    self.incumbent['budget']['split'], {'oracle_key': self.cls})
        n = ag['nodes']
        if self.cls == 'SENSE_BLIND':
            n['s2']['params']['expr'] = self.z_expr
        elif self.cls in ('GLOBAL_ONLY', 'DECOY'):
            n['pol'] = G.node('Policy', 'threshold', {'n_cuts': 1})
        elif self.cls == 'FUSION_NEEDED':
            n['s2']['params']['expr'] = self.z_expr
        elif self.cls == 'SEARCH_WEAK':
            n['search'] = G.node('Search', 'exhaustive')
        elif self.cls == 'EVAL_NOISY':
            n['ev'] = G.node('Evaluator', 'paired', {'repeats': 2})
        return ag

    def view(self):
        return View(self)


class View:
    """What ARA receives: the incumbent AG, the dev splits' graphs and a noisy evaluator that counts every unit. No
    class, hidden sense, effect, noise model, cut or sealed graph is reachable through its methods."""

    __slots__ = ('_draw', '_graphs', '_units', 'incumbent', 'K', 'budget')

    def __init__(self, env):
        self._draw = env.draw
        self._graphs = {s: env.graphs[s] for s in ('dev_a', 'dev_b')}
        self._units = [0]
        self.incumbent = G.make(env.incumbent['nodes'], env.incumbent['edges'], env.incumbent['budget']['total'],
                                env.incumbent['budget']['split'])
        self.K = K
        self.budget = env.incumbent['budget']['total']

    def graphs(self, split):
        if split not in self._graphs:
            raise KeyError('ARA sees dev_a and dev_b only')
        return self._graphs[split]

    def size(self, split):
        return len(self.graphs(split))

    def evaluate(self, split, i, c, r):
        if split not in self._graphs or not 0 <= c < self.K:
            raise KeyError('ARA evaluates dev_a and dev_b only')
        self._units[0] += 1
        return self._draw(split, i, c, r)

    @property
    def units(self):
        return self._units[0]


def environment(index, sealed_seed, cls=None):
    """The index-th environment of a zoo whose sealed draws come from `sealed_seed`."""
    return Environment(int(digest({'zoo': index})[:12], 16), sealed_seed, cls)


__all__ = ['CLASSES', 'DEFECTS', 'CONTROLS', 'LOCATION', 'K', 'SIZES', 'BUDGET', 'Environment', 'View',
           'environment', 'random_graph']
