# GV4 (better improver): capability study design, DRAFT

**Status.** A DRAFT by the builder, 13 Oct 2026. It is not frozen and not registered with any custodian, and it licenses no claim.

**Decision behind it.** The user chose a capability study design for GV4 on 13 Oct 2026.

**Evidence base.** All DEV, builder-run:

| Batch | What it tested | Result |
|---|---|---|
| B20_R3, R6, R9 | equational research policies | no headroom |
| B20_R13 | choosing among existing graph-construction configurations | no headroom: the cheapest fixed improver ties the oracle |
| B20_R14 | how far those configurations are from the optimum | 0.6–1.4 edges per host below the certified optimum on harder families |
| B20_RX3 | making LP- and SAT-guided construction methods available | deployable capability headroom of +0.75 to +1.25 edges per host at matched budgets |
| B20_RX3b | fresh-seed replication of RX3 | **replicated**: +0.88, +0.63 and +1.38 edges per host, every 90% interval above 0. Random proposals over the enlarged space do *not* reliably find the good methods (−0.27 on C2); successive halving does |

## Update after B20_RX5 (proposal pilot)

Over a typed pipeline grammar of these components, **NO_PROPOSAL_HEADROOM** in all three settings. 18–28 of 25–40 pipelines are within 0.5 edges of the best. Fixed enumeration and random sampling find one as reliably as successive halving does.

The capability gain lives in the *components*, not in how they are composed. The study below is therefore only meaningful if the improvers' research *produces components*: new construction orders, relaxations, representations or derived primitives, as in handoff s15.3 and W22. A learned composer of builder-written components would have nothing to win.

The design below is kept for the component-level version. Its step 1 (proposal headroom over compositions) is answered: there is none.

## Update after B20_R23 (E1b)

The LP-guided candidate is now a `construct-pipeline-v1` descriptor. It ran through the custodian's runner, under E1's decided design, on fresh DEV hosts of the settings below: **READY_FOR_REVIEW** on both domains (`evidence/e1b_readiness_b20r23/`, `handoff/e1b/`). That is a GV3 (better-solver) path for a builder-written method. It does not touch the GV4 question, which still needs components that a research process invents.

## The question

Does a *learned* research process produce better successor solvers than a *fixed* research process, when both may build methods from the same components and spend the same research budget? Each successor solver gets the same CPU per host, and the comparison is on sealed fresh hosts.

RX3 showed that the *method space* matters. It did not show that a research process can find the good methods without being handed them: the improver there selected among builder-written pipelines. The study must make the improvers *construct* the pipelines.

## Proposed design (to be reviewed; nothing frozen)

**Component grammar.** A bounded, typed pipeline language with no code in the data:
- **initialisers:** menu configuration, LP-ordered greedy, random greedy, representation decode;
- **improvers:** LP-perturbed restarts, exchange local search, SAT climbing;
- **time splits:** each step's share of the CPU budget, from {0.25, 0.5, 0.75};
- **depth:** at most 3 steps.

The components are trusted code in `discovery/construct.py` and the menu modules. A pipeline is data, like a DSL program. This needs a candidate kind, for example `construct-pipeline-v1`, in the canonical candidate registry (B20_R5/R7). That registry exists only in the canonical history, so this step is blocked on B20_R11.

**Improvers (the arms).**
- **Fixed:** the B20 fixed research policy, adapted to propose pipelines in a fixed order (enumerate by depth, then registry order).
- **Learned:** a policy trained on DEV research runs to propose pipelines; it is frozen before any panel.
- **Controls:** random proposal at the same budget; successive halving over the RX3 builder-written set as an "oracle-menu" reference.

**Budgets.**
- **Research:** the same number of DEV evaluations per improver, for example 25% of an exhaustive menu evaluation, as in RX3.
- **Successor solver:** 2.0 CPU s per host, child processes included, with runs over 1.25× scoring 0.
- **Cost rule:** time-matched, as decided for E1.

**Families.** Calibrated on DEV with room to the optimum (B20_R14): triangle-free n30–40 at p 0.2–0.3, and C4 n30 at p 0.2. Sealed CONFIRM panels are drawn by the custodian, excluding every DEV host named in the evidence.

**Endpoint.** Edges per sealed host of the successor produced by the learned improver, minus that of the fixed improver. The analysis is clustered by research run, not by host (handoff s20.5): one research run yields one successor, and the hosts are its evaluation.

**Replication.** At least 3 independent research runs per arm, with different research seeds and DEV material.

**Power.** Taken from the RX3/RX3b paired-difference variance and the between-run variance (a further DEV pilot). It must be decided under a model the statistician signs off (B19-OPEN-4).

**Decision rule.** SUPPORTED only if the clustered lower confidence bound exceeds the minimum useful effect, 0.5 edges per host, and the learned improver's successors are not dominated by the oracle-menu reference at matched cost.

**Custody.** As in E1:
- the custodian's SELECT step chooses the comparator;
- a v4 request with descriptor arms;
- the judge recomputes the result.

`sealed_improver_evaluation` stays refused until the export carries paired research lineages (handoff s20.5, H08). That export is blocked on the canonical B20_R11 code.

## Proposed additions after B20_R44 (from design material the user supplied, MISSING-BIT-1; DRAFT)

Two controls from that report. Both are cheap, and both address the way this programme could fool
itself.

1. **False-discovery control across attempts.**
   - **The risk.** Nine component attempts have been run so far, and more will follow. With enough
     attempts, one will pass a 5% test by chance. They are six construction attempts in four
     families (B20_R17, R19, R26, R27, R31, R36) and three certification attempts (B20_R32, R35,
     R37).
   - **Where B20_R35 stands.** Its CERTIFICATION_UTILITY (McNemar p ≈ 1e-6) survives BY at any
     plausible family size.
   - **The control.** Treat every preregistered component attempt as one hypothesis in a running
     family, and promote only attempts that survive Benjamini–Yekutieli control at q = 0.1 over all
     attempts so far.
   - **Why BY.** BY is valid under arbitrary dependence. The attempts share hosts, components and
     code, so they are dependent.
   - **What it means for each verdict.** An attempt's own preregistered verdict still stands as
     recorded. BY decides only whether a positive verdict may count toward GV4.
2. **Null worlds.**
   - **The control.** Every invention pipeline that can promote a component is also run, at the same
     budget, on a null world, where the truth is known to be "nothing to promote".
   - **Examples.** Hosts already triangle-free, where every method is optimal. Or a component that a
     Lean check shows is equal to its baseline (B20_R44's null arm, `adjacent_2` = `cross_2`).
   - **Acceptance.** The pipeline must promote nothing there. A promotion on a null world blocks the
     pipeline, whatever it found elsewhere.

3. **Stepping stones and combinations** (from the Genesis-Ω² concept, "Gap Engine: combination gaps"). A
   component that fails alone is archived as a stepping stone, not discarded.
   - **What is archived.** Its verdict, its effect estimate and interval, and the hosts on which it
     helped.
   - **What a combination attempt is.** A preregistered test of the *combination* of two archived
     components, against the better of the two alone, at matched budget. It requires a stated
     mechanism for why they should interact. Each one is its own attempt, inside the BY family
     above.
   - **The candidates so far:**
     - K5/K7 row guidance (B20_R31/R36) as the initialiser of the `cross_2` representation search;
     - the quotient attempt (B20_R26) with the relaxation rows.
   - **A note on scale.** Lean checks the rows themselves (B20_R37). The generated-rows LP, rounded,
     already reaches the optimum on 38 of 38 certified planted hosts at about 20 s (B20_R41). That is
     a construction signal at a large budget, which a matched-budget combination would have to turn
     into utility.

## Update after B20_R49 (a certification attempt that combines a stepping stone)

This section is DRAFT. It records results and changes no design.

**The chain (all preregistered, all DEV).**
- **B20_R46.** The row-invention procedure transferred to C4-free subgraphs, and all 37 obligations
  are Lean-CHECKED.
- **B20_R47.** The transferred rows alone added no certification coverage (22 vs 22 of 40). This
  attempt failed, and was archived as a stepping stone.
- **B20_R48.** The same rows combined with branching, with exact LP-dual leaf certificates, gave
  **CERTIFICATION_UTILITY**: 38 vs 26 of 40, p = 0.00024.
- **B20_R49.** A registered ablation attributes that utility to the rows: 36 vs 24 of 40 with vs
  without them, p = 0.00024.

**In this draft's terms**, B20_R48 is the first combination attempt: a stepping stone (B20_R47's rows)
with a stated mechanism. B20_R47's disclosed diagnostics showed the remaining gap is global, which
branching addresses. Note, though, that the partner component, branching, was written by the builder,
not invented.

**False-discovery control.** The attempt family is now:
- six construction attempts: B20_R17, R19, R26, R27, R31, R36;
- seven certification attempts: B20_R32, R35, R37, R47, R48, and, added after B20_R49, B20_R56 (sum-free rows,
  p = 0.25) and B20_R57 (sum-free rows on hosts hard for the conventional route, p = 0.0039; it survives
  Benjamini–Yekutieli at q = 0.1 over all 13 attempts, but its internal replication B20_R59 did not reproduce the
  coverage effect, p = 0.25).

B20_R49 is an attribution test of B20_R48, not a new attempt. Under Benjamini–Yekutieli at q = 0.1,
the two smallest p-values survive whatever the others are: B20_R35 at 9.5e-7, and B20_R48 at 0.00024.
B20_R48 survives for any family of up to 147 attempts.

**What this does and does not give GV4.**
- **What it gives.** A research *procedure* (generate, keep by LP gap, prove in Lean) that produced a
  component with a prospective, causally attributed utility in a domain it was not built for.
- **What it does not give.** It is not a better-improver comparison. No learned research process has
  been compared with a fixed one. The utility is in certification, and whether certification utility
  counts toward GV4 is still B20R35-OPEN-1.
- **A candidate GV4 pilot this enables.** Two research processes would generate C4 rows under one
  Lean proof budget:
  - a fixed enumerator over all graphs on at most 7 vertices, in atlas order;
  - a usage-driven process that proves first the patterns the tree route's certificates use most on
    DEV failures.
  Their successors, the registries, would be compared by tree-route coverage and time on fresh hosts.
  Headroom is unknown: B20_R37 found no coverage gain from 7-vertex triangle-free rows at 60 s.

## What is blocked, and on what

| Item | Blocked on |
|---|---|
| The `construct-pipeline-v1` candidate kind, custody and sandbox | **DONE in B20_R23** (pending review). In-process components only: the SAT finisher needs a subprocess, which the runner forbids. The LP guidance of `lp_greedy` is a registered intervention (ablation `random_greedy`, placebo `lp_shuffled_greedy`). |
| Paired research lineages for `sealed_improver_evaluation` | H08 remainder: the export format and the custodian path are not built; they need this study design first |
| The learned proposal policy | a DEV training corpus of pipeline research runs; can be built on DEV here |
| Statistician sign-off and power model | an external reviewer |
| Independent custodian, second machine | external parties (BLOCKED_ENVIRONMENT) |

## Next DEV steps possible here

1. The pipeline grammar and a fixed enumerating improver, on DEV, in process. Measure how much of the RX3 headroom a fixed proposer recovers by itself. If the fixed improver finds the good pipelines as easily as RX3's successive halving did, a learned improver has little room. That would be another fair negative, to be preserved.
2. A learned proposer (for example, a bandit or regression over pipeline features) against the fixed one, on DEV, with matched research budgets and the rule fixed in advance.

## Update after B20_R53–R58 (headroom)

No probed setting has a research decision with headroom:
- Wolfram's axiom at hard settings, for selection, keeping and 6-node conjectures (B20_R53, R54);
- sum-free pattern selection (B20_R58): all 17 patterns certify 13 of 16, against 9–11 for any development-ranked
  subset; the patterns' value is joint.

Two certification utilities of invented components were added: transferred, and positive only where the
conventional relaxation is the bottleneck (B20_R57). With graph construction (B20_R13, RX5) and larger C4 rows,
the builder now recommends the roadmap's fallback for GV4: report a useful solver without claiming a better
improver, unless a reviewer names a new domain to pilot.

