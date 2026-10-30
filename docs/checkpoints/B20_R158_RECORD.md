# B20_R158 record (F5): Genesis posed nine conjectures of its own, and the self-improving inventor settled one more than its predecessor (NOT_SHOWN; DEV)

**Run by:** the builder, on DEV. F5 of Daniel's directive of 27 Oct 2026, 19:55 (`docs/OMEGA_FRONTIER.md`). It
licenses nothing and adopts nothing.

**Preregistration and its amendments.**
- Preregistered at `703b2ee` (27 Oct 2026).
- Amended at `ff9eada` (28 Oct 2026), before it ran, for Γ's star-size defect.
- Amended a second time at `f7803e3` (30 Oct 2026, 11:15 SGT), after its first run stopped and before any result was
  looked at.

The script is `scripts/b20r158_open_conjectures.py`, SHA-256
`f44333c3355607da31fd54d10bf6444ecc3a753d8d431b12d7dd9ea15f85c06c` (the second amendment), unchanged since. It ran
from the clean worktree `/home/claude/f5c-wt` at `f7803e3`.

**The first run (disclosed in the second amendment).**
- It ran from `ff9eada` on 30 Oct 2026 from 10:44:29 to 10:50:30 SGT and stopped with exit 1.
- The cause was template genomes overflowing in generation 1's FULL arm (B20R158-TEMPLATE, `docs/BLOCKING_DEFECTS.md`).
- Its files are in `evidence/open_conjectures_b20r158_attempt1/`. Only the log's traceback was read, and nothing of
  that run is used.
- On two other data seeds, the repair alone (on `ff9eada`) and the second amendment commit gave byte-identical
  summaries.

**This run.** Alone on CPU 0, in one slice, on 30 Oct 2026 from 12:29:35 to 12:53:06 SGT: 24 min, against "about
1.5 h". It was short because generations 2 and 3 posed nothing (below).
- **CPU 0 idle time (disclosed):** 10:50–10:56, after the first run stopped; and 12:29:30–12:29:35, after the first
  checkpoint attempt was stopped.
- The checkpoint's matrix started on CPU 0 19 s after this study ended.

**Evidence and checks.**
- `code_identity` `4f81e33b1894b169ae0b26d7841c58357b69dcf2d62f60e1c994f27271ccc87a`. It was recomputed at recording
  from a temporary worktree of `f7803e3`, and it matches.
- The evidence is in `evidence/open_conjectures_b20r158/`:
  - `generations.jsonl`;
  - `summary.json`;
  - each generation's conjectures, arm records and engine states (`gen1/`–`gen3/`);
  - `run.log`, the slice log.
- The record tests are `RecordB20R158` in `tests_genesis/test_open_conjectures_study.py`. They were drafted before the
  study ran (28 Oct 2026, 09:40 SGT), updated for both amendments (the digest, and the commit the audit reads), and
  are otherwise unchanged. All 7 pass on the evidence (98 s). They check:
  - the script's digest;
  - validity: the budgets, no proved bound refuted, and the audit of the research plane at `f7803e3`;
  - every certified refutation double checked again;
  - the analysis and the verdict;
  - generation 1's posed set regenerated from the data seed;
  - the survivors' small exhaustive check repeated.

## Result

**Verdict NOT_SHOWN, by the preregistered rule; valid.**
- No certified refutation of a conjecture equivalent to a proved bound.
- The audit is clean.
- Both arms spent their 900,000 evaluations.
- The pins held.

**P1** (exact one-sided McNemar test over all generations): FULL alone refuted 1 conjecture, PLAIN alone 0; p 0.5.

**Generation 1** (600 graphs Genesis drew itself):
- The generator kept 11 conjectures.
- The kernel withheld 2 as the proving test's bounds: `sqrt(2d² + 2m³/d)` and `sqrt(3m² + d³/m)`.
- It posed 9. Here d is a vertex's degree and m the average degree of its neighbours; each conjecture bounds the
  Laplacian spectral radius by the maximum of the expression over the vertices.

| Posed conjecture | FULL | PLAIN | Label |
|---|---|---|---|
| `sqrt(d³/m + 3m³/d)` | refuted | — | |
| `sqrt((3d² + 5m³/d)/2)` | refuted | refuted | |
| `sqrt(m² + 3m³/d)` | refuted | refuted | rediscovery of bound 29 (refuted 2024) |
| `sqrt((m² + 7m³/d)/2)` | refuted | refuted | |
| `sqrt((3m² + 5m³/d)/2)` | refuted | refuted | |
| `sqrt(dm + 3m³/d)` | refuted | refuted | |
| `sqrt((5d² + 3m³/d)/2)` | — | — | **survivor, unlabelled** |
| `d + m` | — | — | rediscovery of Merris 1998 (proved) |
| `sqrt(d² + 3dm)` | — | — | rediscovery of bound 10 (proved) |

- FULL's one extra refutation came from annealing on edge bits (an "imagine" branch), not from a template or a
  procedure.
- FULL extracted 6 procedures and abstracted 7 templates.
- **Generations 2 and 3 posed nothing.** Each kept 5 conjectures, but every one was equivalent to a conjecture posed
  in generation 1. So the templates and procedures had nothing to act on, and compounding (S4) is 0.

**The survivors** (S2; each checked on every connected graph with up to 7 vertices, all holding):
- two are proved published bounds (Merris; bound 10);
- one, `μ ≤ max_v sqrt((5 d_v² + 3 m_v³ / d_v)/2)`, carries no label. It is a **candidate**, never a theorem, and it
  has not been checked against the literature. It is one weighting, (5, 3), of the same two terms as the withheld
  bound 18, `sqrt(2d² + 2m³/d) = sqrt((4d² + 4m³/d)/2)`, weighting (4, 4), and the refuted
  `sqrt((3d² + 5m³/d)/2)`, weighting (3, 5).

**CPU** (S5, generation 1): FULL 898 s, PLAIN 213 s, for the same evaluations. The templates build larger graphs.

## Against the expectation

The expectation (low confidence) said:
- generation 1 poses "about 20–30". **Wrong**: 9.
- "Several are rediscoveries" (Merris, 10 and 29 seen in development) and "18 and 21 would be withheld". Right: all
  three appeared, and two were withheld.
- "Most of the refutable ones fall to both arms; few are refuted by one arm only: P1 NOT_SHOWN". Right.
- "The survivors are mostly proved published bounds". Right: 2 of 3.

The expectation did not foresee that the later generations would pose nothing.

## What it means

1. **Genesis posed its own conjectures and settled most of them, with no human problem.** It rediscovered three
   published bounds, among them one the literature refuted in 2024, and refuted it again.
2. **The self-improving inventor was not shown to be better than its predecessor.** It refuted one more conjecture,
   by an ordinary search branch. Its abstractions never got a chance to act, because the generator ran dry after one
   generation.
3. **The open-ended loop stalls at its generator.** Adding counterexamples to the data did not make the generator
   produce new conjectures; it re-derived equivalents of earlier ones. A generator that extends its expression
   language, or poses relations among other invariants, would be needed before generations can compound. That bears
   on PT-1 part 5, family C (`docs/handoff/PT1_DESIGN_DRAFT.md`, open item 3: "generated conjectures are few per data
   draw").
4. **One candidate worth a literature check:** `sqrt((5d² + 3m³/d)/2)`. Nothing is claimed for it.

## Looks at the study's data before it finished

None. The study ran in one slice, and its summary was read after exit 0. The first run's log was read for its
traceback (above).

## Prior art

The conjecture generator follows Graffiti and TxGraffiti (Fajtlowicz; Davila), including TxGraffiti's rule that a
counterexample joins the data. The bounds are Brankov, Hansen and Stevanović's (2006), and Merris (1998).
