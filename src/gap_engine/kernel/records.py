"""Strict record types shared by the kernel and research code (pydantic v2)."""
from __future__ import annotations

import time
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=False)


class Candidate(Strict):
    id: str
    kind: Literal["lemma", "procedure", "guidance", "concept", "synthetic"]
    text: str                                  # normalised statement / description
    payload: Any = None                        # adapter-specific object (not serialised to ledger)
    provenance: list[str] = Field(default_factory=list)
    verified: bool = False                     # set only by a checker (kernel side)
    created: float = Field(default_factory=time.time)


class FingerprintRecord(Strict):
    candidate_id: str
    probe_suite: str
    touched: list[int]                         # probe-task indices whose behaviour changed
    effect: list[float] = Field(default_factory=list)
    cost: float


class DropoutDesignRecord(Strict):
    pool_ids: list[str]
    p: float
    blocks: list[tuple[str, str]] = Field(default_factory=list)
    q: float = 0.0
    runs: int
    seed_policy: Literal["common", "independent"]
    mode: Literal["plain", "blocked"]


class BundleEvidence(Strict):
    votes: int
    pvalue: float
    fdr_rejected: bool
    credit: Optional[tuple[float, float, float]] = None   # estimate, lower, upper


class Bundle(Strict):
    members: tuple[str, ...]
    kind: Literal["single", "pair", "triple", "batch"]
    evidence: BundleEvidence
    route: Literal["first_order", "stepping_stone"] = "first_order"


class GateDecision(Strict):
    gate: str
    bundle: tuple[str, ...]
    passed: bool
    stage: str
    reasons: list[str] = Field(default_factory=list)
    stats: dict[str, float] = Field(default_factory=dict)
    ledger_hash: str = ""


class HarvestRecord(Strict):
    text: str
    source_task: str
    kind: Literal["byproduct_lemma", "solved_task", "refutation", "fantasy", "trace"]
    kernel_verified: bool
    label: float = 1.0
    features: Optional[list[float]] = None


class DatasetManifest(Strict):
    name: str
    items: list[HarvestRecord]
    rejected_sealed: int = 0
    rejected_unverified: int = 0
    contamination_class: str = "DEV"
    hash: str = ""


class GenerationRecord(Strict):
    gen_id: str
    parent: Optional[str]
    kind: str
    train_items: int
    train_cost: float
    metrics: dict[str, float] = Field(default_factory=dict)
    promoted: bool = False
    reasons: list[str] = Field(default_factory=list)


class ProcedureContract(Strict):
    name: str
    signature: str
    precondition: str                    # human-readable decision list
    status: Literal["PROPOSED", "SURVIVED_N", "CERTIFIED", "RETIRED"] = "PROPOSED"
    adversarial_rounds: int = 0
    sealed_precision: Optional[float] = None
    sealed_recall: Optional[float] = None
    steps: list[str]
    stop_rules: list[str] = Field(default_factory=list)
    cost_per_call: float = 0.0
    dropout_credit: Optional[tuple[float, float, float]] = None
    provenance: list[str] = Field(default_factory=list)


class InterventionLog(Strict):
    step: int
    kind: str
    randomised: bool
    propensity: float
    cost: float
    reward: float
    cluster: str = ""


class StopRecord(Strict):
    line: str
    reason: str
    tried: list[str]
    final_estimates: dict[str, float]
    reversal_observation: str
    audited: bool = False
