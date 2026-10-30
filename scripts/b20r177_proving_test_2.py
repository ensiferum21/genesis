#!/usr/bin/env python3
"""B20_R177 (PT-2): the proving test again, with the inadequacy gate judged bound by bound. PREREGISTERED (30 Oct 2026).

    taskset -c 0 python3 scripts/b20r177_proving_test_2.py evidence/proving_test_2_b20r177     run ALONE (resumable)

**Why a second test.** PT-1 (B20_R159, `docs/checkpoints/B20_R159_RECORD.md`) stopped at its gate: the predecessor P0
certified bound 40 of family A (a 273-vertex graph), so A as a whole was not beyond it, and parts 1 and 3-5 never
ran. G certified bounds 40 and 21 (352 and 360 vertices), both from graph products it derived itself; P0 did not
certify 21. Daniel was asked how to proceed and answered "Do the best" (30 Oct 2026, 20:06 SGT). This test is the
builder's choice, made after seeing PT-1's result (disclosed): the same five parts, the same families, constants,
budgets and pinned code as PT-1, with two changes.
  * **The gate, bound by bound.** The proving test asks for a family where the predecessor's representation is
    inadequate. PT-1 required P0 to certify nothing in A; here the predecessor runs K_GATE = 3 times on A (fresh
    seeds), and the bounds none of its runs certified form A', the part of A beyond it. The gate fails only if A' is
    empty. P0 gets three tries to G's one, so a bound in A' is one the predecessor missed three times at the same
    budget.
  * **The discovery must be in A'.** Part 2 passes if G certifies a bound of A'; G's first such certificate is the
    discovery that parts 1 and 3 study and part 5 charges. A certificate on a bound outside A' does not count.
  * Fresh seeds: opaque ids (SEALED_SEED), engine seeds (STUDY) and C's ten data draws (C_SEEDS) are all new; the
    families' statements are PT-1's.
This is PT-1's code otherwise (copied, with the stage-1 and analysis changes only). Nothing in this file has run on
family A, B or C with these seeds before the first attempt (below). The design tests run it end to end on invented
families only, through the registered path (output and pins redirected).

**Amendment (30 Oct 2026, 21:30 SGT, after a first attempt crashed; disclosed).** The first attempt, from `a7303de`
(`/home/claude/pt2-wt`), ran from 20:23:09 to 21:04:12 SGT and stopped with exit 1 in part 3's replay. The cause was
a defect in `conjecture/library.py` (B20R177-LIBRARY, `docs/BLOCKING_DEFECTS.md`): a macro learned from programs of a
derived representation contains its derived operation ('r<table>'), but the library representation was built
without that operation, so the macro's slots were miscounted, a drawn leaf carried too few parameters, and its
expansion failed (`StopIteration` inside a generator).
  * The repair: a library representation carries every derived operation its macros use (`library.ops_in`; the
    operation's name carries its table). A library whose macros use no derived operation is built exactly as before
    (`test_operations`, `Library.test_a_macro_with_a_derived_operation_expands_and_builds`).
  * The pins below differ from PT-1's (and from `a7303de`'s) in `conjecture/library.py` only.
  * Main on the design tests' invented families gave the same summary from `a7303de` and from the amendment commit.
  * **What the crash revealed (disclosed).** Only the log's traceback was read. It shows the attempt had reached
    part 3's replay, which happens only after the gate held, G certified a bound beyond the predecessor (part 2), and
    a procedure was extracted. Nothing else of that attempt was read, and its files
    (`evidence/proving_test_2_b20r177_attempt1/`) are not used. Every stage runs again, with the same seeds, in a
    fresh output directory. Whether stage 1 repeats exactly depends on whether the first attempt's G drew a library
    macro with a derived operation before part 3; that is not checked, so as not to read the attempt's files.

PT-1's documentation follows, unchanged except where it says what differs.

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
  1. A: P0 K_GATE times and G once over A, each run at |A| x B_A evaluations. Kernel: a refutation counts if the
     rational Rayleigh certificate and a second exact check confirm it (Sturm for n <= 40; the matrix form above
     that).
     - The inadequacy gate (PT-2): A' = the bounds of A that no P0 run certified. If A' is empty, the verdict is
       INADEQUACY_GATE_FAILED.
     - Part 2 passes if G certifies a bound in A' (PT-2).
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
  Secondary in parts 4 and 5 (`docs/OMEGA_FOUNDRY.md` G1), two controls of what the procedure knows against what it
  does:
     - the notebook: the predecessor after every certified counterexample from A has been checked on every task, one
       unit per check, charged;
     - the given representation: the predecessor whose domain starts with the representation credited in part 1
       (`give`), without the procedure.
     On C both are charged the discovery like the improved arm. Each is compared with the improved arm by the same
     two statistics. **Part 5 passes only if the improved arm beats the predecessor and both controls**
     (PART5_REQUIRES_CONTROLS; Daniel delegated the choice on 28 Oct 2026, 10:58 SGT: "Do what's the best"). This
     is an intersection-union test: each comparison must pass at its own level, so requiring all three does not
     inflate the error rate. A given-representation control skipped because the discovery used a starting
     representation is the predecessor itself. In part 4 the two comparisons are reported, as the labels
     OPERATIONAL_OVER_FACTS and PROCEDURE_OVER_REPRESENTATION; there part 4's causal-use condition already requires
     that the procedure's own branches produced a certificate.
**Verdict:** INVALID if validity fails; else INADEQUACY_GATE_FAILED if the gate fails (A' empty); else PROVED_OUT if
parts 1-5 all pass; else NOT_PROVED_OUT, naming the parts that failed. Parts 1 and 3-5 need part 2's discovery (in
A'); without it they fail.
**Validity:**
  * the forbidden-concept audit of the research plane is clean;
  * no certificate in C against a conjecture equivalent to a proved bound;
  * every arm spent its budget, to within one quantum and one verification;
  * the pins (filled at preregistration).

**Fixed at PT-1's preregistration (30 Oct 2026; the draft's open items), kept unchanged here.**
  1. Budgets.
     - B_A = 100,000 evaluations per bound of A: F4's B_PER, the budget at which the engine refuted 14-26 of the 33
       known-false sealed bounds.
     - B_B = 50,000 per statement of B. B's domain is cheap: about 0.3 ms per evaluation, timed on invented
       statements with its costliest invariants. B's known counterexamples are small, so a larger budget lets both
       arms certify the shared statements and makes part 4's time-to-first-certificate statistic informative.
     - B_C = 100,000 per task of C: F5's B_PER. Part 5 charges the improved arm the compute G spent on A up to the
       discovery. That is at most |A| x B_A = 500,000, against |C| x B_C, about 1.7 million with the expected |C|
       (item 3), so the charge is a real price and not a forfeit.
     - The CPU, timed on proved bounds (never A) at the cap of 400 vertices, is about 1.5 ms per evaluation for P0
       and 2.2 ms for G.
  2. P_DERIVE = 0.2 and the abstraction settings: the engine's defaults, not tuned on anything. F3-F5 never used
     derivation, so they could not inform it. In the timing pilot (on proved bounds) G built two derived operation
     sets at 0.2.
  3. Family C: Genesis's own conjectures from ten fresh data draws (C_SEEDS), pooled. One draw is not enough: in
     F5, generation 1 posed 9 conjectures and the next generations nothing new. A development look on other seeds
     (992001-992010, never a study's) posed 3, 8, 11, 12, 12, 16, 16, 16, 17 and 17 distinct conjectures from one
     to ten draws pooled (5 withheld); ten draws are expected to give about 17. Their formulas were seen in the look;
     C_SEEDS's are fresh.
  4. Part 1's ablation: K_ABLATION = 5 fresh seeds. Its compute is reported and is not charged to G. It is the
     kernel's test of usefulness, not part of the inventor's procedure, and A's comparison of P0 and G (the gate and
     part 2) does not depend on it.
  5. Part 4's statistic: the two statistics with Holm, as the draft proposed (implemented in `compare`).
  6. The sum-type operations stay closed to derivation, as the draft proposed: they add no reachable graph, and
     opening them hands over more.
  7. The size cap: one cap of 400 vertices for every program representation and arm (PROGRAM_MAX_N), as built.
  8. **Templates do not count for part 1** (PART1_MECHANISMS = derivation, library). This is the stricter of the
     draft's two readings, chosen because of Daniel's "Do the hardest so it proves it can find its way". His
     decision named only library learning and operators on Γ's operations. Templates stay in G as its standing
     abstraction, but a discovery credited to a template does not pass part 1.
  9. Part 5 must beat the predecessor and both controls (decided 28 Oct 2026, 10:58 SGT).

**Expectation, stated before running (PT-2; PT-1's results seen).** NOT_PROVED_OUT, high confidence.
  * The gate holds, at about 0.9: in PT-1 P0 certified only bound 40 (at 120,511 of 500,000 evaluations); three runs
    may also reach another, but all five is unlikely.
  * Part 2, about 0.35: in PT-1, G's certificate on bound 21 came late (at 463,067 of 500,000 evaluations), from a
    derived product; a fresh seed may not reach it, and a P0 run might.
  * Part 1, if part 2 passes, about 0.5 (the discovery came from a derived representation in PT-1; the ablation must
    credit it); part 3's replay at G's budget, about 0.3 given a late discovery; parts 4 and 5, each uncertain.
  * PROVED_OUT, a few per cent at most.

**Development looks (disclosed).**
  * PT-1's run and its record, read in full (`docs/checkpoints/B20_R159_RECORD.md`): which bounds P0 and G
    certified, when, through which representations, and the certificates' sizes.
  * PT-1's own: the timing pilots (P0 and G on five proved bounds, none in A, B or C; B's domain on five invented
    true statements); C's pooling look on data seeds 992001-992010; the draft's check on seed 991001; F4's and F5's
    records.
  * Nothing has run on these seeds, and nothing has run on B or C.

**Cost.** A: about 1.5 h (four runs at 500,000 evaluations, about 12 min each, then the ablation and part 3's
replay). B: about 40 min. C: about 4 h. About 6.5 h, in slices of 6,600 s.

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

STUDY = 'b20r177'
PREREGISTERED = True                      # 30 Oct 2026, with the constants below fixed (as PT-1's)
SEALED_SEED = 17717733                    # fresh at preregistration (PT-1's was another)
C_SEEDS = tuple(range(17718001, 17718011))   # ten fresh data draws, pooled (PT-1's item 3)
B_A = 100_000                             # evaluations per bound of A: F4's B_PER (item 1)
B_B = 50_000                              # evaluations per statement of B (item 1)
B_C = 100_000                             # evaluations per task of C: F5's B_PER (item 1)
C_COUNT = 600                             # C's data: graphs drawn by Genesis (as B20_R158)
P_DERIVE = 0.2                            # the default, never tuned on anything (item 2)
RHO = 0.5                                 # the improved inventor's share for its procedures (`ProcedurePolicy`)
PROGRAM_MAX_N = 400                       # one cap for every program representation and arm (the draft's item 7)
K_ABLATION = 5
K_GATE = 3                                # the predecessor's runs on A (the per-bound gate)
PART1_MECHANISMS = ('derivation', 'library')   # the strict reading: a template does not count (item 8)
PART5_REQUIRES_CONTROLS = True            # part 5 must also beat both controls (decided 28 Oct 2026, 10:58 SGT)
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
PINNED = {             # `pins()` at preregistration; checked at run time
    'frontier/direction.py': '3b54f061f5979b6527e75785a7694c47bb19ac61ac8dd64ff9aa47ee17416940',
    'frontier/curves.py': 'e531ef807bad4007e6bc04071fd3173d1eacfd98b53f26780622d9b328caa0a9',
    'frontier/converge.py': 'fec005b93be9b5e5320c5a587c8291ead0b2d9028514779ab424cbbda9a8a956',
    'frontier/allocate.py': '5518affe5f521d20288d2f1982f2016efe9641222954e2782d6473b7be07d9e9',
    'frontier/engine.py': 'bbea0852b1ecaec56ffa4ac669a6ef5e1375f47b5fcb4f71289af62c8b0ef150',
    'frontier/manifest.py': 'c9fb74568982cb8c554311559eba29d2c7fc6c30194f99229a71b63ac54a2a46',
    'frontier/procedure.py': '866324a74ee4f0a0e21c28ff72ef1667508408551c9b1f11f5198a2d32347638',
    'frontier/ablation.py': 'e8ca7076b92650dc0f599d1e43e052a79da3115dde25cb91ba53f63b444e4fb9',
    'conjecture/expr.py': '75690202d6a7ab54f75a76500ada6e675b51cf23e7b78b20b4c33f90bc62adf9',
    'conjecture/graphs.py': 'f84059118cf6d74a8ca218fefc98593110e5634353655323b2b108fbca42a972',
    'conjecture/attack.py': '59c4cdb6e5517abd9e3b6ba2642f66893db6fc17b5aab3e2d6983b6cfc5d5ef8',
    'conjecture/domain.py': '0671ad30f0deb234b202fa830f0af4f105bd26c5b6de4600f4c7ad26ea8760bf',
    'conjecture/abstraction.py': 'f9ab4ea8251ebb53a796e2e19cfcc9fea9fc165c95bb7de2b7e2afd941a79fdc',
    'conjecture/generate.py': '386d17bc934b6959e5ee7dc6e96cf9d7f0e742b8854dd6ecf2e6596cb3b6644e',
    'conjecture/operations.py': 'd9ae9d907432f265a7447db496004f172af0612e33a7fb5827bf7bcca9b71ab4',
    # the amendment (B20R177-LIBRARY): library.py's digest differs from PT-1's
    'conjecture/library.py': 'f5e8acad77090b8b7033d92e2ada4a55f1fa4fa04e40ad5df0292c6dd1b8be91',
    'conjecture/invariants.py': '98620b18ec5457122dd442d2c9dc68ad4787dfc22af6ef868dc2a021d1cdfab2',
    'conjecture/statement.py': '7ca76e71f224aa19267337a03e691d948962ff1bfd96c5897180eb6ba9d678ff',
    'conjecture/invariant_domain.py': 'c0db7d3b90b601f6c6de1bca5883395883db3f3423c05683220bcffc0f77d617',
    'conjecture/sealed.py': 'ae7d429c76e12171f9918213eaef9c33d83a1ffbd7d905953b9a79d129f41bcf',
    'conjecture/verify.py': '712c5fc1ed0c4404ac2f423c12cb7356cf9e9a90b305e19ebd293b5ec2cc0706',
    'conjecture/wowii.py': '9082fa4aca8ad90cebc8c4c7cd5fc065d58549a445328180d0e189461d6157cf',
    'conjecture/invariants_ref.py': 'd0a407774f7d085741fbfb4e7207533f0e20fc9f56a33359e0d96edb698454f9',
    'conjecture/audit.py': 'a0830b20639525f6063da4869baf2892fa551f415bcb104276a88c8118ebcd4c',
}
OUTPUT = ROOT / 'evidence' / 'proving_test_2_b20r177'


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
    if arm in ('G', 'predecessor', 'notebook', 'given_rep'):
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


def check_facts(problems, verify, facts):
    """The notebook control's first step: every fact (a certified artifact from A) checked on every task, one unit
    per check. Returns ({task: units spent when it was certified}, units spent)."""
    found, units = {}, 0
    for p in sorted(problems):
        for art in facts:
            units += 1
            if p not in found and float(verify(p, art)) > 0:
                found[p] = units
    return found, units


def give(dom, source, name):
    """The given-representation control: `dom` starts with the representation `name` of the domain `source` (a
    derived operation set, a template or a library), under a fresh name, without any procedure."""
    import copy
    if name in source.derived:
        dom.derived['derived0'] = {'ops': dict(source.derived[name]['ops']), 'from': 'given'}
    elif name in source.templates:
        dom.templates['template0'] = copy.deepcopy(source.templates[name])
    elif name in source.libraries:
        dom.macros.update(copy.deepcopy(source.libraries[name]['macros']))
        dom.libraries['library0'] = {'macros': copy.deepcopy(source.libraries[name]['macros']), 'from': 'given'}
    return dom


ARMS_LATER = ('improved', 'predecessor', 'notebook', 'given_rep')


# ------------------------------------------------------------------------------------------------------- main

def main(argv=None, registered=True, families=None, budgets=None, seed=None, output=None, pinned=None):
    """Run (or resume) the test; 0 when done, PAUSED at the end of a time slice. `families` ({'A': (posed, numbers),
    'B': (posed, verifier factory), 'C': posed}) and `budgets` replace the sealed families in the design tests, which
    also redirect the output and the pins while keeping registered=True (B20_R141's lesson); `pinned` stands in for
    PINNED only there."""
    from genesis.conjecture import audit as AU
    from genesis.conjecture import verify as V
    from genesis.frontier import ablation as AB
    from genesis.frontier import procedure as PR
    argv = sys.argv[1:] if argv is None else argv
    out = Path(argv[0]).resolve()
    pinned = PINNED if pinned is None else pinned
    output = OUTPUT if output is None else output
    if registered:
        if not PREREGISTERED:
            raise SystemExit('PT-1 is a draft: it is not preregistered')
        if out != Path(output).resolve():
            raise SystemExit(f'the registered output is {output}')
        if pins() != pinned:
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
        # stage 1: A, the predecessor K_GATE times (the gate) and G once
        engines = {}
        runs = [(f'A_P0_{k}', 'P0', (k,)) for k in range(K_GATE)] + [('A_G', 'G', ())]
        for key, arm, parts in runs:
            e, dom = run_engine(key, conjecture_domain(pa, arm == 'G'), verify_a, arm, len(pa) * b_a, out, due(),
                                seed_parts=parts)
            engines[key] = (e, dom)
            if key not in done:
                rec = record(e, pa)
                rec['certified'] = [p for p in rec['claimed']
                                    if double_check(*pa[p], rec['artifacts'][p]) == 'CONFIRMED']
                save(key, rec)
                made += 1
        engines['G'] = engines['A_G']
        beyond = beyond_p0(done, pa)
        gate = bool(beyond)
        found = [p for p in sorted(done['A_G']['first'], key=lambda p: done['A_G']['first'][p])
                 if p in done['A_G']['certified'] and p in beyond]
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
            # stages 4 and 5: B, then C at matched total compute; the two controls are secondary arms
            if proc is not None:
                facts = [done['A_G']['artifacts'][p] for p in done['A_G']['certified']]
                given = (done.get('part1') or {}).get('representation')
                charge = next(ev['spent'] for ev in e.events if ev['kind'] == 'verified' and ev['problem'] == disc)
                certify_b = lambda p, a: verify_b(p, a) > 0                              # noqa: E731
                certify_c = lambda p, a: double_check(*pc[p], a) == 'CONFIRMED'           # noqa: E731
                plan = (('B', pb, verify_b, certify_b, invariant_domain, len(pb) * b_b, 0),
                        ('C', pc, verify_c, certify_c, conjecture_domain, len(pc) * b_c, charge))
                for fam, problems, verify, certify, factory, total, cost in plan:
                    for arm in ARMS_LATER:
                        key = f'{fam}_{arm}'
                        if key in done:
                            continue
                        budget = total - (cost if arm != 'predecessor' else 0)
                        found, units = check_facts(problems, certify, facts) if arm == 'notebook' else ({}, 0)
                        if arm == 'given_rep' and given is None:
                            save(key, {'skipped': 'the discovery used a starting representation'})
                            continue
                        if budget - units < QUANTUM:
                            save(key, {'spent': units, 'budget': budget, 'claimed': [], 'certified': sorted(found),
                                       'artifacts': {}, 'first': dict(found), 'via': {}, 'branches': 0,
                                       'charge': cost, 'fact_units': units})
                            continue
                        dom = factory(problems, True)
                        if arm == 'given_rep':
                            give(dom, engines['G'][1], given)
                        eng, _ = run_engine(key, dom, verify, arm, budget - units, out, due(), proc=proc)
                        rec = record(eng, problems)
                        mine = [p for p in rec['claimed'] if certify(p, rec['artifacts'][p])]
                        rec['certified'] = sorted(set(mine) | set(found))
                        rec['first'] = {p: found[p] if p in found else units + rec['first'][p] for p in rec['certified']}
                        rec.update(spent=rec['spent'] + units, budget=budget, charge=cost, fact_units=units)
                        save(key, rec)
                        made += 1
    except Paused:
        return PAUSED
    summary = analyse(done, pa, pb, pc, number_a, number_b, labels_c, withheld_c, registered, pinned)
    summary['audit_hits'] = AU.scan(AU.research_plane(ROOT))
    summary['valid'] = summary['valid'] and not summary['audit_hits']
    summary['verdict'], summary['failed'] = verdict(summary)
    summary.update(study=STUDY, schema='genesis-b20r177-proving-test-2-v1', preregistered=PREREGISTERED,
                   code_identity=code_identity(ROOT)['sha256'], status='DEV; licenses nothing')
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True, default=list) + '\n')
    print(json.dumps({k: summary[k] for k in ('verdict', 'failed', 'valid', 'parts')}, indent=1, default=list))
    return 0


def spent_ok(rec):
    return rec['budget'] < QUANTUM or rec['spent'] >= rec['budget'] - QUANTUM - 1


def beyond_p0(done, pa):
    """The bounds of A beyond the predecessor: those none of its K_GATE runs certified."""
    hit = {p for k in range(K_GATE) for p in done[f'A_P0_{k}']['certified']}
    return sorted(p for p in pa if p not in hit)


def analyse(done, pa, pb, pc, number_a, number_b, labels_c, withheld_c, registered, pinned=None):
    """The parts, validity and the record (kernel side)."""
    from genesis.conjecture import generate as GN
    from genesis.conjecture import sealed as SD
    g = done['A_G']
    beyond = beyond_p0(done, pa)
    gate = bool(beyond)
    found = sorted((p for p in g['certified'] if p in beyond), key=lambda p: g['first'][p])
    disc = found[0] if found else None
    parts = {'gate': gate, 'part2': bool(found)}
    ab = done.get('part1')
    parts['part1'] = bool(ab and ab['useful'] and ab.get('mechanism') in PART1_MECHANISMS)
    pr = done.get('part3_procedure')
    rp = done.get('part3_replay')
    parts['part3'] = bool(pr and pr['procedure'] and not pr['names'] and rp and disc in rp['certified'])
    stats, labels = {}, {}
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
        for control, label in (('notebook', 'OPERATIONAL_OVER_FACTS'), ('given_rep', 'PROCEDURE_OVER_REPRESENTATION')):
            c = done.get(f'{fam}_{control}')
            if c is None or 'skipped' in c:
                s[f'vs_{control}'] = {'skipped': (c or {}).get('skipped', 'not run')}
                continue
            s[f'vs_{control}'] = compare(imp, c, list(problems))
            if s[f'vs_{control}']['pass']:
                labels.setdefault(fam, []).append(label)
        if fam == 'C' and PART5_REQUIRES_CONTROLS:
            parts['part5'] = parts['part5'] and all(beats(s, control) for control in ('notebook', 'given_rep'))
        stats[fam] = s
    proved_c = sorted({pc[p][0] for a in ARMS_LATER for p in done.get(f'C_{a}', {}).get('certified', [])
                       if _proved_equivalent(*pc[p], GN, SD)})
    spent = all(spent_ok(done[k]) for k in done if (k[:2] in ('A_', 'B_', 'C_') or k == 'part3_replay')
                and 'spent' in done[k] and 'skipped' not in done[k])
    pins_ok = (not registered) or pins() == (PINNED if pinned is None else pinned)
    valid = not proved_c and spent and pins_ok
    return {'parts': parts, 'stats': stats, 'labels': labels, 'discovery': disc, 'discovery_bound': number_a.get(disc),
            'certified_A': {k[2:]: sorted(number_a[p] for p in done[k]['certified'])
                            for k in [f'A_P0_{j}' for j in range(K_GATE)] + ['A_G']},
            'beyond_p0': sorted(number_a[p] for p in beyond),
            'part1': ab, 'part3': {'names': pr['names'] if pr else None, 'replayed': bool(rp and disc in rp['certified'])},
            'certified_B': {a: sorted(str(number_b[p]) for p in done.get(f'B_{a}', {}).get('certified', []))
                            for a in ARMS_LATER},
            'C': {'posed': len(pc), 'withheld': len(withheld_c), 'labels': labels_c},
            'proved_equivalents_refuted': proved_c, 'spent_ok': spent, 'pins_ok': pins_ok, 'valid': valid}


CLASSICAL_PROVED = (('d + m', 'vertex'), ('sqrt(2*d^2 + 2*d*m)', 'vertex'), ('2*d', 'vertex'), ('di + dj', 'edge'))


def beats(s, control):
    """Whether the improved arm beat a control in part 5. A given-representation control skipped because the
    discovery used a starting representation is the predecessor itself, which already has that representation, so
    the primary comparison decides it. A control that did not run is not beaten."""
    v = s.get(f'vs_{control}', {})
    if 'skipped' in v:
        return v['skipped'] == 'the discovery used a starting representation' and s['pass']
    return bool(v.get('pass'))


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
