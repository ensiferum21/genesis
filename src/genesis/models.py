"""Versioned trust-boundary records; unknown fields and coercion are forbidden."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, frozen=True)


class GraphTask(StrictModel):
    task_id: str = Field(min_length=1, max_length=128)
    domain: Literal['c4_host_v2', 'triangle_free_host_v1'] = 'c4_host_v2'
    n: int = Field(ge=0, le=63)
    edges: tuple[tuple[int, int], ...]
    family: str = Field(min_length=1, max_length=128)
    split: Literal['DEV','SELECT','CONFIRM','FUTURE'] = 'DEV'

    @model_validator(mode='after')
    def simple(self):
        if not (self.task_id.isprintable() and self.family.isprintable()):
            raise ValueError('task_id and family must be printable single-line labels')
        if any(not 0 <= u < v < self.n for u,v in self.edges):
            raise ValueError('edges must be ordered endpoints of a simple graph')
        if tuple(sorted(set(self.edges))) != self.edges:
            raise ValueError('edges must be sorted without duplicates')
        return self


class CandidateGraph(StrictModel):
    """What a candidate solver may see of a task (W05): the host graph and its domain.
    No task identifier, family, split label, reference optimum or certificate."""
    domain: Literal['c4_host_v2', 'triangle_free_host_v1'] = 'c4_host_v2'
    n: int = Field(ge=0, le=63)
    edges: tuple[tuple[int, int], ...]

    @model_validator(mode='after')
    def simple(self):
        if any(not 0 <= u < v < self.n for u,v in self.edges):
            raise ValueError('edges must be ordered endpoints of a simple graph')
        if tuple(sorted(set(self.edges))) != self.edges:
            raise ValueError('edges must be sorted without duplicates')
        return self


class SolverProgram(StrictModel):
    schema_version: Literal['graph-priority-v1'] = 'graph-priority-v1'
    # linear combination of degree sum, product, codegree and forbidden-motif incidence
    weights: tuple[int,int,int,int] = (0,0,0,0)
    rounds: int = Field(default=4, ge=1, le=32)
    exchange: bool = False
    componentwise: bool = False

    @model_validator(mode='after')
    def bounds(self):
        if any(abs(x)>8 for x in self.weights):
            raise ValueError('coefficient outside fixed grammar')
        return self


class Limits(StrictModel):
    queries: int = Field(default=60, ge=1, le=100000)
    wall_seconds: int = Field(default=120, ge=1, le=600)
    cpu_seconds: int = Field(default=1, ge=1, le=120)
    memory_mib: int = Field(default=2048, ge=64, le=8192)
    output_bytes: int = Field(default=8388608, ge=4096, le=8388608)


class Config(StrictModel):
    schema_version: Literal['genesis-campaign-v1'] = 'genesis-campaign-v1'
    profile: Literal['offline_engineering','external_replication'] = 'offline_engineering'
    seed: int = 20261010
    domain: Literal['c4_host_v2','triangle_free_host_v1'] = 'c4_host_v2'
    generations: int = Field(default=3, ge=1, le=8)
    tasks_per_panel: int = Field(default=12, ge=2, le=100)
    proposals_per_epoch: int = Field(default=8, ge=2, le=8)
    research_trials: int = Field(default=96, ge=8, le=5000)
    max_active_worlds: int = Field(default=8, ge=1, le=8)
    max_exact_edges: int = Field(default=18, ge=1, le=24)
    limits: Limits = Field(default_factory=Limits)
    paid_api_budget: int = Field(default=0, ge=0, le=0)
    network: Literal[False] = False
    concurrency: Literal[1] = 1


class Evidence(StrictModel):
    math: Literal['UNCHECKED','EXECUTABLE','WITNESS_VALID','FINITE_CERTIFIED',
                  'THEOREM_CHECKED','OPTIMALITY_CHECKED','REJECTED','UNSETTLED','CHECKER_ERROR'] = 'UNCHECKED'
    utility: Literal['NOT_TESTED','DEV_ONLY','CONFIRMED_SAME_DOMAIN','CONFIRMED_TRANSFER'] = 'NOT_TESTED'
    causality: Literal['NOT_TESTED','CORRELATED','ABLATION_SUPPORTED','PLACEBO_CONTROLLED'] = 'NOT_TESTED'
    improver: Literal['NOT_TESTED','SAME_DOMAIN_CONFIRMED','CROSS_DOMAIN_CONFIRMED','MULTIGEN_CONFIRMED'] = 'NOT_TESTED'
    novelty: Literal['UNKNOWN','REDISCOVERY','VARIANT','CANDIDATE_NOVEL','EXTERNALLY_CHECKED_NOVEL'] = 'UNKNOWN'
    replication: Literal['NONE','INTERNAL_INDEPENDENT','EXTERNAL_REPRODUCTION'] = 'NONE'
    effects: tuple[str,...] = ()
    assumptions: tuple[str,...] = ()
    references: tuple[str,...] = ()


class BoundState(StrictModel):
    lower: int = Field(ge=0)
    upper: int = Field(ge=0)
    lower_check: str = Field(min_length=64,max_length=64)
    upper_check: str = Field(min_length=64,max_length=64)
    scope: str

    @model_validator(mode='after')
    def order(self):
        if self.lower>self.upper:
            raise ValueError('contradictory certificates')
        return self

    @property
    def gap(self):
        return self.upper-self.lower


class Modification(StrictModel):
    parent: str
    child: str
    hypothesis: str
    predicted_effect: str
    falsifier: str
    rollback: str
    component: Literal['solver_program','research_policy','macro']
    authority_delta: Literal[0] = 0
    evidence: Evidence = Field(default_factory=Evidence)


class Capability(StrictModel):
    name: str
    program: SolverProgram
    domains: tuple[str,...]
    preconditions: tuple[str,...]
    dependencies: tuple[str,...] = ()
    evidence: Evidence
    maintenance_queries: int = Field(ge=0)
    status: Literal['QUARANTINED','DEV_RETAINED','CONFIRMED','RETIRED'] = 'QUARANTINED'
    rollback: str | None = None
