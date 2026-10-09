"""Trace capture and compression into procedures.

Exploration runs random well-typed programs on training tasks and keeps the traces of
successful episodes. Compression then scores every contiguous sub-sequence by how much it
would shorten the successful traces if it were a single new operation
(gain = occurrences x (length - 1), the sequence analogue of Stitch's compression
objective) and keeps the best well-typed ones as candidate procedures.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

import numpy as np

from .procedures import random_program, run, well_typed


@dataclass
class ExplorationLog:
    successes: list[tuple[str, ...]] = field(default_factory=list)
    attempts: int = 0
    solved_tasks: set = field(default_factory=set)


def explore(make_ctx, tasks, rng: np.random.Generator, episodes_per_task: int = 4,
            max_cost: float = 2.0) -> ExplorationLog:
    log = ExplorationLog()
    for ti, goal in enumerate(tasks):
        for _ in range(episodes_per_task):
            prog = random_program(rng)
            ctx = make_ctx()
            res = run(prog, ctx, goal, max_cost=max_cost)
            log.attempts += 1
            if res.solved and len(res.trace) > 1:
                log.successes.append(tuple(res.trace))
                log.solved_tasks.add(ti)
                break
    return log


def compress(traces: list[tuple[str, ...]], top: int = 5, min_len: int = 2, max_len: int = 6) -> list[tuple[tuple[str, ...], int]]:
    gain: Counter = Counter()
    for tr in traces:
        seen = set()
        for L in range(min_len, min(max_len, len(tr)) + 1):
            for i in range(len(tr) - L + 1):
                sub = tr[i:i + L]
                if sub not in seen:
                    seen.add(sub)
                    gain[sub] += L - 1
    ranked = [(s, g) for s, g in gain.most_common() if well_typed(s) and s[0] == "attempt"]
    out: list[tuple[tuple[str, ...], int]] = []
    for s, g in ranked:
        if any(s == o[0] for o in out):
            continue
        out.append((s, g))
        if len(out) >= top:
            break
    return out
