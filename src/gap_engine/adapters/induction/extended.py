"""DEV-only genuinely new inductive families, opt-in and isolated from Theory.default().

These functions change the signature and task distribution, so their results are NOT
comparable with the old benchmark without rerunning *all* arms on a frozen new pool.
They are not promoted to the standard theory or sealed benchmark by this module.
"""
from __future__ import annotations

from .theory import LIST, NAT, Rule, Theory

EXTENDED_DEFS = {
    'snoc': ((LIST, NAT), LIST, [
        'snoc Nil x = Cons x Nil',
        'snoc (Cons y ys) x = Cons y (snoc ys x)',
    ]),
    'mapplus': ((NAT, LIST), LIST, [
        'mapplus n Nil = Nil',
        'mapplus n (Cons x xs) = Cons (plus n x) (mapplus n xs)',
    ]),
    'mapdouble': ((LIST,), LIST, [
        'mapdouble Nil = Nil',
        'mapdouble (Cons x xs) = Cons (double x) (mapdouble xs)',
    ]),
    'countzero': ((LIST,), NAT, [
        'countzero Nil = Z',
        'countzero (Cons Z xs) = S (countzero xs)',
        'countzero (Cons (S x) xs) = countzero xs',
    ]),
    'filterzero': ((LIST,), LIST, [
        'filterzero Nil = Nil',
        'filterzero (Cons Z xs) = Cons Z (filterzero xs)',
        'filterzero (Cons (S x) xs) = filterzero xs',
    ]),
    'sumsquares': ((LIST,), NAT, [
        'sumsquares Nil = Z',
        'sumsquares (Cons x xs) = plus (mult x x) (sumsquares xs)',
    ]),
    'zipplus': ((LIST, LIST), LIST, [
        'zipplus Nil ys = Nil',
        'zipplus (Cons x xs) Nil = Nil',
        'zipplus (Cons x xs) (Cons y ys) = Cons (plus x y) (zipplus xs ys)',
    ]),
    'interleave': ((LIST, LIST), LIST, [
        'interleave Nil ys = ys',
        'interleave (Cons x xs) ys = Cons x (interleave ys xs)',
    ]),
}

EXTENDED_THEMES = {
    'snoc_rev': ['snoc', 'rev', 'app', 'len', 'Cons', 'Nil'],
    'snoc_sum': ['snoc', 'sum', 'app', 'plus', 'Cons', 'Nil'],
    'mapplus_len': ['mapplus', 'len', 'app', 'plus', 'Cons', 'Nil'],
    'mapplus_sum': ['mapplus', 'sum', 'plus', 'mult', 'len', 'Cons', 'Nil'],
    'mapdouble': ['mapdouble', 'sum', 'double', 'len', 'app', 'Cons', 'Nil'],
    'countzero': ['countzero', 'app', 'plus', 'Cons', 'Nil', 'Z', 'S'],
    'filterzero': ['filterzero', 'countzero', 'len', 'app', 'Cons', 'Nil', 'Z', 'S'],
    'sumsquares': ['sumsquares', 'sum', 'mult', 'app', 'plus', 'Cons', 'Nil'],
    'zipplus': ['zipplus', 'len', 'min', 'app', 'Cons', 'Nil'],
    'interleave': ['interleave', 'len', 'sum', 'plus', 'Cons', 'Nil'],
}

EXTENDED_LEMMAS = [
    'len (snoc xs x) = S (len xs)',
    'sum (snoc xs x) = plus (sum xs) x',
    'rev (Cons x xs) = snoc (rev xs) x',
    'len (mapplus n xs) = len xs',
    'mapplus n (app xs ys) = app (mapplus n xs) (mapplus n ys)',
    'len (mapdouble xs) = len xs',
    'mapdouble (app xs ys) = app (mapdouble xs) (mapdouble ys)',
    'countzero (app xs ys) = plus (countzero xs) (countzero ys)',
    'len (filterzero xs) = countzero xs',
    'filterzero (app xs ys) = app (filterzero xs) (filterzero ys)',
    'sumsquares (app xs ys) = plus (sumsquares xs) (sumsquares ys)',
    'len (zipplus xs ys) = min (len xs) (len ys)',
    'len (interleave xs ys) = plus (len xs) (len ys)',
]


def extended_theory() -> Theory:
    th = Theory.default()
    th.name = 'peano-lists-extended-dev-v1'
    for f, (argtypes, result, _) in EXTENDED_DEFS.items():
        if f in th.funs:
            raise ValueError(f'extended function collision: {f}')
        th.funs[f] = (argtypes, result)
    parser = th.parser()
    for f, (_, _, eqs) in EXTENDED_DEFS.items():
        th.defs[f] = [Rule(('def', f, k), *parser.parse_eq(eq)) for k, eq in enumerate(eqs)]
        for rule in th.defs[f]:
            if not th.well_sorted_eq(rule.lhs, rule.rhs):
                raise ValueError(f'ill-sorted extended definition: {rule}')
    return th
