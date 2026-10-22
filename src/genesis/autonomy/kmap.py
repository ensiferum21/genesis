"""The knowledge map (B20_R100): what Genesis knows about which method does how well where, with how much certainty.

Why (docs/RECURSIVE_IMPROVEMENT_ARCHITECTURE.md, "predictive coding and curiosity"). A research policy that improves
itself needs a model of its own knowledge: where its predictions are reliable, where they are thin, and where they
are wrong. The map is that model for solver performance. It is fitted on every study the adaptation cell can read
(`adaptation.discovery`), predicts the quality a method reaches on an instance at a budget with an interval, and so
gives the research loop three things:
  * *expectations* that can be written before a study runs and scored after it (calibration of the system's
    own beliefs);
  * *thin knowledge*: wide intervals where it has little data (unseen methods, sizes, families), which is where an
    experiment teaches the most;
  * *surprises*: results far outside their interval, which the immune response turns into checks (B20_R97's
    collapse of two champions on large hosts is the motivating case; see B20_R98).

Model (fixed). The unit is a cell (method, instance, budget) with quality q = the mean over runs of
min(1, value / target) (quality-at-equal-time studies: value / best known value). Features: ln n, edge density, a
planted-family flag, ln budget. Per method, a Gaussian process (scikit-learn; constant x anisotropic RBF + white
noise; inputs as they are, outputs normalised; at most MAX_POINTS points, a deterministic even subsample) gives a
mean and a standard deviation that grows away from the data. A method with fewer than MIN_POINTS cells falls back to
its class's process (CLASSES: what kind of method it is) with sd inflated by CLASS_SD, and an unknown class to the
process over every cell with GLOBAL_SD. The map also *calibrates itself*: SCALE multiplies every sd so that, on the
studies it has already replayed (each predicted from the studies before it), 90% of cells fall within the 90%
interval; the scale is learned from those replays only, never from the study being predicted.

Prior art: performance prediction for algorithm selection (SATzilla, Xu et al. 2008; Hutter et al. 2014) and
Bayesian optimisation's surrogate models. What is specific here is its use as the research policy's model of its own
knowledge, scored prospectively.
"""
import math
import warnings

ALIAS = {'found': 'gen1', 'tfxw': 'tfx_engine', 'tfx': 'tfx_engine', 'first_design': 'tfx_engine_default'}
CLASSES = {
    'language': ('gen1', 'gen2', 'gen3', 'control', 'random'),
    'invented_representation': ('candidate', 'system'),
    'builder_engine': ('engine', 'tfx_engine', 'tfx_engine_default', 'no_cross', 'no_dsb', 'no_pt',
                       'no_relink_restart', 'previous_generation'),
    'physics': ('dsb', 'eo'),
    'maxcut_heuristic': ('tabu', 'burer', 'mq1', 'mq2', 'mq3'),
    'exact': ('cpsat', 'highs'),
}
DEFAULT_CLASS = 'maxsat_champion'
MIN_POINTS, MAX_POINTS = 12, 600
CLASS_SD, GLOBAL_SD = 0.05, 0.15
Z90 = 1.6449


def method_key(arm):
    return ALIAS.get(arm, arm)


def method_class(m):
    return next((c for c, ms in CLASSES.items() if m in ms), DEFAULT_CLASS)


def features(n, edges, planted, budget):
    return (math.log(n), edges / (n * (n - 1) / 2), 1.0 if planted else 0.0, math.log(budget))


def cells(study):
    """[(method, features, quality)] of one `adaptation.receptors.Study`."""
    out = []
    for r in study.rows:
        n = r['n']
        m = r['edges'] if isinstance(r['edges'], int) else len(r['edges'])
        planted = 'planted' in (r.get('family') or r.get('task_id', ''))
        if study.profile.kind == 'qet':
            best = r['best_value']
            b = study.budgets()[0]
            for arm, byb in r['runs'].items():
                x = byb.get(f'{b:g}')
                if x and x.get('value') is not None and best:
                    out.append((method_key(arm), features(n, m, planted, b), x['value'] / best))
            continue
        target = r['target']
        for arm, byb in r['runs'].items():
            for t, runs in byb.items():
                vals = [x['value'] for x in runs if x.get('run') == 'SUCCESS']
                if vals and target:
                    out.append((method_key(arm), features(n, m, planted, float(t)),
                                sum(min(1.0, v / target) for v in vals) / len(vals)))
    return out


def corpus(root):
    """[(study name, [(method, features, quality)])] for every readable study, in batch order."""
    from ..adaptation import discovery as D
    from ..adaptation.receptors import Study
    return [(p.evidence.split('/')[-1], cells(Study.load(p, str(root)))) for p in D.discover(str(root))]


class Map:
    def __init__(self, cell_list, scale=1.0):
        import numpy as np
        from sklearn.gaussian_process import GaussianProcessRegressor
        from sklearn.gaussian_process.kernels import RBF, WhiteKernel, ConstantKernel as C
        self.scale = scale
        self.models, self.counts = {}, {}
        groups = {}
        for meth, f, q in cell_list:
            groups.setdefault(('method', meth), []).append((f, q))
            groups.setdefault(('class', method_class(meth)), []).append((f, q))
            groups.setdefault(('global', 'all'), []).append((f, q))
        for key, pts in sorted(groups.items()):
            self.counts[key] = len(pts)
            if len(pts) < MIN_POINTS:
                continue
            X = np.array([p[0] for p in pts])
            y = np.array([p[1] for p in pts])
            if len(pts) > MAX_POINTS:
                idx = np.linspace(0, len(pts) - 1, MAX_POINTS).astype(int)
                X, y = X[idx], y[idx]
            kern = C(0.05, (1e-4, 1.0)) * RBF([1.0, 0.3, 1.0, 1.5], (1e-2, 1e2)) + WhiteKernel(1e-3, (1e-6, 0.1))
            gp = GaussianProcessRegressor(kern, normalize_y=True, random_state=0, n_restarts_optimizer=1)
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                gp.fit(X, y)
            self.models[key] = gp

    def predict(self, meth, f):
        """(mean, sd, level): level is 'method', 'class' or 'global' (what the prediction rests on)."""
        import numpy as np
        for key, extra in ((('method', meth), 0.0), (('class', method_class(meth)), CLASS_SD),
                           (('global', 'all'), GLOBAL_SD)):
            if key in self.models:
                mu, sd = self.models[key].predict(np.array([f]), return_std=True)
                return float(mu[0]), self.scale * math.hypot(float(sd[0]), extra), key[0]
        return 0.5, self.scale * 0.5, 'none'

    def interval(self, meth, f):
        mu, sd, _ = self.predict(meth, f)
        return max(0.0, mu - Z90 * sd), min(1.0, mu + Z90 * sd)


def replay(corp):
    """Each study predicted from the studies before it, with the scale learned from the replays before it.
    Returns ([{study, cells, mae_map, mae_baseline, coverage90, surprises (|z| > 3 x scale), scale}], every z)."""
    out, zs = [], []
    for k in range(1, len(corp)):
        train = [c for _, cs in corp[:k] for c in cs]
        scale = learned_scale(zs)
        M = Map(train, scale=1.0)
        base, allq = {}, [q for _, _, q in train]
        for meth, _, q in train:
            base.setdefault(meth, []).append(q)
        gmean = sum(allq) / len(allq)
        name, test = corp[k]
        e_map = e_base = 0.0
        inside = 0
        sur = []
        new_z = []
        for meth, f, q in test:
            mu, sd, lvl = M.predict(meth, f)
            b = sum(base[meth]) / len(base[meth]) if meth in base else gmean
            e_map += abs(q - mu)
            e_base += abs(q - b)
            z = (q - mu) / max(sd, 1e-6)
            new_z.append(z)
            inside += abs(z) <= Z90 * scale
            if abs(z) > 3 * scale:
                sur.append(meth)
        n = len(test)
        out.append({'study': name, 'cells': n, 'mae_map': e_map / n, 'mae_baseline': e_base / n,
                    'coverage90': inside / n, 'surprises': len(sur), 'surprise_methods': sorted(set(sur)),
                    'scale': scale})
        zs.extend(new_z)
    return out, zs


def learned_scale(zs):
    """The factor that puts 90% of past |z| within Z90 (at least 1): the map's own record of how wrong it is."""
    if not zs:
        return 1.0
    a = sorted(abs(z) for z in zs)
    q90 = a[min(len(a) - 1, int(0.9 * len(a)))]
    return max(1.0, q90 / Z90)
