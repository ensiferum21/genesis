"""Multigeneration controller (roadmap W21, E4 shape), DEV only.

A generation is a frozen research state: its library (lemmas with proof objects), its
research policy (weights), and the lineage that produced it. A transition starts from a
frozen parent, runs independent research runs under the parent's policy with the
parent's library as starting memory, retrains the policy on the accumulated
trajectories, and proposes a child. The child is evaluated against its parent:
  * on a fresh panel that neither has seen (the transition's own panel);
  * on every earlier panel (retention; negative transfer shows here).
Rule (declared in `RULE` before any generation runs): the child is accepted only if it
beats its parent on the fresh panel by at least `margin` targets and loses no more than
`retention_tolerance` on any earlier panel. Otherwise the transition is rolled back: the
parent stays current, and the child is kept in the record as REJECTED.

The controller records two quantities separately (W21): the quality of each accepted
solver (panel scores), and the quality and cost of the improvement process (research
CPU per transition, CPU per accepted improvement, marginal gains). Human interventions
are counted; this controller makes none. Branching is limited to `max_children`.
"""
from ..common import digest
from . import equational as Q
from . import research as RS

RULE = {'margin': 1, 'retention_tolerance': 1, 'max_children': 1, 'human_interventions_allowed': 0}


def freeze(library, weights, lineage):
    state = {'library': [{'id': l['id'], 'text': l['text'], 'proof_sha256': digest({'p': l['proof']})}
                         for l in library], 'weights': list(weights), 'lineage': list(lineage)}
    return {'state': state, 'sha256': digest(state)}


def score(system, library, panel, cfg):
    return RS.evaluate_successor(system, library, panel, eval_s=cfg['eval_s'], premise_k=cfg['premise_k'])


def transition(system, parent, materials, cfg, *, generation, log=None):
    """parent: {'library', 'weights', 'trajectories', 'lineage', 'panels'}; materials: list
    of (pool, dev) for the transition's independent research runs, and 'panel'."""
    library = [dict(l) for l in parent['library']]
    trajectories = list(parent['trajectories'])
    cpu = 0.0
    X, y = list(parent.get('X', [])), list(parent.get('y', []))
    for k, (pool, dev) in enumerate(materials['runs']):
        known = {l['text'] for l in library}
        fresh_pool = [e for e in pool if Q.text(e) not in known]
        res = RS.run(system, RS.Learned(parent['weights'], k), fresh_pool, budget_s=cfg['budget_s'], dev_targets=dev,
                     prove_s=cfg['prove_s'], premise_k=cfg['premise_k'], library=library,
                     id_prefix=f'G{generation}R{k}L')
        cpu += res['cpu_s']
        library = res['library']
        evd = score(system, library, dev, cfg)
        labels = RS.usefulness_labels(res, evd)
        by_text = {Q.text(e): e for e in fresh_pool}
        for t, lab in labels.items():
            if t in by_text:
                X.append(RS.features(by_text[t], dev)); y.append(lab)
        trajectories.append({'generation': generation, 'run': k, 'tried': len(res['trajectory']),
                             'proved': sum(s['outcome'] == 'PROVED' for s in res['trajectory']),
                             'sha256': digest(res['trajectory'])})
        if log:
            log(f'  gen {generation} run {k}: library {len(library)}')
    weights = RS.fit_logistic(X, y) if X else parent['weights']
    return {'library': library, 'weights': weights, 'trajectories': trajectories, 'X': X, 'y': y,
            'lineage': parent['lineage'] + [generation], 'research_cpu_s': round(cpu, 2)}


def decide(parent_scores, child_scores, rule=RULE):
    """parent_scores / child_scores: {panel name: proved}; the last panel is the fresh one."""
    panels = list(child_scores)
    fresh = panels[-1]
    gain = child_scores[fresh] - parent_scores[fresh]
    losses = {p: parent_scores[p] - child_scores[p] for p in panels[:-1]}
    worst = max(losses.values(), default=0)
    accepted = gain >= rule['margin'] and worst <= rule['retention_tolerance']
    return {'fresh_gain': gain, 'retention_losses': losses, 'decision': 'ACCEPTED' if accepted else 'ROLLED_BACK',
            'reason': None if accepted else ('no gain on the fresh panel' if gain < rule['margin'] else
                                             'regression on an earlier panel')}


__all__ = ['RULE', 'freeze', 'transition', 'decide', 'score']
