"""One entry point for both candidate registries (B20_R42; wiring built for review, opt-in).

Registry v1 (`genesis.candidates`) and registry v2 (`genesis.candidates_v2`, B20_R40) each refuse
the other's descriptors. The custodian and the CLI rebuild and run arms through this module. It
picks the registry by the descriptor's schema, and nothing else:
  * a v1 descriptor goes to registry v1 exactly as before, so every existing request, receipt and
    frozen descriptor id is unchanged;
  * a v2 descriptor goes to registry v2.

Exact baselines. `EXACT_BASELINE_KINDS` lists the v2 kinds that may stand as comparators beside
the conventional DSL baselines (`candidates.CONVENTIONAL_KINDS`). A study may use them only if its
calibration rule names them (`EXACT_BASELINES_BY_RULE`). The rules registered today name none,
except the DRAFT rule `e1-hard-v3-draft` (B20_R41). A comparator selection under an adopted rule
therefore behaves exactly as before.

`candidates_v2.py` still says "not wired". Its text is part of every v2 descriptor's identity
(by design), so it is left unchanged, and the wiring lives here instead.
"""
from . import candidates as V1
from . import candidates_v2 as V2

REGISTRIES = {V1.SCHEMA: V1, V2.SCHEMA: V2}
EXACT_BASELINE_KINDS = ('milp-highs-v1',)
EXACT_BASELINES_BY_RULE = {'e1-hard-v3-draft': ('milp-highs-v1',)}


def registry_of(desc):
    """The registry module for a descriptor, or None if its schema is neither registry's."""
    return REGISTRIES.get(desc.get('schema')) if isinstance(desc, dict) else None


def descriptor_problems(desc, *, expected_id=None, domain=None):
    reg = registry_of(desc)
    if reg is None:
        return ['not a candidate descriptor of a known registry']
    return reg.descriptor_problems(desc, expected_id=expected_id, domain=domain)


def run(task, desc, *, seed, expected_id=None, isolation='process', context=None):
    """Run an arm through its own registry. A context (statement evaluations) is a v1-only feature."""
    reg = registry_of(desc)
    if reg is V1:
        return V1.run(task, desc, seed=seed, expected_id=expected_id, isolation=isolation, context=context)
    if reg is V2 and context is None:
        return V2.run(task, desc, seed=seed, expected_id=expected_id, isolation=isolation)
    return {'status': 'REFUSED', 'reason': 'not a runnable descriptor of a known registry'
            if reg is None else 'registry v2 takes no execution context'}


def is_conventional(desc):
    """A fixed DSL baseline of registry v1 (the comparators E1, E1b and the adopted rules use)."""
    return registry_of(desc) is V1 and desc.get('kind') in V1.CONVENTIONAL_KINDS


def is_exact_baseline(desc, rule_name):
    """A registry-v2 exact baseline the named calibration rule allows as a comparator."""
    return (registry_of(desc) is V2 and desc.get('kind') in EXACT_BASELINE_KINDS
            and desc.get('kind') in EXACT_BASELINES_BY_RULE.get(rule_name, ()))
