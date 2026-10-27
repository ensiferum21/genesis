# B20_R152 record: Genesis's language did not grow on real engines, because the judge admitted neither proposed statement (NOTHING_ADMITTED; DEV)

**Status:** run by the builder, on DEV. It licenses nothing and adopts nothing.

**Preregistration.** Preregistered at `14232e4` and amended once before it ran (the slice clock), as disclosed in
the script. The script that ran is `scripts/b20r152_self_extension.py`, SHA-256
`2d3d8f899162c381beddf559a7a392487645e0984484b3d71a37b59a9e215b98`. It ran from the clean worktree
`/home/claude/r152-wt` at `3d88ad6`.

**This run.** Alone on CPU 0, in two slices of the study log (`/home/claude/logs/r152_slices.log`):
- the first, from 27 Oct 2026, 17:48 UTC, paused as designed after 6,601 s;
- the second ended at 20:35 UTC with exit 0, after 3,435 s.

It took 2.8 h in all, against "at most about 15 h". The line ended at generation 1, so the confirmation stage, the
longest part, never ran.

**Evidence and checks.**
- `code_identity` `a4247f4f…d293`.
- Evidence is in `evidence/self_extension_b20r152/`: the study's runs, the language judge's runs, the vault, and
  `summary.json` with SHA-256 `71fbcf12…d347`.
- The record tests (`RecordB20R152` in `tests_genesis/test_self_extension_study.py`) were written from the script
  before the study ran. They pass unchanged on the evidence:
  - the script's digest;
  - validity, with the median CPU recomputed from all the runs;
  - the verdict recomputed;
  - the judge's ledger, one entry per decision;
  - the vault complete;
  - the graphs regenerate.
- The confirmation test skips itself, because there was no confirmation.

## Result

**Verdict NOTHING_ADMITTED, which was one of the two outcomes expected before running** ("NOTHING_ADMITTED or
NOT_SHOWN").

**Generation 1.**
- Genesis's four dev searches each made 256 evaluations. The budget was 240, and the last generation of each
  search runs past it. Their best engines scored
  1.0054, 1.0028, 1.0048 and 1.0038 of REX on their own dev graphs.
- From the 20 corpus engines, the library learner proposed two named statements, both of the search claim. Both
  were judged on the sealed graphs:

| Statement | Body | Compression | Uses in the learner's programs | Candidate lane | Parent lane (Λ1) | Control lane (a random statement) | Decision |
|---|---|---|---|---|---|---|---|
| g1a | `?f>700 C X [ H B53 D@c P12 D D P12 ]` | 163 bits | 3, in programs 3 and 4 | +0.589% | +0.591% | +0.623% | refused: no better than the parent (p 0.51) or the control |
| g1b | `*5 B10 H ?f>700 C` | 162 bits | 5, in programs 0–4 | +0.624% | +0.591% | +0.605% | refused: no better than the control (+0.019%, p 0.33; replicates p 0.2) |

g1b came closest. All three of its candidate searches beat all three parent searches (replicate p 0.05). The gain
was small (+0.033%), and per graph it was not distinguishable (p 0.25). Against a random statement of the same size
it was indistinguishable. The judge's rule needs both comparisons, so it refused. The line then ended by the
preregistered stagnation rule.

**S3, the trend.**
- Generation 1's best dev engine, `X *5 B10 H ?f>700 C X [ [ H B53 D@c P12 ] D D P29 ] b1222`, beats REX on the 24
  truth graphs by **+0.670%**.
- With only generations 0 (REX) and 1, Page's trend test is undefined, so it is reported as p 1.0 by its rule.
- The gain is consistent with B20_R151's S5. B20_R165 tests that finding confirmatorily.

S2, reuse: 0, since nothing was admitted. Compounding: none.

## What it means

1. **The pipeline ran end to end on real engines and stopped where its judge said.**
   - Genesis abstracted statements from its own engines, and the sealed language judge refused both, at the
     preregistered bar.
   - That bar requires a statement to beat both the parent language and a random statement of the same size.
   - Self-extension did not happen here. That is the result.
2. **The near miss is informative.** g1b, a repeat of a single construct (`*5 B10 H ?f>700 C`), helped the search
   slightly and consistently across replicates. It did no better than a random statement, though. So what helps at
   this bound may be adding *any* named statement, which shortens programs, rather than this particular one.
   - That is a hypothesis, not a finding. The control exists to catch exactly this.
3. **For the queue:**
   - B20_R155, the expressiveness of Genesis's grown language, is conditional on admissions, so it does not run;
   - X3 has no support here either;
   - the planar-engine gain over REX, now seen in B20_R151 and again here (+0.67%), is what B20_R165 tests. It
     began at 20:36 UTC.

## Looks at the study's data before it finished

None. Progress was checked by the count of slice exits only. The log's lines were first read after exit 0.

## Prior art

None is claimed. The library learning by compression follows DreamCoder (Ellis et al. 2021) and Stitch (Bowers et
al. 2023); the language judge is Genesis's own (X2, B20_R154).
