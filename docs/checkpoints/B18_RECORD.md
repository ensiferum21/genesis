# B18 checkpoint record — Concept invention (roadmap W09–W12)

Parent: `GENESIS_COMPLETION_CHECKPOINT_B17.zip`
(sha256 `3a3a7c703924d47eeb119e7ae5b28cfa48e287ecc66aa23dce2ac9fd4acc757f`, commit `1ce101c`).

## Built and tested (builder only, DEV only; nothing independently reviewed)

| Item | What |
|---|---|
| Loop | `formal_research/loop.py`: generic screen → disprove → search → accept → package. Search tries specialised candidates first. The check stage also returns statement trees and proof sizes. |
| W10 | `invention/representations.py`: a typed, bounded grammar with Lean obligations. 4 representations are sound for triangle-free. Every C4 soundness claim is refuted. Dominance and loss witnesses are checked. |
| W11 | represent-and-repair uses only a Lean-checked sound representation. Fresh DEV panel: 6W/5T/1L against the strongest baseline per task, 4 optima against 2, every witness valid. |
| W12 | `invention/worlds.py`: worlds, interventions, checked consistency and inconsistency, implications, separation, transport decisions, vacuous claims, and a discriminating experiment. |
| W09 | `invention/recovery.py`: snapshot, typed anti-unification, reification with rfl-checked instances, and a hidden-constant check. Fresh families in four arms: 4/4/8/8 of 16 proved (none, retrieval, concept, manual). The concept proves the Matching family and shortens the LoopFree proofs about 60-fold. |
| Evidence | `evidence/invention_b18/`: 8 packages, all REPLAYED. |
| Tests | `tests_formal/test_invention.py` (14 tests, formal suite; no skips allowed). |

## Exit

"Typed concepts, explicit worlds and checked semantics": met by the builder on DEV.
Independent review is outstanding; see `B18_REVIEW_BRIEF.md`.

## Open

- **New in B18.** B18-OPEN-1, B18-OPEN-2 and B18-OPEN-3.
- **Carried over.**
  - B17-OPEN-1 to B17-OPEN-3.
  - B16-OPEN-1 and B16-OPEN-2, and the B16 phase-exit review.
  - R-04, B14-OPEN-3 and B14-OPEN-4, and GV0.

## Claim ceiling

Engineering checkpoint. DEV material only. No sealed task, no promoted claim, no novelty
claim.

## Next

B19: useful discovery (W13–W17), and E1/E2 readiness. Sealed evaluation needs an
independent custodian.
