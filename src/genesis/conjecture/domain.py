"""The conjecture domain as the Frontier sees it (research plane; F2, `docs/OMEGA_FRONTIER.md` §5, §8).

`ConjectureDomain(posed)` offers the public calls the Frontier's manifest allows (`frontier.manifest.PUBLIC`):
  * problems: the posed bounds, by opaque id (`posed` is {id: (formula, kind)}, from a study; the statuses stay
    kernel side);
  * statement: 'kind: formula' (public content: the engine orders and seeds problems by its digest);
  * approaches: representations x methods x n (the starting set has no quotient, partition, blow-up or symmetry
    concept, §7b);
  * step: advances one attack (`attack.Runner`) by `quantum` evaluations. The curve point is the best score so
    far (exact, monotone). The artifact is the step's best graph when it improved: its fingerprint (a
    Weisfeiler-Leman hash), its signature (the sorted degree sequence), its score, and a certificate candidate
    (n, edges, a rational vector) for the kernel to check;
  * abstract: when the Frontier sees independent branches converge on a structure (`converge`), the domain parses
    the converged graphs into Gamma programs and generalises their sizes into a TEMPLATE (`abstraction.py`): a new
    representation, available on every problem from then on (the starting set never contains one). When no new
    template comes of it, library learning (`library.py`, the proving test's mechanism 1): a piece recurring in the
    best Γ programs of two independent branches becomes a macro in a new representation. With abstraction off
    (`abstraction=False`) it answers None;
  * derive: an operator acting on Γ's own operations (`operations.py`; the proving test's mechanism 4): from a Γ
    representation, a new one with one more binary operation, a mutation or recombination of its product-type
    operations, deterministic in the engine's seed; None for representations that are not Γ programs;
  * successors: none yet (Genesis's own conjectures are F5).
Runners are cached and rebuilt by replay when a resumed engine asks for a position the cache does not hold (attacks
are deterministic in their seed).
"""
import hashlib

from . import attack as AT

DEFAULT_N = (8, 12, 16, 20, 28)


def _h(*parts):
    return int(hashlib.sha256(repr(parts).encode()).hexdigest()[:12], 16)


class ConjectureDomain:
    def __init__(self, posed, representations=('edges', 'tree', 'bounded', 'gamma'),
                 methods=('hill', 'anneal', 'evolution', 'gbfs', 'cem', 'nrpa'), n_values=DEFAULT_N, abstraction=True,
                 program_max_n=None, library=True):
        self.posed = dict(posed)
        self.library = library                             # abstraction falls back to library learning (mechanism 1)
        # one size cap for every program representation (Γ, derived, library); None keeps attack.MAX_N
        self.program_max_n = program_max_n
        self.representations, self.methods, self.n_values = tuple(representations), tuple(methods), tuple(n_values)
        self.abstraction = abstraction
        self._runners = {}
        self._issued = {}                                  # (problem, fingerprint) -> adjacency of an issued artifact
        self.templates = {}                                # representation name -> {'template', 'from', 'examples'}
        self.derived = {}                                  # representation name -> {'ops': {name: table}, 'from'}
        self.macros = {}                                   # macro name -> skeleton (library learning, mechanism 1)
        self.libraries = {}                                # representation name -> {'macros': {...}, 'from'}

    def problems(self):
        return sorted(self.posed)

    def statement(self, pid):
        formula, kind = self.posed[pid]
        return f'{kind}: {formula}'

    def approaches(self, pid):
        return {'representation': list(self.representations) + sorted(self.templates) + sorted(self.derived)
                + sorted(self.libraries),
                'method': list(self.methods),
                'params': {'n': list(self.n_values)}}

    def neighbours(self, pid):
        return [p for p in self.problems() if p != pid]

    def _runner(self, pid, d, seed, t):
        key = (pid, d['representation'], d['method'], d['params']['n'], seed)
        r = self._runners.get(key)
        if r is None or r.evals > t:
            formula, kind = self.posed[pid]
            rep = self._rep_for(d)
            r = AT.Runner(formula, kind, d['representation'], d['method'], d['params']['n'],
                          _h('attack', pid, d['representation'], d['method'], d['params']['n'], seed), rep=rep)
            self._runners[key] = r
        if r.evals < t:
            r.advance(int(t - r.evals))                       # replay to the requested position
        return r

    def _rep_for(self, d, max_n=None):
        """The representation object for a template or a derived representation; None for a starting one."""
        name = d['representation']
        if name in self.templates:
            from . import abstraction as AB
            if max_n is None:
                return AB.TemplateRep(self.templates[name]['template'])
            return AB.TemplateRep(self.templates[name]['template'], max_n=max_n)
        if name in self.derived:
            from . import operations as OP
            return OP.GammaPlus(d['params']['n'], self.derived[name]['ops'], self.program_max_n)
        if name in self.libraries:
            from . import library as LB
            return LB.GammaLib(d['params']['n'], {}, self.libraries[name]['macros'], self.program_max_n)
        if name == 'gamma' and self.program_max_n is not None:
            return AT.GammaRep(d['params']['n'], self.program_max_n)
        return None

    def _gamma_family(self, name):
        return name == 'gamma' or name in self.derived or name in self.libraries

    def learn(self, pid, fingerprint):
        """Library learning (mechanism 1): a piece recurring in the best Γ programs of at least two independent
        branches becomes a macro, offered in a new representation with every macro learned so far; or None."""
        from . import attack as ATK
        from . import library as LB
        binary = ATK.GammaRep.BINARY + tuple(sorted({o for x in self.derived.values() for o in x['ops']}))
        sources = [r.best_g for key, r in sorted(self._runners.items(), key=lambda kv: repr(kv[0]))
                   if self._gamma_family(key[1]) and r.best_g is not None and r.best > -1e300]
        skel = LB.learn(sources, binary, known=self.macros.values())
        if skel is None:
            return None
        self.macros[f'm{len(self.macros)}'] = skel
        name = f'library{len(self.libraries)}'
        self.libraries[name] = {'macros': dict(self.macros), 'from': [pid, fingerprint]}
        return name

    def derive(self, pid, representation, seed):
        """A new representation: `representation` (a Γ one) with one more binary operation (`operations.py`)."""
        from . import operations as OP
        if representation == 'gamma':
            ops = {}
        elif representation in self.derived:
            ops = self.derived[representation]['ops']
        else:
            return None
        t = OP.derive_table(ops, seed)
        if t is None:
            return None
        new_ops = dict(ops, **{f'r{t}': t})
        for name, x in self.derived.items():               # the same operation set reached twice: one name
            if x['ops'] == new_ops:
                return name
        name = f'derived{len(self.derived)}'
        self.derived[name] = {'ops': new_ops, 'from': representation}
        return name

    def step(self, pid, d, seed, t, quantum):
        r = self._runner(pid, d, seed, t)
        improved = r.advance(int(quantum))
        pts = [(t + quantum, r.best if r.best > -1e300 else -1.0)]
        if not improved or r.best_A is None:
            return pts, []
        import warnings
        import networkx as nx
        A = r.best_A
        G = nx.from_numpy_array(A)
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')                  # networkx 3.5 changed unlabelled hashes; ours are new
            fp = nx.weisfeiler_lehman_graph_hash(G, iterations=4)
        n, edges, x = AT.certificate(A)
        art = {'problem': pid, 'fingerprint': fp,
               'signature': ','.join(map(str, sorted(int(v) for v in A.sum(axis=1)))), 'score': float(r.best),
               'n': n, 'edges': [list(e) for e in edges], 'x': [str(v) for v in x]}
        self._issued.setdefault((pid, fp), A)
        return pts, [art]

    def abstract(self, pid, fingerprint):
        """A new representation (a template) from the graphs issued with this fingerprint on any problem, or None."""
        if not self.abstraction:
            return None
        from . import abstraction as AB
        examples = [A for (p, fp), A in sorted(self._issued.items(), key=lambda kv: kv[0]) if fp == fingerprint]
        if not examples:
            return self.learn(pid, fingerprint) if self.library else None
        for t in AB.candidates(examples):
            key = repr(AB._shape(t['program']))                # one template per shape: its sizes are its parameters
            if any(repr(AB._shape(x['template']['program'])) == key for x in self.templates.values()):
                continue
            name = f'template{len(self.templates)}'
            self.templates[name] = {'template': t, 'from': [pid, fingerprint], 'examples': len(examples)}
            return name
        return self.learn(pid, fingerprint) if self.library else None   # no new template: library learning

    def state(self):
        """What the domain has invented (templates, derived operations, macros, libraries), JSON-able; a study saves
        it with the engine, because a resumed engine's replay cannot rebuild what came from the runners."""
        return {'templates': self.templates, 'derived': self.derived, 'macros': self.macros,
                'libraries': self.libraries}

    def restore(self, state):
        def tup(x):
            if isinstance(x, dict):
                return {k: tup(v) for k, v in x.items()}
            if isinstance(x, list):
                return tuple(tup(v) for v in x)
            return x
        st = tup(state)
        self.templates.update(st.get('templates', {}))
        self.derived.update({k: {'ops': dict(v['ops']), 'from': v['from']} for k, v in st.get('derived', {}).items()})
        self.macros.update(st.get('macros', {}))
        self.libraries.update({k: {'macros': dict(v['macros']), 'from': list(v['from'])}
                               for k, v in st.get('libraries', {}).items()})

    def successors(self, pid, artifact):
        return []

