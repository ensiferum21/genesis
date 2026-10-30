# B20_R159 record (PT-1, the proving test): the predecessor refuted a held-out bound, so the inadequacy gate failed (INADEQUACY_GATE_FAILED; DEV)

**Run by:** the builder, on DEV. PT-1 is Daniel's proving test (27 Oct 2026, 20:22). Part 1's mechanisms are his
decision of 28 Oct 2026, 00:53 ("Do the hardest so it proves it can find its way"), and part 5's controls his
delegation of 28 Oct, 10:58. It licenses nothing.

**Preregistration.** Preregistered at `a775227` (30 Oct 2026). The script is `scripts/b20r159_proving_test.py`,
SHA-256 `56037017038a2d1261bdaf85c37300a435918c1152002646820999d2eeee3a05`, unchanged. It ran from the clean worktree
`/home/claude/pt1-wt` at that commit, which holds the 24 pinned modules.

**This run.** Alone on CPU 0, in one slice, on 30 Oct 2026 from 19:24:33 to 19:49:46 SGT: 25 min, against "about 6
h". It stopped after stage 1, as the verdict rule requires when the gate fails.
- **CPU 0 idle time (disclosed):** 5 s before it (after B20_R174), and 31 s after it (B20_R175 started at 19:50:17;
  the builder was in a foreground call on CPU 1 when PT-1 ended).

**Evidence and checks.**
- `code_identity` `2d131c915ccd2c131a1cf1f6b18711af3948e1a1c6f5a20e468cec27e41e8dd6`. It was recomputed at recording
  from a temporary worktree of `a775227`, and it matches.
- The evidence is in `evidence/proving_test_b20r159/`:
  - `stages.json`: stage 1's two records (P0 and G on family A), with every claimed artifact;
  - `state_A_P0.json`, `state_A_G.json` and their `.domain.json`: the two engines' saved states, G's with the
    templates, derived operation sets and libraries it made;
  - `summary.json`;
  - `run.log`, the slice log.
- The record tests are `RecordB20R159` in `tests_genesis/test_proving_test_study.py`. They were drafted before the
  study ran (30 Oct 2026, 14:15 SGT) and appended unchanged. They pass on the evidence, and the whole suite passes (16 tests, 805 s). They check:
  - the script's digest;
  - every certificate of every saved stage checked again by the kernel (the Rayleigh certificate and the second exact
    check);
  - the families posed again from the sealed seed and the data seeds;
  - the parts, statistics, validity and verdict recomputed from the saved stages.

## Result

**Verdict INADEQUACY_GATE_FAILED, by the preregistered rule; valid** (the audit clean, no proved-equivalent refuted,
both arms spent their budgets, the pins held).

**Family A**, the five Laplacian bounds held out of F4 and F5 (18, 21, 24, 30 and 40). Each is refuted in the
literature only by large equitable-partition constructions of 158-352 vertices (Damnjanovic, Ha and Stevanovic,
June 2026). Each arm had 500,000 evaluations over the five, with every program capped at 400 vertices.

| Arm | Certified (kernel: rational Rayleigh certificate and a second exact check) | How |
|---|---|---|
| P0, the predecessor (starting representations only) | bound 40, at evaluation 120,511: a 273-vertex graph | Γ, by NRPA |
| G, Genesis (abstraction, libraries, derivation) | bound 40, at evaluation 70,510: a 352-vertex graph | `derived0`, by hill climbing |
| | **bound 21**, at evaluation 463,067: a 360-vertex graph | `derived1`, by GBFS |

- **The gate:** P0 certified a bound in A, so A was not beyond the predecessor, and the verdict is
  INADEQUACY_GATE_FAILED. By the rule, parts 1 and 3-5 are not run.
- **Part 2 would have passed:** G certified two of the five bounds, one of them (21) the predecessor did not.
- **Both of G's certificates came from representations it derived itself.** `derived0` and `derived1` are Γ with one
  extra graph product each, made by `derive` from Γ's cartesian product (operation tables 7 and 21 of the 256 in
  `conjecture/operations.py`). That is one of the two mechanisms that count for part 1. Whether the ablation would
  have credited them was not measured.
- G also made 4 templates, 9 derived operation sets, 12 macros and 12 libraries during the run.

## Against the expectation

The expectation said NOT_PROVED_OUT with high confidence: the gate holds at about 0.8, and part 2, the crux, passes
at about 0.15.
- **The gate failed** (the one-in-five case). The expectation named the reason in advance: with the cap raised to
  400 vertices, P0's Γ programs can build graphs as large as the published constructions, which F4's cap of 64 did
  not allow.
- **Part 2 passed**, against odds of about 0.15.

## What it means

1. **PT-1, as preregistered, is over, and it does not test parts 1, 3, 4 or 5.** The gate exists so that a discovery
   on A means something the predecessor could not do; here the predecessor refuted bound 40 too. Nothing about
   procedure extraction, transfer to WOWII or matched-compute improvement was measured.
2. **What the run does show** (one run per arm, no statistics):
   - The engine refuted two published bounds whose only known counterexamples are constructions of 158-352
     vertices, independently and without those constructions. Both are already refuted in the literature, so these
     are rediscoveries of refutations, not new results; whether the graphs differ structurally from the published
     ones has not been checked.
   - G refuted one bound P0 did not (21), from a graph product it derived itself, and refuted bound 40 sooner
     (70,510 evaluations against 120,511).
3. **What a second proving test would need** (for Daniel to decide; nothing is queued):
   - a family the predecessor cannot touch at the same cap: bound 21 alone qualifies from this run, but that is a
     family chosen after seeing the result, so it would have to be posed on fresh bounds of the same kind, or the
     predecessor's cap and Γ fixed in advance so that A is out of its reach;
   - or a gate defined differently, for example on the predecessor failing a majority of A rather than all of it.

## Looks at the study's data before it finished

None. The study ran in one slice; its summary was read after exit 0.

## Prior art

Refuting graph-theory conjectures by search: Wagner (2021, cross-entropy), Ghebleh et al. (2024), Taieb et al. (LION
2025, Monte Carlo search), Damnjanovic, Ha and Stevanovic (2026), whose constructions refute bounds 18, 21, 24, 30 and
40. Graph products as search operators are standard; deriving the product table by mutation is Genesis's own
operator space (`conjecture/operations.py`). Nothing about the method is claimed new.
