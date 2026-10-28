#!/usr/bin/env python3
"""B20_R157 (F4): Genesis's Frontier against prior-art counterexample searches on the sealed Laplacian bounds (DEV,
preregistered)

    taskset -c 0 python3 scripts/b20r157_laplacian_bounds.py evidence/laplacian_bounds_b20r157     run ALONE (resumable; slices exit 3)

**Why.** Daniel's directive of 27 Oct 2026, 19:55 (`docs/OMEGA_FRONTIER.md`): an engine that imagines, extrapolates,
converges and allocates without handholding, in a domain where discoveries are verified exactly. The domain: the 68
candidate upper bounds on the Laplacian spectral radius mu of Brankov, Hansen and Stevanovic (2006). As of June 2026
(arXiv 2606.14550), 44 are refuted, 22 proved and 2 open (44 and 46).

**The sealed set** (`conjecture.sealed.sealed()`, kernel side): the 56 bounds of tiers A1 and A2, without the
duplicate 23 and without the proving test's family A (18, 21, 24, 30, 40). Of these, 21 are proved (the nulls), 33
refuted and 2 open. Each is posed to every arm by its formula only, under an opaque id drawn from SEALED_SEED; no arm
sees any status.

**Arms** (matched compute in evaluations, one evaluation being one candidate graph scored; CPU recorded):
  * FRONTIER: the Frontier (`frontier.engine`, allocation policy only: no abstraction or branching out is defined in
    this domain yet) over all 56 bounds jointly, with B_TOTAL = 56 x B_PER evaluations. It chooses the
    representation (edge bits, Pruefer trees, bounded degree 4, programs of the construction language Gamma), the
    method (hill climbing, annealing, evolution, GBFS, CEM, NRPA) and n (8, 12, 16, 20, 28) per direction, and how
    much each bound gets;
  * UCB and UNIFORM: the same engine and space, with the UCB1 and uniform policies (the allocators of F3);
  * three single prior-art searches, run per bound with B_PER evaluations each, at settings from the literature:
    NRPA on edge bits at n = 20 (Roucairol and Cazenave 2025 recommend NRPA among their best; n = 20 as Ghebleh et
    al. 2024's RL); GBFS on bounded-degree graphs at n = 12 (the 2025 paper's best single method; Ghebleh et al.'s
    subquartic class at n = 12); CEM on edge bits at n = 20 (the cross-entropy method; Wagner 2021 used a network
    policy, here independent edge probabilities).
B_PER = 100,000 evaluations (about 15 s per bound for a single search, from a timing pilot on invented bounds).

**Verification** (kernel side). A refutation counts only if two exact checks confirm it:
  * the rational Rayleigh certificate (`verify.check`);
  * the Sturm count on the exact characteristic polynomial (`verify.check_charpoly`, n <= 40).
A refutation that only the first confirms is reported as UNCONFIRMED and not counted.

**Primary (Holm over the five comparators, alpha 0.05).** On the 33 known-false bounds, FRONTIER against each
comparator c: the exact one-sided McNemar test on the bounds refuted by exactly one of the two. c is BEATEN if
p_Holm < 0.05. **Verdict:** INVALID if validity fails; else FRONTIER_BETTER if every comparator is beaten; PARTIAL
(naming those beaten) if some are; NOT_SHOWN if none is.
**Secondary:**
  * refutations per arm, also without the six bounds attacked in a development look (2, 3, 36, 48, 57 and 61; 48 is
    not in the set);
  * where the Frontier's refutations came from (representation, method, n);
  * **bounds 44 and 46**: any doubly confirmed certificate is a candidate new result. It is checked against the
    literature before anything is said, and saved with its certificate.
**Validity:**
  * no doubly confirmed certificate against any of the 21 proved bounds (one would mean a verifier or transcription
    error);
  * every arm spent its budget (the joint arms to within one quantum);
  * the pinned module digests.

**Expectation, stated before running (low confidence).**
  * Most of the 33 refuted bounds fall to every arm: small counterexamples exist (Ghebleh et al.'s subquartic n = 12
    disproved 23 at once), and B_PER is generous.
  * The arms differ on a handful of bounds, so the McNemar tests have few discordant pairs.
  * Verdict NOT_SHOWN or PARTIAL (UNIFORM beaten).
  * Bounds 44 and 46 are not refuted.

**Development looks (disclosed).**
  * The timing pilot used invented bounds only.
  * The six refuted bounds above were attacked once in a smoke test while the attacks were built; nothing was tuned
    on the results.
  * The transcription checks (`evidence/bhs_transcription_f2/`) evaluated every sealed formula on all graphs with at
    most 7 vertices.

**Cost.** Single searches about 56 x 3 x 15 s; the joint arms about 3 x 15-30 min: about 2 h, in slices of 6,600 s.
**Status.** DEV; licenses nothing; adopts nothing.

**Amendment (28 Oct 2026, 10:55 SGT, after a first attempt was killed and before any of its results was looked at;
disclosed).** The first attempt, from `bdf0c57`, was killed by the memory limit (6.1 GB) about two minutes into its
first joint arm, after the 168 single-search runs. The cause was a defect in `conjecture/attack.py`: the size of a Γ
program counted a star S_k as k vertices, while `_build` makes it k leaves and a centre. Nested products of stars
therefore passed the 64-vertex cap and built graphs of thousands of vertices (an eigensolve on one took 0.35 s). The
size now counts the centre; nothing else in the design changes. The study runs from the amendment commit, whose
other changes since `bdf0c57` are inert at this study's settings (abstraction off, `p_derive` 0): this script's
`main` on invented bounds gave the same rows from `bdf0c57` with only the fix and from the amendment commit. The
pins below are the amended modules. The first attempt's rows are kept in
`evidence/laplacian_bounds_b20r157_attempt1/`; only their arm and problem keys were read, to find where it stopped.
They are not used: every arm, the single searches included, runs again.
"""
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from genesis.common import code_identity  # noqa: E402

STUDY = 'b20r157'
SEALED_SEED = 61884213
B_PER = 100_000
QUANTUM = 500
JOINT = ('FRONTIER', 'UCB', 'UNIFORM')
SINGLE = {'NRPA': ('edges', 'nrpa', 20), 'GBFS': ('bounded', 'gbfs', 12), 'CEM': ('edges', 'cem', 20)}
ARMS = JOINT + tuple(SINGLE)
COMPARATORS = ('UCB', 'UNIFORM', 'NRPA', 'GBFS', 'CEM')
DEV_LOOKED = (2, 3, 36, 48, 57, 61)
ALPHA = 0.05
SLICE_S, PAUSED = 6600, 3
CHUNK = 400                                     # joint-arm steps between time checks and state saves
MODULES = ('frontier/direction.py', 'frontier/curves.py', 'frontier/converge.py', 'frontier/allocate.py',
           'frontier/engine.py', 'frontier/manifest.py', 'conjecture/expr.py', 'conjecture/graphs.py',
           'conjecture/attack.py', 'conjecture/domain.py', 'conjecture/sealed.py', 'conjecture/verify.py')
PINNED = {             # `pins()` at preregistration; checked at run time
    'frontier/direction.py': '3b54f061f5979b6527e75785a7694c47bb19ac61ac8dd64ff9aa47ee17416940',
    'frontier/curves.py': 'e531ef807bad4007e6bc04071fd3173d1eacfd98b53f26780622d9b328caa0a9',
    'frontier/converge.py': 'fec005b93be9b5e5320c5a587c8291ead0b2d9028514779ab424cbbda9a8a956',
    'frontier/allocate.py': 'fca1f97867264963539f533831cfbb6c8384501dc4007e2c948d7e2aaea53550',
    'frontier/engine.py': 'bbea0852b1ecaec56ffa4ac669a6ef5e1375f47b5fcb4f71289af62c8b0ef150',
    'frontier/manifest.py': 'c9fb74568982cb8c554311559eba29d2c7fc6c30194f99229a71b63ac54a2a46',
    'conjecture/expr.py': '75690202d6a7ab54f75a76500ada6e675b51cf23e7b78b20b4c33f90bc62adf9',
    'conjecture/graphs.py': 'f84059118cf6d74a8ca218fefc98593110e5634353655323b2b108fbca42a972',
    'conjecture/attack.py': '59c4cdb6e5517abd9e3b6ba2642f66893db6fc17b5aab3e2d6983b6cfc5d5ef8',
    'conjecture/domain.py': '0671ad30f0deb234b202fa830f0af4f105bd26c5b6de4600f4c7ad26ea8760bf',
    'conjecture/sealed.py': 'ae7d429c76e12171f9918213eaef9c33d83a1ffbd7d905953b9a79d129f41bcf',
    'conjecture/verify.py': '712c5fc1ed0c4404ac2f423c12cb7356cf9e9a90b305e19ebd293b5ec2cc0706',
}


class Paused(Exception):
    pass


def h(*parts):
    return hashlib.sha256(json.dumps(parts, sort_keys=True).encode()).hexdigest()


def pins():
    return {m: hashlib.sha256((ROOT / 'src/genesis' / m).read_bytes()).hexdigest() for m in MODULES}


def posed():
    """({opaque id: (formula, kind)}, {opaque id: number}) for the sealed set."""
    from genesis.conjecture import sealed as SD
    bounds = SD.sealed()
    ids = {k: 'B' + h(STUDY, SEALED_SEED, k)[:10] for k in bounds}
    return {ids[k]: (f, kind) for k, (f, kind, _) in bounds.items()}, {ids[k]: k for k in bounds}


def double_check(formula, kind, art):
    """'CONFIRMED', 'UNCONFIRMED' (Rayleigh only) or 'REJECTED'."""
    from fractions import Fraction
    from genesis.conjecture import verify as V
    try:
        edges = [tuple(e) for e in art['edges']]
        a = V.check(formula, kind, art['n'], edges, [Fraction(v) for v in art['x']])['verdict']
    except (KeyError, ValueError, ZeroDivisionError, TypeError):
        return 'REJECTED'
    if a != 'REFUTED':
        return 'REJECTED'
    b = V.check_charpoly(formula, kind, art['n'], edges)
    return 'CONFIRMED' if b and b['verdict'] == 'REFUTED' else 'UNCONFIRMED'


def run_single(arm, formula, kind, budget):
    """A single prior-art search on one bound: its best certificate candidate and evaluations to its first positive
    score."""
    from genesis.conjecture import attack as AT
    rep, meth, n = SINGLE[arm]
    r = AT.Runner(formula, kind, rep, meth, n, int(h(STUDY, arm, formula)[:12], 16))
    first = None
    c0 = time.process_time()
    while r.evals < budget:
        r.advance(min(1000, budget - r.evals))
        if first is None and r.best > 0:
            first = r.evals
    out = {'evals': r.evals, 'best': r.best, 'first_positive': first, 'cpu': round(time.process_time() - c0, 3)}
    if r.best > 0 and r.best_A is not None:
        nn, es, x = AT.certificate(r.best_A)
        out['artifact'] = {'n': nn, 'edges': [list(e) for e in es], 'x': [str(v) for v in x]}
    return out


def run_joint(arm, problems, budget_total, state_path, deadline):
    """A joint arm over all problems; pauses (saving its state) at the deadline; returns its summary when done."""
    from genesis.conjecture.domain import ConjectureDomain
    from genesis.conjecture import verify as V
    from genesis.frontier.engine import Frontier
    from genesis.frontier.manifest import Manifest
    dom = ConjectureDomain(problems)
    m = Manifest(dom, V.verifier(problems), budget_total, quantum=QUANTUM, description={'study': STUDY, 'arm': arm})
    policy = {'FRONTIER': 'frontier', 'UCB': 'ucb', 'UNIFORM': 'uniform'}[arm]
    if state_path.exists():
        e = Frontier.load(state_path, m)
    else:
        e = Frontier(m, policy, seed=int(h(STUDY, arm)[:8], 16), abstraction=False, branch_out=False)
    c0 = time.process_time()
    while True:
        status = e.run(CHUNK)
        if status == 'done':
            break
        e.save(state_path)
        if time.monotonic() > deadline:
            raise Paused
    first = {}
    for ev in e.events:
        if ev['kind'] == 'verified' and ev['problem'] not in first:
            first[ev['problem']] = ev['spent']
    sources = {}
    for ev in e.events:
        if ev['kind'] == 'verified':
            br = e.branches[ev['branch']]['direction']
            sources[ev['problem']] = [br['representation'], br['method'], br['params']['n']]
    return {'spent': e.spent, 'budget': budget_total, 'refuted': sorted(p for p, v in e.best_verified.items() if v > 0),
            'artifacts': {p: {k: a[k] for k in ('n', 'edges', 'x')} for p, a in e.best_artifact.items()},
            'first': first, 'sources': sources, 'branches': len(e.branches), 'verify_calls': e.verify_calls,
            'cpu_this_slice': round(time.process_time() - c0, 3)}


def mcnemar_one_sided(b, c):
    """P(X >= b) for X ~ Binomial(b + c, 1/2): the exact one-sided McNemar test (b: only FRONTIER refutes)."""
    from math import comb
    n = b + c
    if n == 0:
        return 1.0
    return sum(comb(n, k) for k in range(b, n + 1)) / 2 ** n


def holm(ps):
    order = sorted(ps, key=lambda k: ps[k])
    out, run = {}, 0.0
    for i, k in enumerate(order):
        run = max(run, min(1.0, (len(ps) - i) * ps[k]))
        out[k] = run
    return out


def analyse(refuted, status_of, numbers):
    """refuted: {arm: set of opaque ids doubly confirmed}. Known-false = status refuted-*."""
    false = [p for p in status_of if status_of[p].startswith('refuted')]
    out = {'counts': {a: len(refuted[a] & set(false)) for a in ARMS}}
    tests = {}
    for c in COMPARATORS:
        b = len((refuted['FRONTIER'] - refuted[c]) & set(false))
        cc = len((refuted[c] - refuted['FRONTIER']) & set(false))
        tests[c] = {'frontier_only': b, 'comparator_only': cc, 'p': mcnemar_one_sided(b, cc)}
    ph = holm({c: tests[c]['p'] for c in COMPARATORS})
    for c in COMPARATORS:
        tests[c]['p_holm'] = ph[c]
        tests[c]['label'] = 'BEATEN' if ph[c] < ALPHA else 'NOT_BEATEN'
    out['P1'] = tests
    clean = [p for p in false if numbers[p] not in DEV_LOOKED]
    out['counts_without_dev_looked'] = {a: len(refuted[a] & set(clean)) for a in ARMS}
    out['known_false'] = len(false)
    return out


def verdict(valid, res):
    if not valid:
        return 'INVALID', []
    beaten = [c for c in COMPARATORS if res['P1'][c]['label'] == 'BEATEN']
    if len(beaten) == len(COMPARATORS):
        return 'FRONTIER_BETTER', beaten
    return ('PARTIAL' if beaten else 'NOT_SHOWN'), beaten


def main(argv=None, registered=True, b_per=B_PER, test_problems=None):
    """Run (or resume) the study; 0 when done, PAUSED at the end of a time slice. `test_problems` ({id: (formula,
    kind, status)}, invented bounds) replaces the sealed set in the design tests."""
    from genesis.conjecture import sealed as SD
    argv = sys.argv[1:] if argv is None else argv
    out = Path(argv[0]).resolve()
    if registered and out != (ROOT / 'evidence' / 'laplacian_bounds_b20r157').resolve():
        raise SystemExit('the registered output is evidence/laplacian_bounds_b20r157')
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    deadline = t0 + SLICE_S
    if test_problems is None:
        problems, number_of = posed()
        status_fn = lambda p: SD.status(number_of[p])
    else:
        problems = {p: (f, k) for p, (f, k, _) in test_problems.items()}
        number_of = {p: p for p in test_problems}
        status_fn = lambda p: test_problems[p][2]
    rows_path = out / 'rows.jsonl'
    rows = {}
    if rows_path.exists():
        for line in rows_path.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                rows[(r['arm'], r.get('problem'))] = r
    made = 0
    try:
        for arm in SINGLE:
            for p in sorted(problems):
                if (arm, p) in rows:
                    continue
                if made and time.monotonic() > deadline:
                    raise Paused
                formula, kind = problems[p]
                r = dict(run_single(arm, formula, kind, b_per), arm=arm, problem=p)
                rows[(arm, p)] = r
                with rows_path.open('a') as f:
                    f.write(json.dumps(r, sort_keys=True) + '\n')
                made += 1
        for arm in JOINT:
            if (arm, None) in rows:
                continue
            r = dict(run_joint(arm, problems, b_per * len(problems), out / f'state_{arm}.json',
                               deadline if made else deadline + 10 ** 9), arm=arm, problem=None)
            rows[(arm, None)] = r
            with rows_path.open('a') as f:
                f.write(json.dumps(r, sort_keys=True) + '\n')
            made += 1
    except Paused:
        return PAUSED
    # the kernel's view: double checks and statuses
    status_of = {p: status_fn(p) for p in problems}
    checks, refuted = {}, {}
    for arm in ARMS:
        arts = rows[(arm, None)]['artifacts'] if arm in JOINT else \
            {p: rows[(arm, p)]['artifact'] for p in problems if 'artifact' in rows[(arm, p)]}
        refuted[arm] = set()
        for p, art in sorted(arts.items()):
            formula, kind = problems[p]
            c = double_check(formula, kind, art)
            checks[f'{arm}|{p}'] = c
            if c == 'CONFIRMED':
                refuted[arm].add(p)
    nulls = sorted({number_of[p] for a in ARMS for p in refuted[a] if status_of[p] == 'proved'})
    open_hits = {number_of[p]: sorted(a for a in ARMS if p in refuted[a]) for p in problems
                 if status_of[p] == 'open' and any(p in refuted[a] for a in ARMS)}
    spent_ok = all(rows[(a, None)]['spent'] >= rows[(a, None)]['budget'] - QUANTUM - 1 for a in JOINT) and \
        all(rows[(a, p)]['evals'] >= b_per for a in SINGLE for p in problems)
    pins_ok = (not registered) or pins() == PINNED
    valid = not nulls and spent_ok and pins_ok
    res = analyse(refuted, status_of, number_of)
    v, beaten = verdict(valid, res)
    summary = {'study': STUDY, 'schema': 'genesis-b20r157-laplacian-bounds-v1', 'verdict': v, 'beaten': beaten,
               'valid': valid, 'proved_bounds_refuted': nulls, 'open_bound_certificates': open_hits,
               'spent_ok': spent_ok, 'pins_ok': pins_ok, 'results': res,
               'refuted': {a: sorted(number_of[p] for p in refuted[a]) for a in ARMS},
               'unconfirmed': sorted(k for k, c in checks.items() if c == 'UNCONFIRMED'),
               'frontier_sources': {number_of[p]: s for p, s in rows[('FRONTIER', None)]['sources'].items()},
               'ids': {p: number_of[p] for p in problems}, 'b_per': b_per,
               'code_identity': code_identity(ROOT)['sha256'], 'status': 'DEV; licenses nothing'}
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True, default=list) + '\n')
    print(json.dumps({k: summary[k] for k in ('verdict', 'beaten', 'valid', 'proved_bounds_refuted',
                                                'open_bound_certificates', 'refuted')}, indent=1, default=list))
    return 0


if __name__ == '__main__':
    sys.exit(main())
