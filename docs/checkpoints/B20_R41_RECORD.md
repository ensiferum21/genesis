# B20_R41 record: E1d readiness, in which a frozen candidate beats an exact MIP given four times the budget (GV3 path; DEV, DRAFT rule)

- **Run by:** the builder, on DEV. Nothing here is independently reviewed or licenses a claim. The
  rule `e1-hard-v3-draft` is a DRAFT and is not in `calibration.RULES`.
- **Commits:**
  - `39b0999` (setup): the script and the route option, committed before the run. The script's
    SHA-256 was sent to the user beforehand.
  - The result commit that follows it.
- **Evidence:** `evidence/e1d_readiness_b20r41/`. Its README has the full tables.

## Why

GV3 asks for a candidate "beyond strong baselines".
- On the decided family an exact MIP is always optimal (B20_R33).
- B20_R38 found a dense planted regime where E1's frozen candidate beats HiGHS at four times its
  budget. That regime is certifiable with the generated rows (B20_R35, R37).
- The custody for a generated-rows reference (B20_R39) and an exact-MIP baseline kind (B20_R40)
  are built.

This step does for that regime what B20_R24 did for E1: a versioned rule, a candidate-blind
calibration, and a re-pilot with power, with the MIP among the comparators.

## Design

**Rule.** e1-hard-v2's thresholds, with three changes:
- **Strongest baseline:** the per-host best of E1's three DSL baselines and HiGHS at 0.5 s and at
  2.0 s.
- **Reference:** the generated-rows route with rounding of its own LP. It never takes the
  candidate as input.
- **Median reference time limit:** 30 s, because the route's separation step alone takes 15 s.

**Part A:** 8 dense settings × 8 hosts. **Part B:** 30 hosts on the selected settings.

**Development looks.** All are disclosed, and they used 8 new tiny hosts plus hosts already
exposed in B20_R38. One of them showed that the generated-rows LP is integral on dense planted
hosts. `generated_certify.certify_with_rows` therefore gained `lp_rounding_seconds`, which is off
by default.

## Result

**Calibration.** Three planted settings were selected: n38 (0.8, 0.07), n40 (0.8, 0.06) and n40
(0.7, 0.06).
- **Erdos settings:** all three fail, because HiGHS at 2 s is at the optimum on 20 of 21
  certified hosts.
- **The densest planted setting** fails on certification (6/8) and on speed.
- **The reference:** on all 38 certified planted hosts, rounding the route's own LP reached the
  optimum, with no SAT step.

**Re-pilot.** 30 fresh hosts, all certified, with reference wall times of median 20.5 s and max
27.5 s.
- **Comparator:** the strongest baseline was **the MIP at four times the budget**.
- **Optimum hits:** the candidate was at the certified optimum on **30/30** hosts; the MIP at
  2 s on 6/30; the best DSL baseline on 0/30.
- **Difference:** candidate − comparator was **+10.6 per host [9.1, 12.1]**, W/T/L 24/6/0, with
  every stratum positive (+10.9, +16.4, +4.5).
- **Cost ratio:** 0.34.
- **Dry run:** SUPPORTED.
- **Centred power:** 80 hosts per stratum (240) for power 0.81 at the minimum useful effect.

**Verdict: READY_FOR_REVIEW.**

## What it means

**GV3 (B20R33-OPEN-1).** On DEV, there is now a calibrated, certifiable family in which E1's frozen
candidate beats every registered baseline, including an exact solver given four times its CPU,
and the readiness checks pass. A real run is the reviewer's to authorise. It needs:
- `e1-hard-v3-draft` adopted;
- the generated-rows reference adopted, with its custody (B20R35-OPEN-1);
- registry v2 wired so that the custodian can select the MIP comparator (B20R40-OPEN-1);
- a new E1 package version (E1d);
- a statistician and an independent custodian.

**Caveats:**
- The reference itself, LP plus rounding, solves these hosts exactly in about 20 s. The plan
  treats it as ground truth, not as a competitor.
- The regime came from DEV exploration.

## Tests

`tests_genesis/test_e1d_readiness.py` (11).
- **Design checks:**
  - the rule changes only what it declares;
  - the arms are the frozen E1 descriptors plus two v2 MIP budgets;
  - the comparator comes from the explicit set;
  - the LP rounding is off by default, uses the route's own LP, keeps only a checked witness, and
    its edge values are the LP primal.
- **Record checks:**
  - the hosts match the digests;
  - the summaries, eligibility and selection recompute;
  - the calibration was candidate-blind;
  - the pilot verdict recomputes from the rows;
  - no arm exceeds a certified optimum;
  - the hosts are fresh and in the addenda.

## Open

B20R41-OPEN-1 is new: the E1d package decision. B20R33-OPEN-1 is updated with this result.
