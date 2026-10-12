"""Research runs over an equational system (B20: W19 policies, E3 successors).

A run starts from a frozen initial solver (pinned E, the system's axioms, an empty
library) and spends a CPU budget on research actions. An action takes one conjecture
from the pool, checks it with the exact decider (a false conjecture is discarded at the
decider's small cost), and otherwise asks E for a proof from the axioms and the most
relevant library lemmas. A proved conjecture enters the library with its proof object.
Every action is logged with its cost and outcome, including failures.

The successor of a run is its frozen library. It is evaluated on held-out targets: E
gets a fixed budget per target, with the axioms and the most relevant library lemmas.

Policies choose the next conjecture:
  fixed      smallest first, then lexicographic (a conventional enumeration order);
  random     uniform over the untried conjectures;
  heuristic  smallest first among conjectures sharing a subterm with the development
             targets (a tuned, goal-directed heuristic);
  bandit     UCB1 over conjecture classes (size, number of variables): reward is a proof;
  learned    a logistic model of "proved and later used", trained on other systems'
             trajectories and frozen before use.
"""
import math
import random
import resource
import time

from ..common import digest
from ..verification.eprover import prove
from . import equational as Q


def _cpu():
    me = resource.getrusage(resource.RUSAGE_SELF); ch = resource.getrusage(resource.RUSAGE_CHILDREN)
    return me.ru_utime + me.ru_stime + ch.ru_utime + ch.ru_stime


def subterms(t, out=None):
    out = set() if out is None else out
    if t[0] == 'fn' and t[2]:
        out.add(Q.canon((t, t))[0])
        for a in t[2]:
            subterms(a, out)
    return out


def eq_subterms(eq):
    return subterms(eq[0]) | subterms(eq[1])


def relevance(lemma, target):
    a, b = eq_subterms(lemma), eq_subterms(target)
    return len(a & b) / (len(a | b) or 1)


def premises(library, target, k):
    """The k library lemmas most relevant to `target` (subterm Jaccard, then recency)."""
    ranked = sorted(range(len(library)), key=lambda i: (-relevance(library[i]['eq'], target), -i))
    return [library[i] for i in ranked[:k]]


def used_inputs(proof, n_inputs):
    """Indices of the E inputs (ax0 … ax{n-1}) that a proof object uses."""
    import re
    return sorted({int(m) for m in re.findall(r"file\('[^']*', ax(\d+)\)", proof or '') if int(m) < n_inputs})


# ---------------------------------------------------------------- features and policies

def features(eq, dev_targets):
    l, r = eq
    vs = len(Q._vars(l, set()) | Q._vars(r, set()))
    st = eq_subterms(eq)
    overlap = max((len(st & eq_subterms(t)) / (len(st | eq_subterms(t)) or 1) for t in dev_targets), default=0.0)
    return [1.0, (Q.size(l) + Q.size(r)) / 8.0, vs / 3.0, abs(Q.size(l) - Q.size(r)) / 8.0,
            float(l[0] == 'var' or r[0] == 'var'), overlap]


FEATURE_NAMES = ['bias', 'size', 'variables', 'imbalance', 'variable_side', 'target_overlap']


class Policy:
    name = 'base'

    def __init__(self, seed=0):
        self.rng = random.Random(seed)

    def reset(self, pool, dev_targets):
        self.pool, self.dev = pool, dev_targets

    def choose(self, untried):
        raise NotImplementedError

    def observe(self, eq, outcome):
        pass


class Fixed(Policy):
    name = 'fixed'

    def choose(self, untried):
        return min(untried, key=lambda e: (Q.size(e[0]) + Q.size(e[1]), repr(e)))


class Random(Policy):
    name = 'random'

    def choose(self, untried):
        return self.rng.choice(sorted(untried, key=repr))


class Heuristic(Policy):
    name = 'heuristic'

    def reset(self, pool, dev_targets):
        super().reset(pool, dev_targets)
        dev_st = set().union(*(eq_subterms(t) for t in dev_targets)) if dev_targets else set()
        self.related = {e for e in pool if eq_subterms(e) & dev_st}

    def choose(self, untried):
        key = lambda e: (e not in self.related, Q.size(e[0]) + Q.size(e[1]), repr(e))
        return min(untried, key=key)


class Bandit(Policy):
    """UCB1 over classes (total size, variable count)."""
    name = 'bandit'

    def reset(self, pool, dev_targets):
        super().reset(pool, dev_targets)
        self.n, self.w, self.t = {}, {}, 0

    @staticmethod
    def cls(e):
        return (Q.size(e[0]) + Q.size(e[1]), len(Q._vars(e[0], set()) | Q._vars(e[1], set())))

    def choose(self, untried):
        self.t += 1
        classes = sorted({self.cls(e) for e in untried})

        def ucb(c):
            n = self.n.get(c, 0)
            return float('inf') if n == 0 else self.w[c] / n + math.sqrt(2 * math.log(self.t) / n)
        best = max(classes, key=lambda c: (ucb(c), [-x for x in c]))
        return min((e for e in untried if self.cls(e) == best), key=lambda e: repr(e))

    def observe(self, eq, outcome):
        c = self.cls(eq)
        self.n[c] = self.n.get(c, 0) + 1
        self.w[c] = self.w.get(c, 0.0) + (1.0 if outcome == 'PROVED' else 0.0)


class Learned(Policy):
    """Ranks by a frozen logistic model of P(proved and later used)."""
    name = 'learned'

    def __init__(self, weights, seed=0):
        super().__init__(seed)
        self.weights = list(weights)

    def reset(self, pool, dev_targets):
        super().reset(pool, dev_targets)
        self.score = {e: sum(w * x for w, x in zip(self.weights, features(e, dev_targets))) for e in pool}

    def choose(self, untried):
        return max(untried, key=lambda e: (self.score[e], -(Q.size(e[0]) + Q.size(e[1])), repr(e)))


def fit_logistic(X, y, *, l2=1e-2, steps=3000, lr=0.5):
    """Plain gradient descent; returns weights. Deterministic."""
    w = [0.0] * len(X[0])
    n = len(X)
    for _ in range(steps):
        g = [l2 * wi for wi in w]
        for xi, yi in zip(X, y):
            z = sum(a * b for a, b in zip(w, xi))
            p = 1 / (1 + math.exp(-max(-30, min(30, z))))
            for j in range(len(w)):
                g[j] += (p - yi) * xi[j] / n
        w = [wi - lr * gi for wi, gi in zip(w, g)]
    return w


def predict(w, x):
    z = sum(a * b for a, b in zip(w, x))
    return 1 / (1 + math.exp(-max(-30, min(30, z))))


# ---------------------------------------------------------------- runs (repaired: B20-REVIEW-02, -01, -03)

def lemma_uid(run_id, local_id, text, proof_sha256):
    """Globally unique, run-bound identity of a library lemma (local names like L0 are not)."""
    return digest({'run': run_id, 'local': local_id, 'statement': text, 'proof_sha256': proof_sha256})


def _sha_text(s):
    import hashlib
    return hashlib.sha256(s.encode()).hexdigest() if s is not None else None


def _default_prover(axioms, goal, *, res, label):
    from ..verification.eprover import prove_bounded
    return prove_bounded(axioms, goal, limit_s=res.prover_limit_s, cpu_ns=res.cpu_ns, wall_ns=res.wall_ns,
                         mode='auto', label=label)


def _settle(account, res, r):
    rr = r.get('resource') or {}
    return account.settle(res, cpu_ns=rr.get('cpu_ns'), wall_ns=rr.get('wall_ns', 0),
                          termination=rr.get('termination', 'UNMETERED'), status=r['status'],
                          meter=rr.get('meter', {'kind': 'none', 'lower_bound': True}),
                          extra={'proof_sha256': _sha_text(r.get('proof'))})


def run(system, policy, pool, *, budget_s=None, account=None, dev_targets=(), prove_s=2, premise_k=8, log=None,
        screen=None, run_id=None, prover=None):
    """One research run under a resource account (Repair B). Returns the frozen successor
    (library), the full trajectory and the account record.

    * The account is open before policy preparation; reset, choice, deciders and retrieval
      are charged. Each proof attempt is reserved before launch and runs bounded; a proof
      is admitted only from an attempt the account marks eligible (no late results).
    * Every admitted lemma is screened through ``screen(route, system, eq)`` (a
      ``partitions.InsertionScreen``); a BLOCK keeps it out and is logged.
    * Lemmas carry run-bound identities (``uid``), their proof hash and attempt id, so a
      successor manifest can be built and replayed (Repair C).

    ``budget_s`` (legacy argument) builds a strict account with ``prove_s`` per attempt.
    """
    from .budget import Account, StudyBudget
    if account is None:
        if budget_s is None:
            raise ValueError('a research run needs an account or a budget')
        account = Account(StudyBudget.from_seconds(budget_s, attempt_s=prove_s), label=f'{system}:{policy.name}')
    prover = prover or _default_prover
    run_id = run_id or digest({'system': system, 'policy': policy.name, 'account': account.label,
                               'budget': account.budget.identity(), 'pool': [Q.text(e) for e in pool]})
    with account.measure('preparation', 'policy reset and axioms'):
        spec = Q.SYSTEMS[system]
        ax = Q.axioms(system)
        policy.reset(list(pool), list(dev_targets))
        untried = set(pool)
    library, trajectory, screened = [], [], []
    while untried and not account.stop_reason:
        with account.measure('policy', 'choose'):
            eq = policy.choose(untried)
            untried.discard(eq)
        with account.measure('decider'):
            truth = Q.holds(eq, spec['decider'])
        if account.stop_reason:
            trajectory.append({'step': len(trajectory), 'eq': Q.text(eq), 'outcome': 'NOT_ATTEMPTED',
                               'reason': account.stop_reason})
            break
        if not truth:
            with account.measure('policy', 'observe'):
                policy.observe(eq, 'FALSE')
            trajectory.append({'step': len(trajectory), 'eq': Q.text(eq), 'outcome': 'FALSE'})
            continue
        with account.measure('retrieval'):
            prem = premises(library, eq, premise_k)
        res = account.reserve('prover', purpose=f'prove {Q.text(eq)}')
        if res is None:
            trajectory.append({'step': len(trajectory), 'eq': Q.text(eq), 'outcome': 'NOT_ATTEMPTED',
                               'reason': account.stop_reason})
            break
        r = prover(ax + [Q.closed(p['eq']) for p in prem], Q.closed(eq), res=res, label=res.attempt_id)
        settled = _settle(account, res, r)
        proved = r['status'] == 'THEOREM' and bool(r.get('proof'))
        rec = {'e_status': r['status'], 'premises': [p['id'] for p in prem], 'attempt_id': res.attempt_id,
               'eligible': settled['eligible']}
        if proved and not settled['eligible']:
            outcome = 'PROVED_NOT_CREDITED'
            rec['reason'] = settled['reason']
        elif proved and screen is not None and screen('lemma', system, eq)['decision'] != 'ALLOW':
            outcome = 'SCREENED_OUT'
            screened.append(Q.text(eq))
        elif proved:
            outcome = 'PROVED'
            used = used_inputs(r['proof'], len(ax) + len(prem))
            local = f'L{len(library)}'
            psha = _sha_text(r['proof'])
            uses = [prem[i - len(ax)]['id'] for i in used if i >= len(ax)]
            by_local = {l['id']: l['uid'] for l in library}
            library.append({'id': local, 'eq': eq, 'text': Q.text(eq), 'proof': r['proof'], 'proof_sha256': psha,
                            'uid': lemma_uid(run_id, local, Q.text(eq), psha), 'attempt_id': res.attempt_id,
                            'uses': uses, 'uses_uids': [by_local[u] for u in uses],
                            'premise_ids': [p['id'] for p in prem],
                            'premise_uids': [by_local[p['id']] for p in prem]})
        else:
            outcome = 'UNPROVED'
        with account.measure('policy', 'observe'):
            policy.observe(eq, 'PROVED' if outcome == 'PROVED' else 'UNPROVED')
        trajectory.append({'step': len(trajectory), 'eq': Q.text(eq), 'outcome': outcome,
                           'cpu_s': round(settled['cpu_ns'] / 1e9, 3), **rec})
        if log and outcome == 'PROVED':
            log(f'  {system} {policy.name}: proved {Q.text(eq)} ({len(library)} lemmas)')
    acct = account.record()
    return {'system': system, 'policy': policy.name, 'run_id': run_id, 'library': library, 'trajectory': trajectory,
            'cpu_s': round(acct['cpu_ns_total'] / 1e9, 3), 'library_sha256': digest([l['text'] for l in library]),
            'account': acct, 'screened_out': screened, 'screen': 'INSERTION_SCREEN' if screen else 'NONE'}


def evaluate_successor(system, library, targets, *, eval_s=3, premise_k=8, account=None, task_ids=None, prover=None,
                       label='evaluation'):
    """Targets proved by E with the axioms and the most relevant library lemmas, each under
    its own bounded reservation of ``eval_s`` prover seconds (equal for every arm). A target
    counts only if its attempt was eligible (exited within its reservation). Rows keep the
    proof object, the premise identities in input order and the attempt record, so each
    scored proof can be taken into custody and replayed."""
    from .budget import Account, StudyBudget
    prover = prover or _default_prover
    if account is None:
        per = StudyBudget.from_seconds(eval_s, attempt_s=eval_s)
        n = max(1, len(targets))
        account = Account(StudyBudget(cpu_ns=(per.attempt_cpu_ns + per.tolerance_ns) * n, wall_ns=per.wall_ns * n,
                                      attempt_cpu_ns=per.attempt_cpu_ns, overhead_ns=per.overhead_ns), label=label)
    ax = Q.axioms(system)
    by_local = {l['id']: l for l in library}
    rows, used = [], {}
    for n, t in enumerate(targets):
        prem = premises(library, t, premise_k)
        res = account.reserve('evaluation', purpose=f'target {n}')
        if res is None:
            rows.append({'target': Q.text(t), 'eq': t, 'status': 'NOT_ATTEMPTED', 'reason': account.stop_reason,
                         'lemmas_used': [], 'premise_ids': [], 'premise_uids': [], 'proof': None,
                         'eligible': False, 'task_id': task_ids[n] if task_ids else n})
            continue
        r = prover(ax + [Q.closed(p['eq']) for p in prem], Q.closed(t), res=res, label=res.attempt_id)
        settled = _settle(account, res, r)
        ok = r['status'] == 'THEOREM' and bool(r.get('proof'))
        ids = [prem[i - len(ax)]['id'] for i in used_inputs(r['proof'], len(ax) + len(prem)) if i >= len(ax)] \
            if ok else []
        if ok and settled['eligible']:
            for i in ids:
                used[i] = used.get(i, 0) + 1
        status = ('PROVED' if settled['eligible'] else 'PROVED_NOT_CREDITED') if ok else r['status']
        rows.append({'target': Q.text(t), 'eq': t, 'status': status, 'lemmas_used': ids,
                     'premise_ids': [p['id'] for p in prem],
                     'premise_uids': [by_local[p['id']].get('uid') for p in prem],
                     'proof': r['proof'] if ok else None, 'proof_sha256': _sha_text(r['proof']) if ok else None,
                     'attempt_id': res.attempt_id, 'eligible': settled['eligible'], 'cpu_ns': settled['cpu_ns'],
                     'task_id': task_ids[n] if task_ids else n})
    return {'proved': sum(r['status'] == 'PROVED' for r in rows),
            'prover_reported': sum(r['status'] in ('PROVED', 'PROVED_NOT_CREDITED') for r in rows),
            'targets': len(targets), 'rows': rows, 'lemma_use': used, 'account': account.record()}


# ---------------------------------------------------------------- the original B20 loop (kept for reproduction)

def run_legacy_b20(system, policy, pool, *, budget_s, dev_targets=(), prove_s=2, premise_k=8, log=None):
    """The B20 research loop, unchanged. DEFECTIVE (B20-REVIEW-02): preparation uncharged,
    cap checked before the action, fractional remainders rounded up to whole prover
    seconds, late proofs accepted. Kept only so the finding stays reproducible."""
    spec = Q.SYSTEMS[system]
    ax = Q.axioms(system)
    policy.reset(list(pool), list(dev_targets))
    untried = set(pool)
    library, trajectory = [], []
    start = _cpu()
    while untried and _cpu() - start < budget_s:
        eq = policy.choose(untried)
        untried.discard(eq)
        c0 = _cpu()
        if not Q.holds(eq, spec['decider']):
            outcome, rec = 'FALSE', {}
        else:
            prem = premises(library, eq, premise_k)
            left = budget_s - (_cpu() - start)
            r = prove(ax + [Q.closed(p['eq']) for p in prem], Q.closed(eq),
                      seconds=max(1, min(prove_s, int(math.ceil(left)))), mode='auto')
            outcome = 'PROVED' if r['status'] == 'THEOREM' and r['proof'] else 'UNPROVED'
            rec = {'e_status': r['status'], 'premises': [p['id'] for p in prem]}
            if outcome == 'PROVED':
                used = used_inputs(r['proof'], len(ax) + len(prem))
                library.append({'id': f'L{len(library)}', 'eq': eq, 'text': Q.text(eq), 'proof': r['proof'],
                                'uses': [prem[i - len(ax)]['id'] for i in used if i >= len(ax)],
                                'premise_ids': [p['id'] for p in prem]})
        policy.observe(eq, outcome)
        trajectory.append({'step': len(trajectory), 'eq': Q.text(eq), 'outcome': outcome,
                           'cpu_s': round(_cpu() - c0, 3), **rec})
        if log and outcome == 'PROVED':
            log(f'  {system} {policy.name}: proved {Q.text(eq)} ({len(library)} lemmas)')
    return {'system': system, 'policy': policy.name, 'library': library, 'trajectory': trajectory,
            'cpu_s': round(_cpu() - start, 2), 'library_sha256': digest([l['text'] for l in library])}


def evaluate_successor_legacy_b20(system, library, targets, *, eval_s=3, premise_k=8):
    """The B20 successor evaluation, unchanged (kept for reproduction; no proof custody)."""
    ax = Q.axioms(system)
    rows, used = [], {}
    for t in targets:
        prem = premises(library, t, premise_k)
        r = prove(ax + [Q.closed(p['eq']) for p in prem], Q.closed(t), seconds=eval_s, mode='auto')
        ok = r['status'] == 'THEOREM' and bool(r['proof'])
        ids = [prem[i - len(ax)]['id'] for i in used_inputs(r['proof'], len(ax) + len(prem)) if i >= len(ax)] if ok else []
        for i in ids:
            used[i] = used.get(i, 0) + 1
        rows.append({'target': Q.text(t), 'eq': t, 'status': 'PROVED' if ok else r['status'], 'lemmas_used': ids,
                     'premise_ids': [p['id'] for p in prem], 'proof': r['proof'] if ok else None})
    return {'proved': sum(r['status'] == 'PROVED' for r in rows), 'targets': len(targets), 'rows': rows,
            'lemma_use': used}


def lean_chain(library, proof, premise_ids, n_axioms):
    """The lemma chain a proof needs for Lean replay: every library lemma it uses, and
    recursively the lemmas those proofs use, in dependency order. Returns (entries for
    `fof_lean.replay(lemmas=…)`, goal_deps, goal_positions)."""
    by = {l['id']: l for l in library}
    order, index = [], {}

    def visit(lid):
        if lid in index:
            return
        for u in by[lid]['uses']:
            visit(u)
        index[lid] = len(order)
        order.append(lid)
    used = [i for i in used_inputs(proof, n_axioms + len(premise_ids)) if i >= n_axioms]
    goal_ids = [premise_ids[i - n_axioms] for i in used]
    for g in goal_ids:
        visit(g)
    entries = []
    for lid in order:
        lem = by[lid]
        deps = [index[u] for u in lem['uses']]
        pos = [n_axioms + lem['premise_ids'].index(u) for u in lem['uses']]
        entries.append((Q.closed(lem['eq']), lem['proof'], deps, pos))
    return entries, [index[g] for g in goal_ids], used


def usefulness_labels(result, evaluation):
    """Per tried conjecture: 1 if it was proved and later used (by a library lemma's proof or
    a target proof), else 0. The training signal for the learned policy."""
    used = set(evaluation['lemma_use'])
    for lem in result['library']:
        used |= set(lem['uses'])
    proved = {l['text']: l['id'] for l in result['library']}
    return {s['eq']: int(s['eq'] in proved and proved[s['eq']] in used) for s in result['trajectory']}


__all__ = ['run', 'evaluate_successor', 'run_legacy_b20', 'evaluate_successor_legacy_b20', 'lemma_uid',
           'usefulness_labels', 'lean_chain', 'Fixed', 'Random', 'Heuristic', 'Bandit', 'Learned',
           'fit_logistic', 'predict', 'features', 'FEATURE_NAMES', 'premises', 'used_inputs']
