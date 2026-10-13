"""Sealed statement panels for equational evaluations (handoff s13.3; B20_R7, B20R5-OPEN-1).

E2/E3 need evaluation statements generated on the custodian side, after the candidate is frozen,
with a defensible exposure history. This module is the generator the custodian calls at
registration:

* a preregistered **spec** (``genesis-statement-panel-spec-v1``): system, node ranges (one
  stratum per range), statements per range, maximum term size, and an inclusion rule from a
  closed set;
* a **private seed** drawn by the custodian (never the requester's), so the panel cannot be
  predicted from the request;
* **exposure screening** with the global partition builder (``learning.partitions``): every
  statement visible to research in the bound campaign export, every statement in the
  custodian's public manifest, and every statement already sealed or reserved at this custodian
  are registered first; candidates related to any of them (EXACT, ALPHA, INSTANCE: rejected;
  GENERALIZES: quarantined) never enter the panel; statements are distinct across strata;
* the **reference obligation**: every statement is decided true in the variety
  (``equational.holds``: the two-element algebra, or the free group). That is ground truth for
  validity, not a proof; a proof is what the arms must produce;
* the **inclusion rule** (closed set, preregistered):
    ``valid-screened``             every valid, admitted statement;
    ``valid-screened-nontrivial``  additionally excludes statements E proves from the axioms
                                   alone within ``trivial_limit_s`` (an evaluator-side
                                   calibration step, accounted separately; no arm's result
                                   is consulted);
* a **generation record** with every count (drawn, rejected by relation, quarantined, excluded
  as trivial, accepted) and the residual pretraining-exposure note; if a stratum cannot be
  filled the result is ``INSUFFICIENT_DISTINCT_MATERIAL`` and nothing is registered.

The panel and its record stay in the custodian's private root; the anchor carries a salted
commitment. A modern model may know small Boolean or group identities from textbooks even
though Genesis never saw them: that residual risk is recorded, not screened.
"""
from ..common import digest
from . import equational as Q
from . import partitions as P

SPEC_SCHEMA = 'genesis-statement-panel-spec-v1'
PANEL_SCHEMA = 'genesis-statement-panel-v1'
RECORD_SCHEMA = 'genesis-statement-panel-record-v1'
INCLUSION = ('valid-screened', 'valid-screened-nontrivial')
SPEC_FIELDS = {'schema', 'system', 'ranges', 'per_range', 'max_term', 'inclusion', 'trivial_limit_s'}
RESIDUAL_PRETRAINING = ('small identities of Boolean algebras, rings and groups are textbook material; a pretrained '
                        'model or the operator may know a panel statement although Genesis never saw it; no '
                        'literature search was performed and none is claimed')
MAX_TASKS = 400


class PanelError(Exception):
    def __init__(self, code, **detail):
        self.code, self.detail = code, detail
        super().__init__(code)


def statement_domain(system):
    return f'eq_{system}_v1'


def system_of_domain(domain):
    if isinstance(domain, str) and domain.startswith('eq_') and domain.endswith('_v1'):
        s = domain[3:-3]
        if s in Q.SYSTEMS:
            return s
    return None


def spec_problems(spec, *, domain=None, task_count=None):
    """Why ``spec`` is not a valid preregistered panel spec (empty: valid)."""
    if not isinstance(spec, dict) or set(spec) != SPEC_FIELDS or spec.get('schema') != SPEC_SCHEMA:
        return ['panel spec schema']
    out = []
    if spec['system'] not in Q.SYSTEMS:
        out.append('unknown system')
    elif domain is not None and statement_domain(spec['system']) != domain:
        out.append('panel system differs from the request domain')
    r = spec['ranges']
    if not isinstance(r, list) or not r or len(r) > 8 or any(
            not isinstance(x, list) or len(x) != 2 or any(type(v) is not int for v in x) or not 2 <= x[0] <= x[1] <= 24
            for x in r) or len({tuple(x) for x in r}) != len(r):
        out.append('ranges must be distinct [lo, hi] integer pairs with 2 <= lo <= hi <= 24')
    if type(spec['per_range']) is not int or not 1 <= spec['per_range'] <= 200:
        out.append('per_range must be an integer in 1..200')
    if type(spec['max_term']) is not int or not 2 <= spec['max_term'] <= 6:
        out.append('max_term must be an integer in 2..6')
    if spec['inclusion'] not in INCLUSION:
        out.append(f'inclusion must be one of {INCLUSION}')
    elif spec['inclusion'] == 'valid-screened' and spec['trivial_limit_s'] is not None:
        out.append('trivial_limit_s is only for the nontrivial inclusion rule')
    elif spec['inclusion'] == 'valid-screened-nontrivial' and (
            type(spec['trivial_limit_s']) is not int or not 1 <= spec['trivial_limit_s'] <= 5):
        out.append('trivial_limit_s must be an integer number of seconds in 1..5')
    if not out:
        total = spec['per_range'] * len(r)
        if total > MAX_TASKS:
            out.append(f'at most {MAX_TASKS} statements per panel')
        if task_count is not None and task_count != total:
            out.append('task_count differs from per_range x number of ranges')
    return out


def stratum(rng):
    return f'nodes-{rng[0]}-{rng[1]}'


def _trivial(system, eq, seconds, prover):
    r = prover(Q.axioms(system), Q.closed(eq), seconds=seconds)
    return r['status'] == 'THEOREM'


def generate(spec, *, private_seed, exposure, prover=None):
    """Draw the sealed panel. ``exposure``: iterable of (system, equation tuple, route) for every
    statement visible to research or already sealed. Returns (panel, record); raises PanelError
    INSUFFICIENT_DISTINCT_MATERIAL when a stratum cannot be filled under the frozen policy."""
    problems = spec_problems(spec)
    if problems:
        raise PanelError('INVALID_SPEC', problems=problems)
    system = spec['system']
    decider = Q.SYSTEMS[system]['decider']
    excluded = {'trivial': 0, 'not_valid': 0}
    trivial_cpu = {'attempts': 0}
    if spec['inclusion'] == 'valid-screened-nontrivial' and prover is None:
        from ..verification.eprover import prove as prover

    def sampler(unit, system_, rng):
        lo, hi = (int(x) for x in unit.split('-')[1:3])
        inner = P.equational_sampler(min_total=lo, max_total=hi, max_term=spec['max_term'])(unit, system_, rng)
        for eq in inner:
            if not Q.holds(eq, decider):                 # the reference obligation (never expected to fail)
                excluded['not_valid'] += 1
                continue
            if spec['inclusion'] == 'valid-screened-nontrivial':
                trivial_cpu['attempts'] += 1
                if _trivial(system_, eq, spec['trivial_limit_s'], prover):
                    excluded['trivial'] += 1
                    continue
            yield eq
    visible = [(s, e, 'custodian-exposure', route) for s, e, route in exposure]
    units = [(f'range-{lo}-{hi}', system) for lo, hi in spec['ranges']]
    try:
        manifest = P.build_partition(study=f'sealed-statements:{digest(spec)[:16]}', study_seed=private_seed,
                                     visible=visible, units=units, sampler=sampler, count=spec['per_range'])
    except P.PartitionError as exc:
        raise PanelError(exc.code, **getattr(exc, 'detail', {})) from None
    panel, n = [], 0
    for (lo, hi), (unit, _) in zip(spec['ranges'], units):
        for a in manifest['units'][unit]['accepted']:
            panel.append({'task_id': f'S{n:04d}', 'statement': a['text'], 'stratum': stratum((lo, hi)),
                          'structural_sha256': a['structural_sha256']})
            n += 1
    body = {'schema': PANEL_SCHEMA, 'system': system, 'domain': statement_domain(system), 'statements': panel}
    panel_doc = dict(body, panel_sha256=digest(body))
    record = {'schema': RECORD_SCHEMA, 'spec': spec, 'spec_sha256': digest(spec), 'partition_id': manifest['partition_id'],
              'exposure_root': manifest['exposure']['root'], 'exposure_items': manifest['exposure']['items'],
              'policy': manifest['policy'], 'per_stratum': {
                  stratum(r): {'requested': manifest['units'][u]['requested'], 'draws': manifest['units'][u]['draws'],
                               'accepted': len(manifest['units'][u]['accepted']),
                               'rejected_counts': manifest['units'][u]['rejected_counts'],
                               'quarantined': len(manifest['units'][u]['quarantined'])}
                  for r, (u, _) in zip(spec['ranges'], units)},
              'excluded': dict(excluded), 'trivial_checks': trivial_cpu['attempts'],
              'reference_obligation': 'every statement decided true in its variety (equational.holds)',
              'residual_limits': list(P.RESIDUAL_LIMITS), 'residual_pretraining_exposure': RESIDUAL_PRETRAINING,
              'panel_sha256': panel_doc['panel_sha256'], 'statements': len(panel)}
    return panel_doc, record


def panel_problems(panel_doc):
    """Structural check of a stored panel (the custodian re-checks before evaluation)."""
    if not isinstance(panel_doc, dict) or panel_doc.get('schema') != PANEL_SCHEMA:
        return ['panel schema']
    body = {k: v for k, v in panel_doc.items() if k != 'panel_sha256'}
    out = []
    if digest(body) != panel_doc.get('panel_sha256'):
        out.append('panel hash')
    system = panel_doc.get('system')
    if system not in Q.SYSTEMS or panel_doc.get('domain') != statement_domain(system):
        return out + ['panel system/domain']
    decider = Q.SYSTEMS[system]['decider']
    ids = [s['task_id'] for s in panel_doc['statements']]
    if len(set(ids)) != len(ids):
        out.append('duplicate task ids')
    for s in panel_doc['statements']:
        try:
            if not Q.holds(eq_of(s['statement']), decider):
                out.append(f'{s["task_id"]} is not valid in the variety')
        except Exception:
            out.append(f'{s["task_id"]} is malformed')
    return out


def eq_of(text):
    from ..fol import parse
    f = parse(text)
    while f[0] == 'all':
        f = f[2]
    if f[0] != 'eq':
        raise ValueError('not an equation')
    return Q.canon((f[1], f[2]))


__all__ = ['SPEC_SCHEMA', 'PANEL_SCHEMA', 'INCLUSION', 'PanelError', 'statement_domain', 'system_of_domain',
           'spec_problems', 'generate', 'panel_problems', 'eq_of', 'stratum']
