"""Inductive mathematics as a reality adapter (the real-mathematics domain of this repo).

Library items are kernel-verified lemmas. A library is evaluated by running the solver
(bounded rewriting + induction) on every task of a split; a task counts as solved only if
the trusted checker accepts the solver's proof. Fingerprints record which probe tasks a
lemma changes: the normal forms of the task's sides or of the subgoals the base solver got
stuck on.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

import numpy as np

from ...kernel.ledger import Ledger
from ...kernel.sealed import SealedStore
from .checker import CheckError, LemmaStore, check_proof
from .conjecture import THEMES, generate
from .prover import Normaliser, PRECEDENCE, Prover, RW, orient
from .tasks import PROPERTIES, TEXTBOOK, validated_properties
from .theory import Equation, Theory

SPLITS = ("DEV", "SELECT", "CONFIRM")


@dataclass
class SolverConfig:
    fuel: int = 150
    max_depth: int = 2
    max_vars: int = 2


@dataclass
class InductionWorld:
    name: str
    theory: Theory
    store: LemmaStore                       # kernel: every verified lemma (pool + base)
    base_ids: list[str]                     # accepted library at the start
    pool: list[str]                         # verified candidate lemmas, not yet accepted
    tasks: dict[str, list[Equation]]        # DEV / SELECT / CONFIRM
    sealed: SealedStore
    solver: SolverConfig = field(default_factory=SolverConfig)
    stuck_cache: dict = field(default_factory=dict)
    meta: dict = field(default_factory=dict)
    accepted_extra: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------ adapter API
    def pool_ids(self) -> list[str]:
        return list(self.pool)

    def n_tasks(self, split: str) -> int:
        return len(self.tasks[split])

    def _library(self, extra: list[str]) -> dict[str, Equation]:
        # GEN-AUD-023: never feed public mutable lemma entries to the prover.
        # In particular, do not silently certify a forged lemma on sealed tasks.
        self.store.assert_theory_matches(self.theory)
        ids = list(dict.fromkeys([*self.base_ids, *self.accepted_extra, *extra]))
        return self.store.verified_subset(ids)

    def solve(self, eq: Equation, lib: dict[str, Equation], seed: int, fuel: int | None = None,
              max_depth: int | None = None) -> bool:
        # Even direct callers of solve() must not supply forged lemma premises.
        self.store.assert_theory_matches(self.theory)
        trusted = self.store.verified_subset(lib)
        if lib != trusted:
            raise CheckError("solver library differs from kernel-admitted premises")
        pr = Prover(self.theory, trusted, fuel=fuel or self.solver.fuel,
                    max_depth=self.solver.max_depth if max_depth is None else max_depth,
                    max_vars=self.solver.max_vars, seed=seed)
        att = pr.prove(eq)
        if not att.proved:
            return False
        try:
            return check_proof(self.theory, trusted, eq, att.proof)
        except CheckError:
            return False

    def run_library(self, extra: list[str], split: str, seed: int) -> np.ndarray:
        lib = self._library(extra)
        return np.array([self.solve(eq, lib, seed * 7919 + t) for t, eq in enumerate(self.tasks[split])],
                        dtype=np.int8)

    def evaluate(self, X: np.ndarray, split: str, seed: int, crn: bool) -> np.ndarray:
        X = np.asarray(X, bool)
        out = np.zeros((X.shape[0], self.n_tasks(split)), dtype=np.int8)
        for r in range(X.shape[0]):
            extra = [self.pool[i] for i in np.nonzero(X[r])[0]]
            out[r] = self.run_library(extra, split, seed if crn else seed * 100_003 + r)
        return out

    def library_eval_cost(self, n_items: int) -> float:
        return 1.0

    def eval_cost(self, library: frozenset[str], split: str) -> float:
        return self.n_tasks(split) / max(1, self.n_tasks("DEV"))

    def outcomes(self, library: frozenset[str], split: str, reps: int, seed: int) -> np.ndarray:
        # sorted: iterating a set of str ids depends on PYTHONHASHSEED, and the order of library
        # lemmas changes which rewrite fires first, so gate outcomes were not reproducible
        # across processes (found by the round-2b fact-check)
        extra = [i for i in sorted(library) if i not in self.base_ids]
        return np.stack([self.run_library(extra, split, seed * 31 + k) for k in range(reps)])

    # ------------------------------------------------------------------ fingerprints
    def _rules(self, lib: dict[str, Equation]):
        table = {f: k for k, f in enumerate(PRECEDENCE)}
        rules = [RW(r.rid, r.lhs, r.rhs, 1) for r in self.theory.all_rules()]
        for lid, e in lib.items():
            rules.extend(orient(("lemma", lid), e, table))
        return rules, table

    def _probe_terms(self) -> list[list]:
        if "probe" not in self.stuck_cache:
            lib = self._library([])
            probes = []
            for t, eq in enumerate(self.tasks["DEV"]):
                att = Prover(self.theory, lib, fuel=self.solver.fuel, max_depth=self.solver.max_depth,
                             seed=t).prove(eq)
                terms = [eq.lhs, eq.rhs]
                for s in att.stuck[:6]:
                    terms += [s.lhs, s.rhs]
                probes.append(terms)
            self.stuck_cache["probe"] = probes
        return self.stuck_cache["probe"]

    def _normal_forms(self, lib: dict[str, Equation]) -> list[tuple]:
        rules, table = self._rules(lib)
        out = []
        for terms in self._probe_terms():
            N = Normaliser(rules, [0], 20000, table)
            nf = []
            for t in terms:
                try:
                    nf.append(N.norm(t)[0])
                except Exception:
                    nf.append(None)
            out.append(tuple(nf))
        return out

    def fingerprint(self, i: int, seed: int) -> np.ndarray:
        if "base_nf" not in self.stuck_cache:
            self.stuck_cache["base_nf"] = self._normal_forms(self._library([]))
        base = self.stuck_cache["base_nf"]
        mine = self._normal_forms(self._library([self.pool[i]]))
        return np.array([a != b for a, b in zip(base, mine)], dtype=bool)

    def fingerprint_cost(self) -> float:
        return 0.05

    def null_fingerprint(self, seed: int) -> np.ndarray:
        return np.zeros(self.n_tasks("DEV"), bool)

    def statement(self, lid: str) -> str:
        return self.store.verified_subset([lid])[lid].text()

    def screen_reason(self, text: str) -> str | None:
        """The single rule for what may enter the candidate pool or a training set (INV-20):
        nothing that is a sealed item or a near-duplicate of one (kernel screen), and nothing
        that is a held-out gate task (SELECT/CONFIRM), word for word. Returns why a statement
        is refused, or None if it may enter."""
        if self.sealed.near_duplicate(text):
            return "sealed"
        if text in {e.text() for s in ("SELECT", "CONFIRM") for e in self.tasks[s]}:
            return "held_out"
        return None


def _lid(eq: Equation) -> str:
    return "L" + hashlib.sha1(eq.text().encode()).hexdigest()[:10]


def discover_pool(theory: Theory, store: LemmaStore, base_ids: list[str], conjectures: list[Equation],
                  exclude: set[str], rounds: int = 3, fuel: int = 20000) -> tuple[list[str], list[Equation]]:
    """Prove conjectures in rounds (later rounds may use lemmas proven earlier). Returns
    (verified pool ids, still-open conjectures). Statements in `exclude` are never admitted
    to the pool (they are tasks or sealed items)."""
    pool: list[str] = []
    pending = [c for c in conjectures if c.text() not in exclude]
    for _ in range(rounds):
        nxt = []
        lib = store.verified_subset(base_ids + pool)
        for eq in pending:
            att = Prover(theory, lib, fuel=fuel, max_depth=2, max_vars=2).prove(eq)
            if att.proved:
                lid = _lid(eq)
                try:
                    store.verify(lid, eq, att.proof)
                    if lid not in pool and lid not in base_ids:
                        pool.append(lid)
                        lib[lid] = eq
                except CheckError:
                    nxt.append(eq)
            else:
                nxt.append(eq)
        if len(nxt) == len(pending):
            break
        pending = nxt
    return pool, pending


def build_world(seed: int = 0, lesion: bool = True, cache_dir: str | None = None,
                ledger: Ledger | None = None, conj_size: int = 6, task_size: int = 7,
                n_generated_tasks: int = 400, solver: SolverConfig | None = None) -> InductionWorld:
    """Build the lesion-suite world.

    Security: cache_dir is deprecated and ignored; no world pickle is read/written.
    Tasks: the 75 hand-written properties plus generated theorems that the base solver
    cannot prove but deep search with the textbook lemmas can. Splits are assigned by a
    seeded shuffle; the SEALED split is registered in the SealedStore and removed from the
    adapter. Candidate pool: conjectures (enumeration up to `conj_size`) proven and
    verified, excluding any statement that is a task or sealed."""
    key = f"world-s{seed}-l{int(lesion)}-c{conj_size}-t{task_size}-n{n_generated_tasks}.pkl"
    # SECURITY: legacy pickle world caches embed sealed task payloads and loading
    # them executes arbitrary Python code. Never deserialize research-writable
    # world caches, even when the filename matches a deterministic key.
    # cache_dir is retained only for API compatibility; no world is persisted.
    theory = Theory.default()
    ledger = ledger if ledger is not None else Ledger()
    store = LemmaStore(theory)
    textbook, _ = validated_properties(theory, TEXTBOOK)
    # textbook lemmas are proven (verified) so the lesion ground truth can use them
    tb_ids: list[str] = []
    pending = list(textbook)
    for _ in range(4):
        nxt = []
        for eq in pending:
            att = Prover(theory, store.verified_subset(tb_ids), fuel=20000, max_depth=2).prove(eq)
            if att.proved:
                lid = _lid(eq)
                store.verify(lid, eq, att.proof)
                tb_ids.append(lid)
            else:
                nxt.append(eq)
        pending = nxt
    props, _ = validated_properties(theory, PROPERTIES)
    # generated tasks: true, base-unprovable at solver budget, provable with textbook + deep search
    sv = solver or SolverConfig()
    gen = generate(theory, {}, themes=list(THEMES), max_size=task_size, seed=seed + 1000,
                   max_terms=12000, prune=True)
    tb_lib = store.verified_subset(tb_ids)
    task_eqs: dict[str, Equation] = {e.text(): e for e in props}
    rng = np.random.default_rng(seed)
    gen_eqs = [c.eq for c in gen]
    rng.shuffle(gen_eqs)
    added = 0
    for eq in gen_eqs:
        if added >= n_generated_tasks:
            break
        if eq.text() in task_eqs:
            continue
        base_ok = Prover(theory, {}, fuel=sv.fuel, max_depth=sv.max_depth, seed=1).prove(eq).proved
        if base_ok:
            continue
        deep = Prover(theory, tb_lib, fuel=5000, max_depth=2, seed=1).prove(eq)
        if not deep.proved:
            continue
        task_eqs[eq.text()] = eq
        added += 1
    all_tasks = list(task_eqs.values())
    order = rng.permutation(len(all_tasks))
    all_tasks = [all_tasks[i] for i in order]
    n = len(all_tasks)
    n_dev, n_sel, n_conf = int(0.30 * n), int(0.20 * n), int(0.20 * n)
    tasks = {"DEV": all_tasks[:n_dev], "SELECT": all_tasks[n_dev:n_dev + n_sel],
             "CONFIRM": all_tasks[n_dev + n_sel:n_dev + n_sel + n_conf]}
    sealed_tasks = all_tasks[n_dev + n_sel + n_conf:]
    sealed = SealedStore(ledger=ledger)
    sealed.seal("SEALED", [(e.text(), e) for e in sealed_tasks])
    base_ids = [] if lesion else list(tb_ids)
    # candidate pool from a separate enumeration, screened against every task and sealed item
    conj = generate(theory, {}, max_size=conj_size, seed=seed + 7, max_terms=3000, prune=True)
    # DEV tasks may be rediscovered as lemmas (that is research); held-out items may not
    exclude = {e.text() for e in tasks["SELECT"] + tasks["CONFIRM"] + sealed_tasks}
    conj_eqs = [c.eq for c in conj if c.eq.text() not in exclude]
    kept, rejected = sealed.screen([e.text() for e in conj_eqs])
    conj_eqs = [conj_eqs[i] for i in kept]
    pool, open_conj = discover_pool(theory, store, base_ids, conj_eqs, exclude)
    w = InductionWorld(name=f"induction-lesion-s{seed}" if lesion else f"induction-full-s{seed}",
                       theory=theory, store=store, base_ids=base_ids, pool=pool, tasks=tasks,
                       sealed=sealed, solver=sv,
                       meta={"textbook_ids": tb_ids, "n_tasks": n, "n_sealed": len(sealed_tasks),
                             "n_conjectures": len(conj), "n_open": len(open_conj),
                             "screened_out": len(rejected),
                             "open_conjectures": [e.text() for e in open_conj]})
    # Never write a world cache: it would expose SEALED tasks to the researcher.
    w.meta["world_cache_policy"] = "DISABLED_NO_PICKLE_NO_SEALED_CACHE"
    return w


def judge_sealed(world: InductionWorld, library_extra: list[str], seed: int, actor: str,
                 fuel: int | None = None, max_depth: int | None = None,
                 unsafe_dev: bool = False) -> dict:
    """Legacy DEV-only evaluation; never a trusted prospective sealed result."""
    lib = world._library(library_extra)
    counter = [0]

    def solver(eq):
        counter[0] += 1
        return world.solve(eq, lib, seed * 7919 + counter[0], fuel=fuel, max_depth=max_depth)

    return world.sealed.judge("SEALED", solver, actor=actor,
                              purpose="UNTRUSTED DEV ONLY", unsafe_dev_callback=unsafe_dev)


def build_world_from_suite(name: str, task_texts: list[str], seed: int, cache_dir: str | None = None,
                           ledger: Ledger | None = None, conj_size: int = 6,
                           split: tuple[float, float, float] = (0.20, 0.15, 0.15),
                           props_in_dev_select_confirm: bool = True,
                           solver: SolverConfig | None = None, cache_key: str | None = None,
                           screen_visible: bool = True) -> InductionWorld:
    """Round-2 world: its SEALED theorems come only from its own disjoint slice of the task
    pool (so sealed suites are independent across worlds); the hand-written properties, which
    every world shares, are used only for DEV, SELECT and CONFIRM.

    screen_visible (default True, round 2b on): no DEV/SELECT/CONFIRM item may be a sealed
    item or a near-duplicate of one; offending visible items are dropped and counted in
    meta["visible_screened"]. Round 2 ran with this off, and the independent review found
    sealed theorems in its visible splits; `screen_visible=False` exists only to reproduce
    that (superseded) run.
    cache_key: None derives a deterministic provenance key from every input.
    SECURITY: cache_dir is ignored and no cached world is read or written;
    old pickle caches are unsafe and can expose sealed tasks. Never trust them."""
    if cache_key is None:
        spec = {"v": "2b", "name": name, "tasks": list(task_texts), "seed": seed, "conj_size": conj_size,
                "split": list(split), "props": props_in_dev_select_confirm, "screen_visible": screen_visible,
                "solver": None if solver is None else vars(solver)}
        import json as _json
        digest = hashlib.sha256(_json.dumps(spec, sort_keys=True).encode()).hexdigest()[:16]
        cache_key = f"{name}-{digest}.pkl"
    key = cache_key
    # SECURITY: never load legacy .pkl world caches from research-writable
    # directories. Cache keys are not an authentication mechanism.
    theory = Theory.default()
    ledger = ledger if ledger is not None else Ledger()
    store = LemmaStore(theory)
    textbook, _ = validated_properties(theory, TEXTBOOK)
    tb_ids: list[str] = []
    pending = list(textbook)
    for _ in range(4):
        nxt = []
        for eq in pending:
            att = Prover(theory, store.verified_subset(tb_ids), fuel=20000, max_depth=2).prove(eq)
            if att.proved:
                lid = _lid(eq)
                store.verify(lid, eq, att.proof)
                tb_ids.append(lid)
            else:
                nxt.append(eq)
        pending = nxt
    P = theory.parser()
    rng = np.random.default_rng(seed)
    gen = [Equation(*P.parse_eq(t)) for t in task_texts]
    order = rng.permutation(len(gen))
    gen = [gen[i] for i in order]
    n = len(gen)
    a, b, c = (int(f * n) for f in split)
    tasks = {"DEV": gen[:a], "SELECT": gen[a:a + b], "CONFIRM": gen[a + b:a + b + c]}
    sealed_tasks = gen[a + b + c:]
    if props_in_dev_select_confirm:
        props, _ = validated_properties(theory, PROPERTIES)
        props = [props[i] for i in rng.permutation(len(props))]
        k1, k2 = int(0.5 * len(props)), int(0.75 * len(props))
        tasks["DEV"] += props[:k1]
        tasks["SELECT"] += props[k1:k2]
        tasks["CONFIRM"] += props[k2:]
    sealed = SealedStore(ledger=ledger)
    sealed.seal("SEALED", [(e.text(), e) for e in sealed_tasks])
    visible_screened = {}
    if screen_visible:
        for sp in ("DEV", "SELECT", "CONFIRM"):
            keep = [e for e in tasks[sp] if not sealed.near_duplicate(e.text())]
            visible_screened[sp] = len(tasks[sp]) - len(keep)
            tasks[sp] = keep
    conj = generate(theory, {}, max_size=conj_size, seed=seed + 7, max_terms=3000, prune=True)
    exclude = {e.text() for e in tasks["SELECT"] + tasks["CONFIRM"] + sealed_tasks}
    conj_eqs = [cj.eq for cj in conj if cj.eq.text() not in exclude]
    kept, rejected = sealed.screen([e.text() for e in conj_eqs])
    conj_eqs = [conj_eqs[i] for i in kept]
    pool, open_conj = discover_pool(theory, store, [], conj_eqs, exclude)
    w = InductionWorld(name=name, theory=theory, store=store, base_ids=[], pool=pool, tasks=tasks,
                       sealed=sealed, solver=solver or SolverConfig(),
                       meta={"textbook_ids": tb_ids, "n_tasks": n, "n_sealed": len(sealed_tasks),
                             "n_conjectures": len(conj), "n_open": len(open_conj), "screened_out": len(rejected),
                             "open_conjectures": [e.text() for e in open_conj], "round": 2,
                             "visible_screened": visible_screened, "cache_key": key})
    # Never write a world cache: it would expose SEALED tasks to the researcher.
    w.meta["world_cache_policy"] = "DISABLED_NO_PICKLE_NO_SEALED_CACHE"
    return w
