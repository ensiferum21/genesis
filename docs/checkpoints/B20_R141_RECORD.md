# B20_R141 record: ARA's calibration on the sealed Limitation Zoo is INVALID, by a defect in the script's freshness check (INVALID; DEV)

**Run by:** the builder, on DEV. It is a calibration and licenses nothing. The protected judge was not asked.

**Preregistration.** Preregistered at `a3b3eda`. The script is `scripts/b20r141_ara_zoo.py`, SHA-256
`ccec4633599faa628a26c8ca4aeeaa6061a8e857a114bc6b24d46875025660bf`, unchanged. It ran from the clean worktree
`/home/claude/r141-wt` at that commit.

**This run.** Alone on CPU 0, in two slices of the study log (`/home/claude/logs/r141_slices.log`):
- the first, from 27 Oct 2026, 21:50 UTC, paused as designed after 6,652 s with 295 of 475 arm runs;
- the second ended on 28 Oct 2026 at about 00:55 UTC with exit 0, after 4,393 s.

That is 3.1 h in all, against "about 3 h". The arms' own CPU was 3.0 h, of which the tuning sweep took 2.7 h.

**Evidence and checks.**
- `code_identity` `d4f9403b…3891`.
- The evidence is in `evidence/ara_zoo_b20r141/`: the arm rows, the judge's ledger (272 submissions), the run log and
  `summary.json`.
- The record tests are `RecordB20R141` in `tests_genesis/test_ara_zoo_study.py`. They were drafted before the study
  ran (`docs/handoff/RECORD_TEST_DRAFTS.md`, 28 Oct 2026, 04:55 SGT). They pass on the evidence:
  - the script's digest;
  - the environments and the validity record;
  - the analysis, experiment C and the verdict, recomputed from the saved rows, ledger and keys;
  - at recording, two re-derivations were added:
    - the 95 environments regenerate from the sealed seed with their keys;
    - every one of the 272 judged submissions re-judges, with the same oracle, range and sealed gain from
      re-executing its variant.
- **One assertion of the draft was changed, disclosed here.** The draft asserted that the run was valid. It is not,
  so the test now asserts the validity record as it is: well formed, within budget, the pinned judge, and *not
  fresh*. It also asserts the verdict INVALID.

## Result

**Verdict INVALID, by the preregistered rule.** Every validity check held except the freshness clause, and that
clause cannot hold in any registered run:

```python
envs = envs or environments()          # main replaces envs by the registered list ...
...
fresh = all(i >= INDEX0 for i in rows) and (sealed_seed != SEALED_SEED or envs is None or not registered)
```

In the registered run, `sealed_seed` is `SEALED_SEED`, `registered` is True, and `envs`, already replaced, is never
None. So the second conjunct is False whatever the environments were. The clause was meant to stop a custom list of
environments from running at the sealed seed. As written, it rejected the registered list too.

- **Why the design tests missed it.** They ran `main` only unregistered, at another sealed seed, where the clause is
  True. `test_the_freshness_defect` reproduces the defect from the script's source and the run's values.
- **What the clause was meant to establish did hold.** The 95 environments are the registered ones, at indices
  20000–20094, at least INDEX0, and none was used by the development look. The run was valid in substance. But a
  failed validity check makes a study INVALID (`docs/OMEGA_EXPERIMENT_PROTOCOL.md` §6), and checks are not relaxed
  after the fact. So the verdict stands.

**What the experiments show, descriptively.** None of this is evidence; it is the run as it came out. Had validity
held, every experiment would have passed (`S.verdict(True, …)` is ARA_CALIBRATED, which the record test checks).

| Experiment | Result | Its bar |
|---|---|---|
| A1: ARA's top-1 localisation, 50 defect environments | 42 of 50 (chance 1/4), p 3 × 10⁻¹⁸ | p < 0.05 |
| A2: NONE on NULL and NO_HEADROOM | 30 of 30 | at least 0.8 |
| B: ara over tuning, per class, Holm | GLOBAL_ONLY 0.005, SENSE_BLIND 0.008, EVAL_NOISY 0.023; FUSION_NEEDED 0.063, SEARCH_WEAK 0.41 | some class < 0.05 |
| C: every promoted variant well formed and admissible | no failures (189 promotions) | none |
| D: ara2 over blind2 (2 tries each) | +0.413 of the range, p_Holm 2.7 × 10⁻⁶ | both p < 0.05 and +0.05 |
| D: ara2 over tuning | +0.509, p_Holm 2.6 × 10⁻⁷ | |
| S: releases on the 45 controls | ara 0, ara2 0 (upper bound 0.064 each); blind 2, blind2 1, tuning 0 | at most 0.10 for ara and ara2 |

**By class**, the mean released gain on the 10 environments of each class, in units of the attainable range:

| Class | ARA localised | ara | ara2 | blind (14 tries) | blind2 | tuning | oracle key |
|---|---|---|---|---|---|---|---|
| SENSE_BLIND | 8 of 10 | 0.707 | 0.642 | 0.771 | 0.185 | 0.000 | 0.828 |
| GLOBAL_ONLY | 9 of 10 | 1.000 | 0.998 | 1.007 | 0.667 | 0.000 | 1.015 |
| FUSION_NEEDED | 5 of 10 (4 NONE) | 0.233 | 0.208 | 0.381 | 0.146 | 0.000 | 0.429 |
| SEARCH_WEAK | 10 of 10 | 1.092 | 1.075 | 1.066 | 0.510 | 0.924 | 1.072 |
| EVAL_NOISY | 10 of 10 | 1.005 | 1.005 | 1.005 | 0.353 | 0.458 | 0.985 |

On the controls:
- ARA diagnosed NONE on all 30 NULL and NO_HEADROOM environments.
- It diagnosed "expressiveness" on all 15 DECOY environments, as designed (a decoy is a defect on dev by
  construction). The judge refused every resulting submission.
- The blind arms' three releases were on NO_HEADROOM environments.

Median units spent per environment:

| Arm | Median units |
|---|---|
| ara | 1,588 |
| ara2 | 1,570 |
| blind2 | 1,488 |
| tuning | 2,371 |
| blind | 9,888 |

## What it means

1. **The verdict is INVALID, and that is the record.** The defect is in the builder's script, not in ARA, and it was
   caught by the script's own validity rule. It was not caught by its design tests, which never ran the registered
   path.
2. **Descriptively, the run looks like what the expectation said:** ARA_CALIBRATED.
   - ARA localises planted limitations far above chance and says "nothing to fix" where there is nothing.
   - With two tries it gets twice what blind rewriting gets.
   - With fourteen tries blind rewriting matches it, at about six times the units.
   - It never released on a control.
   - FUSION_NEEDED is its weak class, as the development look warned: it localised 5 of 10 there and said NONE on 4,
     and its gain, 0.23, is about half the oracle key's, 0.43.
   - SEARCH_WEAK is the class tuning repairs alone, so B is not significant there.
   None of this counts until a valid run says it.
3. **Next: B20_R167, preregistered.** It is the same design with the defect repaired, on a fresh sealed seed and
   fresh indices (21000+), because these environments have now been seen. A design test runs `main` through the
   registered path. B20_R142, ARA on a real Genesis workflow, still requires `ara-calibrated`, and stays queued
   behind it.
4. **For the protocol:** a study's design tests should run its `main` through the registered path, with the seed,
   the output and the environments redirected. B20_R167 does. Earlier scripts with a registered branch are not
   re-audited here; that is a candidate item.

## Looks at the study's data before it finished

None. Progress was checked by the count of slice exits only. The slice log's lines were read after exit 0.

## Prior art

None is claimed. Diagnosis by oracle substitution is ablation and its relatives (Meyes et al. 2019). The controls
follow `docs/OMEGA_EXPERIMENT_PROTOCOL.md`.
