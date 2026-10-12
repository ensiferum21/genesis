# H02 exit (B20_R2): fresh frozen DEV E3 study on the repaired harness

`scripts/b20r_e3_fresh.py` was committed (e4e431b) before it ran; its docstring fixes every rule.
Phase 1 (`run.log`): material, calibration, training, evaluation, custody. Phase 2 (`lean.log`): Lean
replay from custody, run in two shards by `scripts/b20r_e3_lean_shard.py` (the frozen selection and
replay call, unchanged). Phase 3: `e3_summary.json`. DEV only; builder-run; no sealed panel or custodian.

## Material and budgets

- Global exposure: 3,253 statements from all prior DEV evidence (B20 pools regenerated and hash-checked)
  plus this study's pools and development targets; calibration and evaluation targets drawn with
  `learning.partitions` (`partition_calibration.json`, `partition_evaluation.json`; validator clean).
- Calibration (B20 rule): Sheffer 6–9 nodes (empty-library rate 0.20), cap 1.848 s; Huntington: no range in
  [0.2, 0.6] (all >= 0.90), closest 7–10, cap 0.648 s. Caps are 0.25 x the fixed policy's pool-exhaustion
  CPU measured under the repaired account (every category charged).
- Learned policy retrained here (457 examples), frozen before any evaluation run; training CPU 75.3 s.

## Results (declared primary endpoint: prover-reported successes eligible under budget and exposure)

| | fixed | heuristic | bandit | random | learned | empty |
|---|---|---|---|---|---|---|
| mean per 25 targets (8 runs) | 16.125 | 16.0 | 15.875 | 15.25 | 13.75 | 13.375 |

Learned vs fixed: 0 wins, 2 ties, 6 losses (mean −2.375). All 40 research runs within cap; zero
custody problems; the insertion screen allowed all 1,296 lemma insertions (pools were already disjoint).

Why: on Huntington the learned policy's feature computation (pool x development-target overlap) takes
~0.61 s of the 0.648 s cap, so it attempts no proof (library 0 in all four runs); on Sheffer it builds
the largest libraries (66–76 lemmas) without beating fixed. Under full or amortized charging of its
training (75 s against these caps) it could not run at all; the declared primary comparison does not
charge training.

## Checked coverage (secondary; Lean replay from custody, proof search disabled)

338 replays (every fixed and learned success; a preregistered 20% sample of the other arms):
269 CHECKED, 69 CHECK_FAILED, 0 incomplete. All 69 are in Huntington seeds 602 and 603 and trace to one
link: lemma L1 (`plus(plus(X,X),X) = X`, proved by E from L0) has a step the Lean tactic cascade cannot
close (`simp made no progress`, B19-OPEN-5); L0 alone replays. Every target depending on it fails.
CHECK_FAILED means the replay route did not produce a kernel-checked proof; it is not evidence of falsity
(every target is true by construction).

| | reported | replayed | checked |
|---|---|---|---|
| fixed | 129 | 129 | 80 |
| learned | 110 | 110 | 110 |
| random / heuristic / bandit / empty (20% sample) | 484 | 99 | 79 |

On the checked metric the comparison moves (Huntington 602/603: fixed 0 and 1 checked vs learned 22
and 20) because the learned arm's empty library leaves only axioms-only proofs, which replay. That
measures translator coverage, not research quality, which is why the endpoint is declared in advance.
Naming: in `rows.json`, `eligible` is prover-level (budget and exposure); in `metrics_by_run`
(custody.score), `eligible` additionally requires CHECKED.

## What this does and does not show

- The repaired harness runs the B20 E3 design end to end: global partition, enforced budgets, custody of
  every scored proof, Lean replay from custody alone.
- The learned policy does not beat fixed rules here; better-improver remains UNESTABLISHED.
- Nothing here is sealed, independently run, or reviewed.
