# B20_R106 evidence: Genesis's max-cut engine on Gset, once: MCX_LEADS

Builder-run on DEV (the open-record track). It licenses nothing; no record claim.
- **Script:** `scripts/b20r106_mcx_gset.py`, preregistered at `ff08000` (SHA-256 `257d7ea0…e7a5`), before B20_R102 or
  B20_R105 ran.
- **Run:** alone on CPU 0, 1,290 s, on 23 Oct 2026 (14:51–15:12 SGT), right after B20_R102 on the same machine.
  `code_identity` `e7a8ac93…`, the committed tree (B20_R102's).
- **The other core.** While it ran, the builder wrote B20_R102's record (documents, one test run of under a second).
- **Inputs, refused unless valid:**
  - B20_R105's `configs.json` (SHA-256 `7c9e9aca…`);
  - B20_R102's rows (the comparators);
  - the best-known table (`3b97a82b…`: the BLS 2013 and MACUT 2012 papers' values).
- **Engine:** `mcx-v1`, binary pinned `10825596…0978`.

| File | What |
|---|---|
| `rows.jsonl` | 54 instances, each with its class from B20_R105's classifier, four runs (chosen and default, at 1 s and 10 s) with their witness cuts, and B20_R102's comparator values. Every cut was re-checked by the domain's two checkers |
| `summary.json` | The seven sign tests, the headline, per-arm fractions by family, instances reaching the best known value, record candidates, validity |
| `run.log` | The run |

## Result: MCX_LEADS

**Sign tests** over the 54 instances (ties dropped, two-sided, alpha 0.05 / 7):

| Comparison | Wins–losses (ties) | p | Label |
|---|---|---|---|
| chosen@1 vs BURER2002@1 | 48–4 (2) | 1e-10 | **AHEAD** |
| chosen@10 vs BURER2002@10 | 46–3 (5) | 7e-11 | **AHEAD** |
| chosen@1 vs dSB@1 | 47–5 (2) | 1e-9 | **AHEAD** |
| chosen@10 vs dSB@10 | 45–3 (6) | 1e-10 | **AHEAD** |
| chosen@10 vs the virtual best of 12 heuristics @10 (12x the compute) | 40–3 (11) | 3e-9 | **AHEAD** |
| chosen@1 vs default@1 (BLS's setting in this engine) | 24–17 (13) | 0.35 | COMPARABLE |
| chosen@10 vs default@10 | 26–11 (17) | 0.020 | COMPARABLE |

**Fraction of the best known value** (mean over 54 instances) and instances reaching it:

| Arm | Mean | Random | Toroidal | Planar | Reaching the best known |
|---|---|---|---|---|---|
| **mcx chosen@10** | **0.99860** | 0.99954 | 0.99984 | 0.99686 | **24** |
| mcx default@10 | 0.99730 | 0.99898 | 0.99952 | 0.99419 | 18 |
| **mcx chosen@1** | **0.99728** | 0.99914 | 0.99882 | 0.99426 | 16 |
| Virtual best of 12 published heuristics @10 | 0.99675 | 0.99882 | 0.99483 | 0.99502 | 11 |
| dSB@10 | 0.99618 | 0.99869 | 0.99290 | 0.99451 | 6 |
| mcx default@1 | 0.99544 | 0.99804 | 0.99904 | 0.99056 | 13 |
| BURER2002@10 | 0.99537 | 0.99758 | 0.99320 | 0.99359 | 6 |
| dSB@1 | 0.99328 | 0.99537 | 0.99113 | 0.99164 | 2 |
| BURER2002@1 | 0.99202 | 0.99440 | 0.98928 | 0.99030 | 3 |

- **At 1 s the configured engine is ahead of the virtual best at 10 s**, which runs twelve heuristics for ten seconds
  each.
- **Where the published tools are weakest it is strongest.** On the ±1 tori G32–G34 every published tool ends at least 20
  below the best known value. The engine reaches it on G32 (1410) and G33 (1382) and ends 2 below on G34 (1382 vs
  1384). On G11–G13 it reaches the best known value on all three.
- **Planar instances remain the hardest.** At 10 s it is 0.31% below the best known value on average, while still
  ahead of every published tool. G37: 7686 against MACUT's 7690, which MACUT reported after about 15 minutes per
  run. G36: 7656 against 7679.
- **Its three losses to the virtual best (and to BURER2002) at 10 s:** G4 (11634 vs 11646), G21 (922 vs 930) and
  G23 (13323 vs 13324).
- **No run exceeded a best known value: no RECORD_CANDIDATE.**
- **The classifier** put every instance in Gset's own family (25 random, 9 toroidal, 20 planar).
- **Validity:** median metered CPU 1.21 of the budget at 1 s and 1.02 at 10 s (the Python child's start-up is metered,
  for every arm alike); 0 failed runs of 216.

## Against the expectation (stated before running)

| Expectation | What happened |
|---|---|
| Chosen AHEAD of BURER2002 at 1 s, COMPARABLE at 10 s, so MCX_COMPARABLE | AHEAD at both: **MCX_LEADS** |
| Chosen AHEAD of dSB at both budgets | Yes |
| Chosen@10 BEHIND or COMPARABLE to the virtual best at 10 s | AHEAD (40–3) |
| Chosen vs default COMPARABLE at both budgets | Yes |
| No RECORD_CANDIDATE | None |

## What it means, and what it does not

- **Genesis now has a max-cut solver that beats the strongest pinned published tools on the public benchmark.** It
  wins at equal budgets on one core, under the same harness and on the same day, preregistered, on instances it was
  never developed or configured on (after one disclosed development look at an earlier draft on seven of them).
- **Where the lead comes from.**
  - **Mostly the engine.** The engine with BLS's own published setting (default) already beats every published tool
    here at 10 s.
  - **Less from the system's configuration.** It adds more on Gset (0.99860 vs 0.99730; 24 vs 18 instances at the
    best known value), but not significantly at the preregistered level.
  - So what is shown is an engine of published parts, combined by the builder and configured by the system, not an
    invention of the system's.
- **Not a record.** It matches the 2012–13 best known values on 24 of 54 instances and exceeds none. BLS's and MACUT's
  published runs used minutes per instance. The comparators are MQLib's 2018 implementations and Genesis's dSB, not
  the authors' own BLS or MACUT code, which is not available here.
- **One seed per run,** as in B20_R102; a replication with more seeds, and longer budgets against the best known
  values, are the next steps.
