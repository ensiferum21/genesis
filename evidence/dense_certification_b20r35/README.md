# B20_R35 evidence: certification with generated rows where the evaluator's certification fails (DEV)

Builder-run. Nothing here is independently reviewed. It licenses no claim and changes no
evaluator.
- **Script:** `scripts/b20r35_dense_certification.py`. It was committed before running in
  `50e567a`, and its SHA-256 was sent to the user beforehand.
- **Route:** `src/genesis/discovery/generated_certify.py`, with the separation budget added in
  that commit; the defaults are unchanged.
- **Checker:** `src/genesis/verification/lp_dual_rows.py`, unchanged since B20_R32.
- **Log:** `run.log`, 3,414 s, run in one go with no resume.

## Design (fixed before running)

**Enrichment.** B20R32-OPEN-1 asked for a study enriched for hosts the evaluator cannot certify
by its LP, with the enrichment fixed in advance. Enrichment here is by setting: the two settings
B20_R34 found mostly uncertifiable at 60 s.
- planted_cluster n40 p_in 0.8 p_out 0.06;
- erdos n30 p0.42.

**Hosts.** 20 fresh DEV hosts per setting, seeds 20263501 and 20263511.

**Routes.** Both start from the evaluator's own seed witness, each at the calibration's 60 s,
back to back in alternating order.
- **a**: the evaluator's joint LP/SAT certification.
- **b**: the same, with the copies of B20_R31's Lean-checked K5 and W5 bounds added as LP rows
  (smallest pattern first, at most 10 s or 50,000 copies per pattern). The exact checker checks
  every LP certificate first.

**Verdict.** CERTIFICATION_UTILITY iff all four hold:
- b is sound;
- b certifies at least as many hosts as a;
- McNemar p < 0.05 on hosts certified by one route only;
- the 90% interval of the per-host wall saving is above 0.

## Result (`summary.json`, `rows.jsonl`, `hosts.json`, `certificates/`)

| | a (evaluator) | b (generated rows) |
|---|---|---|
| **Certified within the 60 s budget** | **7/40** | **27/40** |
| … planted n40 (0.8, 0.06) | 1/20 | 15/20 |
| … erdos n30 p0.42 | 6/20 | 12/20 |
| Upper bound from an exact LP dual | 6 | 27 |
| Total wall time | 2,054 s | 1,315 s |
| Median wall time per host | 59.5 s | 28.3 s |

| Check | Result |
|---|---|
| Discordant hosts (certified by one route only) | **20 against 0**, McNemar one-sided p = 9.5 × 10⁻⁷ |
| Mean wall saving per host | **+18.5 s**, 90% interval [+13.9, +23.3] (planted +24.6, erdos +12.3) |
| Soundness | every b certificate VALID, no value disagreements |

**Verdict: CERTIFICATION_UTILITY.**

**Detail:**
- **Certificates kept.** The 20 LP certificates b produced on hosts a did not certify are in
  `certificates/`, and `tests_genesis` re-checks them.
- **Bounds.** b's upper bound is lower than a's on 30 of 40 hosts: by 1–3 on 12 of them, and by
  6–10 on 18. b's LP step took a median of 4.1 s and at most 9.4 s, with a median of 31,000 rows.
- **What b left uncertified.** On its 13 uncertified hosts, b's remaining gap is 1 edge on 12 and
  2 on one. Either the LP bound is one above the optimum, or SAT did not reach the bound within
  the budget.
- **The budget is soft.** a certified one host by SAT/DRAT after 77.7 s wall: the evaluator's
  SAT call overran the 60 s budget, as B20_R30 also saw. The tally counts it as certified, which
  favours a. b's slowest certification took 42.0 s.

## What it means

This is the first preregistered positive DEV utility of a machine-generated, Lean-checked
component in this project. The benefit is in certification, not construction.

On the two settings where the evaluator's certification mostly fails, the generated rows let the
same procedure certify four times as many hosts (27 against 7) within the same budget, in less
time. Every certificate was checked exactly against Lean-checked validity.

**Limits, all for the reviewer:**
- **Scope.** DEV, builder-run, and preregistered. The two settings were chosen from a DEV probe
  (B20_R34), and the enrichment was declared before this run.
- **Novelty.** The rows are classical facts: a triangle-free graph has at most 6 edges on 5
  vertices, and at most 7 on the 5-wheel. They are machine-*generated* and machine-*checked*,
  not new mathematics. No novelty is claimed.
- **Strong baselines for certification are unmeasured.** HiGHS proves these optima in about 10 s
  but emits no checkable certificate. A certifying MIP, or SAT with symmetry breaking, would be
  the stronger comparison.
- **The evaluator is unchanged.** Using the route there would be a reviewed trust-path change:
  a new checker identity, with the Lean package in custody.
- **Coverage.** Even with the rows, these settings reach 27/40 at 60 s, below the 90%
  certification limit. They are not yet usable as a calibrated family.

The 40 hosts are in `hosts.json`, and the handoff exposure addenda list them
(`handoff/e1*/exposure_hosts_addendum_b20r35.json`).
