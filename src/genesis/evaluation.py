"""Paired statistics, family sensitivity, effects and conservative claim wording."""
from collections import defaultdict
from math import comb


def sign_test(wins,losses):
    if type(wins) is not int or type(losses) is not int or min(wins,losses)<0:raise ValueError('counts')
    n=wins+losses
    return sum(comb(n,k) for k in range(wins,n+1))/2**n if n else 1.0


def paired(rows):
    ids=[r['task_id'] for r in rows]
    if len(ids)!=len(set(ids)):raise ValueError('duplicate paired task')
    wins=sum(r['candidate']>r['baseline'] for r in rows)
    losses=sum(r['candidate']<r['baseline'] for r in rows)
    groups=defaultdict(int)
    for r in rows:groups[r['family']]+=r['candidate']-r['baseline']
    return {'n':len(rows),'wins':wins,'losses':losses,'ties':len(rows)-wins-losses,
            'exploratory_sign_p':sign_test(wins,losses),
            'family_sensitivity_p':sign_test(sum(v>0 for v in groups.values()),sum(v<0 for v in groups.values())),
            'family_deltas':dict(groups),'claim':'DEV_ONLY','confirmation_p_value':None}


def causal_controls(incumbent,candidate,ablated,placebo):
    """A paired DEV intervention diagnostic. No fresh utility status is conferred."""
    keys=set(incumbent)
    if any(set(x)!=keys for x in (candidate,ablated,placebo)):raise ValueError('unmatched causal panels')
    deltas={k:candidate[k]-incumbent[k] for k in keys}
    return {'candidate_gain':sum(deltas.values()),
            'ablation_loss':sum(candidate[k]-ablated[k] for k in keys),
            'placebo_delta':sum(placebo[k]-incumbent[k] for k in keys),
            'status':'DEV_INTERVENTION_DIAGNOSTIC','causal_claim_supported':False}


def propagate_effects(parents,own=()):
    return tuple(sorted(set(own).union(*(set(p.get('effects',())) for p in parents))))


def evidence_wording(evidence):
    mathematical={
        'UNCHECKED':'An unchecked candidate was produced.',
        'EXECUTABLE':'A bounded program executed.',
        'WITNESS_VALID':'The returned witness passed the registered checks.',
        'FINITE_CERTIFIED':'Independent algorithms agreed on the exact value for these finite instances.',
        'OPTIMALITY_CHECKED':'The checked lower and upper certificates meet for the stated scope.',
        'THEOREM_CHECKED':'The theorem was replayed by the registered formal checker.',
        'REJECTED':'The submitted result was rejected.',
        'UNSETTLED':'The available evidence does not settle the result.',
        'CHECKER_ERROR':'Verification failed; no mathematical conclusion is licensed.'}
    text=mathematical[evidence.math]
    if evidence.utility=='DEV_ONLY':text+=' Utility measurements are development-only.'
    if evidence.improver=='NOT_TESTED':text+=' Better-improver and recursive-improvement claims remain unestablished.'
    return text


from .kernel.phases import TRANSITIONS, SCIENTIFIC, advance  # noqa: F401  (single state machine)


def transition(store,target,*,external_receipt=None,reason=None):
    """Engineering transitions for research code. Scientific phases go through
    kernel.phases.advance with a signed envelope; research code cannot pass a
    dict or boolean as authority."""
    current=store.state('phase','CREATED')
    if target not in TRANSITIONS[current]:raise ValueError(f'illegal phase transition {current} -> {target}')
    if target in SCIENTIFIC:
        raise PermissionError('scientific phases belong to the separately operated evaluator/release service')
    if target in ('ABORTED','INVALIDATED') and reason is None:
        reason='research runtime: '+target.lower()
    return advance(store,target,reason=reason)
