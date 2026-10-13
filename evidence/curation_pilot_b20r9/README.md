# B20_R9 design pilot: is there headroom in curating a lemma library? (B20R3-OPEN-1/2)

- **Script:** `scripts/b20r9_curation_pilot.py`, committed as `63f7d8b` before running.
- **Status:** DEV, run by the builder. This is a design diagnostic; it licenses no claim.
- **Exposure:** every pool statement and target is written here, so later studies count them as exposed.

## Question

B20_R3 and B20_R6 found no room for choosing *which lemmas to prove*, and they found that true lemmas interfere. This pilot asks the next question: does choosing *which proved lemmas to keep* have headroom?

Libraries compared, all built from the exhaust library and closed under lemma dependencies:

| Library | What it is |
|---|---|
| EMPTY | no lemmas |
| FIXED@CAP | the fixed policy's library under the cap |
| ALL | the full exhaust library |
| DEV-CURATED | deployable: lemmas ranked by use in development-target proofs, top-k chosen on the development targets |
| EVAL-CURATED | the same procedure run on the evaluation targets; an optimistic reference, not an arm |
| BEST-OF | per target, any library proves it; a diagnostic ceiling |

Each library is evaluated on 12 evaluation targets per range.

## Results (verdict rule fixed before running)

| Variant | Range | EMPTY | FIXED@CAP | ALL | DEV-CURATED | EVAL-CURATED | BEST-OF | Verdict |
|---|---|---|---|---|---|---|---|---|
| ba_huntington:t6 | 9–12 | 6 | 12 | 12 | 12 (k=1) | 12 | 12 | NO_CURATION_HEADROOM |
| | 10–12 | 7 | 10 | 10 | 10 (k=1) | 10 | 10 | |
| ba_huntington | 7–10 | 9 | 12 | 12 | 12 (k=1) | 12 | 12 | NO_CURATION_HEADROOM |
| | 8–10 | 10 | 12 | 12 | 12 (k=1) | 12 | 12 | |
| bool_ring:t5 | 7–10 | 11 | 11 | 10 | **12** (k=1) | 12 | 12 | NO_CURATION_HEADROOM |
| | 8–10 | 8 | 10 | 8 | 10 (k=16) | 11 | 11 | |
| ba_sheffer:t6 | 9–12 | 6 | 6 | 6 | 6 (k=4) | 6 | 6 | NO_CURATION_HEADROOM |
| | 10–12 | 6 | 6 | 7 | 6 (k=1) | 7 | 7 | |

## What this says

- **Huntington.** One lemma, idempotence, is all the evaluation targets need (k=1). Every library that contains it reaches the per-target ceiling.
- **Boolean rings.** Interference is real but small. DEV-curated beats max(FIXED@CAP, ALL) by at most 1 of 12, and the optimistic EVAL-curated reference also by at most 1. The cap already keeps the fixed library small enough to avoid most of the interference.
- **Sheffer.** Libraries barely matter: at most one target separates any two libraries.
- **Across B20_R3, R6 and R9.** No research-policy dimension tried reaches the preregistered 2 of 12 threshold:
  - which lemmas to prove (eight systems);
  - prover strategy and time (B20_R3 round 5);
  - which lemmas to keep (four variants).

  On these families with E at 1 s, a better research policy has at most one target in twelve to gain.

## Consequence

The better-improver question (GV4) cannot be answered positively on this domain at these settings. A frozen E3 study here would have no power to show superiority, and handoff s14.4 says not to launch one.

GV4 needs a different domain or a harder setting where research outputs matter, for example:

- a formal Lean domain;
- the graph construction domain, where B19's represent-and-repair candidate shows a DEV gain;
- longer horizons, where libraries compound.

This record does not choose among them; that is a design decision for review.

## Files

- `<variant>.json`: libraries, development and evaluation targets, per-k results, per-target outcomes.
- `summary.json`: verdicts.
- `run.log`: run log.
