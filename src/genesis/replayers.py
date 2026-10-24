"""Registered replayers for vault artifacts (Genesis Ω contract §3, §9, §16.5: an archived discovery is replayable).

An artifact may carry `replay`: {'replayer': NAME, 'args': {...}, 'expect': {...}}. Only replayers registered here run
(nothing named in data is imported or executed): a replayer recomputes the artifact's recorded behaviour from its
exact content and the arguments, and `replay` compares the result with `expect`.

  * `acquire-on-causal-worlds`: an acquisition program of `science.acquire` (the artifact's content['source']) run by
    the experimental scientist on regenerated causal worlds (`causal.sem` seeds and settings in args, the theory
    model), for `budget` experiments; the result is the experiments it chooses on each world.
"""
from .common import canonical


def _acquire_on_causal_worlds(content, args):
    from .causal import active3 as A3
    from .causal import sem as S
    from .science import design as D
    out = []
    for seed in args['seeds']:
        view, truth = S.instance(seed, args['p'], args['h'], args['density'], args.get('noise', 'gauss'),
                                 args.get('k_env', 3), args.get('n_total', 1500))
        dom = A3.CausalDomain(A3.prepare(view, truth, args.get('n_int', 500), seed), A3.THEORY)
        r, _ = D.run(dom, {'kind': 'program', 'program': content['source']}, args['budget'])
        out.append(list(r.done))
    return {'choices': out}


REPLAYERS = {'acquire-on-causal-worlds': _acquire_on_causal_worlds}


def replay(record):
    """{'verdict': 'REPRODUCED' | 'DIFFERENT' | 'NOT_REPLAYABLE', 'result', 'expect'} for a vault record."""
    spec = record.get('replay')
    if not spec or spec.get('replayer') not in REPLAYERS:
        return {'verdict': 'NOT_REPLAYABLE', 'reason': 'no registered replayer'}
    got = REPLAYERS[spec['replayer']](record['content'], spec['args'])
    same = canonical(got) == canonical(spec.get('expect'))
    return {'verdict': 'REPRODUCED' if same else 'DIFFERENT', 'result': got, 'expect': spec.get('expect')}
