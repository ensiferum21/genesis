# B20_R20 record: THEOREM_CHECKED through a theory package (B14-OPEN-4 remainder)

Builder-run engineering batch. Nothing here is independently reviewed.

## What changed

Before this batch, THEOREM_CHECKED could be reached through only one route: equational custody (B20_R8). The theory packages Genesis produces could not license it. These include the B17 triangle theory, the B18 inventions, the CRPD-2b pair count and the B20_R17/R19 relational decoders.

The new route, `lean-package-v1`, takes a formal_check payload of the form {theorem_sha256, package}.

**The theorem object.** It is `genesis-lean-theorem-v1`, built by `replay_contracts.lean_theorem_object(package, statement_id)`. It names:
- the package by its `package_sha256`, which binds every definition module;
- the statement's id;
- the statement's exact Lean text.

**What the kernel requires:**
- The package passes its integrity checks (source hashes, package digest, claimed outcomes backed by bindings).
- The package is the one the theorem names, and it holds the statement with exactly that Lean text, with status CHECKED and allowed axioms only.
- The specification constant is defined in its module as exactly that proposition (`def <id> : Prop := <text>`), and a proof is bound to it.
- The Lean-package route identity is not revoked. This identity covers the pinned Lean, the workspace's source and artifact identities, the checker and package-replay code, and the allowed axioms.
- A fresh `theory_package.replay` of the whole package in Lean returns REPLAYED, with this statement's proof CHECKED.

**Claim wording.** It is generated from the package: "under the definitions of Lean theory package <id> (statement <id>), <Lean text> holds".

## Limits

- What a statement means depends on the package's definition modules. A reviewer must still read them: the kernel binds them, it cannot judge them.
- Each promotion replays the whole package, which takes several seconds of Lean for the small packages here.

## Tests

`tests_genesis/test_replay_contracts.py::LeanPackage` (3 tests), on the committed B20_R17 package:
- a checked statement replays, reaches THEOREM_CHECKED, and is worded from the package;
- refusals before any replay: altered Lean text, a tampered package, another package, an equational theorem on this route, and a Lean theorem on the equational route;
- a revoked route licenses nothing.
