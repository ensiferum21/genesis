# B20_R55 record: the row-invention procedure transferred to sum-free sets of integers (GV6, second target)

- **Built and run by:** the builder. Engineering and formal checking, DEV; no claim.
- **Setup commit:** `565e36b`, containing `invention/cuts_sf.py`, `scripts/b20r55_sf_generator.py` and
  `tests_genesis/test_cuts_sf.py`.
- **Evidence:** `evidence/sf_generator_b20r55/`, with the package, summary, log and README.

## Why

The C4 chain (B20_R46–R52) is near-domain transfer by the roadmap's own words (E5). B20_R53 and R54 found the
equational target empty at these scales. The roadmap names "a different theorem family" as a more distinct
setting. Sum-free sets (additive combinatorics) are one: integers under addition, not graph edges.

The builder's structural caveat is stated in the module, the script and the README: abstractly, the problem is
the same hypergraph-free packing as the source.

## What was built

`invention/cuts_sf.py` is generator v2 with only the motif-specific parts changed:
- **Structures:** sets P ⊆ {1..m}, m ≤ 8.
- **Rows:** Schur rows.
- **Copies:** Freiman-type copies.
- **Lean definitions:** a new trusted module `SFDefs`, defining `SF.SumFree` and `SF.ind`.
- **Bridges:** one per row shape.
- **Pattern statements:** over values satisfying the pattern's relations.

## Result

- **Patterns.** 17 kept, from 214 candidates.
- **Screen.** No counterexample.
- **Lean.** **All 20 obligations CHECKED** (3 base lemmas and 17 pattern bounds); 17 of 17 patterns usable.
- **Package.** It replays. Construction took 267.5 CPU-s.

## Tests

- `tests_formal/test_sf_generator.py` (3, Lean).
- `tests_genesis/test_cuts_sf.py` (7, no Lean).

## Disclosed development looks

The script docstring lists:
- a host LP probe;
- the generation counts;
- the scratch Lean run on the base lemmas and three patterns, after an `exfalso` fix.

The evidence README adds the host probes run for B20_R56's design.

## Limits

- **The new definitions need review.** `SFDefs` is a new trusted definition module. It is conservative (two
  definitions), but it is the sum-free domain contract and needs review like `G4Defs` did.
- **Bounded structures.** Patterns are limited to max element 8.

## Open

B20R46-OPEN-1 is updated: there is a second transfer target in a different theorem family, with the procedural
step done. Whether it counts as structurally different is for the reviewer. Utility on hosts is B20_R56.
