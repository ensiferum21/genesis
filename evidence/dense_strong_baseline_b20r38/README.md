# B20_R38 evidence: frozen E1 and E1b candidates against an exact MIP in the dense regime (DEV)

Builder-run. Nothing here is independently reviewed. It licenses no claim and changes no package,
comparator or rule.
- **Script:** `scripts/b20r38_dense_strong_baseline.py`. It was committed before running in
  `838dae6`, and its SHA-256 was sent to the user beforehand.
- **Log:** `run.log`, 1,267 s, the whole study pinned to one core.

## Design (fixed before running)

**Hosts.** 20 fresh DEV hosts per dense setting:
- planted_cluster n40 (0.8, 0.06), the regime of the exploratory B20_R36 observation;
- erdos n30 p0.42.

**Arms.**
- The frozen package descriptors, unchanged, in runc:
  - the E1 candidate (`cross_2` represent-and-repair, 0.5 CPU s) and its baselines;
  - the E1b candidate (LP greedy, 2.0 CPU s) and its baselines.
- An exact HiGHS MILP at 0.5 s and at 2.0 s (B20_R33's arm).

**Reference.** B20_R37's generator-v2 certification route at 60 s, seeded with the best witness
of any arm. It certified **all 40 hosts**, by LP over the generated rows alone, the slowest in
27.4 s.

**Verdict per study and setting.**
- CANDIDATE_BEYOND_MIP if the mean of D = candidate − MIP is ≥ 0.5 and its 90% interval is above 0;
- MIP_DOMINATES if the mean is ≤ −0.5 and the interval is below 0;
- otherwise NO_MATERIAL_DIFFERENCE.

## Result (`summary.json`, `rows.jsonl`, `hosts.json`)

| Study, setting | Candidate − MIP (same budget) | W / T / L | Verdict | Candidate at optimum | MIP at optimum | Candidate − best DSL baseline |
|---|---|---|---|---|---|---|
| E1 (0.5 s), planted | +91.1 [+89.8, +92.3] | 20 / 0 / 0 | CANDIDATE_BEYOND_MIP | **19/20** | 0/20 | +12.8 |
| E1 (0.5 s), erdos | +75.8 [+55.9, +94.2] | 14 / 6 / 0 | CANDIDATE_BEYOND_MIP | **19/20** | 6/20 | +10.5 |
| E1b (2.0 s), planted | +4.75 [+2.85, +6.35] | 17 / 0 / 3 | CANDIDATE_BEYOND_MIP | 0/20 | 0/20 | +2.0 |
| E1b (2.0 s), erdos | −6.75 [−8.85, −4.60] | 0 / 5 / 15 | MIP_DOMINATES | 5/20 | 17/20 | +2.9 |

**Two readings, one strong and one weak:**
- **The MIP at 0.5 s is nearly a non-arm.** Its incumbent at that budget had a median of 33
  edges on planted hosts and 16.5 on erdos, against optima around 120. HiGHS barely starts in
  0.5 s. The E1 contrasts at matched budget are huge for that reason, and they say little.
- **The meaningful comparison is across budgets: E1's candidate at 0.5 s against the MIP at
  2.0 s, four times the budget.**

| Setting | E1 at 0.5 s − MIP at 2.0 s | W / T / L | Mean gap to optimum (E1 / MIP) |
|---|---|---|---|
| planted | **+14.6** | 20 / 0 / 0 | 0.05 / 14.65 |
| erdos | +0.45 | 3 / 16 / 1 | 0.05 / 0.50 |

This is descriptive, and it was not a preregistered contrast.

## What it means

1. **A regime exists where a frozen candidate beats a strong exact baseline.** In the dense
   planted regime, E1's frozen candidate (`cross_2`, 0.5 s) reaches the certified optimum on
   19 of 20 fresh hosts. HiGHS at four times the budget reaches it on none, and is 14.6 edges
   below on average. On dense erdos hosts, E1 at 0.5 s matches the MIP at 2 s. E1b is beyond the
   MIP on planted and dominated on erdos.
2. **The regime is certifiable, but only with the generated rows.** With a good seed witness,
   the generated-rows route certified 40/40 at 60 s. The evaluator's own route certifies about 1
   in 20 dense planted hosts (B20_R35).
3. **What a real run would need.** These settings are not E1's decided settings (`e1-v2`).
   A real run here would need all of:
   - a versioned family rule and a calibration;
   - a new E1 package version;
   - adoption of a generated-rows reference by the evaluator (B20R35-OPEN-1; the engineering is
     B20_R39);
   - a reviewer's choice of the strong-baseline comparator: which MIP budget, and whether warm
     starts are allowed.

   It would support a scoped better-solver statement against an exact solver, on that panel
   only. This regime was found by DEV exploration (B20_R34, B20_R36) and declared before this
   run.

The 40 hosts are in `hosts.json`, and the handoff exposure addenda list them
(`handoff/e1*/exposure_hosts_addendum_b20r38.json`).
