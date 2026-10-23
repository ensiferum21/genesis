"""Task models of the DEV-only weighted max-cut domain (B20_R101): public benchmark graphs (Gset) and generated ones.

A separate module, as `models_large`: code of the other domains never receives a max-cut task, and the files every
existing descriptor's identity hashes are unchanged. No sealed receipt can name the domain.

A task is a simple undirected graph with integer edge weights (Gset's are 1 or -1). The objective is the weight of a
cut: the sum of the weights of the edges whose endpoints lie on different sides.
"""
from typing import Literal

from pydantic import Field, model_validator

from .models import StrictModel

MAXCUT_MAX_N = 20000
MAX_ABS_WEIGHT = 10 ** 6


def _check_edges(n, edges):
    if any(not 0 <= u < v < n for u, v, _ in edges):
        raise ValueError('edges must be ordered endpoints of a simple graph')
    if any(type(w) is not int or w == 0 or abs(w) > MAX_ABS_WEIGHT for _, _, w in edges):
        raise ValueError('weights must be non-zero integers')
    if any((b[0], b[1]) <= (a[0], a[1]) for a, b in zip(edges, edges[1:])):
        raise ValueError('edges must be sorted without duplicates')


class MaxCutTask(StrictModel):
    task_id: str = Field(min_length=1, max_length=128)
    domain: Literal['maxcut_v1'] = 'maxcut_v1'
    n: int = Field(ge=1, le=MAXCUT_MAX_N)
    edges: tuple[tuple[int, int, int], ...]
    family: str = Field(min_length=1, max_length=128)
    split: Literal['DEV'] = 'DEV'

    @model_validator(mode='after')
    def simple(self):
        if not (self.task_id.isprintable() and self.family.isprintable()):
            raise ValueError('task_id and family must be printable single-line labels')
        _check_edges(self.n, self.edges)
        return self


class MaxCutCandidateView(StrictModel):
    """What a candidate solver may see of a max-cut task: the weighted graph and its domain, nothing else."""
    domain: Literal['maxcut_v1'] = 'maxcut_v1'
    n: int = Field(ge=1, le=MAXCUT_MAX_N)
    edges: tuple[tuple[int, int, int], ...]

    @model_validator(mode='after')
    def simple(self):
        _check_edges(self.n, self.edges)
        return self
