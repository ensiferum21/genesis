# B20 checkpoint record — Learning to research (roadmap W18–W20; E3)

Parent: `GENESIS_COMPLETION_CHECKPOINT_B19.zip`
(sha256 `e589eb1ff91334d47ee907e1a50472d27ee3a37b9c0dd8bcb14bac68f465441a`, commit `49c9f15`).

## Built and tested (builder only, DEV only; nothing independently reviewed)

| Item | What |
|---|---|
| Domain | `learning/equational.py`: varieties with exact deciders (Boolean algebra, groups, Boolean rings, distributive lattices), seven axiomatizations, conjecture pools and target sampling. |
| W19 | `learning/research.py`: research runs under a CPU budget, successors evaluated on unused targets, and five policies (fixed, random, heuristic, bandit, learned-and-frozen), with calibration, diversity and exhaustion recorded. |
| W18 | `learning/macros.py`: macros induced from used-lemma closures, with faithful replay, compression, revocation, preconditions, and strict or non-strict expansion. |
| W20 | `learning/memory.py`: contamination screening (EXACT, INSTANCE), retrieval, demotion, and a failure-driven curriculum from development targets. |
| Lean | `fof_lean`: chained replay of lemma-dependent proofs (`goal_deps`, `goal_positions`). 67 of 68 successor proofs replay, with 583 chained lemmas. |
| E3 | 8 independent DEV runs per policy. Learned vs fixed: 1W/7T/0L. The better-improver claim is explicitly UNESTABLISHED. |
| Hard system | On Wolfram's single axiom, research matters: 60 s takes successors from 0 to 8–12 of 15. Curriculum ≈ plain research at equal effort. The strict macro transfer failed; the non-strict one equals plain research. |
| Evidence | `evidence/learning_b20/`: the main run, `e3_hard/`, `hard_followup/` and `curriculum_control.json`, with logs. |
| Tests | `tests_formal/test_learning.py`: deciders, pools, policies, logistic fit, macros, revocation, screening, curriculum, runs, Lean chains (including a tampered chain) and the evidence. |

## Exit

"Better-improver claim supported or explicitly unestablished": explicitly UNESTABLISHED.
GV4 needs sealed downstream evaluation and independent runs.

## Open

- **New in B20:** B20-OPEN-1 to B20-OPEN-4.
- **Carried over:**
  - B19-OPEN-1 to B19-OPEN-6, B18-OPEN-1 to B18-OPEN-3 and B17-OPEN-1 to B17-OPEN-3;
  - B16-OPEN-1, B16-OPEN-2 and the B16 phase-exit review;
  - R-04, B14-OPEN-3, B14-OPEN-4 and GV0.

## Claim ceiling

Engineering checkpoint. DEV material only. No sealed task, no promoted claim, no
better-improver claim.

## Next

B21: repeated improvement — the multigeneration controller (W21), new primitives (W22),
fault-tolerant reasoning and expert interaction (W23), and E4 as DEV transitions.
