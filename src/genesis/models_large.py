"""Task models of the DEV-only large triangle-free domain (B20_R94): hosts with up to 1023 vertices.

A separate module and separate models on purpose. Code written for the n <= 63 domains validates `models.GraphTask`
(whose `else` branches may assume the 4-cycle domain), so it can never receive a large task; and `models.py` is one of
the files every registry-v2 descriptor's identity hashes, so the large domain leaves every existing descriptor's
identity unchanged. No sealed receipt can name the domain (it is not in kernel.receipts.DOMAINS).
"""
from typing import Literal

from pydantic import Field, model_validator

from .models import StrictModel

LARGE_MAX_N = 1023


class LargeGraphTask(StrictModel):
    task_id: str = Field(min_length=1, max_length=128)
    domain: Literal['triangle_free_large_v1'] = 'triangle_free_large_v1'
    n: int = Field(ge=0, le=LARGE_MAX_N)
    edges: tuple[tuple[int, int], ...]
    family: str = Field(min_length=1, max_length=128)
    split: Literal['DEV'] = 'DEV'

    @model_validator(mode='after')
    def simple(self):
        if not (self.task_id.isprintable() and self.family.isprintable()):
            raise ValueError('task_id and family must be printable single-line labels')
        if any(not 0 <= u < v < self.n for u, v in self.edges):
            raise ValueError('edges must be ordered endpoints of a simple graph')
        if any(b <= a for a, b in zip(self.edges, self.edges[1:])):
            raise ValueError('edges must be sorted without duplicates')
        return self


class LargeCandidateGraph(StrictModel):
    """What a candidate solver may see of a large task: the host graph and its domain, nothing else."""
    domain: Literal['triangle_free_large_v1'] = 'triangle_free_large_v1'
    n: int = Field(ge=0, le=LARGE_MAX_N)
    edges: tuple[tuple[int, int], ...]

    @model_validator(mode='after')
    def simple(self):
        if any(not 0 <= u < v < self.n for u, v in self.edges):
            raise ValueError('edges must be ordered endpoints of a simple graph')
        if any(b <= a for a, b in zip(self.edges, self.edges[1:])):
            raise ValueError('edges must be sorted without duplicates')
        return self
