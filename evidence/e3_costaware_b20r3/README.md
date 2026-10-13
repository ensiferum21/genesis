# B20_R3: frozen DEV study of the redesigned (cost-aware) research policy

`scripts/b20r3_e3_costaware.py`. The rules were committed before the run (commit `5aa9774`). The study is
DEV only and builder-run. Its claim ceiling is a DEV diagnostic: better-improver stays UNESTABLISHED.

## Question

The redesigned learned policy is `research.CostAware`, arm `learned2`. Its features are linear in the
pool. It ranks lemmas by P(proved) × P(needed by an eligible development proof) / E[attempt CPU]. The
study asks two things:

1. Does it remove the B20_R2 failure? In B20_R2 the learned policy's preparation used up the Huntington
   cap.
2. Does it beat the fixed rules?

Before the study, the design pilot (`evidence/headroom_pilot_b20r3/`) had found that no arm could
show superiority on this family. That finding was recorded in the script, and the study measures its
own discriminating power through the ORACLE diagnostic.

## Results

Units are prover-level eligible successes per 25 targets: budget- and exposure-eligible, and
prover-reported. Eight units per arm: two systems, four evaluation seeds.

| Arm | Mean eligible | Policy and preparation CPU (ms, mean) |
|---|---|---|
| fixed | 15.75 | 27.4 |
| random | 15.75 | 19.2 |
| heuristic | 15.75 | 38.9 |
| bandit | 15.625 | 29.9 |
| learned (B20_R2 design) | 13.625 | 480.6 |
| **learned2 (cost-aware)** | **10.25** | **15.1** |
| empty library | 12.25 | – |
| ORACLE diagnostic | 15.875 | – |

Preregistered verdicts:

- **vs fixed: INFERIOR_DEV.** 2 wins, 3 ties, 3 losses; mean −5.5.
- **material: NOT_DISCRIMINATING.** ORACLE − fixed per unit was 0, 1, 1, −1, 0, 0, 0, 0 (mean 0.125, against
  the 2.0 needed).
- **repair:** learned2 − learned has mean −3.375.
  - The cost-aware policy did fix the preparation cost: 15 ms against 481 ms.
  - Despite that, it is worse on two Huntington units, at 4/25 and 1/25 against 25/25 for fixed.

Other checks:

- All 56 runs (7 arms × 8 units, empty included) stayed within their cap.
- No custody problems.
- Insertion screen: 2515 lemma decisions, all ALLOW.

## Why learned2 lost: a true lemma can hurt the prover (`harmful_library_diagnostic.json`)

On Huntington seeds 612 and 614, learned2 proved two lemmas and then stopped:

- L0 `plus(plus(X,plus(X,X)),X) = X`
- L1 `plus(X,plus(X,plus(X,X))) = X`

Its next pick, `plus(X,plus(Y,X)) = plus(X,Y)`, was unproved, so idempotence `plus(X,X) = X` never
entered the library.

A post-study diagnostic re-ran the first 8 targets of unit 614 under fixed libraries. It is not part of
the frozen study.

| Library | proved at 1 s | proved at 4 s |
|---|---|---|
| empty | 7/8 | 8/8 |
| {L0, L1} | 0/8 | 0/8 |
| {L0} | 0/8 | 0/8 |
| {idempotence} | 8/8 | 8/8 |
| {idempotence, L0, L1} | 8/8 | 8/8 |

A single true consequence of the axioms (L0) turns 7/8 into 0/8. Adding idempotence repairs it.

- **Libraries are not monotone for E.** A lemma's value depends on the rest of the library, so a
  per-lemma usefulness score, which is what learned2 learns, cannot see this interference.
- **Why the fixed rules win.** They take the smallest lemma first, and on Huntington that is
  idempotence. That is why fixed sits at the oracle reference.

This is DEV evidence about E 3.x under these settings, not a general theorem about provers.

## Checked coverage (`lean/`, `lean_failure_trace.json`)

Every prover-reported success of fixed and learned2 was replayed in Lean from custody: 208 replays.

| Result | Count | Where |
|---|---|---|
| CHECKED | 153 | – |
| CHECK_FAILED | 24 | Huntington@612 fixed |
| CHECK_FAILED | 25 | Huntington@614 fixed |
| CHECK_FAILED | 1 | Huntington@613 fixed |
| CHECK_FAILED | 5 | Sheffer@611 learned2 |

Trace (one target per failing run, full Lean logs captured):

- **Huntington fixed:** library lemma `L1_step_c_0_22`. "`simp` made no progress", the same tactic-cascade
  limit as B20_R2 (B19-OPEN-5). Every target that depends on it fails.
- **Sheffer learned2:** `L18_step_c_0_7` and `L19_step_c_0_9`, same message.
- **Huntington@613 fixed:** one goal step, `G_step_c_0_40`, "unsolved goals".

CHECK_FAILED means the replay route produced no kernel-checked proof. It is not evidence of falsity.

On the checked metric fixed totals 76 and learned2 totals 77, but that comparison measures translator
coverage. As in B20_R2 the prover-level endpoint was declared primary.

Diagnostic gap found: the checker keeps only the last 6000 characters of a module log. In these
modules, linter warnings push the error lines out of the stored record. The trace above was obtained
by re-running with full logs; see B20R3-OPEN-3.

## Files

- `setup.json`, `partition_*.json`, `calibration.json`, `train/`: material, partition, calibration and frozen models.
- `runs/<unit>/<arm>.json`: per-run research account, lemma custody and target records. `objects/` holds proof objects.
- `rows.json`, `oracle.json`, `e3_summary.json`: rows, the ORACLE diagnostic and the preregistered report.
- `run.log`: phase 1. `lean.log`: Lean phase, resumed after an interruption at 27/208 and then run in two shards.
- `harmful_library_diagnostic.json`, `lean_failure_trace.json`: post-study diagnostics.
