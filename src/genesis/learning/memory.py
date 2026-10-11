"""Capability memory and failure-driven curriculum (roadmap W20).

Memory. Lemmas from earlier runs, each with provenance (system, run, policy, proof
SHA-256 and Lean status when replayed). Retrieval ranks memory lemmas by relevance to a
target. Before any use against evaluation targets, the memory is screened for
contamination:
  * EXACT: a lemma equal to a target up to variable renaming and orientation;
  * INSTANCE: a target that is a substitution instance of a lemma (the lemma would
    answer the target in one step);
both are excluded and counted, so that success is not storing near-duplicate answers.
Retention: a lemma not used in `demote_after` consecutive evaluations is demoted (kept,
but no longer retrieved); demotions are recorded.

Curriculum. For a failed target, synthesize easier variants:
  * specializations, by identifying two variables;
  * sub-equations, between subterms of the two sides that the decider says are equal.
Each variant is checked for validity (the decider), solvability (E within a small
budget) and difficulty (E time), with its provenance (the target it came from).
Solved variants join the library. Synthetic variants never count as evaluation targets.
"""
from itertools import combinations

from . import equational as Q
from .research import premises, relevance


def _match(p, t, s):
    if p[0] == 'var':
        if p[1] in s:
            return s if s[p[1]] == t else None
        return {**s, p[1]: t}
    if t[0] != 'fn' or p[1] != t[1] or len(p[2]) != len(t[2]):
        return None
    for a, b in zip(p[2], t[2]):
        s = _match(a, b, s)
        if s is None:
            return None
    return s


def instance_of(lemma, target):
    """Is `target` a substitution instance of `lemma` (either orientation)?"""
    for l, r in (lemma, (lemma[1], lemma[0])):
        s = _match(l, target[0], {})
        if s is not None and _match(r, target[1], s) is not None:
            return True
    return False


def screen(memory, targets):
    """Split memory into usable lemmas and contaminated ones."""
    tset = {Q.canon(t) for t in targets}
    keep, excluded = [], []
    for m in memory:
        if Q.canon(m['eq']) in tset:
            excluded.append({'lemma': m['text'], 'reason': 'EXACT'})
        elif any(instance_of(m['eq'], t) for t in targets):
            excluded.append({'lemma': m['text'], 'reason': 'INSTANCE'})
        else:
            keep.append(m)
    return keep, excluded


def demote(memory, evaluations, demote_after=2):
    """Lemmas unused in the last `demote_after` evaluations are demoted."""
    recent = evaluations[-demote_after:]
    if len(recent) < demote_after:
        return memory, []
    used = set().union(*(set(e['lemma_use']) for e in recent))
    keep = [m for m in memory if m['id'] in used or m.get('fresh')]
    demoted = [m['text'] for m in memory if m not in keep]
    return keep, demoted


def variants(target, decider):
    """Easier variants of a target, each with its provenance."""
    out, seen = [], set()
    l, r = target
    vs = sorted(Q._vars(l, set()) | Q._vars(r, set()))
    for a, b in combinations(vs, 2):                        # identify two variables
        eq = Q.canon((_rename_var(l, b, a), _rename_var(r, b, a)))
        if eq[0] != eq[1] and eq not in seen:
            seen.add(eq); out.append({'eq': eq, 'kind': f'specialize {b}:={a}'})
    subs_l = [t for t in _subterms(l) if t[0] == 'fn']
    subs_r = [t for t in _subterms(r) if t[0] == 'fn']
    for a in subs_l:                                          # equal subterms across the sides
        for b in subs_r:
            if a == b:
                continue
            eq = Q.canon((a, b))
            if eq not in seen and Q.holds(eq, decider) and Q.size(eq[0]) + Q.size(eq[1]) < \
                    Q.size(l) + Q.size(r):
                seen.add(eq); out.append({'eq': eq, 'kind': 'equal subterms'})
    return [dict(v, valid=Q.holds(v['eq'], decider), source=Q.text(target)) for v in out]


def _rename_var(t, old, new):
    if t[0] == 'var':
        return ('var', new) if t[1] == old else t
    return ('fn', t[1], tuple(_rename_var(x, old, new) for x in t[2]))


def _subterms(t):
    yield t
    if t[0] == 'fn':
        for a in t[2]:
            yield from _subterms(a)


def retrieve(memory, target, k):
    return premises(memory, target, k)


__all__ = ['screen', 'instance_of', 'demote', 'variants', 'retrieve', 'relevance']
