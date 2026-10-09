"""Large task suites of lemma-dependent theorems, with diversity control.

A task enters the pool only if it is (a) true under random testing, (b) NOT provable by the
solver at its normal budget with an empty library, and (c) provable by deep search with the
textbook lemmas, so every task has an achievable, lemma-dependent solution. Near-duplicates
(token-shingle Jaccard >= `dup_jaccard`) are dropped and each theme is capped so no single
function family dominates. The pool is saved as plain text and partitioned into DISJOINT
per-world suites, so sealed theorems are independent across worlds.
"""
from __future__ import annotations

import json
import multiprocessing as mp
import os
import time

import numpy as np

from ...kernel.sealed import jaccard, shingles
from .checker import LemmaStore
from .conjecture import THEMES, generate
from .prover import Prover
from .tasks import PROPERTIES, TEXTBOOK, validated_properties
from .theory import Equation, Theory

TASK_THEMES = {
    "rev_len": ["rev", "len", "app", "plus", "Nil", "Cons"],
    "qrev_rev": ["qrev", "rev", "app", "len", "Nil"],
    "sum_rev": ["sum", "rev", "app", "plus"],
    "mult_plus": ["mult", "plus", "S", "Z"],
    "double_plus": ["double", "plus", "S"],
    "half_double": ["half", "double", "plus"],
    "takedrop": ["take", "drop", "len", "app", "min", "minus"],
    "rot": ["rot", "len", "app", "rev"],
    "replicate": ["replicate", "len", "sum", "app", "mult"],
    "incall": ["incall", "sum", "len", "app", "rev", "plus"],
    "maxmin": ["max", "min", "plus", "minus"],
    "minus_plus": ["minus", "plus", "S", "Z"],
    "app_len_sum": ["app", "len", "sum", "plus", "Cons", "Nil"],
    "rev_qrev_len": ["rev", "qrev", "len", "plus"],
    "sum_incall_len": ["sum", "incall", "len", "plus", "app"],
    "mult_sum_replicate": ["mult", "sum", "replicate", "plus"],
    "takedrop_rev": ["take", "drop", "rev", "len", "app"],
    "max_plus_double": ["max", "min", "double", "plus"],
}


def textbook_library(theory: Theory) -> dict:
    from .adapter import _lid
    tb, _ = validated_properties(theory, TEXTBOOK)
    store = LemmaStore(theory)
    ids: list[str] = []
    pending = list(tb)
    for _ in range(4):
        nxt = []
        for eq in pending:
            a = Prover(theory, store.verified_subset(ids), fuel=20000).prove(eq)
            if a.proved:
                lid = _lid(eq)
                store.verify(lid, eq, a.proof)
                ids.append(lid)
            else:
                nxt.append(eq)
        pending = nxt
    return store.verified_subset(ids)


def _theme_worker(args):
    name, syms, size, max_terms, seed, solver_fuel = args
    th = Theory.default()
    THEMES[name] = syms
    tblib = textbook_library(th)
    out = []
    for c in generate(th, {}, themes=[name], max_size=size, seed=seed, max_terms=max_terms, prune=True):
        if Prover(th, {}, fuel=solver_fuel, max_depth=2, seed=1).prove(c.eq).proved:
            continue
        if Prover(th, tblib, fuel=5000, max_depth=2, seed=1).prove(c.eq).proved:
            out.append(c.eq.text())
    return name, out


def build_task_pool(path: str, size: int = 7, max_terms: int = 12000, seed: int = 11, per_theme_cap: int = 220,
                    dup_jaccard: float = 0.7, theme_timeout: float = 420.0, workers: int = 2,
                    solver_fuel: int = 150) -> list[str]:
    """Generate (or load) the diverse task pool. Each theme runs in its own process with a
    timeout; a theme that times out contributes nothing (and is reported)."""
    params = {"size": size, "max_terms": max_terms, "seed": seed, "cap": per_theme_cap, "dup_jaccard": dup_jaccard}
    if os.path.exists(path):
        with open(path) as fh:
            doc = json.load(fh)
        recorded = {k: doc.get("params", {}).get(k) for k in params}
        if recorded != params:
            raise ValueError(f"cached pool {path} was built with {recorded}, not {params}; "
                             "use another path or delete the cache")
        return doc["tasks"]
    ctx = mp.get_context("fork")
    results: dict[str, list[str]] = {}
    report: dict[str, str] = {}
    pending = [(n, s, size, max_terms, seed, solver_fuel) for n, s in TASK_THEMES.items()]
    running: list = []
    t0 = time.time()
    while pending or running:
        while pending and len(running) < workers:
            job = pending.pop(0)
            q = ctx.Queue()
            p = ctx.Process(target=lambda j=job, q=q: q.put(_theme_worker(j)))
            p.start()
            running.append((job[0], p, q, time.time()))
        time.sleep(1.0)
        still = []
        for name, p, q, start in running:
            if not q.empty():
                n, out = q.get()
                results[n] = out
                report[n] = f"{len(out)} tasks in {time.time() - start:.0f}s"
                p.join(timeout=5)
            elif time.time() - start > theme_timeout:
                p.terminate()
                p.join(timeout=5)
                q.close()
                report[name] = f"timed out after {theme_timeout:.0f}s"
            elif not p.is_alive() and q.empty():
                report[name] = "worker exited without a result"
            else:
                still.append((name, p, q, start))
        running = still
    # diversity: near-duplicate removal (global) and a per-theme cap
    rng = np.random.default_rng(seed)
    kept: list[str] = []
    kept_sh: list[set] = []
    for name in TASK_THEMES:
        texts = list(results.get(name, []))
        rng.shuffle(texts)
        n_theme = 0
        for t in texts:
            if n_theme >= per_theme_cap:
                break
            sh = shingles(t)
            if any(jaccard(sh, k) >= dup_jaccard for k in kept_sh):
                continue
            kept.append(t)
            kept_sh.append(sh)
            n_theme += 1
        report[name] += f"; kept {n_theme}"
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as fh:
        json.dump({"tasks": kept, "report": report, "seconds": round(time.time() - t0),
                   "params": params,
                   # recorded for reproducibility; wall-clock timeouts make the pool machine-dependent,
                   # so experiments pin the pool file's sha256 in their preregistration
                   "build": {"theme_timeout": theme_timeout, "workers": workers, "solver_fuel": solver_fuel,
                             "themes": TASK_THEMES}}, fh, indent=1)
    return kept


def exclude_handwritten(tasks: list[str], dup_jaccard: float = 0.8) -> tuple[list[str], list[str]]:
    """Drop pool tasks that equal or nearly equal (token-shingle Jaccard >= dup_jaccard) a
    hand-written property or textbook lemma. Those statements are shared by every world's
    DEV/SELECT/CONFIRM splits, so a pool task matching one could otherwise land in a world's
    SEALED suite while also being research-visible (the round-2 leak)."""
    hand = list(PROPERTIES) + list(TEXTBOOK)
    hand_sh = [shingles(h) for h in hand]
    hand_set = set(hand)
    kept, removed = [], []
    for t in tasks:
        sh = shingles(t)
        if t in hand_set or any(jaccard(sh, h) >= dup_jaccard for h in hand_sh):
            removed.append(t)
        else:
            kept.append(t)
    return kept, removed


def partition(tasks: list[str], n_worlds: int, seed: int) -> list[list[str]]:
    rng = np.random.default_rng(seed)
    idx = rng.permutation(len(tasks))
    return [[tasks[i] for i in idx[k::n_worlds]] for k in range(n_worlds)]


def partition_weighted(tasks: list[str], weights: list[float], seed: int) -> list[list[str]]:
    """Disjoint partition with the given relative sizes (e.g. a small calibration world)."""
    rng = np.random.default_rng(seed)
    idx = rng.permutation(len(tasks))
    w = np.asarray(weights, float) / np.sum(weights)
    cuts = np.round(np.cumsum(w) * len(tasks)).astype(int)
    out, start = [], 0
    for c in cuts:
        out.append([tasks[i] for i in idx[start:c]])
        start = c
    return out
