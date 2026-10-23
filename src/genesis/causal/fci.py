"""FCI, the established method that allows hidden variables (B20_R119), written from the papers.

Spirtes, Glymour and Scheines (2000), with the orientation rules of Zhang (2008, "On the completeness of orientation
rules for causal discovery in the presence of latent confounders and selection bias"). It is prior art for any
method that flags hidden causes, so a Genesis method is compared with it.

Steps:
  1. PC-stable's adjacency search with the same test (Fisher's z on pooled data, or the d-separation oracle).
  2. Unshielded colliders (R0) on a graph whose marks all start as circles.
  3. The Possible-D-SEP stage: for each remaining edge a - b, test a and b given subsets of Possible-D-SEP(a) (and of
     Possible-D-SEP(b)) minus {a, b}; remove the edge if one separates them. Then every mark is reset to a circle
     and R0 is redone with the new separating sets.
  4. Rules R1-R4 until nothing changes (R4 by discriminating paths). Without selection bias, R5-R7 do not apply.
     R8-R10 only turn circles into tails and never add arrowheads, so they cannot add or remove a bidirected edge.
     They are omitted, which leaves some edges undecided that complete FCI would orient.

Output, in `admg`'s format: a -> b for a tail at a and an arrowhead at b; a <-> b for arrowheads at both ends; every
other edge (o-o, o->) undirected. Possible-D-SEP subsets are limited to MAX_PDS_SET variables to bound the cost
(the cap is reported; at p = 10 it is rarely reached).
"""
from itertools import combinations

import numpy as np

from . import methods as PCM

CIRCLE, ARROW, TAIL = 'o', '>', '-'
MAX_PDS_SET = 4


class PAG:
    def __init__(self, p, adj):
        self.p = p
        self.adj = {i: set(adj[i]) for i in range(p)}
        self.mark = {(a, b): CIRCLE for a in range(p) for b in self.adj[a]}     # mark at b on the edge a - b

    def at(self, a, b):
        return self.mark.get((a, b))

    def set(self, a, b, m):
        if self.mark.get((a, b)) != m:
            self.mark[(a, b)] = m
            return True
        return False

    def into(self, a, b):           # a *-> b
        return self.at(a, b) == ARROW

    def directed(self, a, b):       # a -> b
        return self.at(b, a) == TAIL and self.at(a, b) == ARROW

    def remove(self, a, b):
        self.adj[a].discard(b)
        self.adj[b].discard(a)
        self.mark.pop((a, b), None)
        self.mark.pop((b, a), None)


def colliders(g, sepset):
    changed = False
    for k in range(g.p):
        for i, j in combinations(sorted(g.adj[k]), 2):
            if j not in g.adj[i] and k not in sepset.get((i, j), set()):
                changed |= g.set(i, k, ARROW)
                changed |= g.set(j, k, ARROW)
    return changed


def possible_d_sep(g, a):
    """Nodes reachable from a by paths on which every inner node is a collider or the corner of a triangle."""
    out, seen = set(), set()
    stack = [(a, b) for b in g.adj[a]]
    while stack:
        prev, cur = stack.pop()
        if (prev, cur) in seen:
            continue
        seen.add((prev, cur))
        out.add(cur)
        for nxt in g.adj[cur]:
            if nxt == prev or nxt == a:
                continue
            if (g.into(prev, cur) and g.into(nxt, cur)) or nxt in g.adj[prev]:
                stack.append((cur, nxt))
    out.discard(a)
    return out


def pds_stage(g, sepset, indep, alpha):
    capped = 0
    for a in range(g.p):
        for b in sorted(g.adj[a]):
            if b not in g.adj[a]:
                continue
            done = False
            for x, y in ((a, b), (b, a)):
                cand = sorted(possible_d_sep(g, x) - {x, y})
                if len(cand) > MAX_PDS_SET:
                    capped += 1
                for size in range(0, min(len(cand), MAX_PDS_SET) + 1):
                    for S in combinations(cand, size):
                        if indep(x, y, S, alpha):
                            g.remove(a, b)
                            sepset[(a, b)] = sepset[(b, a)] = set(S)
                            done = True
                            break
                    if done:
                        break
                if done:
                    break
    return capped


def _r1(g):
    ch = False
    for b in range(g.p):
        for a in list(g.adj[b]):
            if not g.into(a, b):
                continue
            for c in list(g.adj[b]):
                if c != a and c not in g.adj[a] and g.at(c, b) == CIRCLE:
                    ch |= g.set(c, b, TAIL)
                    ch |= g.set(b, c, ARROW)
    return ch


def _r2(g):
    ch = False
    for a in range(g.p):
        for c in list(g.adj[a]):
            if g.at(a, c) != CIRCLE:
                continue
            for b in g.adj[a] & g.adj[c]:
                if (g.directed(a, b) and g.into(b, c)) or (g.into(a, b) and g.directed(b, c)):
                    ch |= g.set(a, c, ARROW)
                    break
    return ch


def _r3(g):
    ch = False
    for d in range(g.p):
        for b in list(g.adj[d]):
            if g.at(d, b) != CIRCLE:
                continue
            for a, c in combinations(sorted(g.adj[b] & g.adj[d]), 2):
                if (c not in g.adj[a] and g.into(a, b) and g.into(c, b)
                        and g.at(a, d) == CIRCLE and g.at(c, d) == CIRCLE):
                    ch |= g.set(d, b, ARROW)
                    break
    return ch


def _r4(g, sepset):
    """R4: a discriminating path <d, ..., a, b, c> for b (d not adjacent to c; every node strictly between d and b a
    collider on the path and a parent of c) with b o-* c: b -> c if b is in Sepset(d, c), else a <-> b <-> c."""
    ch = False
    for b in range(g.p):
        for c in sorted(g.adj[b]):
            if g.at(c, b) != CIRCLE:
                continue
            for a in sorted(g.adj[b] & g.adj[c]):
                if not (g.directed(a, c) and g.at(b, a) == ARROW):
                    continue
                found, queue, visited = None, [(a, (b, a))], {a}
                while queue and found is None:
                    w, path = queue.pop(0)
                    for d in sorted(g.adj[w]):
                        if d in path or d == c or g.at(d, w) != ARROW:
                            continue
                        if d not in g.adj[c]:
                            found = d
                            break
                        if d not in visited and g.directed(d, c) and g.at(w, d) == ARROW:
                            visited.add(d)
                            queue.append((d, path + (d,)))
                if found is None:
                    continue
                if b in sepset.get((found, c), set()):
                    ch |= g.set(c, b, TAIL)
                    ch |= g.set(b, c, ARROW)
                else:
                    ch |= g.set(a, b, ARROW)
                    ch |= g.set(c, b, ARROW)
                    ch |= g.set(b, c, ARROW)
                break
    return ch


def run(p, indep, alpha):
    adj, sepset = PCM.skeleton(p, indep, alpha)
    g = PAG(p, adj)
    colliders(g, sepset)
    capped = pds_stage(g, sepset, indep, alpha)
    g = PAG(p, g.adj)
    colliders(g, sepset)
    while _r1(g) | _r2(g) | _r3(g) | _r4(g, sepset):
        pass
    return g, capped


def to_answer(g):
    d, u, b = [], [], []
    for a in range(g.p):
        for c in sorted(g.adj[a]):
            if a > c:
                continue
            ma, mc = g.at(c, a), g.at(a, c)     # marks at a and at c
            if ma == TAIL and mc == ARROW:
                d.append([a, c])
            elif mc == TAIL and ma == ARROW:
                d.append([c, a])
            elif ma == ARROW and mc == ARROW:
                b.append([a, c])
            else:
                u.append([a, c])
    d, u = PCM._acyclic_part(g.p, sorted(d), u)
    return {'directed': d, 'undirected': u, 'bidirected': sorted(b)}


def fci(view, alpha=PCM.ALPHA, **_):
    X = PCM.pooled(view)
    g, _ = run(view['p'], PCM.fisher_z(np.corrcoef(X, rowvar=False), X.shape[0]), alpha)
    return to_answer(g)


def fci_oracle(view, truth=None, **_):
    from .admg import d_separated, full_dag
    if truth is None:
        raise ValueError('the oracle needs the truth')
    parents = full_dag(truth)
    g, _ = run(truth['p'], lambda i, j, S, alpha: d_separated(parents, i, j, S), None)
    return to_answer(g)
