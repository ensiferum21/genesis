"""Training backends for proposer generations.

`SklearnRankerBackend` is what runs in this repository (u3.proposer_model). The
`LLMFineTuneBackend` contract is the hook for an open-weights prover/proposer fine-tune
(parameter-efficient, on a GPU). It must consume only a kernel-admitted DatasetManifest
and return a new weights reference; G1 decides promotion. It is deliberately not
implemented here (no GPU or model weights in this workspace) and fails loudly.
"""
from __future__ import annotations

from typing import Protocol

from ..kernel.records import DatasetManifest


class TrainingBackend(Protocol):
    def train(self, manifest: DatasetManifest, base: str, budget_units: float) -> str:
        """Return an identifier of the new weights (a generation)."""
        ...


class LLMFineTuneBackend:
    def __init__(self, base_model: str, output_dir: str):
        self.base_model = base_model
        self.output_dir = output_dir

    def train(self, manifest: DatasetManifest, base: str, budget_units: float) -> str:
        if not manifest.hash:
            raise ValueError("manifest was not admitted by the kernel (missing hash)")
        raise NotImplementedError(
            "LLM fine-tuning needs a GPU and model weights; wire your trainer here. "
            "Inputs: manifest.items (kernel-verified, sealed-screened), base weights id, budget.")
