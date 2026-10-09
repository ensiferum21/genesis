"""Benchmark properties and the textbook lemma set used for the lesion suite.

PROPERTIES are TIP / IsaPlanner-style inductive theorems over the default theory. Every
one is checked by random testing when the suite is built (`validated_properties`); a
false property would be dropped and reported, never silently kept.

TEXTBOOK are the standard auxiliary lemmas a human would supply. The lesion suite removes
them from the starting library; arms must rediscover what they need.
"""
from __future__ import annotations

import numpy as np

from .theory import Equation, Theory, counterexample

TEXTBOOK = [
    "plus x Z = x",
    "plus x (S y) = S (plus x y)",
    "plus (plus x y) z = plus x (plus y z)",
    "plus x y = plus y x",
    "plus x (plus y z) = plus y (plus x z)",
    "app xs Nil = xs",
    "app (app xs ys) zs = app xs (app ys zs)",
    "len (app xs ys) = plus (len xs) (len ys)",
    "rev (app xs (Cons x Nil)) = Cons x (rev xs)",
    "rev (app xs ys) = app (rev ys) (rev xs)",
    "mult x Z = Z",
    "mult x (S y) = plus x (mult x y)",
    "mult x (plus y z) = plus (mult x y) (mult x z)",
    "mult (plus x y) z = plus (mult x z) (mult y z)",
    "qrev xs ys = app (rev xs) ys",
    "rot (len xs) (app xs ys) = app ys xs",
    "sum (app xs ys) = plus (sum xs) (sum ys)",
    "len (rev xs) = len xs",
    "double x = plus x x",
    "len (replicate n x) = n",
    "app (take n xs) (drop n xs) = xs",
    "minus (plus x y) x = y",
    "len (incall xs) = len xs",
    "sum (incall xs) = plus (sum xs) (len xs)",
    "app (replicate n x) (Cons x Nil) = Cons x (replicate n x)",
    "max x y = max y x",
    "min x y = min y x",
]

PROPERTIES = [
    # arithmetic
    "plus x y = plus y x",
    "plus x (plus y z) = plus y (plus x z)",
    "plus (plus x y) z = plus (plus x z) y",
    "plus x (S y) = plus (S x) y",
    "plus (plus x y) (plus z w) = plus (plus x z) (plus y w)",
    "mult x y = mult y x",
    "mult x (S Z) = x",
    "mult (S Z) x = x",
    "mult (mult x y) z = mult x (mult y z)",
    "mult x (plus y z) = plus (mult x y) (mult x z)",
    "mult (plus x y) z = plus (mult x z) (mult y z)",
    "mult x (S y) = plus (mult x y) x",
    "mult (S x) y = plus (mult x y) y",
    "double x = plus x x",
    "double (plus x y) = plus (double x) (double y)",
    "half (plus x x) = x",
    "half (double x) = x",
    "minus (plus x y) y = x",
    "minus (plus x y) x = y",
    "minus x x = Z",
    "minus (S x) x = S Z",
    "max x y = max y x",
    "min x y = min y x",
    "max x (max y z) = max (max x y) z",
    "min x (min y z) = min (min x y) z",
    "min x (max x y) = x",
    "max x (min x y) = x",
    "plus (max x y) (min x y) = plus x y",
    "minus (max x y) y = minus x y",
    # lists
    "app xs Nil = xs",
    "app (app xs ys) zs = app xs (app ys zs)",
    "rev (rev xs) = xs",
    "rev (app xs ys) = app (rev ys) (rev xs)",
    "rev (app (rev xs) (rev ys)) = app ys xs",
    "app (rev xs) (rev ys) = rev (app ys xs)",
    "qrev xs Nil = rev xs",
    "qrev (qrev xs Nil) Nil = xs",
    "rev (qrev xs Nil) = xs",
    "qrev xs ys = app (rev xs) ys",
    "len (app xs ys) = len (app ys xs)",
    "len (rev xs) = len xs",
    "len (qrev xs ys) = plus (len xs) (len ys)",
    "len (app xs (app ys zs)) = plus (len xs) (plus (len ys) (len zs))",
    "double (len xs) = len (app xs xs)",
    "len (rev (app xs ys)) = plus (len xs) (len ys)",
    "plus (len xs) (len ys) = len (app ys xs)",
    "sum (app xs ys) = plus (sum xs) (sum ys)",
    "sum (app xs ys) = sum (app ys xs)",
    "sum (rev xs) = sum xs",
    "sum (qrev xs Nil) = sum xs",
    "rot (len xs) xs = xs",
    "rot (len xs) (app xs ys) = app ys xs",
    "len (rot n xs) = len xs",
    "len (incall xs) = len xs",
    "sum (incall xs) = plus (sum xs) (len xs)",
    "incall (app xs ys) = app (incall xs) (incall ys)",
    "rev (incall xs) = incall (rev xs)",
    "len (replicate n x) = n",
    "app (replicate n x) (replicate m x) = replicate (plus n m) x",
    "len (app (replicate n x) xs) = plus n (len xs)",
    "sum (replicate n x) = mult n x",
    "rev (replicate n x) = replicate n x",
    "app (take n xs) (drop n xs) = xs",
    "len (take n xs) = min n (len xs)",
    "len (drop n xs) = minus (len xs) n",
    "drop n (drop m xs) = drop (plus n m) xs",
    "take n (take m xs) = take (min n m) xs",
    "take (len xs) (app xs ys) = xs",
    "drop (len xs) (app xs ys) = ys",
    "plus (len (take n xs)) (len (drop n xs)) = len xs",
    "len (incall (app xs ys)) = plus (len xs) (len ys)",
    "sum (app xs (Cons x Nil)) = plus (sum xs) x",
    "rev (app xs (Cons x Nil)) = Cons x (rev xs)",
    "len (app xs (Cons x Nil)) = S (len xs)",
    "app (rev xs) (Cons x Nil) = rev (Cons x xs)",
]


def validated_properties(theory: Theory, items: list[str], seed: int = 0) -> tuple[list[Equation], list[str]]:
    p = theory.parser()
    rng = np.random.default_rng(seed)
    ok, bad = [], []
    for s in items:
        eq = Equation(*p.parse_eq(s))
        if not theory.well_sorted_eq(eq.lhs, eq.rhs):
            bad.append(s)
            continue
        if counterexample(theory, eq, rng, trials=200) is not None:
            bad.append(s)
            continue
        ok.append(eq)
    return ok, bad
