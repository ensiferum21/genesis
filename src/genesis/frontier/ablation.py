"""Part 1's usefulness ablation (the proving test; `docs/handoff/PT1_DESIGN_DRAFT.md`, open item 4). Research plane;
a study runs it after the engine has finished, with the manifest's verifier.

A representation the engine created during a run is credited with a discovery when the discovering branch searched
it (`credit`). The report names how it was made: derivation (`derive` events), library learning or a template
(`abstract` events, told apart by the domain's own record when it has one). It also gives its lineage back to a
starting representation.

`ablate` decides whether it was *useful*, at matched compute:
  * the discovering approach (its method and parameters) is re-run on the problem through the domain's public
    `step`, exactly as the engine advances a branch, for `k` fresh seeds;
  * each run gets the discovering branch's compute at the time of its verified result (the engine's `verified`
    event records it; older logs fall back to the branch's final compute);
  * this is done once in the credited representation, once in each representation of its lineage, and once in each
    starting representation;
  * every artifact a run issues that improves on that run's best is verified, as the engine would;
  * **useful** iff the credited representation verifies a result in at least one seed, while no starting
    representation does in any seed. The starting representations together get as many times the credited one's
    compute as there are of them;
  * the lineage's intermediate representations are reported, not tested.
The ablation's compute, verification included, is returned so that a study can charge it to the run.
"""
import hashlib
import json

from . import direction as D


def _seed(*parts):
    return int(hashlib.sha256(json.dumps(['ablation', *parts], default=str).encode()).hexdigest()[:12], 16)


def finding(eng, problem):
    """The last verified improvement on `problem`: (event, branch), or None."""
    ev = next((e for e in reversed(eng.events) if e['kind'] == 'verified' and e['problem'] == problem), None)
    return None if ev is None else (ev, eng.branches[ev['branch']])


def lineage(eng, representation):
    """[(representation, how it was made)] from `representation` back to a starting one, which ends the list with
    how 'starting'. How: 'derivation', 'abstraction' (a template or a library), or 'starting'."""
    out, rep, seen = [], representation, set()
    while rep not in seen:
        seen.add(rep)
        dv = next((e for e in eng.events if e['kind'] == 'derive' and e['result'] == rep), None)
        if dv is not None:
            out.append((rep, 'derivation'))
            rep = dv['representation']
            continue
        ab = next((e for e in eng.events if e['kind'] == 'abstract' and e['result'] == rep), None)
        if ab is not None:
            out.append((rep, 'abstraction'))
            return out
        out.append((rep, 'starting'))
        return out
    return out


def credit(eng, problem):
    """The representation credited with the discovery on `problem`, how it was made and its lineage; or None if the
    discovering branch searched a starting representation (nothing created to credit) or there is no discovery."""
    found = finding(eng, problem)
    if found is None:
        return None
    ev, b = found
    rep = b['direction']['representation']
    chain = lineage(eng, rep)
    if chain[0][1] == 'starting':
        return None
    return {'representation': rep, 'how': chain[0][1], 'lineage': chain,
            'approach': {'method': b['direction']['method'], 'params': dict(b['direction']['params'])},
            'compute': ev.get('t', b['t']), 'branch': b['id'], 'event': eng.events.index(ev)}


def replay(domain, verify, problem, d, seed, compute, quantum, verify_cost=1):
    """One run of direction `d` for `compute` units, as the engine advances a branch: (verified, units spent)."""
    t, spent, best = 0.0, 0.0, 0.0
    while t + quantum <= compute + 1e-9:
        pts, arts = domain.step(problem, d, seed, t, quantum)
        t = pts[-1][0] if pts else t + quantum
        spent += quantum
        for a in arts:
            if a['problem'] != problem or a['score'] <= best:
                continue
            spent += verify_cost
            if float(verify(problem, a)) > 0:
                return True, spent
            best = a['score']
    return False, spent


def ablate(eng, problem, verify, starting, k=5, quantum=None, verify_cost=None):
    """Was the credited representation useful for the discovery on `problem`? `starting` is the domain's starting
    representations (a study passes them; the engine does not know which are which)."""
    c = credit(eng, problem)
    if c is None:
        return None
    quantum = quantum or eng.quantum
    verify_cost = eng.verify_cost if verify_cost is None else verify_cost
    domain = eng.domain
    arms = [c['representation']] + [r for r, how in c['lineage'][1:] if how != 'starting'] + list(starting)
    hits, spent = {}, 0.0
    for rep in dict.fromkeys(arms):
        d = D.make(problem, rep, c['approach']['method'], c['approach']['params'], op='ablation')
        hits[rep] = []
        for i in range(k):
            ok, u = replay(domain, verify, problem, d, _seed(problem, i), c['compute'], quantum, verify_cost)
            hits[rep].append(ok)
            spent += u
    useful = any(hits[c['representation']]) and not any(any(hits[r]) for r in starting)
    return dict(c, k=k, hits=hits, useful=useful, ablation_spent=spent)


__all__ = ['finding', 'lineage', 'credit', 'replay', 'ablate']
