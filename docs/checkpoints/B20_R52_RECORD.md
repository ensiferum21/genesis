# B20_R52 record: E1b-C4 DRAFT package; same-operator rehearsal through the v5 C4 tree route SUPPORTED, judge agrees

- **Run by:** the builder, with fixture keys. Nothing is adopted, and nothing is licensed.
- **Commits:**
  - `75d91fa` (setup): committed before the run, with the SHA-256 sent to the user beforehand;
  - the result commit that follows it.
- **Evidence:** `evidence/e1b_c4_package_b20r52/`.
- **Package:** `handoff/e1b_c4/`.

## Why

B20_R50 made E1b's C4 arm scorable under a DRAFT rule whose reference is the tree route over the
transferred rows. B20_R51 wired that route into the custodian path with custody. This step does for
E1b-C4 what B20_R43 did for E1d: it writes the package and runs the whole custody path once, end to end.

## Result

| Item | Result |
|---|---|
| Calibration record | B20_R50's Part A under the registered DRAFT rule; clean; same selection (erdos n40 p0.15, n30 p0.2) |
| SELECT (custodian, 30 hosts) | low_cycle_tm |
| CONFIRM (20 hosts, v5, tree reference at 600 s) | 20/20 certified (median 4.2 s, max 69 s) |
| Outcome | **SUPPORTED**: +1.15 per host [0.70, 1.65], 12/1/7, cost ratio 0.92 |
| Judge | agrees |

The disclosed smoke run at 120 s was INVALID because one reference was unsupported. The preregistered
600 s budget avoided that.

## What it means

Every builder-side step for E1b's C4 arm is done: calibration, readiness, causal pilot, package and
custody rehearsal. As on triangle-free, the claim is scoped to the DSL baselines, because an exact C4
MIP dominates on these settings. The chain from an invented procedure (B20_R46) to a rehearsed custody
path in the new domain (B20_R52) is complete on DEV.

## Tests

`tests_genesis/test_e1b_c4_package.py` (7).

## Open

B20R50-OPEN-1 is updated: package `handoff/e1b_c4`, rehearsal SUPPORTED. The rest is the reviewer's,
plus a statistician and an independent custodian.

## Development probes after the run (disclosed; scratch scripts; nothing committed as code)

1. **Lazy pattern rows in the tree route.** Each node keeps only the 4-cycle rows plus the pattern
   copies its LP violates, added in rounds. The certificate format and checker would be unchanged.
   - It certified K8 in 85 s, where the committed route is open at 120 s.
   - On the sparse hard hosts of the R52 smoke run it took about the same time (108 s against 105 s;
     119 s against still open at 120 s).
   - It helps only where pattern copies number in the tens of thousands.
2. **Dense C4 settings** (erdos n20 p0.4, planted n24 (0.6, 0.15), erdos n24 p0.35; 3 hosts each).
   - Lazy tree certification at 120 s: 1 of 9 hosts.
   - Exact C4 MIP at 2 s: below E1b's candidate on 4 of 9 hosts.
   - Exact C4 MIP at 8 s: at least 1–3 edges above the candidate on every host.
   - There is no dense C4 regime where E1b beats an exact MIP at four times its budget, and none of
     these settings is certifiable at this budget.
   - **Not pursued.** A C4 counterpart of E1d would need a candidate built for dense C4 hosts and a
     stronger certifier.
