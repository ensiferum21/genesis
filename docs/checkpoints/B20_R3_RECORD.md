# B20_R3 record: redesigned research policy in a new frozen DEV study (B20R-OPEN-1)

- **Parent:** B20_R2 (commit `3c1089e`).
- **Run by:** the builder. DEV only. Nothing here has been independently reviewed.
- **Order:** moved ahead of the H08 and H05 wiring at the user's request ("do the recommended move").
  It is the cheapest test of whether the better-improver part of the vision can be reached on the
  current material.
- **Format of each section:** problem, implementation, evidence executed, limitation, consequence.

## Design pilot: is there selection headroom on the E3 family?

- **Problem.** A redesigned policy can only win if some lemma selection beats the fixed rules under
  the same cap. B20_R2 never measured that.
- **Implementation.** `scripts/b20r3_headroom_pilot.py`, committed as `147d613`, in five rounds on six
  systems:
  1. the default configuration;
  2. larger targets;
  3. scarce caps;
  4. target-mined conjectures;
  5. prover strategy.

  ORACLE is the dependency closure of the lemmas that exhaust-library proofs used, built from the targets
  themselves. It is an optimistic reference, not an arm.
- **Evidence.** `evidence/headroom_pilot_b20r3/`: ORACLE − FIXED@CAP is at most +1 target in 12 on every
  system and range.
  - **Huntington:** the smallest pool lemma (idempotence) is the expensive key lemma, so smallest-first
    already is the oracle order.
  - **Sheffer:** libraries barely matter.
  - **Other systems:** the remaining systems sit at floor or ceiling.
- **Consequence.** On this family superiority over fixed rules is not available to any arm. The study
  below was registered as a repair and non-inferiority check, with its own measure of discriminating power.

## Cost-aware learned policy (`research.CostAware`, arm `learned2`)

- **Implementation.** `src/genesis/learning/research.py`, commit `5aa9774`.
  - **Features:** linear in the pool; development-target subterms are counted once.
  - **Ranking:** P(proved) × P(needed by an eligible development proof) / E[attempt CPU].
  - **Model:** one frozen, hash-checked model per system.
  - **Tests:** `tests_genesis/test_research_policy_v2.py` (10).

## Frozen DEV study (`scripts/b20r3_e3_costaware.py`, rules committed before running)

- **Design.**
  - Replicates B20_R2 on fresh seeds: calibration 510, training 511–513, evaluation 611–614.
  - Arms: fixed, random, heuristic, bandit, learned (the B20_R2 design), learned2 and an empty library.
  - Global exposure over all prior DEV evidence, including the pilot.
  - Equal research caps; training is reported, not charged.
  - The ORACLE diagnostic and the verdict rules were fixed in the script.
- **Results** (`evidence/e3_costaware_b20r3/`):
  - **vs fixed: INFERIOR_DEV.** learned2 vs fixed 2W/3T/3L, mean −5.5 per 25 targets.
  - **material: NOT_DISCRIMINATING.** Mean ORACLE − fixed = 0.125.
  - **Repair:** preparation fell from 481 ms (learned) to 15 ms (learned2), yet learned2 − learned has mean −3.375.
  - **Runs:** all 56 within cap; zero custody problems.
- **Finding: libraries are not monotone.** On Huntington 612 and 614 learned2 built {L0, L1} without
  idempotence and proved 4/25 and 1/25.
  - A post-study diagnostic gave these results:
    - L0 alone, a true consequence of the axioms, takes E from 7/8 to 0/8 on the unit's first 8 targets.
    - Adding idempotence restores 8/8.
  - A per-lemma usefulness score cannot see this interaction.
- **Checked coverage.** 208 Lean replays from custody: 153 CHECKED and 55 CHECK_FAILED. The failures
  trace to three library steps and one goal step where the tactic cascade stops ("`simp` made no
  progress"; B19-OPEN-5). They are not falsity.
  - On the checked metric fixed totals 76 and learned2 77. That reflects translator coverage, which is
    why the prover-level endpoint was declared primary.
- **Interruption.** The earlier session hit its usage limit during the Lean phase, at 27 of 208. The
  phase is resumable by design and was completed in two shards. No rule changed.
- **Limitation.**
  - This is one family, one prover and DEV only.
  - The ORACLE is optimistic and built from the evaluation targets themselves.
  - The non-monotonicity finding is a DEV observation about E under these settings.
- **Consequence.**
  - Better-improver stays UNESTABLISHED.
  - The scientific question now needs a family with headroom (B20R3-OPEN-1).
  - The next policy also needs a library-level objective that sees interactions, not per-lemma scores
    (B20R3-OPEN-2).

## Claim ceiling

DEV design diagnostics and one negative DEV study. No sealed task. No promoted claim.
