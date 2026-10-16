# B20_R37 record: generator v2 (seven vertices) and certification coverage in the dense regime

- **Run by:** the builder, on DEV. Nothing here is independently reviewed, and nothing licenses
  a claim. No evaluator was changed.
- **Commits:**
  - `9e043b8` (setup): `invention/cuts_v2.py`, the route options,
    `formal_research.search.split_options`, the script and the unit tests. All were committed
    before the run, and the SHA-256s were sent to the user beforehand.
  - The result commit that follows it.
- **Evidence:** `evidence/generator_v2_b20r37/`.

## Why

B20_R35 found certification utility for the generated rows in two dense settings, but at 27/40,
below the 90% limit. A development look at the hosts it left uncertified showed that 7-vertex
rows close most of their LP gaps.

## Result

**Part A.**
- **Generation.** Generator v2 keeps 9 patterns from every graph on at most seven vertices: K5,
  W5, and seven 7-vertex patterns including K7 ≤ 12 and K7−e ≤ 12.
- **Lean.** All 12 obligations are CHECKED. The proofs are integer rounding certificates taken
  from each pattern's LP dual.
- **Lean change.** The two largest patterns need a larger elaboration budget. Their recipe now
  places `set_option maxHeartbeats 4000000 in` before the theorem. The option is allowed;
  `search.split_options` does the placing.

**Part B, on 40 fresh dense hosts at 60 s.**

| Route | Certified | Planted | erdos |
|---|---|---|---|
| v2 | 33 | 19/20 (meets 90%) | 14/20 |
| v1 | 30 | 17/20 | 13/20 |

- **Discordant pairs:** 4 against 1, McNemar p = 0.19.
- **Time:** v2 is 3.7 s per host slower.
- **Soundness:** every certificate valid.
- **Verdict: NO_COVERAGE_GAIN.**

## What it means

The invention step extends itself, and Lean checks every generated row. But at a 60 s budget
the extra rows add little over K5 and W5. The dense planted regime is certifiable at about the
90% level with either generated-row route. Without one, the evaluator manages 1/20 (B20_R35).

What remains for GV3 is a reviewer question. If a frozen candidate is beyond the exact MIP there
(B20_R38), should the evaluator adopt a generated-row certification route, so that this regime
can be calibrated (B20R35-OPEN-1, B20R33-OPEN-1)?

## Tests

| Test file | Tests | What they check |
|---|---|---|
| `tests_genesis/test_cuts_v2.py` | 6 | the generator's patterns; exact ex values; every rounding certificate exactly valid; fast copies equal v1's; the option hoisting |
| `tests_formal/test_generator_v2.py` | 4 | the package replays and its registry is the CHECKED patterns; the verdict follows from the rows; the kept certificates re-check; fresh hosts in the addenda |

## Open

B20R37-OPEN-1 (new): generator v2 has no coverage gain at 60 s, and the extra rows add cost.
