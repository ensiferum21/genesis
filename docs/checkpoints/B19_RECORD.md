# B19 checkpoint record — Useful discovery (roadmap W13–W17; E1/E2 readiness)

Parent: `GENESIS_COMPLETION_CHECKPOINT_B18.zip`
(sha256 `0f5418749ddebc6aab5dc474076f3ca482ea2ab08ba8e2656d8828cf7aec6127`, commit `bf3b449`).

## Built and tested (builder only, DEV only; nothing independently reviewed)

| Item | What |
|---|---|
| W13 | `discovery/obstruction.py`: an LP relaxation with exact rational dual certificates and an independent exact checker. The inequality validity is Lean-checked. Joint certification is construction, then the LP certificate, then SAT/DRAT on the remaining gap. On 12 fresh hard DEV hosts with matched 60 s budgets: optimum certified on 11 against 6 for the reference, mean gap 0.08 against 21.2, no disagreements. |
| W14 | `discovery/active.py`: Beta–Bernoulli hypotheses, calibration, identifiability classes reported UNRESOLVED, and EIG / KG* / top-two / round-robin / random policies under equal budgets. EIG lost to fixed and random selection; that result is kept. KG* was added afterwards and evaluated on fresh pools, where it beat both at the 20% and 40% budgets. |
| W15 | Solver factorial with removal, placebo, effort and conventional controls: the represent-and-repair gain survives all of them on 24 fresh DEV tasks. Concept controls: placebo 4/16 and effort 4/16, against concept 8/16 and manual 8/16. |
| W16 | `formal_research/fof_lean.py`: E proof objects are replayed step by step in Lean (ground-instance hints, skolem witnesses, lemma chains) and bound to a trusted statement generated from the problem. `discovery/ghost_census.py` runs a preregistered DEV diagnostic on a 125-problem family of ten equational theories. Run 2 (fixed harness) decided RETIRE_NO_HEADROOM: free true lemmas add nothing over the strongest baseline (123 vs 124 at 8 s), and the Ghost Census arms lose. Run 1, with a model-finder budget defect, is kept and reached the same decision. |
| W17 | `literature.py`: provenance-bearing sources, untrusted text screened, exact quotes, notation resolution, Lean and executable links, ambiguity records, an adjudication queue, and scoped novelty reports. All four Genesis results checked have prior art; two links are Lean-checked equivalences (RC.C0 ↔ `Antitone`, ↔ `IsLowerSet`). |
| E1 | Candidate (represent-and-repair, cut representation) identified by code hash. A 60-task DEV pilot gives +1.27 edges per task over `low_cycle`. The B16 power model reports INFEASIBLE; a centred-headroom option (new, not the default) gives n = 25. The DRAFT decision record has no problems; it is not frozen. |
| E2 | Design draft from the B18/B19 DEV arms. |
| Evidence | `evidence/discovery_b19/` (3 packages REPLAYED), `ghost_census_b19/` (run 1 with a harness defect, run 2 fixed), `literature_b19/`, `readiness_b19/`. |
| Tests | Formal suite: `tests_formal/test_discovery.py` and `tests_formal/test_ghost_census.py`, with no skips allowed. Commit suite: `tests_genesis/test_literature.py`, `test_readiness.py`, and the power test in `test_analysis_v2.py`. |

## Exit

"Prospective usefulness accepted or branch rejected". The builder cannot accept. On DEV:

- **W13–W15.** Usefulness evidence exists.
- **W16.** The branch decision is recorded for its scope.
- **E1/E2.** Drafts are ready for review.

Acceptance needs independent review, an independent custodian and sealed panels; see
`B19_REVIEW_BRIEF.md`.

## Open

- **New in B19:** B19-OPEN-1 to B19-OPEN-6 (`docs/BLOCKING_DEFECTS.md`).
- **Carried over:**
  - B18-OPEN-1 to B18-OPEN-3 and B17-OPEN-1 to B17-OPEN-3;
  - B16-OPEN-1, B16-OPEN-2 and the B16 phase-exit review;
  - R-04, B14-OPEN-3, B14-OPEN-4 and GV0.

## Claim ceiling

Engineering checkpoint. DEV material only. No sealed task, no promoted claim, no novelty
claim.

## Next

B20: learning to research (W18–W20), with E3 as an explicitly unestablished or
DEV-supported better-improver question.
