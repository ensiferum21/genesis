# B16 checkpoint record — Evaluator readiness (roadmap W05–W07)

Parent: `GENESIS_COMPLETION_CHECKPOINT_B15_R2.zip`
(sha256 `f56a3bc3cd8d2b4694f27ae0a0161e15293172423d79f6185f8d18f98aabd360`, commit `52ee907`).

## Built and tested (builder only; nothing independently reviewed)

| Workstream | What |
|---|---|
| W05 domains | `genesis.domains` DomainAdapter for both graph domains; candidate views exclude identifiers, families, splits and references; explicit UNSUPPORTED outcomes; conformance suite. |
| W05 calibration | `genesis.calibration` (DEV only, frozen rule). v1 panels: ceiling rate 1.0, headroom 0. Adopted c4 and triangle-free (round 2) families, pinned in `configs/dev_calibration.json`. |
| W07 statistics | `kernel/analysis.py` plan v2 and receipt v3; `genesis.judge` recomputation from raw receipts; `genesis.power` (headroom-limited model, design floor, DEV pilots only). |
| W07 resources | `genesis.resources`: per-category account (discovery, inference per arm, verification, ground truth, memory; human time declared only). Ground truth is not charged to an arm. The account is recorded in sealed evidence and recomputed by the judge, which also checks arm pairing. |
| W06 custody | Signed registration log with custodian-assigned families and size limits; OUTSTANDING registrations visible; `genesis.decision_record`; control declarations; release preflight requires both for v3. |
| Study design | DEV pilot (60 tasks) and power analysis: 30 sealed tasks (10 per family) reach power 0.946 at a design effect of 0.5. `evidence/study_design_b16/decision_record_DRAFT.json` is a DRAFT. |

## Closed (pending review)

- **B14-OPEN-2.** Multiplicity across candidates, scoped to one custodian.
- **B15-OPEN-1.** Unrecovered registrations are now publicly visible.

## Open

- **Phase exit.** Independent review of custody, fairness and study design.
- **B16-OPEN-1.** No external time anchoring.
- **B16-OPEN-2.** The power-model assumption needs review.
- **R-04 (unchanged).** A second machine, the image digest and wheel hashes.
- **B14-OPEN-3..4.**
- **GV0.**

## Claim ceiling

Engineering checkpoint. No sealed task was created, no candidate frozen and no
claim promoted. The pilot candidate is illustrative.

## Next

1. Independent review of `evidence/study_design_b16/` and of the custody records.
2. B17: formal research (W08).
