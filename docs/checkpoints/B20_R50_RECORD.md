# B20_R50 record: E1b's C4 arm, made scorable by the transferred rows (three READY_FOR_REVIEW; MIP dominates)

- **Run by:** the builder, on DEV. A DRAFT rule, adopted by nothing. No claim is licensed.
- **Commits:**
  - `1c19b07` (setup): committed before the run, with the SHA-256 sent to the user beforehand;
  - the result commit that follows it.
- **Evidence:** `evidence/e1b_c4_readiness_b20r50/`.

## Why

E1b had no C4 study:
- under e1-hard-v2, no C4 setting passed the certification limit;
- B20_R23's C4 causal pilot was UNSETTLED_REFERENCE.

B20_R48 and R49 gave a certification route on C4 whose utility comes from the transferred rows.

## Result

**Draft rule `e1-hard-v2-c4tree-draft`.** It is e1-hard-v2 with the tree route as reference.

**Calibration** (candidate-blind):
- selected **erdos n40 p0.15** and **erdos n30 p0.2**, both 8/8 certified with medians of 4.8 and
  6.0 s;
- n36 p0.17 missed at 7/8, and n32 p0.2 at 4/8.

**Re-pilot** on 30 fresh hosts, all certified:

| Contrast | Mean | Verdict |
|---|---|---|
| Candidate vs the strongest DSL baseline | +1.17 | READY_FOR_REVIEW |
| Candidate vs ablation | +1.43 | READY_FOR_REVIEW |
| Candidate vs placebo | +2.73 | READY_FOR_REVIEW |

**Descriptive:** the exact C4 MIP at 2 s is optimal on 30/30, and E1b is 0.93 below it.

## What it means

The invented, transferred component turned an unscorable domain into a scorable one. E1b on C4 now
stands where E1b on triangle-free stands: ready against DSL baselines, dominated by an exact MIP
(B20R33-OPEN-1).

## Tests

`tests_genesis/test_e1b_c4_readiness.py` (6).

## Open

- **B20R50-OPEN-1 (new).** Adopt or decline the draft rule `e1-hard-v2-c4tree-draft` for E1b's C4 arm.
  It depends on B20R48-OPEN-1, the tree route as reference, and on B20R33-OPEN-1, the scope of
  "strong baselines".
- **B20R23 C4 item.** The UNSETTLED_REFERENCE causal pilot is now settled on DEV: both contrasts are
  READY_FOR_REVIEW.
