"""The W09 recovery experiment: a history library, a cutoff, recovery, and fresh families.

History (before the cutoff): closure statements about three predicates, proved by the
loop: down-closure for TriangleFree, Simple and Bounded8, and closure under intersection
for two of them. Recovery reads only the Lean statement trees of the history conjecture
module (`recovery.snapshot`). Anti-unification proposes abstractions, the top one is
reified, and its instances are checked by `rfl`.

Fresh families (after the cutoff) are predicates the history never mentions: LoopFree,
Matching and C4Free, plus NonEmpty, which is not down-closed. A misapplied abstraction
there must fail. Each family needs closure under intersection, difference, filtering and
erasure. Four arms try to prove the same statements with different libraries:
  none       recipes only;
  retrieval  the history lemmas (instance lemmas about other predicates);
  concept    the recovered concept: one instance proof per fresh predicate, plus generic
             lemmas over the concept;
  manual     Mathlib's `Antitone`, supplied by the builder as the equivalent abstraction.
Caching is measured in every arm: a proof reused for an identical statement digest.
"""
from itertools import combinations
import random

from ..formal_research import loop as L
from ..formal_research import triangle_theory as T
from .representations import C4_SOURCE, c4free

HS_MODULE, FF_MODULE, RC_MODULE = 'HSDefs', 'FFDefs', 'RCDefs'

HS_SOURCE = f'''import {T.DEFS_MODULE}

namespace HS

/-- History predicate: every pair is listed as (u, v) with u < v. -/
def Simple (S : GT.Edges) : Prop := ∀ e ∈ S, e.1 < e.2

/-- History predicate: every endpoint is below 8. -/
def Bounded8 (S : GT.Edges) : Prop := ∀ e ∈ S, e.1 < 8 ∧ e.2 < 8

instance (S : GT.Edges) : Decidable (Simple S) := by unfold Simple; infer_instance
instance (S : GT.Edges) : Decidable (Bounded8 S) := by unfold Bounded8; infer_instance

end HS
'''

FF_SOURCE = f'''import {T.DEFS_MODULE}
import G4Defs

namespace FF

/-- Fresh predicate: no loops. -/
def LoopFree (S : GT.Edges) : Prop := ∀ e ∈ S, e.1 ≠ e.2

/-- Fresh predicate: distinct pairs share no endpoint. -/
def Matching (S : GT.Edges) : Prop :=
  ∀ e ∈ S, ∀ f ∈ S, e ≠ f → e.1 ≠ f.1 ∧ e.1 ≠ f.2 ∧ e.2 ≠ f.1 ∧ e.2 ≠ f.2

/-- Fresh predicate that is not down-closed. -/
def NonEmpty (S : GT.Edges) : Prop := S.Nonempty

instance (S : GT.Edges) : Decidable (LoopFree S) := by unfold LoopFree; infer_instance
instance (S : GT.Edges) : Decidable (Matching S) := by unfold Matching; infer_instance
instance (S : GT.Edges) : Decidable (NonEmpty S) := by unfold NonEmpty; infer_instance

end FF
'''

HISTORY = {'tf': ('GT.TriangleFree', T.tf), 'simple': ('HS.Simple', lambda S: all(u < v for u, v in S)),
           'bounded': ('HS.Bounded8', lambda S: all(u < 8 and v < 8 for u, v in S))}


def matching(S):
    S = list(S)
    return all(e == f or (e[0] != f[0] and e[0] != f[1] and e[1] != f[0] and e[1] != f[1]) for e in S for f in S)


FRESH = {'loopfree': ('FF.LoopFree', lambda S: all(u != v for u, v in S)),
         'matching': ('FF.Matching', matching),
         'c4free': ('G4.C4Free', c4free),
         'nonempty': ('FF.NonEmpty', lambda S: len(S) > 0)}

OPS = {'inter': ('S ∩ T', ['T'], lambda v: v['S'] & v['T']),
       'sdiff': ('S \\ T', ['T'], lambda v: v['S'] - v['T']),
       'filter': ('S.filter fun e => q e', ['q'], lambda v: frozenset(e for e in v['S'] if e in v['q'])),
       'erase': ('S.erase e', ['e'], lambda v: v['S'] - {v['e']})}


def _edges(rng, vertices=4, p=0.3):
    return frozenset((u, w) for u in range(vertices) for w in range(vertices) if rng.random() < p)


def lean_value(b, x):
    if b['type'] == 'GT.Edges':
        return '(∅ : GT.Edges)' if not x else '({' + ', '.join(f'({u}, {w})' for u, w in sorted(x)) + '} : GT.Edges)'
    if b['type'] == 'ℕ × ℕ':
        return f'(({x[0]}, {x[1]}) : ℕ × ℕ)'
    if b['type'] == 'ℕ × ℕ → Bool':
        lit = '(∅ : GT.Edges)' if not x else '({' + ', '.join(f'({u}, {w})' for u, w in sorted(x)) + '} : GT.Edges)'
        return f'(fun e => decide (e ∈ {lit}))'
    raise ValueError(b['type'])


def _sampler(extra):
    def s(rng):
        v = {'S': _edges(rng)}
        for x in extra:
            v[x] = _edges(rng) if x in ('T', 'q') else (rng.randrange(4), rng.randrange(4))
        return v
    return s


def _binder(x):
    return {'T': {'name': 'T', 'type': 'GT.Edges'}, 'q': {'name': 'q', 'type': 'ℕ × ℕ → Bool'},
            'e': {'name': 'e', 'type': 'ℕ × ℕ'}}[x]


def down_conj(cid, pred, model, origin):
    return {'id': cid, 'binders': [{'name': 'S', 'type': 'GT.Edges'}, {'name': 'T', 'type': 'GT.Edges'},
                                   {'name': 'h1', 'hyp': True, 'lean': 'T ⊆ S', 'model': lambda v: v['T'] <= v['S']},
                                   {'name': 'h2', 'hyp': True, 'lean': f'{pred} S',
                                    'model': lambda v, m=model: m(v['S'])}],
            'concl': f'{pred} T', 'model': lambda v, m=model: m(v['T']), 'sampler': _sampler(['T']),
            'origin': origin, 'lean_value': lean_value, 'role': 'history', 'subject': pred}


def op_conj(cid, pred, model, op, origin, role='fresh'):
    term, extra, f = OPS[op]
    return {'id': cid, 'binders': [{'name': 'S', 'type': 'GT.Edges'}] + [_binder(x) for x in extra] +
            [{'name': 'h1', 'hyp': True, 'lean': f'{pred} S', 'model': lambda v, m=model: m(v['S'])}],
            'concl': f'{pred} ({term})', 'model': lambda v, m=model, f=f: m(f(v)), 'sampler': _sampler(extra),
            'origin': origin, 'lean_value': lean_value, 'role': role, 'subject': f'{pred}:{op}', 'opterm': term}


def history_conjectures():
    out = [down_conj(f'down_{k}', p, m, 'history') for k, (p, m) in HISTORY.items()]
    out += [op_conj(f'inter_{k}', p, m, 'inter', 'history', role='history') for k, (p, m) in HISTORY.items()
            if k != 'bounded']
    return out


def generic_conjectures(concept, kind):
    """Closure lemmas over an abstract predicate with the concept as hypothesis."""
    out = []
    for op, (term, extra, _) in OPS.items():
        hyp = f'{concept} P' if kind == 'concept' else 'Antitone P'
        out.append({'id': f'gen_{kind}_{op}', 'binders': [{'name': 'P', 'type': 'GT.Edges → Prop'},
                                                          {'name': 'h', 'hyp': True, 'lean': hyp, 'model': None},
                                                          {'name': 'S', 'type': 'GT.Edges'}] +
                    [_binder(x) for x in extra] + [{'name': 'h1', 'hyp': True, 'lean': 'P S', 'model': None}],
                    'concl': f'P ({term})', 'model': None, 'sampler': None, 'origin': f'generated:generic-over-{kind}',
                    'lean_value': lean_value, 'role': 'generic', 'subject': kind, 'opterm': term})
    return out


def instance_conjectures(concept, kind):
    out = []
    for k, (p, m) in FRESH.items():
        stmt = f'{concept} {p}' if kind == 'concept' else f'Antitone {p}'

        def model(v, m=m):
            return not (v['T'] <= v['S'] and m(v['S']) and not m(v['T']))
        c = {'id': f'inst_{kind}_{k}', 'binders': [], 'concl': stmt, 'model': None, 'sampler': None,
             'origin': f'generated:{kind}-instance', 'lean_value': lean_value, 'role': 'instance',
             'subject': p, 'kind': kind}
        # screen the instance through its unfolded meaning (down-closure of p)
        c['_screen'] = down_conj(f'screen_{k}', p, m, 'screen')
        out.append(c)
    return out


def fresh_conjectures(prefix):
    return [op_conj(f'{prefix}_{k}_{op}', p, m, op, 'fresh-family') for k, (p, m) in FRESH.items() for op in OPS]


def extra_recipes_for(kind, concept=None, fresh_defs=(), library_all=True):
    """Recipes added in a recovery arm. All arms also get the standard recipes and
    `library-elim-all` (every library lemma at once), so the arms differ only in their library."""
    def extra(conj, library):
        names = ' '.join(b['name'] for b in conj['binders'])
        intro = f'intro {names}' if names else 'skip'
        out = []
        if library_all:
            # offered in every arm (an empty library is plain solve_by_elim), so arms differ only in content
            out.append(('elim-with-library', f'{intro}\nsolve_by_elim [{", ".join(l["const"] for l in library)}]'
                        if library else f'{intro}\nsolve_by_elim'))
        if conj.get('role') == 'generic' and conj.get('subject') == 'concept':
            out.append(('concept-apply', f'{intro}\nexact h _ _ (by simp) h1'))
            out.append(('concept-apply-intro', f'{intro}\napply h _ _ _ h1\nintro x hx\nsimp_all'))
        if conj.get('role') == 'generic' and conj.get('subject') == 'antitone':
            out.append(('antitone-apply', f'{intro}\nexact h (show {conj["opterm"]} ≤ S by simp) h1'))
            out.append(('antitone-apply-intro', f'{intro}\nexact h (show {conj["opterm"]} ≤ S from '
                                                 f'fun x hx => by simp_all) h1'))
        if conj.get('role') == 'instance':
            unf = '\n'.join(f'try unfold {d} at *' for d in fresh_defs)
            pre = f'unfold {concept}\n' if conj.get('kind') == 'concept' else ''
            out.append(('down-closure-unfold', f'{pre}intro S T h1 h2\n{unf}\nintros\napply h2 <;> solve_by_elim'))
            out.append(('down-closure-aesop', f'{pre}intro S T h1 h2\n{unf}\naesop'))
        return out
    return extra


def screen_instances(conjs, concept, seed=0):
    """Instance statements are screened through their unfolded meaning (down-closure of the
    predicate). A refuted one gets a counterexample and a disproof that instantiates the
    concept, or `Antitone`, at the falsifying pair."""
    for c in conjs:
        if c.get('role') != 'instance':
            continue
        cx, _ = L.screen(c['_screen'], seed=seed)
        if cx is None:
            continue
        S, Tt = (lean_value({'type': 'GT.Edges'}, cx[k]) for k in ('S', 'T'))
        c['preset_counterexample'] = {'values': {'S': S, 'T': Tt},
                                      'model': {k: sorted(v) for k, v in cx.items()}}
        if c['kind'] == 'concept':
            c['disproof_tactic'] = (f'intro h\nunfold {concept} at h\n'
                                    f'exact absurd (h {S} {Tt} (by decide) (by decide)) (by decide)')
        else:
            c['disproof_tactic'] = (f'intro h\nexact absurd (h (show {Tt} ≤ {S} by decide) (by decide)) '
                                    f'(by decide)')
    return conjs


__all__ = ['HS_SOURCE', 'FF_SOURCE', 'C4_SOURCE', 'history_conjectures', 'generic_conjectures',
           'instance_conjectures', 'fresh_conjectures', 'extra_recipes_for', 'FRESH', 'HISTORY', 'OPS']
