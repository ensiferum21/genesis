# B21 checkpoint record — Repeated improvement (roadmap W21–W23; E4 as DEV transitions)

Parent: `GENESIS_COMPLETION_CHECKPOINT_B20.zip`
(sha256 `44bbbbeb1b8781203af8b3489b7c1a396d7694806232193dce9e7fee46f12091`, commit `97fb233`).
The B20 clean-room rehearsal on the build host was REPRODUCED. That is not a second
machine.

## Built and tested (builder only, DEV only; nothing independently reviewed)

| Item | What |
|---|---|
| W21 | `learning/generations.py`: frozen, content-addressed generations (library, policy, lineage); transitions from a frozen parent; the decision rule `RULE`, declared before any run; rollback that keeps the rejected child in the record; solver quality and process cost recorded separately. |
| W22 | `learning/primitives.py`: operator-completeness adversary; fold/unfold; definitional extension (`equational.DEFINITIONS`; deciders unfold); migration and rollback; `fof_lean` definitions bound to the base statement (λ-term instance, `rfl`). |
| W23 | `learning/faults.py`: decider, prover, kernel and countermodel routes; `diagnose` (kernel needed to accept, disagreements named and never settled by majority); fault injection; expert questions with cost, provenance and budget; a labelled `SimulatedExpert`. |
| Lean | `fof_lean.ground_hints`: rewriting after superposition modulo commutativity, and matched overlaps first. `checker` returns error lines. |
| Evidence | `evidence/improvement_b21/`: the main run, plus the follow-ups `w22_lean_followup.json` and `w23_followup.json`, with logs. |
| Tests | `tests_formal/test_improvement.py`: decision rule, freezing, adversary, contract, diagnosis, corruption, expert label, hints, definitional Lean bridge, routes and the evidence. |

## Results (DEV)

- **E4.** Transition 1 was ACCEPTED (0 → 11 of 15). Transitions 2 and 3 were
  ROLLED_BACK: the domain had saturated, so there was no gain on the fresh panel.
  Retention held, and there were no human interventions.
- **W22.** The primitive passes its contract but does not help: base = primitive =
  renaming control.
- **Lean bridge.** 0/11 in the main run, from a hint defect. After the repair, the
  follow-up replays 11/11 primitive-arm chains (bound to the base statement) and 11/11
  base-arm chains.
- **W23.** No false claim was accepted in either run.
  - The follow-up made 48 checks. Corrupted proofs gave UNVERIFIED 8/8 and flipped
    deciders DISAGREEMENT 8/8.
  - Swapped proofs gave UNVERIFIED 7/8 and ACCEPTED 1. That acceptance is sound: the claim
    is an instance of the other item. The strict predeclared count of 1 is reported.
- **SIMULATED expert.** Correct decisions rose from 8/24 to 21/24 with 16 questions.

## Exit

The exit is "three qualifying transitions with retention and audit". It is **not met**.
One transition qualified, and GV5 is NOT ESTABLISHED.

## Open

- **New in B21:** B21-OPEN-1 to B21-OPEN-4.
- **Carried over:**
  - B20-OPEN-1 to B20-OPEN-4, B19-OPEN-1 to B19-OPEN-6, B18-OPEN-1 to B18-OPEN-3 and
    B17-OPEN-1 to B17-OPEN-3;
  - B16-OPEN-1, B16-OPEN-2 and the B16 phase-exit review;
  - R-04, B14-OPEN-3 (partly addressed), B14-OPEN-4 and GV0.

## Claim ceiling

Engineering checkpoint. DEV material only. No sealed task, no promoted claim, no
compounding claim and no claim about real experts.

## Next

B22: transfer and replication (W24; E5/E6). The work:
- a transfer protocol with frozen source capabilities and an equal adaptation budget, in
  a structurally different domain;
- exact replay of historical artifacts;
- a fresh efficacy experiment;
- a replication bundle for an independent operator.

GV6 and GV7 need independent operators.
