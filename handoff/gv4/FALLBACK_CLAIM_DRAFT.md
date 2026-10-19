# GV4 fallback claim, DRAFT: a useful solver, and no better-improver claim

**Status.** Drafted by the builder on 17 Oct 2026 (B20_R60).
- **Not adopted.** It takes effect only if a reviewer accepts the roadmap's fallback for GV4: decision 6 of
  `docs/checkpoints/B20_R57_REVIEW_BRIEF.md` (B20R9-OPEN-1).
- **No claim yet.** Nothing here has been run on a sealed panel or reviewed.
- **Numbers are tested.** `tests_genesis/test_gv4_fallback.py` checks every number quoted below against the
  committed evidence (`scripts/b20r60_gv4_fallback.py`, `CITATIONS`). It also checks the false-discovery table
  (`attempt_family.json`).

## Why the fallback

GV4 asks for a *better improver*: a research policy that produces better future improvements than a fixed one
(spec 12.4 and 19.5). That comparison can only show a difference where a research decision has headroom: where
choosing well beats a fixed policy by more than the minimum useful effect.

No probed domain has such a decision:
- **Equational theories:** six systems (B20_R3), the family search (B20_R6), library curation (B20_R9), and
  Wolfram's axiom at the hard settings, for selection, keeping and 6-node conjectures (B20_R53, R54).
- **Graph construction:** choosing among existing configurations (B20_R13) and proposing pipelines over the LP-
  and SAT-guided components (B20_RX5).
- **Certification rows:** 7-vertex rows add no coverage (B20_R37). For sum-free pattern selection (B20_R58) the
  certified counts are all 13, none 10, best subset 11 of 16, so the patterns' value is joint.

Running a sealed learned-versus-fixed study now would spend an independent custodian on a foregone null. The
roadmap's fallback is to report a useful solver without claiming a better improver. This draft says exactly what
that report would contain.

## Part A: a useful solver (a GV3 claim): E1d

**Wording**, from the E1d decision record (`handoff/e1d/decision_record_DRAFT.json`, `exact_claim`), in short:

> On a custodian-held CONFIRM panel of triangle-free host graphs from three dense planted-cluster settings,
> Genesis's frozen represent-and-repair solver (0.5 CPU s of search) scores more edges per host than the
> strongest of five registered baselines, by at least 0.5. The baselines include the exact MILP solver HiGHS at
> four times the candidate's budget, and optima are certified by the generated-rows reference.

**Evidence so far.** All DEV, builder-run, same operator, every rule fixed before its run.

| Step | Result |
|---|---|
| Re-pilot, 30 fresh hosts (B20_R41) | +10.6 per host [9.1, 12.1] over the strongest baseline, `milp_highs_4x`; the candidate is optimal on 30/30 |
| Same-operator rehearsal of the whole custody path (B20_R43) | **SUPPORTED**: +9.80 per host [9.30, 10.35] on 237 certified hosts; W/T/L 198/39/0; CPU cost ratio 0.34; the judge agrees and re-checked 474 witnesses |
| How much CPU HiGHS needs to catch up, 30 fresh hosts (B20_R63) | **CROSSOVER_AT_8S**. At 2 s (4×): +10.30 [8.77, 11.83] again. At 4 s (8×): +6.37 [4.73, 8.00]. At 8 s (16×): +0.43, no longer a material advantage. At 16 s and 32 s HiGHS ties: it is optimal on 30 of 30 at 16 s, using about 6 CPU s per host |
| A textbook max-cut heuristic at the same budget: 30 fresh calibrated hosts, and 20 at n60 (B20_R68) | **E1D_MATCHES_DOMAIN_HEURISTIC**. Candidate − tabu search on the calibrated settings: +0.03 [0.00, 0.10], 1/29/0, and tabu search beats HiGHS at 2 s by +8.60, as the candidate does. At n60: -1.15 [-1.65, -0.70], 1/6/13, tabu search ahead |

**What must be said with it.**
- **A standard max-cut heuristic does as well, so the advantage over HiGHS is not an advantage over the field
  (B20_R68).** Tabu search over one-vertex flips, with the same greedy completion and the same 0.5 s, ties the
  candidate on the calibrated settings and beats it on n60 hosts. The candidate's lead over HiGHS is the lead of
  the max-cut reduction plus local search over a generic MILP at short budgets: a *potential* speedup in the sense
  of Rønnow et al. (2014), against one chosen baseline. The claim must name its comparator class. If the
  reviewer's strong-baseline set includes domain heuristics (review brief item 1), Part A has no claim; what
  remains is that the system's representation search rediscovered the max-cut reduction on its own.
- **By time-to-solution it is the slowest of the field's methods (B20_R70).** At the optimal run time per size,
  simulated bifurcation reaches the best known value faster than the candidate at n60 (median log2 ratio
  -3.20 [-4.59, -2.56], **E1D_SLOWER_THAN_SOME**), and the candidate's median time grows with host size while the
  heuristics' stay flat. A speed claim cannot be made against the best-known methods.
- **The solver is classical.** Its representation, `cross_2`, is a bipartite cut chosen from a builder-written
  typed grammar whose soundness Lean checks (B18, W10/W11). No novelty is claimed.
- **Why it wins: speed, not quality at any budget (measured in B20_R63).** On dense planted clusters the largest
  triangle-free subgraph is close to a maximum cut, which is what the representation searches, so the candidate
  finds the optimum in 0.5 s. HiGHS gets there too, given about ten times longer. At 2 s it reached the optimum
  on only 6 of 30 re-pilot hosts. The builder's earlier reading, that the MILP's relaxation is too weak on dense
  hosts, was wrong: with time, HiGHS proves every optimum.
- **It does not beat every exact method, or HiGHS at every budget.** HiGHS ties the candidate from 16 s (32×), and
  the generated-rows reference also solves every host. The claim is "a 0.5 s solver beats an exact MILP at 2 s,
  and matches what that MILP needs several seconds to reach". The report must state the crossover (16× here) and
  not imply an advantage beyond it.
- **On larger hosts the advantage grows** (B20_R64, a DEV pilot outside the calibrated settings): **ADVANTAGE_GROWS**.
  The crossover is 16× at n40 and 64× at n50. At n60 (about 430 edges) the candidate still leads HiGHS at 64× its
  budget, +17.6 [8.1, 28.8], 10/0/0, while staying within about one edge of a proven upper bound. Claiming that
  needs a family-space extension and the 200-edge certificate bound lifted for the exact LP-dual route.
- **The n60 result replicates, and holds at 120×** (B20_R66, a DEV replication on 20 fresh hosts):
  **REPLICATED_ADVANTAGE_THROUGH_120X**. Against HiGHS at 64× the lead is +16.65 [11.0, 22.6], 19/1/0; at 120×,
  `milp-highs-v1`'s ceiling, it is +2.00 [1.35, 2.65], 17/2/1. HiGHS is closing fast (its gap to a proven upper
  bound falls from 18.3 to 3.65 between the two budgets), so here too the report must state the budget. These
  larger-host results are against HiGHS only; against tabu search the candidate is behind at n60 (B20_R68).
- **Its scope is narrow.** Only these three settings, on that panel.

**What it needs:**
- a reviewer adopts the DRAFT rule `e1-hard-v3-draft`, the generated-rows reference (decision 3) and the registry
  v2 wiring (B20R40-OPEN-1);
- a statistician signs off the power model (B19-OPEN-4);
- an independent custodian runs SELECT, registration and evaluation on its own machine.

**Optional extension.** If the reviewer accepts claims scoped to time-matched DSL baselines (decision 1), E1, E1b
and E1b-C4 (`handoff/e1`, `e1b`, `e1b_c4`) can join Part A on their own settings. All three are dominated by the
exact MILP there and must say so.

## Part B: why the solver wins (causal attribution of Part A)

| Step | Result |
|---|---|
| Registered ablation (B20_R44): the decoder weakened from `cross_2` to `ordered_2`, which Lean shows is strictly weaker | +7.07 per host [6.47, 7.70] lost; the null control, a Lean-certified *equal* decoder, gives +0.03 [-0.02, 0.09] |
| Same-operator rehearsal of the custodian-signed ablation through v5 custody (B20_R45) | **SUPPORTED**: +6.64 [6.03, 7.29], W/T/L 44/0/0, the judge agrees |

**Wording, if a custodian's run supports it:** the representation's decoder is causally responsible for at least
0.5 edges per host of Part A's effect (ABLATION_SUPPORTED). It needs the same people as Part A, and the reviewer's
acceptance of the intervention (B20R44-OPEN-1).

## Part C, only if certification utility counts (decision 4): generated, Lean-checked inequalities

A generate-screen-prove procedure produced inequalities, each one a theorem checked by Lean. With them, an exact
checker certifies optima that the conventional relaxation leaves open.

| Motif | Result (DEV, 60 s per host) |
|---|---|
| Triangle-free, dense hosts (B20_R35) | 27 vs 7 of 40 certified |
| C4-free, the procedure transferred (B20_R48) | 38 vs 26 of 40 certified, with certified branch and bound |
| C4-free, attribution (B20_R49) | 36 vs 24 of 40 with vs without the rows: the rows are responsible |
| Sum-free sets of integers (B20_R57, then B20_R59) | 22 vs 14 of 40, **not replicated** (23 vs 21 of 40, p 0.25). The certified-bound advantage did replicate: +6.875 [5.375, 8.475], then +3.875 [2.675, 5.125] |

**False-discovery control** (`attempt_family.json`). This is Benjamini–Yekutieli at q = 0.1 over all 13
preregistered component attempts, failures included. The six construction attempts count at p = 1.
- **Survivors:** B20_R35, B20_R48 and B20_R57.
- **How far each would hold.** B20_R35 still survives at any family size this test searched (up to 10,000), B20_R48
  up to 147 attempts, and B20_R57 up to 21.
- **B20_R57 does not count.** It survives the correction but failed its internal replication, so this draft does
  not count it as a coverage result. Sum-free contributes stronger certified bounds only.

**Wording, if counted:**

> On DEV hosts of two motifs, triangle-free and C4-free, inequalities that Genesis generated and Lean
> proved let an exact checker certify optima the conventional relaxation could not.

As written this is a DEV statement. A sealed certification study under custody would be needed for more, and the
trust-path change (decision 3) for any evaluator use. Every row of it is a checked theorem; the producer is never
trusted.

## What the fallback does not claim

- **A better improver (GV4).** No learned research process has been compared with a fixed one.
- **Compounding generations (GV5).** That gate depends on GV4.
- **Structural transfer (GV6).** The C4 and sum-free transfers share the source's abstract structure, a
  hypergraph-free packing (`handoff/gv6/README.md`, structural caveat).
- **Independent replication (GV7).** That needs a second operator.
- **Novelty.** The representation and the bounds are classical.
- **Anything outside the named settings.**

## What would reopen GV4

- **A new domain.** A domain named by the reviewer whose headroom pilot (the B20_R3/R53 pattern) finds a research
  decision worth more than the minimum useful effect between the oracle and a fixed policy.
- **A construction component with utility.** A component family with construction utility after cost, so that
  research has something to produce. Six attempts have none (B20_R17, R19, R26, R27, R31, R36).

## For the reviewer

1. **The fallback.** Accept it for GV4, or name a domain to pilot.
2. **The parts.** Which of Parts A–C go forward. Part C goes forward only if certification utility counts.
3. **The report wording.** Whether the final report states GV4 as "not established; fallback taken".
