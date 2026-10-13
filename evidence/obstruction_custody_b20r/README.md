# B20_R1 obstruction custody re-run: REGENERATED on the recovery branch

**This is not the original B20_R1 evidence.**

- **Original:** commit 708351c, which is in the B20_R1, R5, R8 and R11 checkpoints. It is not present in this workspace. The workspace was lost, and only the B20 base, the R1 repair patch and the CRPD patch came back.
- **This copy:** the same script (`scripts/b20r_obstruction_custody.py`, restored verbatim from the session log) run again on 13 Oct 2026, so that the formal suite's custody test has the bundles it needs on this branch.

| | Original B20_R1 run | This re-run |
|---|---|---|
| Tasks | 12 | 12 |
| OPTIMALITY_CHECKED | 12 | 12, all via LP_DUAL_EXACT |
| Replayed checker-only as recorded | 12 | 12 |

The witness search is time-based, so bytes and bundle identities differ from the original.

**When the canonical history is restored, drop this commit and keep the original.**

It is a new execution on the B19 DEV task specification (HARD settings, seed 20261021). Only the joint arm was run, with represent-and-repair witnesses and 60 s per task. Each bundle was replayed in a separate process with the producers disabled.
