"""U1 stepping-stone archive.

Candidates are kept by *what they change*, not by whether they win. The archive is a
MAP-Elites grid over two fingerprint descriptors (breadth: how many probe tasks a
candidate touches; focus: which task cluster most of its touches fall in). Each cell keeps
its most novel member, where novelty is the mean Jaccard distance to the k nearest
fingerprints already archived (novelty search). Members are sampled into the dropout pool
through the capped stepping-stone route.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


def jaccard_distance(a: np.ndarray, b: np.ndarray) -> float:
    u = np.logical_or(a, b).sum()
    return 0.0 if u == 0 else 1.0 - np.logical_and(a, b).sum() / u


@dataclass
class SteppingStoneArchive:
    n_clusters: int
    breadth_bins: tuple[int, ...] = (1, 2, 4, 8, 16, 1 << 30)
    k_novelty: int = 5
    cells: dict[tuple[int, int], tuple[str, np.ndarray, float]] = field(default_factory=dict)
    cap: int = 200

    def descriptor(self, fp: np.ndarray, cluster_of_task: np.ndarray) -> tuple[int, int]:
        breadth = int(fp.sum())
        b = int(np.searchsorted(self.breadth_bins, breadth, side="left"))
        if breadth == 0:
            return (0, -1)
        focus = int(np.bincount(cluster_of_task[fp], minlength=self.n_clusters).argmax())
        return (b, focus)

    def novelty(self, fp: np.ndarray) -> float:
        if not self.cells:
            return 1.0
        d = sorted(jaccard_distance(fp, f) for _, f, _ in self.cells.values())
        return float(np.mean(d[: self.k_novelty]))

    def offer(self, cid: str, fp: np.ndarray, cluster_of_task: np.ndarray) -> bool:
        """Insert if the cell is empty or the newcomer is more novel. Returns True if kept."""
        cell = self.descriptor(fp, cluster_of_task)
        if cell[1] < 0:
            return False                               # touches nothing: not a stepping stone
        nov = self.novelty(fp)
        cur = self.cells.get(cell)
        if cur is None or nov > cur[2]:
            if cur is None and len(self.cells) >= self.cap:
                return False
            self.cells[cell] = (cid, fp.copy(), nov)
            return True
        return False

    def members(self) -> list[str]:
        return [cid for cid, _, _ in self.cells.values()]

    def sample(self, k: int, rng: np.random.Generator) -> list[str]:
        m = self.members()
        if len(m) <= k:
            return m
        return list(rng.choice(m, size=k, replace=False))
