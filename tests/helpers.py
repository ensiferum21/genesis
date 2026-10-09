"""Small, fast worlds for tests (built in well under a second)."""
from gap_engine.adapters.induction.adapter import InductionWorld, SolverConfig, _lid
from gap_engine.adapters.induction.checker import LemmaStore
from gap_engine.adapters.induction.prover import Prover
from gap_engine.adapters.induction.theory import Equation, Theory
from gap_engine.kernel.ledger import Ledger
from gap_engine.kernel.sealed import SealedStore

POOL = ["plus x Z = x", "plus x (S y) = S (plus x y)", "app xs Nil = xs",
        "app (app xs ys) zs = app xs (app ys zs)", "len (app xs ys) = plus (len xs) (len ys)",
        "rev (app xs (Cons x Nil)) = Cons x (rev xs)", "max x Z = x", "min x Z = Z"]
DEV = ["plus x y = plus y x", "rev (rev xs) = xs", "rev (app xs ys) = app (rev ys) (rev xs)",
       "len (app xs ys) = len (app ys xs)", "plus (plus x y) z = plus x (plus y z)",
       "double x = plus x x", "minus (plus x y) y = x", "len (rev xs) = len xs"]
SELECT = ["plus x (plus y z) = plus y (plus x z)", "app (rev xs) (rev ys) = rev (app ys xs)",
          "plus x (S y) = plus (S x) y", "len (app xs (Cons x Nil)) = S (len xs)"]
CONFIRM = ["rev (app (rev xs) (rev ys)) = app ys xs", "double (len xs) = len (app xs xs)",
           "plus (plus x y) z = plus (plus x z) y", "sum (app xs (Cons x Nil)) = plus (sum xs) x"]
SEALED = ["len (app xs (app ys zs)) = plus (len xs) (plus (len ys) (len zs))",
          "plus (len xs) (len ys) = len (app ys xs)"]


def mini_world(ledger: Ledger | None = None) -> InductionWorld:
    th = Theory.default()
    P = th.parser()
    E = lambda s: Equation(*P.parse_eq(s))
    store = LemmaStore(th)
    pool = []
    for s in POOL:
        eq = E(s)
        att = Prover(th, {i: store.lemmas[i] for i in pool}, fuel=20000).prove(eq)
        assert att.proved, s
        lid = _lid(eq)
        store.verify(lid, eq, att.proof)
        pool.append(lid)
    sealed = SealedStore(ledger=ledger if ledger is not None else Ledger())
    sealed.seal("SEALED", [(s, E(s)) for s in SEALED])
    return InductionWorld(name="mini", theory=th, store=store, base_ids=[], pool=pool,
                          tasks={"DEV": [E(s) for s in DEV], "SELECT": [E(s) for s in SELECT],
                                 "CONFIRM": [E(s) for s in CONFIRM]},
                          sealed=sealed, solver=SolverConfig(fuel=150, max_depth=2))
