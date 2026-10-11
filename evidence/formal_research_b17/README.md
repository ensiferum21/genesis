# B17 evidence: the first theory package (DEV only)

Produced by `scripts/b17_formal_research.py evidence/formal_research_b17 --tasks 12 --certificates 2`
against the pinned workspace (`toolchain/FORMAL_WORKSPACE.json`). The workspace was
built by `toolchain/build_formal_workspace.py`:

- source identity `a3a7569b…c7ef`;
- artifact identity `95a6ec9f…6b41`;
- 699 modules, the import closure of `Mathlib.Data.Finset.Powerset` at Mathlib
  `d13f23b7`.

| File | What |
|---|---|
| `package/package.json` | The theory package (schema `genesis-theory-package-v1`), content-addressed by `package_sha256`. |
| `package/lean/*.lean` | Every module source: trusted context, generated concepts and conjectures, untrusted proofs, task certificates. |
| `replay.json` | Replay from the package's sources alone, in fresh sandboxes: verdict REPLAYED, no differences. Both certificates are re-accepted. |
| `summary.json` | Statement outcomes, method evaluation, certificates and costs. |
| `run.log` | The run's progress log. |

## Outcomes

There are 19 statements:

- **CHECKED (9).**
  - The closure lemmas down_closed and inter_closed.
  - bound_card, bound_union and bound_mono. bound_union's proof uses the generated
    lemma down_closed.
  - Four gadget lemmas, a bound and a tightness lemma for each gadget.
- **DISPROVED (7).** Each disproof is a kernel-checked counterexample. Three of the
  seven are a corrected conjecture that was refuted again:
  - union_closed and union_closed_simple;
  - insert_closed and insert_closed_simple;
  - bound_insert;
  - bound_le_card;
  - bound_zero_empty.
- **UNRESOLVED (2).**
  - bound_zero_empty_simple, a corrected hypothesis that is true but which no recipe
    proves;
  - mantel, true but beyond the recipes.
- **UNSUPPORTED (1).** c4_down_closed, which needs `GT.C4Free`, a definition this
  theory does not have.

The gadget search covered graphs of up to 5 vertices and 7 edges. It kept the triangle
and K4, rediscovered. K4 minus an edge was rejected because one triangle packs it
equally well.

## The executable method

The method gives an upper bound by greedy gadget packing.

- On 12 fresh DEV tasks from the adopted triangle-free calibration it was sound on all
  12. The bound minus the certified optimum ranged from 1 to 9 edges, with a median of
  5. It certified no optimum on these tasks.
- For two tasks the bound `GT.TFBound host B` was proved in Lean, reusing bound_card,
  bound_union and bound_mono.

## What this is not

- **The proofs.** They come from builder-written recipes, chosen by search, and the
  facts are elementary rediscoveries.
- **No novelty or usefulness claim.**
- **No sealed material.**
- **No independent replay yet.**
