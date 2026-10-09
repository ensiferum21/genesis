# Gap Engine v2

A verified, compounding discovery engine. This repository implements the v2 upgrade
(U1-U5) on top of the Gap Engine kernel, together with a real-mathematics domain in which
every claimed result is checked by a small trusted proof checker.

```
python -m unittest discover -s tests -t .          # full test suite (stdlib unittest)
python scripts/build_worlds.py 0 1 2 3              # build + cache inductive lesion worlds
python -m gap_engine.experiments.synthetic_bench    # planted-synergy benchmark (calibrated)
python -m gap_engine.experiments.induction_bench    # head-to-head on inductive mathematics
python -m gap_engine.cli demo                       # one v2 campaign on a lesion world
python scripts/build_round2b_worlds.py              # round-2b worlds + calibration experience
python -m gap_engine.experiments.round2b_bench      # round-2b head-to-head (preregistered)
python -m gap_engine.experiments.round2b_cascade    # compounding, scored on sealed
python -m gap_engine.experiments.rotation_dev       # focus rotation, development worlds only
python scripts/diagnose_round2b.py                  # replay every arm's gate decisions (no sealed access)
python scripts/export_round2_lean.py                # Lean 4 export + independent self-check
```
Latest results: `docs/RESULTS.md` §9 (round 2 is superseded by round 2b).
Run with `PYTHONPATH=src` or `pip install -e .`. Dependencies: numpy, scipy, pydantic,
scikit-learn. No network access, GPU or external prover is needed.

## Layout

| Path | What it is |
|---|---|
| `src/gap_engine/kernel/` | The judge: hash-chained ledger, one-currency budget broker with caps, sealed store, statistics, Gate J, the accepted library, invariants INV-18..23 |
| `src/gap_engine/adapters/induction/` | Real mathematics: terms, theories, an untrusted prover (rewriting + structural induction), a **trusted checker**, conjecture generation, tasks, counterfactual theories, the reality adapter |
| `src/gap_engine/adapters/synthetic.py` | Planted-synergy world with known ground truth |
| `src/gap_engine/u1/` | Effect fingerprints and the stepping-stone archive |
| `src/gap_engine/u2/` | Library dropout (plain and fingerprint-blocked), LLR attribution, FDR-controlled bundles |
| `src/gap_engine/u3/` | Hindsight harvesting, kernel-controlled data admission, the trainable proposer, dream cycles with G1 |
| `src/gap_engine/u4/` | Research language, procedures, trace compression, CEGIS preconditions judged on sealed worlds |
| `src/gap_engine/u5/` | Discovery funnel, Thompson scheduler with a randomised slice, audited STOP |
| `src/gap_engine/engine/` | The search arms (G, R, R+, U) and the full v2 campaign loop |
| `src/gap_engine/experiments/` | Preregistration, calibration, the benchmarks and their analysis |
| `constitution/policy.json` | Budget caps, FDR level, gate settings (hash-locked per run) |

## The trust boundary

Research code may propose anything. Only `kernel/` and
`adapters/induction/checker.py` decide what is true, admitted or spent:

* a theorem counts only if `checker.check_proof` replays its proof; the checker re-derives
  every induction goal and refuses IH instances that substitute fixed eigenvariables;
* a library item enters only through `Library.admit`, citing a ledgered gate decision;
  bundles from U2 pass Gate J as units (INV-18);
* sealed items are reachable only through `SealedStore.judge`; training data passes
  `admit_dataset`, which removes sealed and near-duplicate items (INV-19, INV-20); every
  lemma entering a candidate pool passes `InductionWorld.screen_reason` (sealed
  near-duplicates and held-out gate tasks are refused);
* every unit of compute is charged to a `BudgetBroker` whose caps policy cannot raise.

See `docs/` for the architecture, the traceability matrix against the spec, and results.
