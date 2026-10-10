"""Known-answer ladder: complete hosts K_n whose optima are published or proved.

The ladder tests whether a frozen solver finds known optimal solutions without
being given them. Arms are fixed data-only DSL programs and cannot read the
answer key. Every invocation runs through the bounded subprocess executor and
is charged; all arms receive the same realized-CPU budget per rung.

Evidence semantics:
* Witnesses are checked by the dual predicates (WITNESS_VALID).
* "Matches the known optimum" rests on an external published value
  (effect EXTERNAL_SOURCE) or, for triangle-free hosts, on Mantel's theorem.
  It is a rediscovery, never a novelty claim.
* On frontier rungs (only bounds known) a witness above the published lower
  bound is a CANDIDATE that needs an external priority/literature check. A
  witness above a published exact value or upper bound is a contradiction and
  is reported as HARNESS_ERROR, never as a discovery.
"""
from itertools import combinations
from pathlib import Path
from typing import Literal
from pydantic import Field, model_validator
from .common import canonical, code_identity, digest, utcnow
from .models import StrictModel, GraphTask, SolverProgram, Limits
from .execution import execute
from .graphs import check_witness
from .evaluation import sign_test
from .store import Store

# OEIS A006855 "Maximum number of edges in an n-node squarefree graph", i.e.
# ex(n, C4) for n = 1..40. Terms a(23)-a(31) Michel Marcus (2014), a(32)-a(39)
# Brendan McKay (2022), a(40) McKay via Max Alekseyev (2023). Bounds for
# n = 41..49: lower bounds McKay (Mar 2022), upper bounds Alekseyev (Jan 2023).
# Retrieved 2026-10-10 from https://oeis.org/A006855. Re-verify against the
# OEIS b-file before citing any frontier result.
A006855 = (0, 1, 3, 4, 6, 7, 9, 11, 13, 16, 18, 21, 24, 27, 30, 33, 36, 39, 42, 46,
           50, 52, 56, 59, 63, 67, 71, 76, 80, 85, 90, 92, 96, 102, 106, 110, 113, 117, 122, 127)
A006855_FRONTIER = {41: (132, 133), 42: (137, 139), 43: (142, 145), 44: (148, 151), 45: (154, 158),
                    46: (157, 165), 47: (163, 171), 48: (168, 176), 49: (174, 182)}
SOURCES = {
    'c4_host_v2': {'kind': 'EXTERNAL_SOURCE', 'reference': 'OEIS A006855', 'url': 'https://oeis.org/A006855',
                   'retrieved': '2026-10-10',
                   'note': 'exact values n<=40 from exhaustive computation by others; not re-proved here'},
    'triangle_free_host_v1': {'kind': 'THEOREM', 'reference': "Mantel's theorem: ex(n, K3) = floor(n^2/4)",
                              'note': 'classical theorem; values are exact for every n'},
}


def answer_key(domain):
    if domain == 'c4_host_v2':
        exact = {n: A006855[n - 1] for n in range(1, len(A006855) + 1)}
        return {'exact': exact, 'bounds': dict(A006855_FRONTIER), 'source': SOURCES[domain]}
    if domain == 'triangle_free_host_v1':
        return {'exact': {n: n * n // 4 for n in range(1, 64)}, 'bounds': {}, 'source': SOURCES[domain]}
    raise ValueError('unknown domain')


def answer_key_digest(domain):
    key = answer_key(domain)
    return digest({'exact': {str(k): v for k, v in key['exact'].items()},
                   'bounds': {str(k): list(v) for k, v in key['bounds'].items()},
                   'source': key['source']})


def ladder_task(domain, n):
    return GraphTask(task_id=f'ladder-{domain}-K{n}', domain=domain, n=n,
                     edges=tuple(combinations(range(n), 2)), family='complete_host', split='DEV')


class LadderPreregistration(StrictModel):
    schema_version: Literal['genesis-ladder-prereg-v1'] = 'genesis-ladder-prereg-v1'
    domain: Literal['c4_host_v2', 'triangle_free_host_v1'] = 'c4_host_v2'
    development_rungs: tuple[int, ...]
    test_rungs: tuple[int, ...]
    arms: tuple[tuple[str, SolverProgram], ...]
    cpu_seconds_per_rung: float = Field(gt=0, le=3600)
    invocation_limits: Limits
    queries_per_invocation: int = Field(ge=1, le=100000)
    seed: int
    answer_key_sha256: str = Field(min_length=64, max_length=64)
    primary_metric: Literal['test-rung paired best value vs known optimum'] = \
        'test-rung paired best value vs known optimum'
    notes: str = ''

    @model_validator(mode='after')
    def shape(self):
        rungs = self.development_rungs + self.test_rungs
        if len(set(rungs)) != len(rungs):
            raise ValueError('development and test rungs must be disjoint and unique')
        if any(not 1 <= n <= 63 for n in rungs):
            raise ValueError('rung outside host bound')
        names = [name for name, _ in self.arms]
        if len(names) != len(set(names)) or not 1 <= len(names) <= 8:
            raise ValueError('arm names must be unique, 1..8 arms')
        if self.answer_key_sha256 != answer_key_digest(self.domain):
            raise ValueError('preregistration does not bind the current answer key')
        return self


def default_preregistration(domain='c4_host_v2', development=range(4, 21), test=range(21, 41),
                            cpu_seconds=20.0, seed=20261010, candidate=None, notes=''):
    from .dsl import baseline_programs
    arms = list(baseline_programs().items())
    if candidate is not None:
        arms.append(('frozen_candidate', candidate))
    return LadderPreregistration(
        domain=domain, development_rungs=tuple(development), test_rungs=tuple(test),
        arms=tuple(arms), cpu_seconds_per_rung=cpu_seconds,
        invocation_limits=Limits(queries=100000, wall_seconds=120, cpu_seconds=30),
        queries_per_invocation=100000, seed=seed, answer_key_sha256=answer_key_digest(domain), notes=notes)


def classify(value, n, key):
    exact = key['exact'].get(n)
    if exact is not None:
        if value > exact:
            return {'status': 'HARNESS_ERROR', 'reason': 'witness exceeds published exact value',
                    'reference': exact}
        return {'status': 'MATCHES_KNOWN_OPTIMUM' if value == exact else 'BELOW_KNOWN_OPTIMUM',
                'reference': exact, 'shortfall': exact - value}
    if n in key['bounds']:
        lower, upper = key['bounds'][n]
        if value > upper:
            return {'status': 'HARNESS_ERROR', 'reason': 'witness exceeds published upper bound',
                    'bounds': [lower, upper]}
        if value > lower:
            return {'status': 'EXCEEDS_PUBLISHED_LOWER_BOUND_CANDIDATE', 'bounds': [lower, upper],
                    'requires': ['independent witness re-check', 'external literature/priority check']}
        return {'status': 'WITHIN_PUBLISHED_BOUNDS', 'bounds': [lower, upper], 'shortfall_to_lower': lower - value}
    return {'status': 'NO_REFERENCE'}


def _seed(base, n, arm, k):
    return int(digest({'seed': base, 'n': n, 'arm': arm, 'k': k})[:12], 16)


def run_ladder(root, prereg, progress=None):
    """Execute a preregistered ladder in a fresh store. Returns the results dict."""
    root = Path(root)
    if root.exists() and any(root.iterdir()):
        raise FileExistsError('ladder destination must be empty')
    key = answer_key(prereg.domain)
    budget_ns = int(prereg.cpu_seconds_per_rung * 1e9)
    with Store(root) as s:
        prereg_json = prereg.model_dump(mode='json')
        prereg_id = digest(prereg_json)
        # Persist the preregistration before any execution.
        s.save('ladder_preregistration', prereg_id, prereg_json)
        from .campaign import environment
        identity = code_identity(Path(__file__).resolve().parents[2])
        s.save('source', 'ladder', identity)
        s.save('environment', 'ladder', environment())
        s.set_state('source_hash', identity['sha256'])
        s.set_state('ladder_phase', 'PREREGISTERED')
        rows = []
        for split, rungs in (('development', prereg.development_rungs), ('test', prereg.test_rungs)):
            for n in rungs:
                task = ladder_task(prereg.domain, n)
                for name, program in prereg.arms:
                    spent = 0; k = 0; best = None; statuses = {}
                    while spent < budget_ns:
                        seed = _seed(prereg.seed, n, name, k)
                        request = {'kind': 'ladder', 'prereg': prereg_id, 'split': split, 'n': n, 'arm': name,
                                   'invocation': k, 'task': task.model_dump(mode='json'),
                                   'program': program.model_dump(mode='json'),
                                   'limits': prereg.invocation_limits.model_dump(mode='json'), 'seed': seed}
                        aid = s.start(f'ladder-{prereg_id[:12]}-{split}-K{n}-{name}', request)
                        receipt = execute(task, program, prereg.invocation_limits, seed)
                        s.finish(aid, receipt)
                        statuses[receipt['status']] = statuses.get(receipt['status'], 0) + 1
                        # Failed attempts are charged at their limit when CPU is unknown.
                        cpu = receipt['cpu_ns'] if receipt.get('cpu_ns') is not None else \
                            prereg.invocation_limits.cpu_seconds * 10**9
                        spent += cpu; k += 1
                        if receipt['status'] == 'SUCCESS':
                            value = receipt['result']['value']
                            if best is None or value > best[0]:
                                best = (value, receipt['result']['selected'])
                        if receipt['status'] != 'SUCCESS' and k >= 3 and statuses.get('SUCCESS', 0) == 0:
                            break  # three consecutive failures with no success: stop charging this arm
                    witness_hash = None; value = None
                    if best is not None:
                        checked = check_witness(task, best[1])  # coordinator-side re-check
                        value = checked['value']
                        witness_hash = s.put({'task_id': task.task_id, 'edges': [list(e) for e in checked['selected']]})
                    row = {'split': split, 'n': n, 'arm': name, 'best_value': value, 'witness': witness_hash,
                           'invocations': k, 'realized_cpu_ns': spent, 'budget_cpu_ns': budget_ns,
                           'attempt_statuses': statuses,
                           'classification': classify(value, n, key) if value is not None else
                           {'status': 'NO_VALID_WITNESS'}}
                    rows.append(row)
                    if progress:
                        progress(row)
        if code_identity(Path(__file__).resolve().parents[2])['sha256'] != identity['sha256']:
            raise RuntimeError('source changed during the ladder run; results would not match one SystemVersion')
        results = summarize(prereg, prereg_id, rows)
        results['source_hash'] = identity['sha256']
        s.save('ladder_results', prereg_id, results)
        s.set_state('ladder_phase', 'COMPLETE')
        (root / 'reports' / 'ladder_results.json').write_bytes(canonical(results))
        (root / 'reports' / 'ladder_report.md').write_text(render(results))
        return results


def summarize(prereg, prereg_id, rows):
    arms = [name for name, _ in prereg.arms]
    test = [r for r in rows if r['split'] == 'test']
    per_arm = {}
    for name in arms:
        mine = sorted((r for r in test if r['arm'] == name), key=lambda r: r['n'])
        matched = [r['n'] for r in mine if r['classification']['status'] == 'MATCHES_KNOWN_OPTIMUM']
        height = None
        for r in mine:
            if r['classification']['status'] != 'MATCHES_KNOWN_OPTIMUM':
                break
            height = r['n']
        shortfall = sum(r['classification'].get('shortfall', 0) for r in mine
                        if r['classification']['status'] in ('MATCHES_KNOWN_OPTIMUM', 'BELOW_KNOWN_OPTIMUM'))
        cpu = [r['realized_cpu_ns'] / r['budget_cpu_ns'] for r in mine if r['budget_cpu_ns']]
        per_arm[name] = {
            'test_rungs': len(mine), 'matched_known_optimum': len(matched), 'matched_rungs': matched,
            'unbroken_height_from_first_test_rung': height, 'total_shortfall_on_exact_rungs': shortfall,
            'frontier_candidates': [r['n'] for r in mine
                                    if r['classification']['status'] == 'EXCEEDS_PUBLISHED_LOWER_BOUND_CANDIDATE'],
            'harness_errors': [r['n'] for r in mine if r['classification']['status'] == 'HARNESS_ERROR'],
            'realized_cpu_over_budget_max': round(max(cpu), 3) if cpu else None,
        }
    pairs = {}
    for i, a in enumerate(arms):
        for b in arms[i + 1:]:
            wins = losses = ties = 0
            for n in prereg.test_rungs:
                va = next(r['best_value'] for r in test if r['arm'] == a and r['n'] == n)
                vb = next(r['best_value'] for r in test if r['arm'] == b and r['n'] == n)
                va = -1 if va is None else va
                vb = -1 if vb is None else vb
                wins += va > vb; losses += va < vb; ties += va == vb
            pairs[f'{a} vs {b}'] = {'wins': wins, 'losses': losses, 'ties': ties,
                                    'exploratory_sign_p': sign_test(wins, losses)}
    any_error = any(r['classification']['status'] == 'HARNESS_ERROR' for r in rows)
    return {
        'schema': 'genesis-ladder-results-v1', 'preregistration': prereg_id, 'domain': prereg.domain,
        'completed_utc': utcnow(), 'rows': rows, 'per_arm_test_summary': per_arm, 'paired_test_comparisons': pairs,
        'answer_key': {'sha256': prereg.answer_key_sha256, 'source': answer_key(prereg.domain)['source']},
        'status': 'HARNESS_ERROR' if any_error else 'PUBLIC_CALIBRATION_COMPLETE',
        'evidence': {'math': 'WITNESS_VALID', 'utility': 'DEV_ONLY', 'novelty': 'REDISCOVERY',
                     'effects': ['EXTERNAL_SOURCE'] if prereg.domain == 'c4_host_v2' else []},
        'limitations': [
            'Public calibration: complete hosts and their optima are published; not a sealed evaluation.',
            'Matched values are known optima only according to the cited source; no optimality certificate is produced here.',
            'Realized CPU includes interpreter start-up for every invocation; the final invocation may overshoot.',
            'A frontier candidate is not a discovery until independently re-checked and priority-checked.',
        ],
        'promotion_allowed': False,
    }


def render(results):
    lines = [f"# Known-answer ladder: {results['domain']}", '',
             f"Preregistration `{results['preregistration']}` · status **{results['status']}** · "
             f"answer key `{results['answer_key']['sha256'][:16]}…` [cited: {results['answer_key']['source']['reference']}]", '',
             '## Test rungs', '', '| Arm | Matched | Unbroken height | Total shortfall | Max CPU/budget |',
             '|---|---:|---:|---:|---:|']
    for name, a in results['per_arm_test_summary'].items():
        lines.append(f"| {name} | {a['matched_known_optimum']}/{a['test_rungs']} | "
                     f"{a['unbroken_height_from_first_test_rung'] or '—'} | {a['total_shortfall_on_exact_rungs']} | "
                     f"{a['realized_cpu_over_budget_max']} |")
    lines += ['', '## Per rung', '', '| Split | n | Arm | Best | Reference | Status | Invocations |',
              '|---|---:|---|---:|---|---|---:|']
    for r in results['rows']:
        c = r['classification']
        ref = c.get('reference', c.get('bounds', '—'))
        lines.append(f"| {r['split']} | {r['n']} | {r['arm']} | {r['best_value']} | {ref} | {c['status']} | "
                     f"{r['invocations']} |")
    lines += ['', '## Paired test comparisons (exploratory)', '']
    for pair, p in results['paired_test_comparisons'].items():
        lines.append(f"- {pair}: {p['wins']}/{p['losses']}/{p['ties']} W/L/T, sign p = {p['exploratory_sign_p']:.3g}")
    lines += ['', '## Limitations', ''] + [f'- {x}' for x in results['limitations']]
    lines += ['', 'Promotion allowed: **no**.', '']
    from .kernel.wording import require_clean
    return require_clean('\n'.join(lines), {'math': 'WITNESS_VALID', 'utility': 'DEV_ONLY', 'causality': 'NOT_TESTED',
                                              'improver': 'NOT_TESTED', 'novelty': 'REDISCOVERY', 'replication': 'NONE'})
