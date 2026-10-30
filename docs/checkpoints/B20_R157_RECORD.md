# B20_R157 record (F4): on the sealed Laplacian bounds the Frontier beats NRPA, but not GBFS, CEM, UCB or uniform allocation (PARTIAL; DEV)

**Run by:** the builder, on DEV. F4 of Daniel's directive of 27 Oct 2026, 19:55 (`docs/OMEGA_FRONTIER.md`). It
licenses nothing and adopts nothing.

**Preregistration.** First preregistered at `bdf0c57`, and amended at `ff9eada` (28 Oct 2026, 10:55 SGT) after the
first attempt was killed and before any of its results was looked at. The script is
`scripts/b20r157_laplacian_bounds.py`, SHA-256
`fb5dd07e5ccce94a8d80fe951611d1a21235be26ab6a45ad26149fc67f075785` (the amended script), unchanged since. It ran from
the clean worktree `/home/claude/f4b-wt` at `ff9eada`.

**The first attempt (disclosed in the amendment).** It ran from `bdf0c57` on 28 Oct 2026 and was killed by the memory
limit (6.1 GB) by Γ's star-size defect (B20R157-STAR, `docs/BLOCKING_DEFECTS.md`). Its rows are kept in
`evidence/laplacian_bounds_b20r157_attempt1/` and are not used. Every arm, the single searches included, ran again.

**This run.** Alone on CPU 0, in two slices of the study log (`/home/claude/logs/f4b_slices.log`):
- the first, from 30 Oct 2026, 08:23:37 SGT, paused as designed after 6,624 s, with the 168 single searches and the
  FRONTIER arm done;
- the second, from 10:14:06, ended with exit 0 at 10:44:15.

That is 2.3 h in all, against "about 2 h". The single searches took longer than the timing pilot suggested:
- NRPA a median of 53 s per bound;
- GBFS 17 s;
- CEM 12 s, against the pilot's "about 15 s".

The joint arms spent 5,599,809 (FRONTIER), 5,599,890 (UCB) and 5,599,921 (UNIFORM) of their 5,600,000 evaluations.
B20_R158 started on CPU 0 14 s after the study ended.

**Evidence and checks.**
- `code_identity` `d823bcbbc75f00756ce19ddaafe7a6933f116dae5160dac4a147fede9b01173a`. It was recomputed at recording
  from a temporary worktree of the run tree `ff9eada`, and it matches.
- The evidence is in `evidence/laplacian_bounds_b20r157/`:
  - `rows.jsonl`: every arm's row, with its artifacts;
  - `summary.json`;
  - `run.log`: the slice log;
  - `state_FRONTIER.json.gz`, `state_UCB.json.gz`, `state_UNIFORM.json.gz`: the joint arms' final engine states, gzipped.
    The originals' SHA-256 are `ab075e4c…f5e4`, `6176b45a…d923` and `c207abcf…1eb4`.
- The record tests are `RecordB20R157` in `tests_genesis/test_laplacian_bounds_study.py`. They were drafted before
  the study ran (28 Oct 2026, 02:55 SGT; digest updated for the amendment at 11:10) and appended unchanged. They pass
  on the evidence. They check:
  - the script's digest;
  - the posed ids;
  - every artifact of every arm double checked again by the kernel, and each arm's refuted set recomputed;
  - the null check;
  - the McNemar tests, Holm and the verdict.

## Result

**Verdict PARTIAL (NRPA beaten), by the preregistered rule; valid.**
- No doubly confirmed certificate was found against any of the 21 proved bounds.
- Every arm spent its budget.
- The pins held.

Bounds refuted with both checks confirming (the Rayleigh certificate, and the Sturm count for n ≤ 40), out of the
33 known-false bounds:

| Arm | Refuted | Without the six development-look bounds |
|---|---|---|
| GBFS (bounded degree, n 12) | **19** | 15 |
| FRONTIER | 14 | 11 |
| UCB | 13 | 11 |
| UNIFORM | 12 | 9 |
| CEM (edge bits, n 20) | 9 | 8 |
| NRPA (edge bits, n 20) | 4 | 4 |

P1, FRONTIER against each comparator (the exact one-sided McNemar test on the bounds refuted by exactly one arm; Holm
over five):

| Comparator | FRONTIER only | Comparator only | p | p_Holm | |
|---|---|---|---|---|---|
| NRPA | 12 | 2 | 0.0065 | 0.032 | **BEATEN** |
| CEM | 8 | 3 | 0.11 | 0.45 | not beaten |
| UNIFORM | 7 | 5 | 0.39 | 1 | not beaten |
| UCB | 5 | 4 | 0.50 | 1 | not beaten |
| GBFS | 2 | 7 | 0.98 | 1 | not beaten |

**Bounds 44 and 46, the open ones:** no arm produced a certificate against either.

**Where the Frontier's refutations came from** (its 14 confirmed ones; representation and method):
- Pruefer trees: 6;
- bounded degree: 4;
- edge bits: 3;
- Γ programs: 1.

The methods were mixed, with GBFS, hill climbing and NRPA the most frequent.

## Unconfirmed refutations (a descriptive analysis, added at recording; it decides nothing)

The summary lists 38 refutations from the joint arms that only the Rayleigh certificate confirmed, as "UNCONFIRMED",
not counted:
- FRONTIER 11;
- UCB 13;
- UNIFORM 14.

Every one is a graph of 43 to 64 vertices built by a Γ program, and every one is on a bound known to be refuted. The
preregistered second check, the Sturm count, applies only for n ≤ 40, so these could not be confirmed under this
study's rule.

B20_R158's amendment (`ff9eada`, written for F5) added an independently written matrix-form Rayleigh check for n > 40
(`verify.check_matrix_form`). Applied at recording to the same artifacts, as an analysis outside the preregistered
rule, it confirms every one of them:

| Arm | Refuted, with the matrix-form check above 40 |
|---|---|
| UCB | 26 |
| UNIFORM | 26 |
| FRONTIER | 25 |
| GBFS | 19 |
| CEM | 9 |
| NRPA | 4 |

Under that count, still none against a proved bound. The engine's three allocators all reach 25 or 26 of the 33,
well above every single prior-art search. Against each other they do not differ: FRONTIER−UCB 1−2, FRONTIER−UNIFORM
1−2. So what the engine adds over the single searches on this set is its space of representations, Γ's larger graphs
above all, not the Frontier's allocation.

This analysis was not preregistered and changes nothing in the verdict. It does show that the preregistered rule's
second check cost the joint arms most of their refutations.

## Against the expectation

The expectation (low confidence) said:
- "Most of the 33 refuted bounds fall to every arm". **Wrong.** The single searches got 4 to 19.
- "The arms differ on a handful of bounds". Right for the joint arms against each other.
- "NOT_SHOWN or PARTIAL (UNIFORM beaten)". PARTIAL, but with NRPA beaten, not UNIFORM.
- "Bounds 44 and 46 are not refuted". Right.

## What it means

1. **Under the preregistered rule, the Frontier is not better than the strongest single prior-art search on this
   set.** GBFS on bounded-degree graphs at n = 12, the 2025 paper's best single method, refuted the most (19). The
   Frontier beat only NRPA.
2. **The Frontier's allocation adds nothing measurable over UCB1 or uniform allocation here.** That holds both under
   the rule and in the descriptive count. This is unlike F3's planted worlds (B20_R156), where it beat both.
3. **The engine's representation space reaches counterexamples the single searches do not.** These are Γ programs
   building 43–64-vertex graphs. The preregistered verification rule could not confirm them, and the descriptive
   matrix-form check does.
   - This bears directly on PT-1 (`docs/handoff/PT1_DESIGN_DRAFT.md`, open item 7 on the size cap): a second check
     above 40 vertices must be part of any study whose representations build large graphs. B20_R158 has one.
4. **No candidate new result.** Bounds 44 and 46 are untouched.

## Looks at the study's data before it finished

The row count of `rows.jsonl` was read three times to estimate progress: 27 and 28 at about 08:48, and 169 at
10:14. No row's
content was read. The summary and log were read after exit 0.

## Prior art

The comparators are the literature's:
- NRPA, GBFS and CEM (Roucairol and Cazenave 2025);
- Ghebleh et al. 2024;
- Wagner 2021.

The set is Brankov, Hansen and Stevanović (2006), with statuses as of June 2026 (arXiv 2606.14550). Nothing about the
methods is claimed new.
