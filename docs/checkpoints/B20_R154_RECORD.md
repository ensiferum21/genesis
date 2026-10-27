# B20_R154 record: X2, the pipeline that lets the engine language grow itself (engineering, on a planted fixture)

- **What this is.** The second batch of Daniel's direction of 27 Oct 2026, 14:33 (`docs/OMEGA_EXPRESSIVE_LANGUAGE.md`),
  queue `expr-x2-build`. It builds his pipeline for the engine language:
  > ARA diagnoses the obstacle → Genesis invents a structural repair → the independent Judge verifies it → the
  > Consolidator preserves it → Genesis resumes research with the improved workflow.
- **No claims.**
  - Nothing here is a result.
  - The fixture is a planted world, as the Limitation Zoo is for ARA; nothing measured in it is evidence about max-cut
    engines.
  - The study that tests the pipeline on real engines is B20_R152.
- **Built by** the builder on 27 Oct 2026, with no LLM, on CPU 1 while B20_R151 ran alone on CPU 0. The protected judge
  `autonomy/feedback.py` is untouched.

## What was built (`src/genesis/expressive/`)

| Module | Plane | Pipeline step | What it does |
|---|---|---|---|
| `workflow.py` | research | ARA diagnoses | The engine-invention workflow as an Architecture Graph: four typed nodes (language, search, evaluator, output as the closed kernel), `check`, ARA's change classes (LANGUAGE, STRUCTURAL, TUNING). **ARA's loss ladder** over the workflow's stand-ins: A (as it is), S_exact (exact evaluation), C_cur (ceiling search), C_rich (the richest language under the ceiling), O (REX at ten times the budget). Terms expressiveness, search, evaluation and residual, with bootstrap intervals, materiality as a fraction of the attainable range, NONE and AMBIGUOUS, and the next step |
| `library.py` | research | Genesis invents | **Library learning.** Fragments that can become one item without changing meaning (guard rules); skeletons; anti-unification, where positions that always agree share a parameter (Plotkin's rule); rewriting with every rewritten program checked to expand to exactly what it was; greedy choice by compression of corpus plus library in bits. A statement can call earlier ones. Prior art: Plotkin 1970; Reynolds 1970; DreamCoder; Stitch; babble |
| `judge.py` | **kernel** | the independent Judge verifies | **The language judge.** Correctness; a structural check for expressiveness claims; a random control statement of the same size drawn by the judge; the registered searches in the parent, candidate and control languages on training graphs it draws; winners on truth graphs it draws; a saturation check for expressiveness claims; the decision over graphs and over search replicates (below). Verdicts carry no numbers; the ledger has them, with the digests of the code it ran. Digest pinned `8390b199…5d05` |
| `fixture.py` | **kernel** | (test world) | The planted fixture: values rise with `D@c` items in the expanded program, up to a cap beyond the bound of 6 items, so a named statement holding several can raise what fits in the bound. A decoy (`H@a`) helps only on development and training graphs; there is a null world; `dev_view` is the research plane's development view |
| `consolidate.py` | research | the Consolidator preserves | Capability records in the vault: each statement with its contract (expansion semantics), implementation, property tests run at consolidation, verification (the judge's decision), cost, failure envelope and provenance; each language version with its parent (the registry is the chain); `requires`, `improves` and `combines_with` edges. Admitted statements are `reproducible`; refused ones are `dormant` with their failure. Nothing is `verified` without a recorded study's evidence |
| `pipeline.py` | research | Genesis resumes | `generation`: diagnosis (optional; a language repair only where the ladder says EXPRESSIVENESS, unless forced); Genesis's dev searches give the corpus; the learner proposes one statement at a time; the judge decides; refused skeletons are excluded and the next is proposed; every decision is consolidated; the new language and the rewritten engines seed the next generation |

## The pipeline end to end, on the fixture (disclosed; `test_expressive_pipeline`)

Two generations, starting from Λ1 with an empty library, with claim 'search'. Values are truth-set gains over REX in
the fixture, the means of the judge's three replicates.

| Generation | Proposed by the learner | Judge | Truth gain: parent → candidate (control) |
|---|---|---|---|
| 1 | `g1a = D@c` | refused (`sealed`) | 1.71% → 1.99% (control 1.71%; the replicate test failed) |
| 1 | `g1b = D@c D@c` | **admitted** | 1.71% → 3.31% (control 1.98%) |
| 2 | `g2a = g1b g1b g1b g1b` | **admitted** | 3.96% → 10.38% (control 3.98%) |

Generation 2's statement is built from generation 1's. The language extended itself, and what fits in the bound
compounded. That is the mechanism Daniel asked for ("They should improve on themselves as in expressiveness wise and
richness"), shown working in a planted world. Whether it happens with real engines is B20_R152's question.

In a null world nothing is admitted; when the ladder diagnoses SEARCH, no language repair is attempted.

## Found while building (disclosed; each changed the design)

1. **A one-item statement cannot add expressiveness, but was admitted as expressive.** A call to it is as long as
   its expansion, so it cannot raise what fits in the bound; the judge admitted `D@c` because it made the pattern
   easier to find. The judge now refuses expressiveness claims for single-item statements (`structural`).
2. **A ceiling that is not a ceiling.** The judge now runs the parent's ceiling again at half budget. If the full
   ceiling still beats the half one, an expressiveness claim fails as `not_saturated`.
3. **Search luck passed for a language, twice.**
   - With two replicates per language and a per-graph test alone, the judge admitted `X I` (worth nothing in the
     fixture): one parent search had stuck short of the optimum. A per-graph test over specific engines cannot
     tell a language from search luck. Fix: three replicates, and the exact permutation test of the replicates'
     mean gains.
   - With the replicate test alone, it admitted `X I` again, on noise-level margins, because the material mean
     difference came from the stuck parent search. Fix, for expressiveness claims: a margin (the worst candidate
     replicate beats the best parent and control replicates by at least MATERIAL). The random control is what
     refused `X I` in the end.
   - **B20_R151 had the same structure.** It was amended twice, before any of its ceiling searches ran (records
     `85fda78`, `41cfcd8`; disclosed in its script):
     - first, three ceiling replicates and the replicate test, with its first slice stopped after the gate;
     - second, the margin (analysis only).
4. **An X1 bug.** The `target` mutation assumed an operator on the program's surface. With a library, a program
   can be calls only, and the mutation crashed. Fixed, with a test. B20_R151 is unaffected: it uses no library, so
   its programs always have their operators on the surface.
5. **REX at ten times the budget is not an upper bound.** An engine can beat it, so the ladder's attainable range is
   the best mean of O and the stand-ins; the residual can then be negative.
6. **Compression needs recurrence.** A statement pays for its name only with enough uses (`R B$1` in 6 uses
   compresses by −11 bits). The fixture's dev searches need enough budget (8 searches of 400 evaluations) for
   structure to recur across engines.

## Limits

- **Cost on real engines.** A submission runs three languages × three replicates of the registered search:
  - for a search claim at the inventor's budget, about 9 × 1,024 graph-seconds ≈ 2.6 h;
  - for an expressiveness claim at the ceiling, about 9 × 3,968 graph-seconds plus the saturation rerun ≈ 11 h.
  B20_R152 must be designed around this, for example with few submissions per generation, smaller graphs, or
  search claims first.
- **The judge runs research-plane code** (the operators, the front end, the kind). Its ledger records their
  digests, and a study checks them.
- **The workflow ladder decides; it does not measure.** A study supplies the stand-ins' values (B20_R151 supplies
  them for the real workflow).
- **Disclosure.** The amendment commit `85fda78` also carried X2's unfinished modules, through a broad `git add`.
  B20_R151 imports none of them. This record is their finished state.

## Tests (48 in `genesis.expressive`, all passing)

- New:
  - `test_expressive_library` (6);
  - `test_expressive_judge` (8), the digest pin included;
  - `test_expressive_consolidate` (5);
  - `test_expressive_pipeline` (7);
  - `test_expressive_boundary` (5): the research plane imports neither the judge nor the fixture and never
    reaches the judge's state, and the judge shows only `submit` and `ledger`.
- Extended: `test_expressive_operators` (7), with call-only programs.
- Unchanged: `test_expressive_lambda1` (8); `test_omega_boundary` (2) covers the package.
