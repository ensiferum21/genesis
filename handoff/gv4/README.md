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

## What is blocked, and on what

| Item | Blocked on |
|---|---|
| The `construct-pipeline-v1` candidate kind, custody and sandbox | the canonical B20_R5/R7 code (B20_R11 history) |
| Paired research lineages for `sealed_improver_evaluation` | H08 in the canonical line (B20_R11 history) |
| The learned proposal policy | a DEV training corpus of pipeline research runs; can be built on DEV here |
| Statistician sign-off and power model | an external reviewer |
| Independent custodian, second machine | external parties (BLOCKED_ENVIRONMENT) |

## Next DEV steps possible here

1. The pipeline grammar and a fixed enumerating improver, on DEV, in process. Measure how much of the RX3 headroom a fixed proposer recovers by itself. If the fixed improver finds the good pipelines as easily as RX3's successive halving did, a learned improver has little room. That would be another fair negative, to be preserved.
2. A learned proposer (for example, a bandit or regression over pipeline features) against the fixed one, on DEV, with matched research budgets and the rule fixed in advance.
