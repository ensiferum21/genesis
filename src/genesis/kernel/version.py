"""Complete, content-derived SystemVersion identity (spec §2.1).

A comparison is only valid between executions whose SystemVersion matches;
changing any component (including the dependency lock or the verifier set)
creates a new version. Research code supplies the component values; the
kernel only defines and hashes the identity.
"""
from typing import Any
from pydantic import Field
from ..common import digest
from ..models import StrictModel


class SystemVersion(StrictModel):
    schema_version: str = 'genesis-system-version-v1'
    generation: int = Field(ge=-1)
    parent: str | None
    solver: dict[str, Any]
    tool_library: tuple[str, ...]
    memory_snapshot: str | None              # store event head at freeze
    curriculum_policy: dict[str, Any]
    research_policy: dict[str, Any]
    model_configuration: dict[str, Any] | None   # hosted model id/settings; None when no model is used
    cognitive_kernel: str                     # digest of the primitive contracts and MRDL limits
    verifier_set: dict[str, str]              # checker identity -> implementation hash
    resolved_config: dict[str, Any]
    dependency_lock: str                      # sha256 of requirements.lock
    environment_digest: str
    source: str                               # code identity

    def version_id(self):
        return digest(self.model_dump(mode='json'))
