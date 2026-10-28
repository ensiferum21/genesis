#!/usr/bin/env python3
"""B20_R159 (PT-1): the proving test (Daniel, 27 Oct 2026, 20:22). DRAFT: NOT PREREGISTERED.

    taskset -c 0 python3 scripts/b20r159_proving_test.py evidence/proving_test_b20r159     run ALONE (resumable)

**This file is a draft.** `PREREGISTERED` is False, and `main` refuses a registered run until it is True. The
constants marked PROVISIONAL are still to be fixed (`docs/handoff/PT1_DESIGN_DRAFT.md`, "Still open"). Fixing them,
setting `PREREGISTERED`, committing, and recording the script's SHA-256 is the preregistration. Nothing here has run
on family A, B or C. The design tests run it end to end on invented families only.

**The test** has five parts, each scored separately. PROVED_OUT requires all five.
  1. Discover a useful new representation.
  2. Establish a nontrivial mathematical consequence.
  3. Extract the procedure.
  4. Use it in another family.
  5. Show that the improved inventor outperforms its predecessor at matched total compute.
**Part 1's mechanisms** (Daniel, 28 Oct 2026, 00:53, "Do the hardest so it proves it can find its way"): only
library learning over Γ (`conjecture/library.py`) and operators acting on Γ's own operations
(`conjecture/operations.py`, the engine's `derive`). Templates abstracted from convergence (`conjecture/abstraction.py`)
are the engine's standing abstraction. Whether they count for part 1 is the setting PART1_MECHANISMS.

**The families** (posed under opaque ids drawn from SEALED_SEED; every status stays kernel side):
  * A: the Laplacian bounds held out of F4 and F5 (`sealed.PROVING_TEST_HOLDOUT`: 18, 21, 24, 30, 40), each refuted
    in the literature only by large constructions;
  * B: the Graffiti statements of WOWII that are disproved (25) or open (9), posed as text (`wowii.TEXT`), checked
    by `wowii.verifier` with two independent invariant implementations;
  * C: fresh tasks, Genesis's own conjectures from its own data, pooled over the data seeds C_SEEDS
    (`conjecture.generate`). Conjectures equivalent to a published bound or to one of A are withheld, as in
    B20_R158.

**Arms.**
  * P0, the predecessor: the Frontier's allocation with the starting representations only (no abstraction, no
    derivation).
  * G, Genesis: the Frontier with abstraction (templates, then library learning) and derivation (`p_derive` P_DERIVE).
  * On A and C, every program representation is capped at PROGRAM_MAX_N vertices in every arm. B keeps its search
    limit of 18, which its verifier needs.

**Stages** (each saved, so the study resumes after a pause):
  1. A: P0 and G jointly over A, each at |A| x B_A evaluations. Kernel: a refutation counts if the rational
     Rayleigh certificate and a second exact check confirm it (Sturm for n <= 40; the matrix form above that).
     - The inadequacy gate: if P0 certifies anything in A, A is not unfamiliar, and the verdict is
       INADEQUACY_GATE_FAILED.
     - Part 2 passes if G certifies a bound in A.
  2. Part 1 (`frontier/ablation.py`): the representation credited with G's first discovery in A must have been made
     by a mechanism in PART1_MECHANISMS, and be useful by the ablation (k = K_ABLATION fresh seeds, at the branch's
     compute when it verified).
  3. Part 3 (`frontier/procedure.py`): the procedure extracted from G's log for that discovery must
     - name no problem and no representation the run made;
     - and, replayed by the improved inventor (`ProcedurePolicy`) on a fresh domain over A at G's budget, certify the
       same bound again.
  4. Part 4, on B: the improved inventor (G's settings plus the procedure) against its predecessor (G's settings
     without it), at the same |B| x B_B evaluations. Two statistics, with Holm over them:
     - (a) the exact one-sided McNemar test on statements certified by one arm only;
     - (b) on statements both certify, the paired evaluations to the first certificate, by a one-sided Wilcoxon test.
     It passes if either has p_Holm < ALPHA and at least one improved certificate came from a branch the procedure
     opened.
  5. Part 5, on C: the same two arms at matched TOTAL compute. The improved arm is charged the compute G spent on A
     up to the discovery, so it gets |C| x B_C minus that, and the predecessor |C| x B_C. The same two statistics and
     rule as part 4. There is no causal-use condition: the charge is the price of the procedure.
**Verdict:** INVALID if validity fails; else INADEQUACY_GATE_FAILED if the gate fails; else PROVED_OUT if parts 1-5
all pass; else NOT_PROVED_OUT, naming the parts that failed. Parts 1 and 3-5 need part 2's discovery; without it
they fail.
**Validity:**
  * the forbidden-concept audit of the research plane is clean;
  * no certificate in C against a conjecture equivalent to a proved bound;
  * every arm spent its budget, to within one quantum and one verification;
  * the pins (filled at preregistration).

**Status.** DEV; licenses nothing.
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

STUDY = 'b20r159'
PREREGISTERED = False                     # set at preregistration, with the constants below fixed
SEALED_SEED = None                        # PROVISIONAL: a fresh seed at preregistration
C_SEEDS = ()                              # PROVISIONAL: fresh data seeds at preregistration (C pools their draws)
B_A = 100_000                             # PROVISIONAL: evaluations per bound of A (F4's B_PER; set from F4's timings)
B_B = 20_000                              # PROVISIONAL: evaluations per statement of B
B_C = 20_000                              # PROVISIONAL: evaluations per task of C
C_COUNT = 600                             # C's data: graphs drawn by Genesis (as B20_R158)
P_DERIVE = 0.2                            # PROVISIONAL: fixed from F3-F5, never tuned on A, B or C
RHO = 0.5                                 # the improved inventor's share for its procedures (`ProcedurePolicy`)
PROGRAM_MAX_N = 400                       # one cap for every program representation and arm (the draft's item 7)
K_ABLATION = 5
PART1_MECHANISMS = ('derivation', 'library', 'template')   # PROVISIONAL: whether a template counts (item 8)
QUANTUM, CHUNK = 500, 400
ALPHA = 0.05
SLICE_S, PAUSED = 6600, 3
MODULES = ('frontier/direction.py', 'frontier/curves.py', 'frontier/converge.py', 'frontier/allocate.py',
           'frontier/engine.py', 'frontier/manifest.py', 'frontier/procedure.py', 'frontier/ablation.py',
           'conjecture/expr.py', 'conjecture/graphs.py', 'conjecture/attack.py', 'conjecture/domain.py',
           'conjecture/abstraction.py', 'conjecture/generate.py', 'conjecture/operations.py', 'conjecture/library.py',
           'conjecture/invariants.py', 'conjecture/statement.py', 'conjecture/invariant_domain.py',
           'conjecture/sealed.py', 'conjecture/verify.py', 'conjecture/wowii.py', 'conjecture/invariants_ref.py',
           'conjecture/audit.py')
PINNED = {}                               # `pins()` at preregistration; checked at run time
OUTPUT = ROOT / 'evidence' / 'proving_test_b20r159'


class Paused(Exception):
    pass


def h(*parts):
    return hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()


def pins():
    return {m: hashlib.sha256((ROOT / 'src/genesis' / m).read_bytes()).hexdigest() for m in MODULES}


# ---------------------------------------------------------------------------------------------- the kernel's side

def posed_a(seed):
    """({opaque id: (formula, kind)}, {opaque id: bound number}) for family A."""
    from genesis.conjecture import sealed as SD
    ids = {k: 'A' + h(STUDY, seed, 'A', k)[:10] for k in SD.PROVING_TEST_HOLDOUT}
    return ({ids[k]: (SD.BOUNDS[k][0], SD.kind(k)) for k in SD.PROVING_TEST_HOLDOUT},
            {ids[k]: k for k in SD.PROVING_TEST_HOLDOUT})


def posed_b(seed):
    """({opaque id: text}, {opaque id: statement number}) for family B: the disproved and open statements."""
    from genesis.conjecture import wowii as W
    nums = sorted(list(W.DISPROVED) + list(W.OPEN), key=str)
    ids = {k: 'S' + h(STUDY, seed, 'B', k)[:10] for k in nums}
    return {ids[k]: W.TEXT[k] for k in nums}, {ids[k]: k for k in nums}


def b_verifier(numbers):
    """Family B's kernel verifier (`wowii.verifier`: both invariant implementations must agree)."""
    from genesis.conjecture import wowii as W
    return W.verifier(numbers)


def posed_c(seed, data_seeds, count=C_COUNT):
    """({opaque id: (formula, 'vertex')}, {opaque id: label}, withheld) for family C: the conjectures of every data
    draw, pooled; one equivalent to a conjecture already posed is skipped. (One draw gives few: 7 posed and 2
    withheld on the development seed 991001, too few for part 5's statistics.)"""
    import numpy as np
    from genesis.conjecture import generate as GN
    posed, labels, withheld = {}, {}, []
    for data_seed in data_seeds:
        data = GN.data(np.random.default_rng(data_seed), count=count)
        for f, _ in GN.conjectures(data):
            if any(GN.equivalent(f, g) for g, _ in posed.values()) or any(GN.equivalent(f, g) for g in withheld):
                continue
            w, label = c_label(f)
            if w:
                withheld.append(f)
                continue
            pid = 'C' + h(STUDY, seed, 'C', f)[:10]
            posed[pid] = (f, 'vertex')
            labels[pid] = label
    return posed, labels, withheld


def c_label(formula):
    """(withheld, label): withheld if equivalent to a bound of A or to any published bound; labelled if proved."""
    from genesis.conjecture import generate as GN
    from genesis.conjecture import sealed as SD
    for k in SD.BOUNDS:
        if SD.kind(k) == 'vertex' and GN.equivalent(formula, SD.BOUNDS[k][0]):
            return True, f'bound {k} ({SD.status(k)})'
    for name, f in (('Merris 1998', 'd + m'), ('Li-Pan 2001', 'sqrt(2*d^2 + 2*d*m)'), ('2 Delta', '2*d')):
        if GN.equivalent(formula, f):
            return True, f'{name} (proved)'
    return False, None


def double_check(formula, kind, art):
    """'CONFIRMED', 'UNCONFIRMED' (the Rayleigh certificate only) or 'REJECTED' (B20_R158's rule)."""
    from fractions import Fraction
    from genesis.conjecture import verify as V
    try:
        edges = [tuple(e) for e in art['edges']]
        x = [Fraction(v) for v in art['x']]
        if V.check(formula, kind, art['n'], edges, x)['verdict'] != 'REFUTED':
            return 'REJECTED'
        second = V.check_charpoly(formula, kind, art['n'], edges) if art['n'] <= 40 else \
            V.check_matrix_form(formula, kind, art['n'], edges, x)
    except (KeyError, ValueError, ZeroDivisionError, TypeError):
        return 'REJECTED'
    return 'CONFIRMED' if second and second['verdict'] == 'REFUTED' else 'UNCONFIRMED'


def mcnemar_one_sided(b, c):
    from math import comb
    n = b + c
    return 1.0 if n == 0 else sum(comb(n, k) for k in range(b, n + 1)) / 2 ** n


def wilcoxon_less(x, y):
    """One-sided paired Wilcoxon (x below y), zeros dropped: {'n', 'p'}; p 1.0 with no pair."""
    from scipy.stats import wilcoxon
    d = [a - b for a, b in zip(x, y) if a != b]
    return {'n': len(d), 'p': float(wilcoxon(d, alternative='less').pvalue) if d else 1.0}


def holm(ps):
    order = sorted(ps, key=lambda k: ps[k])
    out, run = {}, 0.0
    for i, k in enumerate(order):
        run = max(run, min(1.0, (len(ps) - i) * ps[k]))
        out[k] = run
    return out


def compare(improved, predecessor, problems):
    """Parts 4 and 5: the two statistics over `problems` and their Holm-adjusted p."""
    ci, cp = set(improved['certified']), set(predecessor['certified'])
    b, c = len((ci - cp) & set(problems)), len((cp - ci) & set(problems))
    shared = sorted((ci & cp) & set(problems))
    t = wilcoxon_less([improved['first'][p] for p in shared], [predecessor['first'][p] for p in shared])
    ph = holm({'mcnemar': mcnemar_one_sided(b, c), 'first': t['p']})
    return {'improved_only': b, 'predecessor_only': c, 'shared': len(shared), 'wilcoxon_n': t['n'],
            'p_mcnemar': mcnemar_one_sided(b, c), 'p_first': t['p'], 'p_holm': ph,
            'pass': min(ph.values()) < ALPHA}


# ------------------------------------------------------------------------------------------- the research plane

def conjecture_domain(problems, abstraction):
    from genesis.conjecture.domain import ConjectureDomain
    return ConjectureDomain(problems, abstraction=abstraction, program_max_n=PROGRAM_MAX_N)


def invariant_domain(problems, abstraction):
    from genesis.conjecture.invariant_domain import InvariantDomain
    return InvariantDomain(problems, abstraction=abstraction)          # B keeps its own search limit (18)


def settings(arm, proc=None):
    """(policy, policy params, abstraction) for an arm."""
    if arm == 'P0':
        return 'frontier', {'p_derive': 0.0}, False
    if arm in ('G', 'predecessor'):
        return 'frontier', {'p_derive': P_DERIVE}, True
    if arm == 'improved':
        return 'procedure', {'p_derive': P_DERIVE, 'procedures': [proc], 'rho': RHO}, True
    raise ValueError(arm)


def run_engine(tag, dom, verify, arm, budget, out, deadline, proc=None, seed_parts=()):
    """Run (or resume) one engine to its budget; returns (engine, domain); pauses at the deadline (state saved)."""
    from genesis.frontier.engine import Frontier
    from genesis.frontier.manifest import Manifest
    policy, params, abstraction = settings(arm, proc)
    m = Manifest(dom, verify, budget, quantum=QUANTUM, description={'study': STUDY, 'stage': tag, 'arm': arm})
    state, dstate = out / f'state_{tag}.json', out / f'state_{tag}.domain.json'
    if dstate.exists():
        dom.restore(json.loads(dstate.read_text()))
    if state.exists():
        e = Frontier.load(state, m, policy_params=params)
    else:
        e = Frontier(m, policy, seed=int(h(STUDY, tag, arm, *seed_parts)[:8], 16), abstraction=abstraction,
                     branch_out=False, policy_params=params)
    while True:
        status = e.run(CHUNK)
        e.save(state)
        dstate.write_text(json.dumps(dom.state(), default=list))
        if status == 'done':
            return e, dom
        if time.monotonic() > deadline:
            raise Paused


def record(e, problems):
    """An arm's record: what it certified (by the engine's verifier), when, through which branches."""
    first, via = {}, {}
    for ev in e.events:
        if ev['kind'] == 'verified':
            first.setdefault(ev['problem'], ev['spent'])
            d = e.branches[ev['branch']]['direction']
            via.setdefault(ev['problem'], {'representation': d['representation'], 'method': d['method'],
                                           'op': d.get('op')})
    return {'spent': e.spent, 'budget': e.budget, 'claimed': sorted(p for p, v in e.best_verified.items() if v > 0),
            'artifacts': {p: {k: a[k] for k in ('n', 'edges', 'x') if k in a} for p, a in e.best_artifact.items()},
            'first': first, 'via': via, 'branches': len(e.branches)}


# ------------------------------------------------------------------------------------------------------- main

def main(argv=None, registered=True, families=None, budgets=None, seed=None):
    """Run (or resume) the test; 0 when done, PAUSED at the end of a time slice. `families` ({'A': (posed, numbers),
    'B': (posed, verifier factory), 'C': posed}) and `budgets` replace the sealed families in the design tests."""
    from genesis.conjecture import audit as AU
    from genesis.conjecture import verify as V
    from genesis.frontier import ablation as AB
    from genesis.frontier import procedure as PR
    argv = sys.argv[1:] if argv is None else argv
    out = Path(argv[0]).resolve()
    if registered:
        if not PREREGISTERED:
            raise SystemExit('PT-1 is a draft: it is not preregistered')
        if out != OUTPUT.resolve():
            raise SystemExit(f'the registered output is {OUTPUT}')
        if pins() != PINNED:
            raise SystemExit('the modules differ from the preregistered pins')
    out.mkdir(parents=True, exist_ok=True)
    seed = SEALED_SEED if seed is None else seed
    b_a, b_b, b_c = budgets or (B_A, B_B, B_C)
    t0 = time.monotonic()
    deadline = t0 + SLICE_S
    if families is None:
        pa, number_a = posed_a(seed)
        pb, number_b = posed_b(seed)
        verify_b = b_verifier(number_b)
        pc, labels_c, withheld_c = posed_c(seed, C_SEEDS)
    else:
        pa, number_a = families['A']
        pb, verify_b = families['B']
        number_b = {p: p for p in pb}
        pc, labels_c, withheld_c = families['C'], {p: None for p in families['C']}, []
    verify_a, verify_c = V.verifier(pa), V.verifier(pc)
    stages = out / 'stages.json'
    done = json.loads(stages.read_text()) if stages.exists() else {}

    def save(key, value):
        done[key] = value
        stages.write_text(json.dumps(done, indent=1, sort_keys=True, default=list))

    made = 0

    def due():
        return deadline if made else deadline + 10 ** 9            # every slice makes progress

    try:
        # stage 1: A, P0 and G
        engines = {}
        for arm in ('P0', 'G'):
            key = f'A_{arm}'
            e, dom = run_engine(key, conjecture_domain(pa, arm == 'G'), verify_a, arm, len(pa) * b_a, out, due())
            engines[arm] = (e, dom)
            if key not in done:
                rec = record(e, pa)
                rec['certified'] = [p for p in rec['claimed']
                                    if double_check(*pa[p], rec['artifacts'][p]) == 'CONFIRMED']
                save(key, rec)
                made += 1
        gate = not done['A_P0']['certified']
        found = [p for p in sorted(done['A_G']['first'], key=lambda p: done['A_G']['first'][p])
                 if p in done['A_G']['certified']]
        disc = found[0] if found else None
        if gate and disc is not None:
            e, dom = engines['G']
            # stage 2: part 1
            if 'part1' not in done:
                ab = AB.ablate(e, disc, verify_a, list(dom.representations), k=K_ABLATION)
                if ab is not None:
                    name = ab['representation']
                    ab['mechanism'] = ('derivation' if name in dom.derived else 'library' if name in dom.libraries
                                       else 'template' if name in dom.templates else ab['how'])
                save('part1', ab)
                made += 1
            # stage 3: part 3
            proc = PR.extract(e, disc)
            if 'part3_procedure' not in done:
                made_names = set(dom.templates) | set(dom.derived) | set(dom.libraries)
                text = json.dumps(proc['steps'] if proc else None, sort_keys=True)
                names = sorted(x for x in set(pa) | made_names if x in text)
                save('part3_procedure', {'procedure': proc, 'names': names})
                made += 1
            if 'part3_replay' not in done and proc is not None:
                er, _ = run_engine('A_replay', conjecture_domain(pa, True), verify_a, 'improved', len(pa) * b_a, out,
                                   due(), proc=proc)
                rec = record(er, pa)
                rec['certified'] = [p for p in rec['claimed']
                                    if double_check(*pa[p], rec['artifacts'][p]) == 'CONFIRMED']
                save('part3_replay', rec)
                made += 1
            # stage 4: part 4 on B
            if proc is not None:
                for arm in ('improved', 'predecessor'):
                    key = f'B_{arm}'
                    if key in done:
                        continue
                    eb, _ = run_engine(key, invariant_domain(pb, True), verify_b, arm, len(pb) * b_b, out, due(),
                                       proc=proc)
                    rec = record(eb, pb)
                    rec['certified'] = [p for p in rec['claimed'] if verify_b(p, rec['artifacts'][p]) > 0]
                    save(key, rec)
                    made += 1
                # stage 5: part 5 on C, at matched total compute
                charge = next(ev['spent'] for ev in e.events if ev['kind'] == 'verified' and ev['problem'] == disc)
                total = len(pc) * b_c
                for arm in ('improved', 'predecessor'):
                    key = f'C_{arm}'
                    if key in done:
                        continue
                    budget = total - charge if arm == 'improved' else total
                    if budget < QUANTUM:
                        save(key, {'spent': 0, 'budget': budget, 'claimed': [], 'certified': [], 'artifacts': {},
                                   'first': {}, 'via': {}, 'branches': 0, 'charge': charge})
                        continue
                    ec, _ = run_engine(key, conjecture_domain(pc, True), verify_c, arm, budget, out, due(),
                                       proc=proc)
                    rec = record(ec, pc)
                    rec['certified'] = [p for p in rec['claimed']
                                        if double_check(*pc[p], rec['artifacts'][p]) == 'CONFIRMED']
                    rec['charge'] = charge
                    save(key, rec)
                    made += 1
    except Paused:
        return PAUSED
    summary = analyse(done, pa, pb, pc, number_a, number_b, labels_c, withheld_c, registered)
    summary['audit_hits'] = AU.scan(AU.research_plane(ROOT))
    summary['valid'] = summary['valid'] and not summary['audit_hits']
    summary['verdict'], summary['failed'] = verdict(summary)
    summary.update(study=STUDY, schema='genesis-b20r159-proving-test-v1', preregistered=PREREGISTERED,
                   code_identity=code_identity(ROOT)['sha256'], status='DEV; licenses nothing')
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True, default=list) + '\n')
    print(json.dumps({k: summary[k] for k in ('verdict', 'failed', 'valid', 'parts')}, indent=1, default=list))
    return 0


def spent_ok(rec):
    return rec['budget'] < QUANTUM or rec['spent'] >= rec['budget'] - QUANTUM - 1


def analyse(done, pa, pb, pc, number_a, number_b, labels_c, withheld_c, registered):
    """The parts, validity and the record (kernel side)."""
    from genesis.conjecture import generate as GN
    from genesis.conjecture import sealed as SD
    p0, g = done['A_P0'], done['A_G']
    gate = not p0['certified']
    found = sorted((p for p in g['certified']), key=lambda p: g['first'][p])
    disc = found[0] if found else None
    parts = {'gate': gate, 'part2': bool(found)}
    ab = done.get('part1')
    parts['part1'] = bool(ab and ab['useful'] and ab.get('mechanism') in PART1_MECHANISMS)
    pr = done.get('part3_procedure')
    rp = done.get('part3_replay')
    parts['part3'] = bool(pr and pr['procedure'] and not pr['names'] and rp and disc in rp['certified'])
    stats = {}
    for fam, problems in (('B', pb), ('C', pc)):
        imp, pre = done.get(f'{fam}_improved'), done.get(f'{fam}_predecessor')
        if imp is None or pre is None:
            parts[f'part{4 if fam == "B" else 5}'] = False
            continue
        s = compare(imp, pre, list(problems))
        if fam == 'B':
            s['causal_use'] = any(imp['via'][p]['op'] == 'procedure' for p in imp['certified'] if p in imp['via'])
            parts['part4'] = s['pass'] and s['causal_use']
        else:
            parts['part5'] = s['pass']
        stats[fam] = s
    proved_c = sorted({pc[p][0] for k in ('C_improved', 'C_predecessor') for p in done.get(k, {}).get('certified', [])
                       if _proved_equivalent(*pc[p], GN, SD)})
    spent = all(spent_ok(done[k]) for k in done if (k[:2] in ('A_', 'B_', 'C_') or k == 'part3_replay')
                and 'spent' in done[k])
    pins_ok = (not registered) or pins() == PINNED
    valid = not proved_c and spent and pins_ok
    return {'parts': parts, 'stats': stats, 'discovery': disc, 'discovery_bound': number_a.get(disc),
            'certified_A': {a: sorted(number_a[p] for p in done[f'A_{a}']['certified']) for a in ('P0', 'G')},
            'part1': ab, 'part3': {'names': pr['names'] if pr else None, 'replayed': bool(rp and disc in rp['certified'])},
            'certified_B': {a: sorted(str(number_b[p]) for p in done.get(f'B_{a}', {}).get('certified', []))
                            for a in ('improved', 'predecessor')},
            'C': {'posed': len(pc), 'withheld': len(withheld_c), 'labels': labels_c},
            'proved_equivalents_refuted': proved_c, 'spent_ok': spent, 'pins_ok': pins_ok, 'valid': valid}


CLASSICAL_PROVED = (('d + m', 'vertex'), ('sqrt(2*d^2 + 2*d*m)', 'vertex'), ('2*d', 'vertex'), ('di + dj', 'edge'))


def _proved_equivalent(formula, kind, GN, SD):
    """Whether a conjecture is equivalent to a proved bound of its kind (vertex or edge)."""
    if any(SD.kind(k) == kind and SD.status(k) == 'proved' and GN.equivalent(formula, SD.BOUNDS[k][0], kind=kind)
           for k in SD.BOUNDS):
        return True
    return any(k == kind and GN.equivalent(formula, f, kind=kind) for f, k in CLASSICAL_PROVED)


def verdict(s):
    if not s['valid']:
        return 'INVALID', []
    if not s['parts']['gate']:
        return 'INADEQUACY_GATE_FAILED', []
    failed = [k for k in ('part1', 'part2', 'part3', 'part4', 'part5') if not s['parts'][k]]
    return ('PROVED_OUT' if not failed else 'NOT_PROVED_OUT'), failed


if __name__ == '__main__':
    sys.exit(main())
