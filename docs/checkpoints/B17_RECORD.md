# B17 checkpoint record — Formal research (roadmap W08 and the first TheoryPackage path)

Parent: `GENESIS_COMPLETION_CHECKPOINT_B16.zip`
(sha256 `2f0d5145d56acbb154d151834914e5d9a8254f49712a79b0aefe8b460bc669af`, commit `db0ffdb`).

## Built and tested (builder only; nothing independently reviewed)

| Item | What |
|---|---|
| Pinned workspace | Defined in `toolchain/FORMAL_WORKSPACE.json`: Lean 4.34.1, Mathlib `d13f23b7` (v4.34.1) and eight dependency commits. `build_formal_workspace.py` builds the 699-module closure of `Mathlib.Data.Finset.Powerset` offline with `--no-cache`, then copies and hashes the artifacts. Audited before every use. Source identity `a3a7569b…`, artifact identity `95a6ec9f…`. Two builds on this host gave identical bytes. |
| Acceptance | `formal_research/checker.py`: sandboxed module chains with a prescreen (constructs, options, imports), statement binding, axiom audit, declaration extraction, dependency closure, leanchecker replay, nonce-guarded results and the roadmap's outcome classes. |
| Search | `formal_research/search.py`: named recipes. The search compiles its own context, charges every attempt, and never accepts anything. |
| Theory package | `formal_research/theory_package.py` and `triangle_theory.py`: generated concepts, gadget search, conjecture screening, hypothesis correction, checked disproofs, the package contract, an executable method compiled only from CHECKED lemmas, and replay. |
| Lean domain | `formal_research/lean_domain.py`: the DomainAdapter for Lean statements. Validation is acceptance. Exact references are UNSUPPORTED. Not a sealed-receipt domain. |
| Evidence | `evidence/formal_research_b17/`: package `6550a279…`. 9 CHECKED, 7 DISPROVED, 2 UNRESOLVED, 1 UNSUPPORTED. The method is sound on 12 fresh DEV tasks, with a gap of 1–9 edges. Two Lean-checked task certificates reuse the package lemmas. The replay gave REPLAYED. |
| Tests | `tests_formal/test_formal_research.py` (22 tests), in the formal suite. That suite accepts no skips, so a missing workspace fails the release. |

## Exit

"Real generated reusable Lean artifacts replay": met by the builder, with no
differences in the replay. An independent replay is outstanding; see `B17_REVIEW_BRIEF.md`.

## Open

- **B17-OPEN-1.** The proof recipes are builder-written.
- **B17-OPEN-2.** Workspace byte-reproducibility has been shown on one host only.
- **B17-OPEN-3.** The package is elementary rediscovery, and W11's done-when is not met.
- **Carried over.** B16-OPEN-1 and B16-OPEN-2, R-04, B14-OPEN-3 and B14-OPEN-4, GV0,
  and the B16 phase-exit review.

## Claim ceiling

Engineering checkpoint. DEV material only. No sealed task was created and no claim was
promoted. No novelty or usefulness claim is made.

## Next

1. An independent replay of `evidence/formal_research_b17/`.
2. B18: concept invention (W09–W12).
