# B20_R6 design pilot: an equational family with selection headroom? (B20R3-OPEN-1)

This pilot was run on DEV material by the builder. It is a design diagnostic, not a study, and it licenses no claim.

- **Method:** `scripts/b20r6_family_search.py`, committed as `d68da75` before the run, together with the new
  `ba_robbins` system. It reuses round 1 of the B20_R3 headroom pilot unchanged.
- **Measurements:** EXHAUST, FIXED@CAP (cap = 0.25 × exhaust CPU), EMPTY, and ORACLE (the dependency
  closure of the lemmas that exhaust target proofs used). Each is measured on 12 targets per range, at 1 s
  and 8 premises per target.
- **Exposure:** every pool statement and target is written here, so later studies count them as exposed.

## Verdicts (rule fixed in the script before running)

| Variant | Range | EMPTY | FIXED@CAP | EXHAUST | ORACLE | Verdict |
|---|---|---|---|---|---|---|
| ba_robbins | 5–8 | 2 | 2 | 2 | 2 | NO_HEADROOM |
| | 6–9 | 0 | 0 | 0 | 0 | |
| | 7–10 | 5 | 5 | 5 | 5 | |
| ba_robbins:t6 | 9–12 | 3 | 3 | 3 | 3 | NO_HEADROOM |
| | 10–12 | 1 | 1 | 1 | 1 | |
| bool_ring | 5–8 | 10 | 12 | 11 | 12 | NO_HEADROOM |
| | 6–8 | 10 | 12 | 11 | 11 | |
| bool_ring:t5 | 7–10 | 7 | 9 | 8 | 9 | NO_HEADROOM |
| | 8–10 | 8 | **11** | 8 | 8 | |

## What this says

**Robbins' basis sits at the floor.**

- E proves only 13 of 155 pool equations at 1 s, and no evaluation proof uses any of them.
- Libraries change nothing: EXHAUST equals EMPTY in every range.
- The fixed policy gets 1 lemma under the cap.

The family is too hard for E at these limits, so there is no library effect to select for.

**Boolean rings sit near the ceiling, and libraries interfere.**

- On 8–10 nodes, the 34-lemma FIXED@CAP library proves 11/12.
- The 132-lemma EXHAUST library proves 8/12, which is no better than EMPTY.
- ORACLE is built from the exhaust proofs, so it inherits that interference and also proves 8/12.
- In both bool_ring:t5 ranges, one target that EMPTY proves is lost by EXHAUST.

This is the second family where adding true lemmas hurts; the first was the B20_R3 Huntington diagnostic.

**Consequence.**

- **B20R3-OPEN-1 stays open.** Six systems in B20_R3 and two new ones here show no room for choosing *which
  lemmas to prove*.
- **The evidence points to a different action space** (handoff s19.2): library curation and premise selection,
  meaning which proved lemmas to keep and offer the prover. A bigger library is not better (B20R3-OPEN-2).
- **The ORACLE built from exhaust proofs is no upper bound once lemmas interfere.** Measuring curation
  headroom needs a reference that searches library subsets. A per-target best-of reference (bool_ring:t5
  8–10: 11 targets proved by at least one library) is a diagnostic ceiling, not a deployable baseline
  (s14.3).

## Files

- `<variant>.json`: pool, exhaust and fixed libraries, targets, per-target outcomes.
- `summary.json`: verdicts.
- `run.log`: the run log.
