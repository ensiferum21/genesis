# B18 evidence: concept invention (W09–W12), DEV only

Produced by `scripts/b18_invention.py evidence/invention_b18`, against the pinned
workspace (artifact identity `95a6ec9f…`). Total time: 3,907 s on 2 cores. All eight
packages replay from their sources alone (`replay.json`: REPLAYED).

| Path | What |
|---|---|
| `representations/package.json` | W10: grammar records and 33 obligations (19 CHECKED, 14 DISPROVED). |
| `representations/dev_evaluation.json` | The DEV selection ranking and a fresh DEV evaluation panel (12 tasks). |
| `worlds/package.json`, `worlds/experiment.json` | W12: five worlds, verdicts, transports, and the discriminating experiment. |
| `recovery/history`, `recovery/concept` | W09: the pre-cutoff library, and the recovered concept with rfl-checked instances and generic lemmas. |
| `recovery/arm_{none,retrieval,concept,manual}` | The fresh families, one package per arm. |
| `recovery/comparison.json`, `recovery/proof_sizes.json` | The arm comparison; proof-term sizes recomputed by re-acceptance (see `corrections`). |
| `summary.json`, `run.log` | Headline numbers and the progress log. |

## Results

**W10 representations.**
- The grammar has 8 typed proposals.
- Four are proved sound for triangle-free in Lean: `cross_2`, `ordered_2`, `adjacent_2`
  and `adjacent_3`.
- Every other triangle-free soundness claim is disproved by a Lean-checked
  counterexample, and so is every C4 soundness claim. That is an honest negative result
  for this grammar on C4.
- Dominance relations and loss witnesses are proved. The loss witness for `cross_2` is
  the 5-cycle, which is triangle-free but no 2-class encoding keeps.

**W11 structural result used by a solver.**
- The selection panel chose `adjacent_2`. It tied with `cross_2` and `adjacent_3`, and
  on two classes it decodes the same edges as `cross_2`.
- On 12 fresh DEV tasks, against the strongest fixed baseline (picked per task after the
  fact, which favours the baseline), represent-and-repair won 6, tied 5 and lost 1.
- It reached the certified optimum on 4 tasks, against 2 for the baseline. Mean gap to the
  optimum: 0.67 edges against 1.58.
- Every witness was validated by the domain checker. The 0.25 s budget gave the same
  values as the 2 s budget.
- The B17 packing bound certified no optimum here.

**W12 worlds.**
- W_conflict (bipartite with a triangle) is INCONSISTENT. Its proof of False uses the
  generated lemma "bipartite → triangle-free". Its claim is VACUOUS.
- The other four worlds are CONSISTENT, each by a checked witness.
- Transports:
  - W_tf → W_bip: TRANSPORTED;
  - W_tf → W_deg1: refused, because "max degree 1 → triangle-free" stayed UNRESOLVED;
  - W_tf → W_conflict: refused, because the target is inconsistent.
- W_tf and W_bip are DISTINCT: the 5-cycle separates them.
- The discriminating experiment:
  - on erdos hosts only W_dense applies, and keep-all was invalid on 6 of 6;
  - on bipartite hosts W_bip and W_tf apply, and keep-all was valid on 6 of 6, made
    optimal by the trivial bound |H|.

**W09 recovery.**
- Typed anti-unification over the snapshot found 2 candidates. The top one,
  `RC.C0 P := ∀ x0 x1, x1 ≤ x0 → P x0 → P x1`, comes from 3 history statements and uses
  no hidden constant.
- It is definitionally Mathlib's `Antitone`, which recovery could not see.
- Its 3 instances are checked by `rfl`, and all 4 generic lemmas are proved.
- On 16 fresh statements:

  | Arm | Proved | Disproved | Unresolved |
  |---|---|---|---|
  | none | 4 | 4 | 8 |
  | retrieval | 4 | 4 | 8 |
  | concept | 8 | 4 | 4 |
  | manual | 8 | 4 | 4 |

  The 4 disproved are the NonEmpty statements, refuted in every arm. C4Free stays
  unresolved in every arm.
- The concept arm proves the Matching family, which no arm without the concept proves
  (enables). It shortens the LoopFree proofs from 1,468–1,646 proof-term nodes to 23–29
  (shortens). The manual `Antitone` arm does exactly as well. Cache hits: 0 in every arm.

## What this is not

- **No sealed evaluation and no novelty claim.** The cut representation, the
  bipartite/triangle-free relations and down-closure are all classical.
- **Not a historical study.** The history library is Genesis-generated, not a historical
  Mathlib cut.
- **The proofs.** They come from builder-written recipes, chosen by search.
