"""Research-lineage records and their pure validator (handoff H08, roadmap W21, B14-OPEN-3).

A *generation transition* claims that a research run, started from a frozen parent
SystemVersion, produced a frozen child that was then evaluated. Counting transitions
(GV5) is only meaningful if the chain cannot be manufactured. This module defines the
records and checks them; it mutates nothing and creates no claim. The custodian keeps
refusing ``sealed_improver_evaluation`` and ``sealed_generation_evaluation`` until an
export carries these records and this validator is wired into request checking.

Records
  * versions:  {version_id: SystemVersion dict}; the id must be the content digest.
  * frozen_at: {version_id: event sequence number of its freeze}.
  * runs:      {run_id: research run} (``genesis-research-run-v1``): parent version, policy
               identity, permitted inputs (exposure root / partition id), seed, budget and
               account hashes, the all-attempt ledger, every candidate (version or program
               identity, score, producing attempt), the declared selection rule and its
               result, declared interventions, start and end event sequence numbers.
  * transitions: [``genesis-transition-v1``]: index, from/to versions, research run, the
               declared changed components, panel, receipt, claim and plan identities, the
               receipt event and the decision (ACCEPTED, REJECTED, INCONCLUSIVE, INVALID,
               DEV_BRANCH).

Checks (stable problem codes; see ``CODES``) cover the handoff's list: parent exists and
was frozen before the run; child's parent and changed components match the manifests;
label-only changes do not count; selection follows the declared rule and every candidate
is in the attempt ledger; panels and receipts are not reused; one transition cannot be
counted under several wrapper ids; indices and edges form one acyclic, unambiguous chain;
no undeclared edit (source/environment) and no undeclared or manual intervention;
chronology parent-freeze < run < child-freeze < receipt; one budget account per run;
revocation is inherited by every later transition.
"""
from .common import digest

SCHEMA_RUN = 'genesis-research-run-v1'
SCHEMA_TRANSITION = 'genesis-transition-v1'
DECISIONS = ('ACCEPTED', 'REJECTED', 'INCONCLUSIVE', 'INVALID', 'DEV_BRANCH')
LABELS = frozenset({'generation', 'parent', 'memory_snapshot'})
ENVIRONMENT = frozenset({'dependency_lock', 'environment_digest', 'verifier_set'})
SELECTION_RULES = ('max_score_then_lowest_identity',)
CODES = ('VERSION_MISSING', 'VERSION_ID_MISMATCH', 'NOT_FROZEN', 'PARENT_MISMATCH', 'GENERATION_INDEX',
         'LABEL_ONLY_CHANGE', 'DECLARED_CHANGES_MISMATCH', 'UNDECLARED_ENVIRONMENT_CHANGE', 'RUN_MISSING',
         'FOREIGN_RUN', 'SELECTION_RULE_UNKNOWN', 'SELECTION_UNVERIFIABLE', 'SELECTION_RULE_VIOLATED',
         'SELECTED_MISMATCH', 'LEDGER_INCOMPLETE', 'MANUAL_INTERVENTION', 'BUDGET_REUSED', 'PANEL_REUSED',
         'RECEIPT_REUSED', 'DUPLICATE_TRANSITION', 'TRANSITION_ID_MISMATCH', 'CHAIN_ORDER', 'AMBIGUOUS_PARENT',
         'CYCLE', 'CHRONOLOGY', 'REVOKED_ANCESTOR', 'UNKNOWN_DECISION', 'MALFORMED')


def _p(code, **kw):
    assert code in CODES, code
    return dict({'code': code}, **kw)


def version_diff(a, b):
    """Components that differ between two SystemVersion dicts."""
    return sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))


def substantive(diff):
    """Changes that can carry a new capability (not labels, not the environment)."""
    return sorted(set(diff) - LABELS - ENVIRONMENT)


def transition_record(**fields):
    body = dict(fields, schema=SCHEMA_TRANSITION)
    return dict(body, transition_id=digest(body))


def run_record(**fields):
    body = dict(fields, schema=SCHEMA_RUN)
    return dict(body, run_id=digest(body))


def _select(rule, candidates):
    if rule == 'max_score_then_lowest_identity':
        if any(not isinstance(c.get('score'), (int, float)) for c in candidates):
            return None
        best = max(candidates, key=lambda c: (c['score'], [-ord(ch) for ch in c['identity']]))
        return best['identity']
    raise KeyError(rule)


def _run_problems(run, rid):
    out = []
    if run.get('schema') != SCHEMA_RUN or run.get('run_id') != rid or \
            digest({k: v for k, v in run.items() if k != 'run_id'}) != rid:
        out.append(_p('MALFORMED', run=rid, detail='run record identity'))
    sel = run.get('selection') or {}
    cands = run.get('candidates') or []
    if sel.get('rule') not in SELECTION_RULES:
        out.append(_p('SELECTION_RULE_UNKNOWN', run=rid))
    elif not cands:
        out.append(_p('SELECTION_UNVERIFIABLE', run=rid, detail='no candidates recorded'))
    else:
        chosen = _select(sel['rule'], cands)
        if chosen is None:
            out.append(_p('SELECTION_UNVERIFIABLE', run=rid, detail='candidate scores missing'))
        elif chosen != sel.get('selected'):
            out.append(_p('SELECTION_RULE_VIOLATED', run=rid, recomputed=chosen, recorded=sel.get('selected')))
    ledger = set(run.get('attempts') or ())
    for c in cands:
        if c.get('attempt_id') not in ledger:
            out.append(_p('LEDGER_INCOMPLETE', run=rid, candidate=c.get('identity')))
    if run.get('interventions'):
        out.append(_p('MANUAL_INTERVENTION', run=rid, count=len(run['interventions'])))
    return out


def lineage_problems(export, trust_context=None):
    """All problems with the transitions of ``export`` (empty list: none found). Pure."""
    tc = trust_context or {}
    revoked = set(tc.get('revoked_versions', ()))
    versions, frozen, runs = export.get('versions', {}), export.get('frozen_at', {}), export.get('runs', {})
    ts = list(export.get('transitions', []))
    out = []
    for vid, v in versions.items():
        if digest(v) != vid:
            out.append(_p('VERSION_ID_MISMATCH', version=vid))
    for rid, run in runs.items():
        out += _run_problems(run, rid)
    seen_accounts = {}
    for rid, run in runs.items():
        acct = run.get('account_sha256')
        if acct in seen_accounts:
            out.append(_p('BUDGET_REUSED', run=rid, other=seen_accounts[acct]))
        seen_accounts.setdefault(acct, rid)
    panels, receipts, keys = {}, {}, {}
    for t in ts:
        tid = t.get('transition_id')
        if t.get('schema') != SCHEMA_TRANSITION or digest({k: v for k, v in t.items() if k != 'transition_id'}) != tid:
            out.append(_p('TRANSITION_ID_MISMATCH', transition=tid))
        if t.get('decision') not in DECISIONS:
            out.append(_p('UNKNOWN_DECISION', transition=tid))
        a, b = t.get('from_version'), t.get('to_version')
        for v in (a, b):
            if v not in versions:
                out.append(_p('VERSION_MISSING', transition=tid, version=v))
            elif v not in frozen:
                out.append(_p('NOT_FROZEN', transition=tid, version=v))
        key = (a, b, t.get('research_run'))
        if key in keys:
            out.append(_p('DUPLICATE_TRANSITION', transition=tid, other=keys[key]))
        keys.setdefault(key, tid)
        for field, seen, code in (('panel_id', panels, 'PANEL_REUSED'), ('receipt_id', receipts, 'RECEIPT_REUSED')):
            val = t.get(field)
            if val is not None and val in seen:
                out.append(_p(code, transition=tid, other=seen[val]))
            if val is not None:
                seen.setdefault(val, tid)
        if a not in versions or b not in versions:
            continue
        va, vb = versions[a], versions[b]
        if vb.get('parent') != a:
            out.append(_p('PARENT_MISMATCH', transition=tid))
        if vb.get('generation') != va.get('generation', -2) + 1:
            out.append(_p('GENERATION_INDEX', transition=tid))
        diff = version_diff(va, vb)
        if not substantive(diff):
            out.append(_p('LABEL_ONLY_CHANGE', transition=tid, changed=diff))
        declared = sorted(t.get('declared_changes') or ())
        if substantive(diff) != sorted(set(declared) - ENVIRONMENT):
            out.append(_p('DECLARED_CHANGES_MISMATCH', transition=tid, actual=substantive(diff), declared=declared))
        env = sorted(set(diff) & ENVIRONMENT)
        if env and not set(env) <= set(declared):
            out.append(_p('UNDECLARED_ENVIRONMENT_CHANGE', transition=tid, changed=env))
        run = runs.get(t.get('research_run'))
        if run is None:
            out.append(_p('RUN_MISSING', transition=tid))
        else:
            if run.get('parent_version') != a:
                out.append(_p('FOREIGN_RUN', transition=tid))
            if (run.get('selection') or {}).get('selected') != b:
                out.append(_p('SELECTED_MISMATCH', transition=tid))
            if not (frozen.get(a, 1 << 62) < run.get('start_event', -1) <= run.get('end_event', -1)
                    < frozen.get(b, -1) < t.get('receipt_event', -1)):
                out.append(_p('CHRONOLOGY', transition=tid))
    # chain structure over the transitions that claim to be accepted improvements
    acc = sorted((t for t in ts if t.get('decision') == 'ACCEPTED'), key=lambda t: t.get('index', 0))
    by_from = {}
    for t in acc:
        by_from.setdefault(t.get('from_version'), []).append(t['transition_id'])
    for v, tids in by_from.items():
        if len(set(tids)) > 1 and len({next(x['to_version'] for x in acc if x['transition_id'] == i)
                                      for i in tids}) > 1:
            out.append(_p('AMBIGUOUS_PARENT', version=v, transitions=sorted(tids)))
    if [t.get('index') for t in acc] != list(range(1, len(acc) + 1)):
        out.append(_p('CHAIN_ORDER', indices=[t.get('index') for t in acc]))
    for prev, nxt in zip(acc, acc[1:]):
        if nxt.get('from_version') != prev.get('to_version'):
            out.append(_p('CHAIN_ORDER', transition=nxt['transition_id'], detail='does not start at the previous child'))
    seen_v = {acc[0].get('from_version')} if acc else set()
    for t in acc:
        if t.get('to_version') in seen_v:
            out.append(_p('CYCLE', transition=t['transition_id'], version=t.get('to_version')))
        seen_v.add(t.get('to_version'))
    dead = False
    for t in acc:
        if dead or t.get('from_version') in revoked or t.get('to_version') in revoked:
            dead = True
            out.append(_p('REVOKED_ANCESTOR', transition=t['transition_id']))
    return out


def accepted_chain(export, trust_context=None):
    """The qualifying chain: consecutive ACCEPTED transitions from the first one, stopping at the
    first transition with any problem (its successors cannot count either). Returns
    {'transitions': [...ids], 'stopped_at': id or None, 'problems': [...]}"""
    problems = lineage_problems(export, trust_context)
    bad = {p.get('transition') for p in problems if p.get('transition')}
    bad_runs = {p.get('run') for p in problems if p.get('run')}
    global_bad = [p for p in problems if not p.get('transition') and not p.get('run') and p['code'] != 'VERSION_ID_MISMATCH']
    acc = sorted((t for t in export.get('transitions', []) if t.get('decision') == 'ACCEPTED'),
                 key=lambda t: t.get('index', 0))
    chain, stopped = [], None
    vid_bad = {p['version'] for p in problems if p['code'] == 'VERSION_ID_MISMATCH'}
    for t in acc:
        if global_bad or t['transition_id'] in bad or t.get('research_run') in bad_runs \
                or {t.get('from_version'), t.get('to_version')} & vid_bad:
            stopped = t['transition_id']
            break
        chain.append(t['transition_id'])
    return {'transitions': chain, 'stopped_at': stopped, 'problems': problems,
            'note': 'a DEV fixture chain is not GV5 evidence: GV5 needs three qualifying prospective transitions '
                    'with sealed panels and a registered joint analysis'}


__all__ = ['SCHEMA_RUN', 'SCHEMA_TRANSITION', 'DECISIONS', 'CODES', 'version_diff', 'substantive',
           'transition_record', 'run_record', 'lineage_problems', 'accepted_chain']
