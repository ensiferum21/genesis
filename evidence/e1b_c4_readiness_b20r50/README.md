# B20_R50 evidence: E1b's C4 arm, made scorable by the transferred rows (DRAFT rule; DEV)

Builder-run. Nothing here is independently reviewed. It licenses no claim, adopts no rule, and changes
no package.
- **Script:** `scripts/b20r50_e1b_c4_readiness.py`, committed before running in `1c19b07`. Its SHA-256
  was sent to the user beforehand.
- **Code identity:** the summary records `f755bcf2…`, the setup commit's.
- **Log:** `run.log`, 1,847 s, in one go.
- **Concurrent work.** The second core ran the B20_R49 checkpoint's release matrix, in a separate
  worktree, for the whole run. It also ran two development probes at low priority, described
  at the end of this file. The study was pinned to its own core. Wall time enters only the calibration's
  median-reference-time limit, and both selected settings passed it with medians of 4.8–6.0 s against
  the 15 s limit.
- **Files:**
  - `calibration_hosts.json` and `calibration_rows.jsonl`, with `calibration_record.json`;
  - `pilot_hosts.json` and `pilot_rows.jsonl`, with `pilot_summary.json` and three power analyses;
  - `summary.json`.

## Why

E1b, the LP-guided `construct-pipeline-v1` candidate, had no study on C4:
- under e1-hard-v2, no C4 setting was eligible (B20_R24): erdos n30 p0.2 certified 6/8 within 60 s,
  with a median evaluator time of 24 s;
- B20_R23's C4 causal pilot was UNSETTLED_REFERENCE.

B20_R48 and R49 gave a certification route whose utility is caused by the rows the system invented
and transferred to C4.

## Draft rule `e1-hard-v2-c4tree-draft`

It is e1-hard-v2 with one change: the reference is B20_R48's tree route, with B20_R46's rows and an
exact tree check, at 60 s. A test checks that nothing else differs, and that no study can adopt the
draft.

## Part A: calibration (candidate-blind; 8 hosts per setting)

| Setting | Certified | Median reference time | Mean gap (edges) | Ceiling rate | Eligible |
|---|---|---|---|---|---|
| erdos n30 p0.2 (E1b's C3) | **8/8** | 6.0 s | 2.50 | 0.0 | **yes** (failed under e1-hard-v2: 6/8, 24 s) |
| erdos n36 p0.17 | 7/8 | 5.7 s | 2.29 | 0.0 | no: too few certified |
| erdos n32 p0.2 | 4/8 | 37.8 s | 3.25 | 0.0 | no: too few certified, too slow |
| erdos n40 p0.15 | **8/8** | 4.8 s | 2.25 | 0.0 | **yes** |

**Selected:** erdos n40 p0.15 and erdos n30 p0.2. These are the first C4 settings eligible under an
e1-hard-v2-type rule.

**Descriptive.** The exact C4 MIP (HiGHS over the 4-cycle rows), on certified hosts:
- at 2.0 s: optimal on 7/8, 6/7, 3/4 and 6/8 of the four settings;
- at 8.0 s: optimal on 8/8, 7/7, 4/4 and 8/8.

## Part B: re-pilot (30 fresh hosts, 15 per selected setting; reference at 120 s)

**The reference certified all 30**, in 3.7–4.8 s each.

| Contrast | Comparator | Mean difference | W / T / L | CPU ratio | Power choice | Dry run | Verdict |
|---|---|---|---|---|---|---|---|
| Readiness | low_cycle_tm, the strongest DSL baseline | **+1.17** [0.83, 1.50] | 22 / 6 / 2 | 0.94 | 10 per stratum | SUPPORTED | **READY_FOR_REVIEW** |
| Causal: ablation (`init random_greedy`) | ablation | **+1.43** [1.20, 1.63] | 24 / 6 / 0 | 1.04 | 10 per stratum | SUPPORTED | **READY_FOR_REVIEW** |
| Causal: placebo (`init lp_shuffled_greedy`) | placebo | **+2.73** [2.30, 3.17] | 25 / 5 / 0 | 1.00 | 10 per stratum | SUPPORTED | **READY_FOR_REVIEW** |

**Descriptive.**
- **The candidate against the exact C4 MIP:** **−0.93 per host**, at 2.0 s and at 8.0 s alike
  (0 / 11 / 19). The MIP was optimal on 30/30 hosts at both budgets; the candidate on 11/30.
- **Gaps to the optimum:**

  | Arm | Mean gap |
  |---|---|
  | candidate | 0.93 |
  | low_cycle_tm | 2.10 |
  | ablation | 2.37 |
  | placebo | 3.67 |
  | multistart_tm | 4.73 |
  | exchange_tm | 6.27 |

## What it means

- **The transferred rows made a domain scorable.** With the tree route as reference, two C4 settings
  become calibratable. E1b's C4 arm is READY_FOR_REVIEW against its time-matched DSL baselines and in
  both causal contrasts: the LP signal is the active ingredient, as on triangle-free (B20_R28).
- **But not beyond strong baselines.** On C4, as on triangle-free (B20R33-OPEN-1), an exact MIP is
  optimal within 2 s on these settings and dominates E1b. A SUPPORTED result here would be scoped to
  the DSL baselines.
- **What a real run needs.** A reviewer adopts the draft rule and the tree route as the C4 reference
  (B20R48-OPEN-1). Then: a statistician, an independent custodian, and custody wiring for the tree
  certificates (B20_R51).

## Tests

`tests_genesis/test_e1b_c4_readiness.py` (6):
- the draft changes only the reference, and no study can adopt it;
- the arms, and the registered interventions;
- the MIP and the reference agree on K6;
- the calibration and the selection recompute from the rows;
- the pilot's verdicts and the descriptive table recompute;
- the 62 hosts are fresh and in the exposure addenda.

## Development probes run alongside (disclosed; not part of this study; scripts in the builder's scratch space)

1. **Do larger C4 rows have headroom?** The C4 kept rule was run on every graph with at most 7 vertices:
   - 1,245 graphs, 393 of them cycle-covered;
   - 166 kept: 34 on up to 6 vertices, as in B20_R46, and 132 on 7 vertices;
   - none of them proved in Lean.
   A synthetic registry of all 166 was then used, DEV only, in B20_R48's tree route on the six hosts
   left open in B20_R48 and B20_R49, at 60 s. It certified none of them, and its upper bounds were
   equal or one edge better. Its node LPs were 3–9 times larger, so it explored 4–8 times fewer nodes.
   **There is no headroom from larger rows at this budget.** A GV4-style pilot comparing a fixed and a
   usage-driven generator of C4 rows would therefore have nothing to win, and is not pursued.
2. **Does branch and bound help on dense triangle-free hosts?** A triangle-free version of the tree
   route and checker was built in scratch, not committed. It certified 16 of 16 small random hosts at
   their exact optimum. On B20_R37's 7 open dense hosts at 60 s it certified 4, but:
   - 2 of the 4 came from LP rounding at the root, not from branching;
   - with up to 80,000 pattern copies, each node LP takes several seconds, so it explored at most 9
     nodes.
   E1d's reference already certifies 237/240 hosts at 120 s (B20_R43), so this is not pursued now.
