"""Research-lineage records and their pure validator (handoff H08, roadmap W21, B14-OPEN-3).

A *generation transition* claims that a research run, started from a frozen parent
SystemVersion, produced a frozen child that was then evaluated. Counting transitions
(GV5) is only meaningful if the chain cannot be manufactured. This module defines the
records and checks them; it mutates nothing and creates no claim. Since B20_R4 the
custodian checks a ``sealed_generation_evaluation`` request against the native records of
the bound export (``custodian.generation_problems``); ``sealed_improver_evaluation`` stays
refused (it needs two research lineages evaluated jointly).

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

Native campaign records (B20_R4). ``campaign.Campaign`` commits a ``lineage_run`` and a
``lineage_transition`` entity with every generation. ``export_from_store`` (and
``export_from_campaign_zip``) completes them from the hash-chained event log rather than
trusting them:
  * event positions come from the log: the first GENERATION_STARTED of the round, the last
    event of a ledgered attempt, the successor freeze and the generation commit;
  * an attempt started inside the run window but missing from the ledger is reported
    (``unledgered_attempts``);
  * the run's account is recomputed from the attempt receipts (``campaign_account``) and its
    hash compared with the recorded one.
Exports without native records fall back to the B20_R2 reconstruction, which the validator
refuses (no selection scores, no attempt binding, no account).
"""
from .common import digest

SCHEMA_RUN = 'genesis-research-run-v1'
SCHEMA_TRANSITION = 'genesis-transition-v1'
DECISIONS = ('ACCEPTED', 'REJECTED', 'INCONCLUSIVE', 'INVALID', 'DEV_BRANCH')
LABELS = frozenset({'generation', 'parent', 'memory_snapshot'})
ENVIRONMENT = frozenset({'dependency_lock', 'environment_digest', 'verifier_set'})
SELECTION_RULES = ('max_score_then_lowest_identity', 'max_score_then_greatest_policy')
ACCOUNT_SCHEMA = 'genesis-campaign-research-account-v1'
CODES = ('VERSION_MISSING', 'VERSION_ID_MISMATCH', 'NOT_FROZEN', 'PARENT_MISMATCH', 'GENERATION_INDEX',
         'LABEL_ONLY_CHANGE', 'DECLARED_CHANGES_MISMATCH', 'UNDECLARED_ENVIRONMENT_CHANGE', 'RUN_MISSING',
         'FOREIGN_RUN', 'SELECTION_RULE_UNKNOWN', 'SELECTION_UNVERIFIABLE', 'SELECTION_RULE_VIOLATED',
         'SELECTED_MISMATCH', 'LEDGER_INCOMPLETE', 'MANUAL_INTERVENTION', 'BUDGET_REUSED', 'PANEL_REUSED',
         'RECEIPT_REUSED', 'DUPLICATE_TRANSITION', 'TRANSITION_ID_MISMATCH', 'CHAIN_ORDER', 'AMBIGUOUS_PARENT',
         'CYCLE', 'CHRONOLOGY', 'REVOKED_ANCESTOR', 'UNKNOWN_DECISION', 'MALFORMED', 'BUDGET_UNACCOUNTED',
         'BUDGET_EXCEEDED', 'CANDIDATE_ATTEMPT_MISMATCH')


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
    if rule == 'max_score_then_greatest_policy':          # campaign.Campaign: max(children, key=(SELECT total, policy))
        if any(not isinstance(c.get('score'), (int, float)) or not isinstance(c.get('policy'), str) for c in candidates):
            return None
        return max(candidates, key=lambda c: (c['score'], c['policy']))['identity']
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
        ids = c.get('attempt_ids') if 'attempt_ids' in c else [c.get('attempt_id')]
        if not ids or any(i not in ledger for i in ids):
            out.append(_p('LEDGER_INCOMPLETE', run=rid, candidate=c.get('identity')))
        if 'score_recomputed' in c and c['score_recomputed'] != c.get('score'):
            out.append(_p('SELECTION_RULE_VIOLATED', run=rid, candidate=c.get('identity'),
                          detail='recorded score differs from the attempt receipts'))
        if c.get('attempt_problems'):
            out.append(_p('CANDIDATE_ATTEMPT_MISMATCH', run=rid, candidate=c.get('identity'),
                          detail=sorted(c['attempt_problems'])[:5]))
    if run.get('unledgered_attempts'):
        out.append(_p('LEDGER_INCOMPLETE', run=rid, detail='attempts inside the run window are missing from its ledger',
                      attempts=sorted(run['unledgered_attempts'])[:10]))
    acct = run.get('account')
    if acct is not None:
        if digest(acct) != run.get('account_sha256'):
            out.append(_p('BUDGET_UNACCOUNTED', run=rid, detail='account record does not match its hash'))
        elif acct.get('within_cap') is not True:
            out.append(_p('BUDGET_EXCEEDED', run=rid))
    if 'account_recomputed_sha256' in run and run['account_recomputed_sha256'] != run.get('account_sha256'):
        out.append(_p('BUDGET_UNACCOUNTED', run=rid, detail='account differs from the attempt receipts'))
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
        if acct is None:
            out.append(_p('BUDGET_UNACCOUNTED', run=rid))
            continue
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
            chosen = [c for c in run.get('candidates') or () if c.get('identity') == b]
            if chosen and 'program_sha256' in chosen[0] and chosen[0]['program_sha256'] != digest(vb.get('solver')):
                out.append(_p('SELECTED_MISMATCH', transition=tid, detail='selected candidate program is not the child solver'))
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


COMPONENT_KEYS = {'solver_program': ('program', 'solver')}


def campaign_account(entries, *, round_, research_trials, policies):
    """The resource account of one campaign research run, from its attempts alone.

    ``entries``: (attempt_id, request, receipt-or-None) in ledger order. Shared by the
    campaign (which records it) and the exporter (which recomputes it from the receipts)."""
    statuses, cpu, wall, unknown, solver, checks = {}, 0, 0, 0, 0, 0
    per = {p: 0 for p in policies}
    for _aid, req, rec in entries:
        st = (rec or {}).get('status', 'RUNNING')
        statuses[st] = statuses.get(st, 0) + 1
        if rec is None or rec.get('cost_unknown') or 'wall_ns' not in rec:
            unknown += 1
        else:
            cpu += int(rec.get('cpu_ns') or 0)
            wall += int(rec.get('wall_ns') or 0)
        if req.get('kind') == 'solver':
            solver += 1
            ctx = str(req.get('context', ''))
            for p in policies:
                if ctx.startswith(f'g{round_}:{p}:proposal-'):
                    per[p] += 1
        else:
            checks += 1
    return {'schema': ACCOUNT_SCHEMA, 'round': round_, 'attempts': len(entries), 'solver_attempts': solver,
            'check_attempts': checks, 'statuses': dict(sorted(statuses.items())), 'cpu_ns': cpu, 'wall_ns': wall,
            'cost_unknown_attempts': unknown, 'research_trials_by_policy': per, 'research_trials_cap': research_trials,
            'within_cap': all(v <= research_trials for v in per.values()),
            'note': 'checking attempts are ledgered and reported; they are not charged to a policy'}


def export_native(events, get):
    """Native lineage export from an event log (``events``: bodies with seq, kind, payload)
    and an object getter. None when the log carries no native lineage records."""
    versions, frozen, runs_raw, trans_raw, gen_commit, started = {}, {}, {}, {}, {}, {}
    a_start, a_finish, a_req, a_rec = {}, {}, {}, {}
    for e in events:
        kind, seq = e['kind'], e['seq']
        if kind == 'ENTITY_COMMITTED':
            p = get(e['payload'])
            if p.get('kind') == 'system_version':
                versions[p['id']] = get(p['object_hash'])
                frozen.setdefault(p['id'], seq)
            elif p.get('kind') == 'generation':
                gen_commit[int(p['id'])] = seq
            elif p.get('kind') == 'lineage_run':
                runs_raw[int(p['id'])] = get(p['object_hash'])
            elif p.get('kind') == 'lineage_transition':
                trans_raw[int(p['id'])] = get(p['object_hash'])
        elif kind == 'DEV_SUCCESSOR_FROZEN':
            frozen[get(e['payload'])['version']] = seq
        elif kind == 'GENERATION_STARTED':
            started.setdefault(get(e['payload'])['generation'], seq)
        elif kind == 'ATTEMPT_STARTED':
            p = get(e['payload'])
            a_start[p['attempt_id']] = seq
            a_req[p['attempt_id']] = p['request']
        elif kind == 'ATTEMPT_FINISHED':
            p = get(e['payload'])
            a_finish[p['attempt_id']] = seq
            a_rec[p['attempt_id']] = p['receipt']
    if not runs_raw:
        return None
    runs, transitions = {}, []
    for g in sorted(runs_raw):
        r, t = runs_raw[g], trans_raw.get(g)
        if t is None:
            continue
        start = started.get(g, -1)
        ledger = list(r.get('attempts') or ())
        end = max([a_finish.get(a, a_start.get(a, -1)) for a in ledger] or [start])
        child_frozen = frozen.get(t.get('to_version'), -1)
        inside = sorted(a for a, s_ in a_start.items() if start < s_ < child_frozen)
        unledgered = sorted(set(inside) - set(ledger))
        entries = [(a, get(a_req[a]) if a in a_req else {}, get(a_rec[a]) if a in a_rec else None) for a in ledger]
        recomputed = campaign_account(entries, round_=g, research_trials=(r.get('budget') or {}).get('research_trials'),
                                      policies=(r.get('policy_identity') or {}).get('policies', ()))
        by_attempt = {a: (q, c) for a, q, c in entries}
        cands = []
        for c in r.get('candidates') or ():
            score, bad = 0, []
            for a in c.get('attempt_ids') or ():
                q, rec = by_attempt.get(a, ({}, None))
                if q.get('kind') != 'solver' or q.get('context') != f"g{g}:select-{c.get('policy')}":
                    bad.append(f'{a}: not a SELECT trial of this candidate')
                elif 'program_sha256' in c and digest(q.get('program')) != c['program_sha256']:
                    bad.append(f'{a}: trial ran another program')
                score += ((rec or {}).get('result') or {}).get('value', 0)      # as campaign.trial counts it
            cands.append(dict(c, score_recomputed=score, attempt_problems=bad))
        body = {k: v for k, v in r.items() if k not in ('run_id', 'candidates')}
        body['candidates'] = cands
        run = run_record(**body, start_event=start, end_event=end, unledgered_attempts=unledgered,
                         account_recomputed_sha256=digest(recomputed))
        runs[run['run_id']] = run
        transitions.append(transition_record(**{k: v for k, v in t.items() if k != 'transition_id'},
                                             research_run=run['run_id'], receipt_event=gen_commit.get(g, -1)))
    return {'versions': versions, 'frozen_at': frozen, 'runs': runs, 'transitions': transitions, 'source': 'native',
            'evidence_class': 'DEV_PUBLIC_PANELS'}


def export_from_store(store):
    """Native lineage export of an open ``store.Store`` (None without native records)."""
    import json
    events = [json.loads(b) for (b,) in store.db.execute('SELECT body FROM events ORDER BY seq')]
    return export_native(events, store.get)


def export_from_campaign_zip(path):
    """Lineage records from a DEV campaign export (``campaign.Campaign`` public zip).
    Native records when present (``export_native``); otherwise the reconstruction below.

    Uses only what the export contains: content-addressed versions, freeze events,
    generation and modification records, and the attempt journal. Where the export lacks
    something the validator needs, the record says so instead of inventing it:
      * the cross-policy selection used SELECT scores that are not exported (no score),
      * research candidates are not bound to journal attempts (no attempt id),
      * there is no per-run resource account (no account hash).
    DEV retention is mapped to ACCEPTED/REJECTED for the chain mechanics only; it is not an
    acceptance decision."""
    import json
    import zipfile
    z = zipfile.ZipFile(path)
    events = [json.loads(line)['event'] for line in z.read('events.jsonl').decode().splitlines() if line.strip()]

    def obj(h):
        return json.loads(z.read(f'objects/sha256/{h}'))
    native = export_native(events, obj)
    if native is not None:
        return native
    versions, frozen, runs, transitions = {}, {}, {}, []
    gens, mods, started, attempts = {}, {}, {}, []
    for e in events:
        if e['kind'] == 'ENTITY_COMMITTED':
            p = obj(e['payload'])
            if p.get('kind') == 'system_version':
                versions[p['id']] = obj(p['object_hash'])
                frozen.setdefault(p['id'], e['seq'])
            elif p.get('kind') == 'generation':
                gens[int(p['id'])] = (e['seq'], obj(p['object_hash']))
            elif p.get('kind') == 'modification':
                mods[p['id']] = obj(p['object_hash'])
        elif e['kind'] == 'DEV_SUCCESSOR_FROZEN':
            frozen[obj(e['payload'])['version']] = e['seq']
        elif e['kind'] == 'GENERATION_STARTED':
            started[obj(e['payload'])['generation']] = e['seq']
        elif e['kind'] == 'ATTEMPT_STARTED':
            attempts.append((e['seq'], obj(e['payload'])['attempt_id']))
    index = 0
    for g in sorted(gens):
        seq, res = gens[g]
        vid = res['version']
        mod = mods.get(vid, {})
        parent = mod.get('parent')
        start, end = started.get(g, -1), frozen.get(vid, 0) - 1
        cands = []
        for pol, summary in sorted(res['research'].items()):
            program = summary['candidate_programs'][summary['winner']]
            ident = vid if pol == res['selected_policy'] else digest(program)
            cands.append({'identity': ident, 'policy': pol, 'research_dev_score': summary['scores'][summary['winner']],
                          'attempt_id': None})
        run = run_record(parent_version=parent, policy_identity={'selected_policy': res['selected_policy']},
                         permitted_inputs={'public_panels': True}, seed=None, budget_sha256=None, account_sha256=None,
                         attempts=[a for s_, a in attempts if start < s_ <= end], candidates=cands,
                         selection={'rule': 'max_score_then_lowest_identity', 'selected': vid,
                                    'note': 'campaign selected by SELECT totals, which the export does not contain'},
                         interventions=[], start_event=start, end_event=end)
        runs[run['run_id']] = run
        retained = bool(res.get('retained_in_dev'))
        if retained:
            index += 1
        transitions.append(transition_record(
            index=index if retained else None, from_version=parent, to_version=vid, research_run=run['run_id'],
            declared_changes=[k for k in COMPONENT_KEYS.get(mod.get('component'), (mod.get('component'),))
                              if k in versions.get(vid, {})],
            panel_id=None, receipt_id=None, claim_id=None, plan_id=None, receipt_event=seq,
            decision='ACCEPTED' if retained else 'REJECTED'))
    return {'versions': versions, 'frozen_at': frozen, 'runs': runs, 'transitions': transitions, 'source': 'legacy'}


__all__ = ['SCHEMA_RUN', 'SCHEMA_TRANSITION', 'DECISIONS', 'CODES', 'version_diff', 'substantive',
           'transition_record', 'run_record', 'lineage_problems', 'accepted_chain', 'export_from_campaign_zip',
           'export_native', 'export_from_store', 'campaign_account']
