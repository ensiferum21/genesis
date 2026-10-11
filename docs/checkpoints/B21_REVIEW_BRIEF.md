# B21 review brief: repeated improvement (W21–W23, E4)

The B21 exit is "three qualifying transitions with retention and audit". The builder
reports it **not met**: one transition qualified, then the domain saturated. This brief
maps what a reviewer has to check.

## Reproduce

```
export GENESIS_TOOLCHAIN=/srv/toolchain PYTHONPATH=src PYTHONPYCACHEPREFIX=$(mktemp -d)
python3 -m unittest tests_formal.test_improvement
python3 scripts/b21_improvement.py /tmp/b21              # about 30 min on 2 cores
python3 scripts/b21_w22_lean_followup.py /tmp/b21        # about 10 min; needs /tmp/b21/w22
python3 scripts/b21_w23_followup.py /tmp/b21             # about 4 min
```

E runs with CPU limits and research runs with CPU budgets, so libraries can differ
between runs. Scores on Wolfram's axiom are load-sensitive (B20-OPEN-3).

## Decisions for the reviewer

| # | Decision | Evidence |
|---|---|---|
| 1 | Is the generation rule fixed before the run and applied mechanically? It covers the fresh-panel margin, retention tolerance, one child and no interventions. Are rejected children kept? | `generations.RULE`, `decide`; `e4/transitions.json`; `Evidence.test_recorded` re-derives each decision |
| 2 | Is saturation, rather than a failed child, the right reading of transitions 2–3? | research CPU 0.07 s and 0.09 s; library 94 → 96; README |
| 3 | Can a definitional extension prove anything new about the base language? Replays are bound to the base statement, with the primitive instantiated by its λ-term and the definition proved by `rfl`. | `fof_lean.proof_module(definitions=…)`; `Routes.test_definitional_extension_is_bound_to_the_base_statement`; `w22_lean_followup.json` |
| 4 | Is the renaming control the right test of whether a primitive is genuinely new (SPEC-41.1)? | `b21_improvement.phase_w22`; `w22/summary.json` |
| 5 | Is the ground-hint repair sound? Hints are only instances handed to Lean, which checks every step, so wrong hints can cause failure but never acceptance. Was it handled honestly? It was found after the main run, whose record stands, and evaluated on regenerated libraries. | `fof_lean.ground_hints`, `_rewrite_path`, `_match_c`; `Hints` tests; the follow-up docstring |
| 6 | Is the one strict-definition "false acceptance" in the W23 follow-up indeed sound? The claim is the `Y := X` instance of another item, and replay is bound to the claim's own statement. | `w23_followup.json` (the flagged row); README; `Evidence.test_followups` |
| 7 | Is the SIMULATED expert labelled everywhere, and kept out of any claim about real experts? | `faults.SimulatedExpert`; `w23/expert.json`; `w23_followup.json` |

## Known limits

- **E4.** Saturation after one transition; GV5 not established (B21-OPEN-1).
- **W22.** The primitive does not help (B21-OPEN-2).
- **W23.** Injected faults and a simulated expert only (B21-OPEN-3).
- **Lean hints.** Heuristic; the main-run bridge was 0/11, and the follow-up used new
  libraries (B21-OPEN-4).
