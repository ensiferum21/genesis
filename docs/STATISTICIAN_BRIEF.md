# Statistician's brief: analysis plans and power models of the GV3 packages (B19-OPEN-4)

**For:** an independent statistician.
- **Status.** Written by the builder on 17 Oct 2026 (B20_R61). Nothing here is signed off. Every package below is
  a DRAFT awaiting this review, and no sealed panel has been run.
- **What is asked.** Sign off, amend or reject the registered analysis (section 2) and the power model that sized
  each package (section 3). Section 6 lists the specific questions.
- **How the numbers are checked.** Every table and derived number is produced by
  `scripts/b20r61_statistician_brief.py` from committed files. `tests_genesis/test_statistician_brief.py` re-derives
  them, and it also re-runs every stored power analysis from its pilot rows and requires an exact match.

## 1. The studies

Every GV3 package compares a frozen *candidate* solver with a *baseline* on the same host graphs. The pairing is
per host, and the outcome is the number of edges in a valid witness.

**The baseline.** It is the strongest of the registered baselines, chosen by the custodian on its own private
SELECT panel. The CONFIRM panel is drawn separately from the same calibrated settings, and the custodian holds it.

**The hosts.** They come from a few calibrated *settings* (random-graph families with fixed parameters). Each
setting is a stratum.

**What is being estimated.** Whether the candidate scores more edges, by a margin worth having (the minimum useful
effect, MUE, 0.5 edges per host).

**The packages:**

| Package | Domain | Strata | Comparison |
|---|---|---|---|
| E1 (`handoff/e1`) | triangle-free | 3 | candidate against time-matched DSL baselines |
| E1b (`handoff/e1b`) | triangle-free | 3 | the same, for an LP-guided candidate |
| E1b-C4 (`handoff/e1b_c4`) | C4-free | 2 | the same, on C4 hosts |
| E1d (`handoff/e1d`) | triangle-free, dense | 3 | candidate against five baselines, including an exact MILP at 4× budget |

**Causal follow-ups.** These use the same analysis with a different comparator: a registered *ablation* (one
component weakened) or a *placebo* (the component's signal scrambled at the same cost).

## 2. The registered analysis (`src/genesis/kernel/analysis.py`, plan schema v2)

The plan core is identical in every package. Only the hypothesis family differs.

| Element | Registered choice |
|---|---|
| Unit and endpoint | One host; the paired difference, candidate edges minus baseline edges |
| Failures | A failed or timed-out run scores 0 and is charged; it is never dropped |
| Unsupported hosts | Hosts whose optimum the reference cannot certify are excluded and reported; the analysis is INVALID if more than 5% are unsupported |
| Estimand | The mean over strata of the stratum mean difference (strata weigh equally) |
| Test | One-sided stratified sign-flip permutation test. It is exact at 18 or fewer non-zero differences; otherwise 20,000 seeded Monte Carlo flips with the +1 correction |
| Interval | Stratified bootstrap percentile, 90% two-sided, 4,000 resamples |
| Multiplicity | Holm within the custodian-assigned family `<evidence kind>:<domain>`, of declared size 3. Members not yet known count as p = 1 |
| Decision | SUPPORTED iff all hold: Holm rejects; the interval's lower end is above 0; the point estimate is at least the MUE; the CPU cost ratio is at most 3.0; and no stratum mean is below −1.0 |
| Stopping | A single analysis; a second analysis of the same evaluation is INVALID |
| Sensitivity (reported, never decisive) | Task sign test, leave-one-stratum-out, failures excluded, stratum-level sign flip |

## 3. The power model (`src/genesis/power.py`, "centred headroom")

**The model.** Headroom-limited integer improvements over centred DEV pilot differences. For each stratum:
- **Resample** pilot hosts, and subtract the stratum's pilot mean, so the pilot's own effect is removed and never
  used.
- **Add whole edges** to hosts that still have headroom below the certified optimum, with the probability that
  makes the stratum's expected gain equal the *design effect*. The design effect is 1.0 in every package, against
  an MUE of 0.5.
- **Measure headroom** from the centred candidate. This is B19's correction, because the B16 model called a
  near-ceiling candidate INFEASIBLE (B19-OPEN-4, B16-OPEN-2).

**Deciding a simulated study.** It uses the registered rule at the worst Holm rank (α/3), with a normal
approximation for the bound, and for the p-value beyond 14 non-zero differences. `approximation_check` compares the
approximations with the exact analysis.

**The size chosen.** The smallest size on the grid (10, 12, 15, 20, … per stratum) whose simulated power is at
least 0.8, with a floor of 10 per stratum. Each analysis uses 1,000 simulations.

**What each package relies on** (derived from the stored analyses):

| Analysis | n per stratum (total) | Power at the design effect | MC s.e. | Power at the MUE | Rejection rate at zero effect | Plan family it is bound to | Family the custodian assigns |
|---|---|---|---|---|---|---|---|
| E1 | 10 (30) | 0.881 | 0.010 | 0.249 | 0.006 | `sealed_evaluation` | `sealed_evaluation` |
| E1b | 10 (30) | 0.974 | 0.005 | 0.444 | 0.018 | `sealed_evaluation` | `sealed_evaluation` |
| E1b ablation | 10 (30) | 1.000 | 0.000 | 0.523 | 0.000 | `sealed_evaluation` **(mismatch)** | `ablation` |
| E1b placebo | 10 (30) | 0.985 | 0.004 | 0.427 | 0.003 | `sealed_evaluation` **(mismatch)** | `placebo` |
| E1b-C4 | 10 (20) | 0.841 | 0.012 | 0.321 | 0.012 | `sealed_evaluation` | `sealed_evaluation` |
| E1b-C4 ablation | 10 (20) | 0.991 | 0.003 | 0.520 | 0.000 | `sealed_evaluation` **(mismatch)** | `ablation` |
| E1b-C4 placebo | 10 (20) | 0.800 (within 2 s.e. of 0.8) | 0.013 | 0.180 | 0.009 | `sealed_evaluation` **(mismatch)** | `placebo` |
| E1d | 80 (240) | 0.814 (within 2 s.e. of 0.8) | 0.012 | 0.238 | 0.012 | `sealed_evaluation` | `sealed_evaluation` |
| E1d ablation | 15 (45) | 0.838 | 0.012 | 0.272 | 0.016 | `ablation` | `ablation` |

**Reproducibility.** Every row reproduces exactly from its pilot rows. The pilot rows' digest matches the stored
one, and `required_sample` returns the stored analysis field for field.

**Why E1d needs 80 per stratum.** Its pilot differences against HiGHS are very spread (s.d. 4.7–6.2 per stratum),
and the model removes the pilot's large mean effect (+10.6). So 80 per stratum is what a 1.0 effect needs, not
what the observed effect needs.

## 4. The same-operator rehearsals

Each package's whole custody path was rehearsed once by the builder, with fixture keys, on DEV panels. All came out
SUPPORTED, and the judge agreed. They test the machinery, not the science.

| Rehearsal | Tasks | Scored | Unsupported (strata) | Strata | Stratum-level sign-flip p | Smallest p it can reach |
|---|---|---|---|---|---|---|
| E1 (B20_R24) | 30 | 30 | 0 | 3 | 0.125 | 0.125 |
| E1b (B20_R24) | 30 | 29 | 1 (erdos:b73f6828) | 3 | 0.125 | 0.125 |
| E1b-C4 (B20_R52) | 20 | 20 | 0 | 2 | 0.250 | 0.250 |
| E1d (B20_R43) | 240 | 237 | 3 (planted_cluster:9491bde8) | 3 | 0.125 | 0.125 |
| E1d ablation (B20_R45) | 45 | 44 | 1 (planted_cluster:9491bde8) | 3 | 0.125 | 0.125 |

## 5. The DEV studies outside the packages

These are builder-run diagnostics, and none of them licenses a claim. They are listed because a reviewer will be
asked whether their positives count (`handoff/gv4/FALLBACK_CLAIM_DRAFT.md`, Part C).
- **Certification studies** (B20_R32, R35, R37, R47, R48, R49, R56, R57, R59). Each compares two certification
  routes on the same 40 fresh hosts at 60 s per route. The rules:
  - **coverage:** a one-sided exact McNemar test on the discordant hosts;
  - **time:** a stratified bootstrap 90% interval of the per-host wall saving;
  - **soundness:** every certificate is checked.
- **The attempt family** (`handoff/gv4/attempt_family.json`). Benjamini–Yekutieli at q = 0.1 over all 13
  preregistered component attempts. Six construction attempts were decided by interval rules with no single
  p-value, and count at p = 1.
- **Replication.** B20_R59 repeated B20_R57 on fresh seeds. Coverage did not replicate; the bound advantage did.

## 6. What the builder flags

1. **The E1b-C4 placebo design is underpowered at its chosen size.** Its stored power is 0.800 at 10 per stratum,
   exactly the target, with a Monte Carlo s.e. of 0.013. Re-simulated at that size with 10,000 simulations, under
   the family the custodian assigns: E1b-C4 placebo at n 10: 0.764. The other borderline row holds:
   E1d at n 80: 0.821. The proposed fix is to choose sizes with at least 10,000 simulations, or to require the chosen power to
   clear the target by two Monte Carlo standard errors.
2. **Four causal power analyses are bound to the wrong family.** They are E1b's ablation and placebo (B20_R28) and
   E1b-C4's (B20_R50). The custodian refuses a registration whose plan names a family other than
   `<evidence kind>:<domain>` (`custody_records.registration_problems`), and a power analysis is bound to its plan
   core. These four must therefore be recomputed before their follow-ups can be registered, as B20_R45 did for
   E1d. Recomputed under the assigned families:
   - E1b ablation: n 10 per stratum, power 1.000
   - E1b placebo: n 10 per stratum, power 0.980
   - E1b-C4 ablation: n 10 per stratum, power 0.992
   - E1b-C4 placebo: n 12 per stratum, power 0.879

   Only the random stream changes: the simulation is seeded from the plan core. The same data and size give
   0.859 under the `sealed_evaluation` family and 0.838 under the `ablation` family (E1d ablation, 15 per
   stratum).
3. **The claim wording outruns the rule.** Each `exact_claim` says the candidate wins "by at least the minimum
   useful effect, under the registered analysis". The rule requires a significant positive difference and a
   *point estimate* of at least 0.5, not a lower confidence bound of at least 0.5. Either reword the claims
   ("superior, with an estimated effect of at least 0.5") or tighten the rule (the bound's lower end at least the
   MUE). The rehearsals' intervals are far above 0.5, so no result so far depends on the choice, but it must be
   settled before a run.
4. **The stratum-level sign flip is uninformative at these strata counts.** With k strata its smallest attainable
   p is 1/2^k: 0.125 at three strata and 0.25 at two. It can never fall below 0.05 here. Drop it, or replace it
   with something that can.
5. **Unsupported hosts are excluded, and they cluster.** All three of E1d's rehearsal exclusions, and the one in
   its ablation rehearsal, are in one stratum (planted_cluster:9491bde8). The 5% cap is global. If the
   reference's failures correlate with the outcome, exclusion biases that stratum's mean. Options:
   - a per-stratum cap;
   - a registered worst-case sensitivity that scores excluded hosts as the stratum's largest observed loss.
6. **The test's null is symmetry, not a zero mean.** The sign-flip test treats each host's difference as
   symmetric about zero under H0. Is that acceptable for integer differences with many ties at zero (zeros carry
   no sign information and are dropped from the flips)?
7. **The interval is not multiplicity-adjusted.** The decision combines a Holm-adjusted test (α/3 at the worst
   rank) with an unadjusted one-sided 95% bound (the 90% two-sided interval). Is the conjunction acceptable, or
   should the bound be at the Holm level?
8. **The family sizes.** `sealed_evaluation:triangle_free_host_v1` is declared at size 3, which is E1, E1b and
   E1d. `sealed_evaluation:c4_host_v2` is also declared at 3 with one known member (E1b-C4); the unknown members
   count at p = 1, which is conservative. Confirm both sizes.
9. **The design effect.** It is 1.0 everywhere, while the pilot effects are 0.8–16.4 per stratum. Sizes are
   therefore set by spread and headroom alone, which is conservative by construction (B16-OPEN-2 asks whether the
   model's integer-bump assumption is reasonable).
10. **The comparator is selected.** It is the strongest of several baselines on a separate SELECT panel. This
    favours the baseline, so it should be conservative for the candidate. Confirm that no correction for the
    selection is needed on CONFIRM.

## 7. Questions to sign off

1. **B19-OPEN-4 and B16-OPEN-2.** Accept the centred-headroom power model, the design effect of 1.0 and the floor
   of 10 per stratum, or name a replacement.
2. **Sizing precision.** Should sizes be chosen with at least 10,000 simulations (finding 1)? Should E1b-C4's
   placebo follow-up use 12 per stratum or more?
3. **The four mismatched causal power analyses** (finding 2). Recompute them under the assigned families before
   freezing.
4. **The claim wording against the rule** (finding 3). Choose one of the two fixes.
5. **The stratum-level sign flip** (finding 4). Drop or replace it.
6. **Unsupported hosts** (finding 5). Choose a per-stratum cap, a worst-case sensitivity, or accept the current
   rule.
7. **The test, interval and family** (findings 6–8). Accept them, or amend.
8. **The certification studies' rules and the attempt family** (section 5). Are McNemar on discordant hosts,
   Benjamini–Yekutieli at q = 0.1, and counting interval-rule attempts at p = 1 an acceptable gate for counting a
   DEV positive?

## 8. Reproduce

```
export PYTHONPATH=src
python3 scripts/b20r61_statistician_brief.py          # tables and derived numbers (about 40 s)
python3 -m unittest tests_genesis.test_statistician_brief
python3 -m unittest tests_genesis.test_analysis_v2     # the analysis itself
```
