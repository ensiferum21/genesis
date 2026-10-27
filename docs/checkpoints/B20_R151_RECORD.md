# B20_R151 record: the builder's richer language does not express better engines at N = 32 on planar2000 (NOT_SHOWN; reading NO_LANGUAGE_EFFECT; DEV)

- **Run by:** the builder, on DEV. It licenses nothing and adopts nothing.
- **Preregistration and amendments.** Preregistered at `52e1d92` and amended twice before any search finished, as
  disclosed in the script:
  - three ceiling replicates per language, with the replicate permutation test in P1 and S1;
  - P1's margin.

  The script that ran its later slices is `scripts/b20r151_expressiveness.py`, SHA-256
  `8742dd8de359f6596367bdde49d73bfaa8a8f4d602a48dd4a7d9e735d998035c`, run from the clean worktree
  `/home/claude/r151c-wt` at `41cfcd8`.
- **This run.** Alone on CPU 0, in six slices of the study log (`/home/claude/logs/r151_slices.log`):
  - the first was stopped by hand for the first amendment (exit 143), at 08:06 UTC on 27 Oct;
  - four paused as designed (exit 3);
  - the last ended on 27 Oct 2026 at 17:47 UTC (exit 0).
- **Identity and checks.** `code_identity` `1dba16b4…1413`. The evidence is in `evidence/expressiveness_b20r151/`
  (31,676 runs; `summary.json` SHA-256 `d021b145…93df`). The record tests (`RecordB20R151` in
  `tests_genesis/test_expressiveness_study.py`, written from the script before the study finished) pass unchanged
  on the evidence:
  - the script's digest;
  - validity, with the CPU medians recomputed from the runs;
  - the gate and the selection, recomputed from the runs;
  - every truth-table mean, recomputed from the runs;
  - P1, S1, S4, the lanes, the readings and the verdict, recomputed from the saved inputs;
  - every Λ0 arm wrote Λ0 programs only;
  - the graphs regenerate with the recorded identities.

## Result

**Verdict NOT_SHOWN, as expected before running. Reading NO_LANGUAGE_EFFECT on the one studied class.**

- **The headroom gate** (REX at 10 s against REX at 1 s on H): planar2000 passed (+0.572%, p 0.00024). toroidal2000
  failed (+0.145%, below the 0.2% threshold), and so did random2000 (+0.058%). Only planar2000 was studied.
- **P1, expressiveness** (the Λ1 ceiling winners against the Λ0 ceiling winners on the 24 truth graphs):
  - Λ1 was lower: −0.115%, p 1.0;
  - replicate means: Λ1 0.481%, 0.723% and 0.590%; Λ0 0.776%, 0.719% and 0.646%;
  - margin −0.294%;
  - NOT_SHOWN.
- **S1, the language under the inventor:**
  - Λ1 was lower: −0.126%. The per-graph test gives p 0.008, but the replicate test gives only p 0.1. The rule
    needs both, so the label is NO_DIFFERENCE;
  - replicate means: Λ1 0.447%, 0.490% and 0.568%; Λ0 0.652%, 0.562% and 0.671%.
- **S2, search:**
  - the ceiling search beats the inventor in both languages: Λ0 +0.085% (p 0.0009), Λ1 +0.096% (p 0.03);
  - S3, the interaction: −0.011%, p 0.17, not distinguishable.
- **S4, saturation.** Neither ceiling had saturated. From half to full budget, Λ0 gained +0.080% (p 0.006) and Λ1
  +0.063% (p 0.03): STILL_IMPROVING in both.
- **S5, every arm against REX at 1 s on T:**
  - every one of the 18 searches' engines beats REX on the fresh truth graphs, by 0.45% to 0.78% (p ≤ 0.02);
  - the best is C0_0, `C b66 X`, at +0.776%. That is more than REX gains from ten times the time on the headroom
    set (+0.572%);
  - the inventor alone, in Λ0, reaches +0.56% to +0.67%.
- **The constructs.** The Λ1 programs evaluated used blocks 500 times, guards 403, repeats 579 and targets 823, in
  1,759 programs. Four of the six Λ1 ceiling winners use them. The ablations of the winners' constructs move them by
  −0.06% to +0.09%.

## What it means

1. **The richer language, which is the builder's construct algebra, did not show more expressiveness here.** The
   searches in Λ1 found engines no better than those in Λ0, and slightly worse under both searches. The reading is
   NO_LANGUAGE_EFFECT.
   - The ceilings had not saturated (S4), so this is a statement about these search budgets at N = 32. It says
     nothing about the languages' true ceilings.
   - A plausible reason, not tested: Λ1's larger program space dilutes the same budget. This is S1's
     direction, short of the replicate rule.
2. **Search finds real gains in the base language.** On fresh planar graphs of 2,000 vertices, the engines found by
   Genesis's searches beat the builder-configured REX by about 0.5% to 0.8% at the same 1 s. That is more than REX's
   own gain from ten times the time.
   - This differs from B20_R127, where Genesis's engines tied REX, and from B20_R132, where nothing on its classes
     beat REX by a confirmed, material amount.
   - It is a secondary finding: per-arm tests, uncorrected, on one class, at DEV. It is not a release, and the
     protected judge was not asked.
3. **For the queue:**
   - B20_R152, Genesis growing its own language, is unaffected in design and runs next. It started at 17:48 UTC;
   - B20_R155 stays conditional on B20_R152 admitting statements;
   - X3, richer conditions, has no support from this result: Λ1's guards did not help;
   - the S5 finding called for a replication. It is preregistered as B20_R165: the same 18 engines, frozen, on 48
     fresh planar graphs, with P1 the engines' mean gain and P2 a single engine chosen by training score. It runs
     after B20_R152. It is not a release; the protected judge is a separate step.
   - **Replicated** (B20_R165, 27 Oct 21:50 UTC; `docs/checkpoints/B20_R165_RECORD.md`): +0.582% on 48 fresh
     graphs, with C0_1 at +0.661%. All of the gain is on the ±1-weighted family (+1.16%, 24 of 24 graphs; here +1.19%,
     12 of 12). Unweighted planar graphs tie, and toroidal and random graphs lose.

## Expectations against results

The expectation was stated before running, with low confidence.

| Item | Expected | Result |
|---|---|---|
| Gate | planar2000 and toroidal2000 pass; random2000 fails | planar2000 passed; toroidal2000 failed (+0.145% < 0.2%), so the expectation was half right |
| P1 | NOT_SHOWN, Λ1 gain 0–0.1% | NOT_SHOWN, Λ1 −0.115% |
| S1 | NO_DIFFERENCE, or the language hurting the inventor | NO_DIFFERENCE (in the hurting direction, short of the replicate rule) |
| S2 | ceiling over inventor 0.05–0.2% in Λ0 | +0.085% |
| S4 | the Λ0 ceiling roughly SATURATED | STILL_IMPROVING: wrong |
| Verdict | NOT_SHOWN | NOT_SHOWN |

## Looks at the study's data before it finished (disclosed)

- **At the first amendment (08:06 UTC).** The gate's results were seen, as the amendment records, along with one
  run's value from a progress check. No search outcome was seen.
- **During the run (27 Oct, before 13:42 UTC).** A `tail -1` of the slices log showed C1_1's winner,
  `?f<850 H [ B38 B38 ?d<8 P13 ] H C *6 b1558 C`, with its training score 1.00825. This is disclosed in the session
  summary and here. Nothing was changed after it; the analysis was already fixed by the second amendment.
- **One unread file.** A background waiter set at 13:42 UTC wrote the log's last line to its own output file. That
  file was not read. Later checks counted slice exits only.

## Prior art

None is claimed. The language is the builder's: mcx3, X1 (B20_R153).
