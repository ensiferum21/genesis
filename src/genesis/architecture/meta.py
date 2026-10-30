"""ARA applied to ARA (research plane; `docs/OMEGA_ARCHITECTURE_INVENTION.md` §9, B20_R144).

ARA's own settings are an object (`ara.DEFAULT_CONFIG`, `ara.CONFIG_SPACE`): how many exact repeats its diagnosis
draws, how rich its observation battery is, its material fraction, how it ranks rewrites, how many variants it tries
and how deep. This module runs ARA's cycle on that object:

  meta-ladder   on meta-development environments, each of ARA's components is replaced in turn by a stronger
                stand-in, and the gain in ARA's released gain is that component's share of ARA's shortfall:
                  localisation  the rewrites ranked by a supplied localisation (a kernel stand-in: the planted
                                location on development environments, the meta-level analogue of the oracle
                                substitution in ARA's own ladder; never available on held-out tasks)
                  exploration   more variants and one more level of depth
                  evaluation    more exact repeats in the diagnosis
                  observation   a larger battery with more edge aggregates
                Each term is the mean paired difference over environments, with a bootstrap interval; the diagnosis
                is the largest term whose lower bound is above MATERIAL, or NONE.
  rewrites      neighbours of the current settings (one setting moved one step in CONFIG_SPACE), the located
                component's settings first (`SETTINGS_OF`), and the operator prior learned from ARA's own traces
                (`learn_prior`) as the 'localised_prior' ranking's input;
  choice        the candidates are evaluated on a second set of development environments; the best is adopted only if
                it beats the current settings there by MATERIAL (paired mean); else the current settings stay (NONE).

`evaluate(config, envs, hint)` is supplied by whoever holds the environments (a study's kernel side); it returns one
released gain per environment (the judge's sealed gain if it promoted, else 0). This module never sees a key.
Every evaluation is counted, so a study can charge the meta-cycle's compute. The held-out comparison of the improved
ARA against the original, against a tuning-only control and on families the meta-cycle never saw is the study's.
"""
import json
import random

from . import ara as A

MATERIAL = 0.02
BOOT = 2000
TERMS = ('localisation', 'exploration', 'evaluation', 'observation')
SETTINGS_OF = {'localisation': ('ranking', 'exact_repeats', 'battery_random', 'material'),
               'exploration': ('max_variants', 'depth'),
               'evaluation': ('exact_repeats', 'material'),
               'observation': ('battery_random', 'edge_aggs')}


def _boot(diffs, seed):
    rng = random.Random(f'meta-boot|{seed}')
    n = len(diffs)
    if n == 0:
        return 0.0, 0.0
    ms = sorted(sum(diffs[rng.randrange(n)] for _ in range(n)) / n for _ in range(BOOT))
    return ms[int(0.025 * BOOT)], ms[int(0.975 * BOOT) - 1]


def _step(space, value, up=True):
    i = space.index(value) if value in space else None
    if i is None:
        return None
    j = i + (1 if up else -1)
    return space[j] if 0 <= j < len(space) else None


def standins(base):
    """{term: (settings, use_hint)} for the meta-ladder, from the settings `base`."""
    b = A.config_of(base)
    sp = A.CONFIG_SPACE
    big = lambda k: sp[k][-1]                                         # noqa: E731
    return {'localisation': (b, True),
            'exploration': (dict(b, max_variants=max(b['max_variants'], big('max_variants')),
                                 depth=min(big('depth'), b['depth'] + 1)), False),
            'evaluation': (dict(b, exact_repeats=big('exact_repeats')), False),
            'observation': (dict(b, battery_random=big('battery_random'), edge_aggs=big('edge_aggs')), False)}


def ladder(evaluate, base, envs, seed=0):
    """The meta-ladder: {'base': gains, 'terms': {term: {mean, lo, hi}}, 'diagnosis', 'evaluations'}."""
    g0 = evaluate(A.config_of(base), envs, False)
    terms, n_eval = {}, len(envs)
    for t, (cfg, hint) in standins(base).items():
        g = evaluate(cfg, envs, hint)
        n_eval += len(envs)
        d = [x - y for x, y in zip(g, g0)]
        lo, hi = _boot(d, f'{seed}|{t}')
        terms[t] = {'mean': sum(d) / len(d), 'lo': lo, 'hi': hi, 'gains': g}
    sig = sorted((t for t in TERMS if terms[t]['lo'] > MATERIAL), key=lambda t: -terms[t]['mean'])
    return {'base': g0, 'terms': terms, 'diagnosis': sig[0] if sig else 'NONE', 'significant': sig,
            'evaluations': n_eval}


def neighbours(base, located=None, first=(), interleave=False):
    """Settings one step from `base` (each setting up or down one place in CONFIG_SPACE), distinct, the located
    component's settings first, then `first`, then the rest in a fixed (alphabetical) order. With `interleave`, every
    setting's first step comes before any setting's second, so a short list covers as many settings as it can (the
    default keeps B20_R144's order)."""
    b = A.config_of(base)
    sp = A.CONFIG_SPACE
    order = []
    for k in list(SETTINGS_OF.get(located, ())) + list(first) + sorted(sp):
        if k not in order:
            order.append(k)
    steps = []
    for k in order:
        vals = sp[k]
        if k in ('ranking', 'edge_aggs'):
            cands = [v for v in vals if v != b[k]]
        else:
            cands = [v for v in (_step(vals, b[k], True), _step(vals, b[k], False)) if v is not None]
        steps.append([(k, v) for v in cands])
    if interleave:
        seq = [x for i in range(max((len(c) for c in steps), default=0)) for c in steps if i < len(c) for x in [c[i]]]
    else:
        seq = [x for c in steps for x in c]
    out, seen = [], {json.dumps(b, sort_keys=True)}
    for k, v in seq:
        c = dict(b, **{k: v})
        key = json.dumps(c, sort_keys=True)
        if key not in seen:
            seen.add(key)
            out.append({'settings': c, 'changed': k})
    return out


def ladder_order(lad):
    """The settings in the order of the meta-ladder's term means, largest first (each term's settings in
    SETTINGS_OF's order): the fall-back when the ladder locates nothing."""
    out = []
    for t in sorted(TERMS, key=lambda t: -lad['terms'][t]['mean']):
        for k in SETTINGS_OF[t]:
            if k not in out:
                out.append(k)
    return out


def learn_prior(traces):
    """An operator prior per diagnosis from ARA's own traces: the mean dev gain of each rewrite operator tried under
    that diagnosis (only diagnosed cycles count)."""
    acc = {}
    for tr in traces:
        dia = (tr.get('diagnosis') or {}).get('diagnosis')
        if not dia or dia in ('NONE',):
            continue
        for v in tr.get('variants', []):
            if 'gain' in v:
                a = acc.setdefault(dia, {}).setdefault(v['rewrite']['op'], [0.0, 0])
                a[0] += v['gain']
                a[1] += 1
    return {d: {op: s / n for op, (s, n) in ops.items()} for d, ops in acc.items()}


FALLBACKS = ('alphabetical', 'ladder')


def improve(evaluate, base, ladder_envs, choice_envs, max_candidates=6, seed=0, fallback='alphabetical'):
    """One meta-cycle: ladder on `ladder_envs`, up to `max_candidates` neighbours (located first) evaluated on
    `choice_envs` against the base; the adopted settings, or the base. When the ladder locates nothing, `fallback`
    orders the candidates: 'alphabetical' (B20_R144's) or 'ladder' (the settings by the terms' means, one step of each
    setting before a second). Returns {'settings', 'adopted', 'ladder', 'candidates', 'evaluations'}."""
    if fallback not in FALLBACKS:
        raise ValueError(f'fallback must be one of {FALLBACKS}')
    lad = ladder(evaluate, base, ladder_envs, seed)
    located = lad['diagnosis'] if lad['diagnosis'] != 'NONE' else None
    if located is None and fallback == 'ladder':
        cands = neighbours(base, None, first=ladder_order(lad), interleave=True)[:max_candidates]
    else:
        cands = neighbours(base, located)[:max_candidates]
    g0 = evaluate(A.config_of(base), choice_envs, False)
    n_eval = lad['evaluations'] + len(choice_envs)
    scored = []
    for c in cands:
        g = evaluate(c['settings'], choice_envs, False)
        n_eval += len(choice_envs)
        d = [x - y for x, y in zip(g, g0)]
        scored.append(dict(c, mean=sum(d) / len(d), gains=g))
    best = max(scored, key=lambda c: c['mean']) if scored else None
    adopted = best is not None and best['mean'] >= MATERIAL
    return {'settings': best['settings'] if adopted else A.config_of(base), 'adopted': adopted, 'ladder': lad,
            'located': located, 'candidates': scored, 'base_choice': g0, 'evaluations': n_eval}


def tune(evaluate, base, choice_envs, evaluations, seed=0):
    """The tuning-only control at the meta level: settings drawn at random from CONFIG_SPACE (seeded), each evaluated
    on `choice_envs`, until `evaluations` environment evaluations are spent (the meta-cycle's own count); the best by
    mean gain, if it beats the base by MATERIAL."""
    rng = random.Random(f'meta-tune|{seed}')
    g0 = evaluate(A.config_of(base), choice_envs, False)
    spent, best, tried = len(choice_envs), None, []
    while spent + len(choice_envs) <= evaluations:
        c = A.config_of({k: rng.choice(v) for k, v in A.CONFIG_SPACE.items()})
        g = evaluate(c, choice_envs, False)
        spent += len(choice_envs)
        m = sum(x - y for x, y in zip(g, g0)) / len(g)
        tried.append({'settings': c, 'mean': m})
        if best is None or m > best['mean']:
            best = {'settings': c, 'mean': m}
    adopted = best is not None and best['mean'] >= MATERIAL
    return {'settings': best['settings'] if adopted else A.config_of(base), 'adopted': adopted, 'tried': tried,
            'evaluations': spent}


__all__ = ['MATERIAL', 'TERMS', 'SETTINGS_OF', 'FALLBACKS', 'standins', 'ladder', 'neighbours', 'ladder_order',
           'learn_prior', 'improve', 'tune']
