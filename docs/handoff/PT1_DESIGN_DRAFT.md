# PT-1 (B20_R159): the proving test, a design draft (now PREREGISTERED)

**30 Oct 2026: PT-1 is preregistered** (`scripts/b20r159_proving_test.py`, sha256 `56037017…3a05`). Every open item below
is fixed in the script's docstring ("Fixed at preregistration"), each with its reason. In particular, templates do not
count for part 1: the strict reading of item 8. This file is kept as the design's history.

Written 28 Oct 2026, 01:25 SGT, for whoever preregisters PT-1 after F1–F5 have run (`docs/OMEGA_FRONTIER.md` §7b).
Nothing here has been run on family A or family B. It records what is built, what was decided, and what remains to
be decided, so that the preregistration can be written from it.

## What is decided

- **Daniel, 27 Oct 2026, 20:22 (the test):** five parts, scored separately; PROVED_OUT only if all five pass.
- **Daniel, 28 Oct 2026, 00:53 (part 1's mechanisms):** "Do the hardest so it proves it can find its way."
  - Only the two mechanisms that hand over nothing are allowed:
    - library learning over Γ (`conjecture/library.py`);
    - operators acting on Γ's own operations (`conjecture/operations.py`, the engine's `derive`).
  - Low-level block primitives and the repeated-row compressor are excluded. They may run afterwards only as
    labelled diagnostics and never count.

## What is built (all on `continuation-b20-rx`)

| Piece | Where |
|---|---|
| Family A: Laplacian bounds 18, 21, 24, 30 and 40, held out of F4 and F5 | `conjecture/sealed.py` (`PROVING_TEST_HOLDOUT`) |
| Family B: all 63 Graffiti statements (29 proved, 25 disproved, 9 open), posed as text | kernel side `conjecture/wowii.py` (evaluators, `TEXT`, `COUNTEREXAMPLES`, `verifier`); research plane `conjecture/statement.py`, `invariant_domain.py` |
| B's double kernel check | `invariants.py` (research plane) and `invariants_ref.py` (kernel side, no shared code); `wowii.verifier` needs both |
| Part 1's mechanisms | `conjecture/library.py`, `conjecture/operations.py`, `ConjectureDomain.learn` / `derive`, `Frontier.derive`, `FrontierPolicy` `p_derive` |
| Part 3: procedures from the engine's own log, including derivation lineages | `frontier/procedure.py` (`extract`) |
| Part 5's improved inventor | `frontier/procedure.py` (`ProcedurePolicy`) |
| The forbidden-concept audit | `conjecture/audit.py` |
| The engine's meta level (not part of PT-1, but available) | `frontier/meta.py` |
| Part 1's usefulness ablation (a candidate protocol, B20_R168) | `frontier/ablation.py` |

## A proposed design (to be argued over and fixed at preregistration)

**Arms.**
- **P0, the predecessor.** The Frontier's allocation with the starting representations only: no abstraction, no
  library learning, no derivation (`p_derive` 0).
- **G, Genesis.** The Frontier with abstraction (templates, then library learning) and derivation on (`p_derive`
  fixed in advance, for example 0.2, not tuned on A or B).
- Both run at the same total compute. The CPU and the evaluations are both reported.

**The inadequacy gate (on A, first).** P0 at the full budget certifies nothing in A. If it certifies something, A
is not unfamiliar: the test stops as INADEQUACY_GATE_FAILED and needs another family. It does not count as a pass.

**Part 1, a useful new representation (on A).** G creates a representation during its run (a derived operation set
or a library) that is absent from the starting set.
- *Useful* is decided by an ablation inside the run's budget: re-running G's best branch's method with and without
  that representation, at matched compute, must give certificates in A that the starting representations do not.
- The report names which mechanism produced it: the derivation lineage, or the library's pieces.

**Part 2, a nontrivial consequence (on A).**
- At least one exact refutation certificate for a bound in A that P0 did not refute, double checked:
  - Sturm up to n = 40;
  - the independent matrix-form check above that.
- The certificate is compared with the published counterexamples. A rediscovery counts for the test but is labelled.

**Part 3, the procedure.** `procedure.extract` on G's log, for the discovery of part 2. It must:
- name no problem and no representation it made;
- replay on A and reproduce the discovery.

**Part 4, independent use in B.**
- *The improved inventor:* `ProcedurePolicy` with the part 3 procedure, on B's 25 disproved and 9 open statements
  posed as text. It is given no B-specific change.
- *Its predecessor:* the same Frontier without the procedure, at matched compute.
- *Pass:* an exact certificate (`wowii.verifier`: both implementations) that the predecessor does not get.
- *Open statements:* a violation of an open statement would be a new result, and is reported as such after the
  double check.

**Part 5, the improved inventor beats its predecessor (on C).**
- C is fresh sealed tasks, chosen by the kernel and never seen. Candidates:
  - generated conjectures from F5's generator, on a new seed;
  - AutoGraphiX adjacency-spectrum conjectures, once transcribed.
- At matched TOTAL compute: the improved arm is charged the cost of discovering the procedure in A.
- Test: a paired one-sided test over tasks, with Holm across the test's claims.

**Validity.**
- The forbidden-concept audit of every research-plane module the test runs, and of the manifest's text.
- The NHP boundary tests and the relabelling audit.
- No certificate against a proved statement or bound. One would mean a transcription or verifier error, and makes
  the run INVALID.
- Pins at preregistration.

## What F4 and F5 showed (30 Oct 2026; for the preregistration)

- **F4 (B20_R157, PARTIAL).**
  - Under its rule (Sturm only for n ≤ 40), the Frontier beat NRPA only. GBFS on bounded-degree graphs refuted the
    most, 19 of 33.
  - Descriptively, the engine's Γ programs built 43–64-vertex counterexamples that the rule could not confirm. A
    matrix-form check confirms them all, which puts the three allocators at 25–26 of 33, level with each other.
  - For PT-1:
    - the second check above 40 vertices (`verify.check_matrix_form`) must be in the kernel's rule, as this draft
      already has it;
    - the gain over single searches came from the representations, not from the allocation.
- **F5 (B20_R158, NOT_SHOWN).**
  - Generation 1 posed 9 conjectures. Generations 2 and 3 posed nothing new, because the generator re-derived
    equivalents of earlier conjectures.
  - For PT-1's family C (item 3 below): pooling several data draws (`C_SEEDS`) is necessary, not optional, and even
    then the number of informative tasks needs checking before the preregistration fixes part 5's statistics.

## Still open (decide before preregistering)

1. Budgets for each part (F4's timings give the scale: about 100,000 evaluations per bound).
2. `p_derive`, and the abstraction settings: fixed in advance from F3–F5's results, never tuned on A, B or C.
3. Family C: which source, how many tasks, and how they are sealed.
   - Generated conjectures are few per data draw. A development check on 28 Oct 2026 (seed 991001, never a study's)
     posed 7 and withheld 2. Each of part 5's statistics needs at least 6 informative tasks to reach p_Holm < 0.05,
     so the draft pools the conjectures of several draws (`C_SEEDS`), skipping equivalent ones.
   - A third candidate, noted on 28 Oct 2026 (not transcribed): Hansen and Lucas, "Bounds and conjectures for the
     signless Laplacian index of graphs", *Linear Algebra Appl.* 432 (2010) 3319–3336 (GERAD G-2009-27). AutoGraphiX
     gave algebraic conjectures in 120 of 152 cases, relating the signless Laplacian index q1 to other invariants
     as functions of n; 18 were open at publication. Later papers settled some, for example on the clique number
     (arXiv 1209.3214, 1308.1653) and the Randić index (arXiv 1601.03511).
     - For: it is close to family A, so a procedure from A has a fair chance to transfer, and it is
       literature-sealed.
     - Against: its statuses are scattered across many papers, so transcribing and tiering it is a project of the
       size of F2's sealed set.
4. Part 1's usefulness ablation: its exact protocol, and how a representation is credited when several are created.
   **A candidate is built (B20_R168, 28 Oct 2026; `frontier/ablation.py`, `tests_genesis/test_frontier_ablation.py`):**
   - the credited representation is the one the discovering branch searched, with how it was made (derivation or
     abstraction) and its lineage back to a starting representation;
   - the engine's `verified` event now records the branch's compute at that moment. Every replay gets exactly that
     compute, through the domain's public `step`, for k fresh seeds, the same seeds in every arm;
   - *useful* iff the credited representation verifies in at least one seed and no starting representation does in
     any. The lineage's intermediate representations are re-run and reported, not tested;
   - the ablation's compute, verification included, is returned so that the study can charge it to G.
   Still to fix at preregistration: k (5 is the default), and whether the charge counts against G's matched budget.
5. Part 4's statistic, if B's small counterexamples are found by both arms: the count of certificates, or time to
   the first one.
   - A proposal (28 Oct 2026). Family B's known counterexamples are mostly small: the kernel's 18 have 5 to 53
     vertices, and 13 are within the search limit of 18. So both arms may certify most of the disproved statements
     within reach, and a count alone would then show nothing. Two statistics, with Holm over both; part 4 passes if either does:
     - (a) the one-sided exact McNemar test on the statements certified by exactly one arm;
     - (b) on the statements both arms certify, the paired evaluations to the first certificate, by a one-sided
       Wilcoxon test (the improved arm faster). Under Holm over the two, its smaller p must be below 0.025, which an
       exact one-sided test can reach only with at least 6 such statements (1/64).
   - And the use must be causal: at least one of the improved arm's certificates comes from a branch its
     procedure opened (the engine's `op` is 'procedure').

6. Whether derived operations should also act on Γ's sum-type operations (union, join) and on corona. Today only
   the product-type space is open to derivation.
   - The builder's reading (28 Oct 2026; an argument, not a proof): the natural sum-type space on X ⊔ Y has
     blocks [[f(X), cJ], [cJ, g(Y)]], with f and g among identity, complement, empty and complete, and c in {0, 1}.
     Every such operation is a composition Γ already has (`compl`, and union or join with E and K bases of the same
     sizes). So opening it adds no reachable graph, only shorter programs. The product-type space is different: its
     256 rules reach operations that are not among Γ's, such as the lexicographic and strong products. Whether Γ
     could compose them is not established.
   - So the proposal is to leave it closed, which also hands over less.
7. **The size cap (found 28 Oct 2026, 09:50 SGT, from the code; it decides whether part 2 is reachable at all).**
   - Programs of Γ, of its derived representations (`GammaPlus`) and of its library representations (`GammaLib`)
     build graphs of at most `attack.MAX_N` = 64 vertices. Templates build up to `abstraction.TEMPLATE_MAX_N` = 400.
   - The only known counterexamples to family A's bounds are equitable-partition constructions of 158 to 352
     vertices. That is the builder's knowledge, from the literature, written in `sealed.py`.
   - So, as built, the two mechanisms Daniel allowed cannot reach a known counterexample to A. Part 1's mechanisms
     reach A only through a template, or through a counterexample smaller than any known one, which may not exist.
   - A proposal, and it must not be tuned to A: one uniform cap for every representation that builds by program, at
     the templates' existing 400, for every arm (P0 included). This is a resource limit already in the code, not a
     hint. The inadequacy gate then says whether P0 can reach A with Γ alone at that cap.
   - The cost of one evaluation of a bound, timed on 28 Oct 2026 on CPU 1 under load: about 0.2 ms at 64 vertices,
     1 ms at 160, 3 ms at 256 and 11 ms at 400. A budget in evaluations therefore needs a CPU check: 100,000
     evaluations all at 400 vertices would take about 18 minutes per bound.
   - **Built (B20_R168 follow-up, 28 Oct 2026):** `ConjectureDomain(program_max_n=...)` sets one cap for Γ, derived
     and library programs (`GammaRep`, `GammaPlus` and `GammaLib` take `max_n`). The default is unchanged, so
     attack.MAX_N = 64 holds for F4–F6 (tests: `test_operations.Cap`).
   - Disclosure: this item was written knowing A's sizes, and the preregistration says so.
8. **Whether a template counts for part 1.** Templates (`conjecture/abstraction.py`) are the engine's standing
   abstraction. They fit a Γ program, with sizes as parameters, to a counterexample that two independent approaches
   converged on. They hand over nothing, but they stay inside Γ's closure. Daniel's decision named only library
   learning and operators on Γ's operations.
   - Proposal: count a template for part 1, and report the mechanism. The draft's `PART1_MECHANISMS` includes
     'template'.
   - The stricter reading, which counts only the two named mechanisms, is one setting away.

9. **The information-only and generic-implementation controls** (from the Foundry proposal §6; `docs/OMEGA_FOUNDRY.md`
   G1). A gain of the improved inventor may come from what its procedure knows, not from what it does. Two secondary
   arms, in parts 4 and 5:
   - notebook: the predecessor, after every certified counterexample from A has been checked on every task at a
     charged cost;
   - given-representation: the predecessor whose domain starts with the representation the procedure would build,
     without the procedure.
   Each is compared with the improved arm by the same two statistics.
   **Decided on 28 Oct 2026, 10:58 SGT.** Daniel delegated it ("Do what's the best"), and the builder chose the
   harder test: **part 5 passes only if the improved arm beats the predecessor and both controls**
   (`PART5_REQUIRES_CONTROLS`).
   - The reason: PROVED_OUT should mean that the procedure transferred, not a list of graphs or a ready-made
     representation.
   - Requiring all three is an intersection-union test, so it costs power but does not inflate the error rate.
   - In part 4 the two comparisons stay reported labels. There, part 4's causal-use condition already requires that
     the procedure's own branches produced a certificate.

## The study, drafted (28 Oct 2026; NOT preregistered)

`scripts/b20r159_proving_test.py`, with design tests in `tests_genesis/test_proving_test_study.py` (invented
families only).
- `PREREGISTERED` is False, and a registered run is refused.
- The constants marked PROVISIONAL are items 1–3, 5 and 8 above.
- Stages:
  1. A: P0 and G, the gate, part 2;
  2. part 1, by the ablation;
  3. part 3: the procedure, with a check that it names nothing the run made, and its replay on a fresh domain;
  4. part 4 on B (improved against predecessor, both statistics, causal use);
  5. part 5 on C, at matched total compute, the improved arm charged G's compute up to the discovery.
- Kernel checks:
  - A and C: the rational Rayleigh certificate, then Sturm for n ≤ 40 or the matrix form above that;
  - B: `wowii.verifier`, with both implementations.
- Validity: the audit, no certificate against a proved-equivalent conjecture in C, the budgets, the pins.
