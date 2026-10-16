# B20_R38 record: frozen E1 and E1b candidates against an exact MIP in the dense regime (GV3 path; B20R33-OPEN-1)

- **Run by:** the builder, on DEV. Nothing here is independently reviewed, and nothing licenses
  a claim. No package, comparator or rule was changed.
- **Commits:**
  - `838dae6` (setup): the script, committed before the run. Its SHA-256 was sent to the user
    beforehand.
  - The result commit that follows it.
- **Evidence:** `evidence/dense_strong_baseline_b20r38/`.

## Why

On the decided family, an exact MIP is always optimal, so neither frozen candidate can be "beyond
strong baselines" there (B20_R33). B20_R34 and B20_R36 pointed to a dense planted regime where
the MIP struggles. This step tests the frozen descriptors there, prospectively.

## Result

40 fresh hosts, all certified by the generated-rows route.

| Study and setting | Verdict |
|---|---|
| E1, planted | CANDIDATE_BEYOND_MIP |
| E1, erdos | CANDIDATE_BEYOND_MIP |
| E1b, planted | CANDIDATE_BEYOND_MIP (+4.75) |
| E1b, erdos | MIP_DOMINATES (−6.75) |

The E1 contrasts at 0.5 s are inflated, because HiGHS barely starts within 0.5 s.

**The informative comparison is descriptive: E1's candidate at 0.5 s against the MIP at 2.0 s.**
- On planted hosts: +14.6 per host, 20/0/0. E1 reached the optimum on 19/20 hosts, the MIP on
  0/20.
- On erdos hosts: +0.45 per host, 3/16/1.

## What it means

**GV3 (B20R33-OPEN-1).** There is a regime where a frozen candidate beats an exact solver given
four times its budget, and the regime is certifiable with generated rows.

Turning this into a real run needs reviewer decisions:
- the generated-rows reference (B20R35-OPEN-1; engineering in B20_R39);
- a versioned family rule and calibration for the dense regime;
- the comparator: which MIP budget, and whether warm starts are allowed;
- a new E1 package version.

The regime came from DEV exploration and was declared before this run.

## Tests

`tests_genesis/test_dense_strong_baseline.py` (4) checks:
- the arms are the frozen descriptors;
- the verdicts follow from the rows;
- no arm exceeds a certified optimum;
- the hosts are fresh and in the addenda.

## Open

B20R33-OPEN-1 is updated with this result. It remains a decision.
