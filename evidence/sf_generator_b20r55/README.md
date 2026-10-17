# B20_R55: the row-invention procedure transferred to sum-free sets of integers (GV6, second target)

- **Script:** `scripts/b20r55_sf_generator.py`, preregistered with the adaptation `invention/cuts_sf.py` in commit
  `565e36b`.
  - Script SHA-256: `c00801e1…f40ce`.
  - Module SHA-256: `b83cd539…350b0`.
- **Run:** the builder, pinned to one core, 284 s.
- **Code identity:** `d5a9014bd9479f30…` (in `summary.json`).
- **Status:** engineering and formal checking. It licenses nothing. Certification on hosts is B20_R56.

## What was transferred

The system's row-invention procedure, unchanged in its search, kept rule and proof method:
- enumerate small structures;
- keep those whose LP under the motif rows, and under copies of earlier patterns, exceeds their true maximum;
- prove each bound in Lean from an integer rounding of the LP dual.

It came from triangle-free subgraphs (B20_R31/R37) and was carried to C4-free subgraphs in B20_R46. Here it is
carried to sum-free sets: sets of positive integers with no a + b = c inside them, a = b allowed. That is a
different theorem family (additive combinatorics: Schur, Erdős), and its objects are integers under addition, not
graph edges.

The registered adaptation (`invention/cuts_sf.py`) changes only the motif-specific parts:

| Part | Graph domains | Sum-free |
|---|---|---|
| Structures | small graphs | sets P ⊆ {1..m}, max P = m ≤ 8, gcd 1, every element in a Schur triple |
| Motif rows | triangles (≤ 2) or 4-cycles (≤ 3) | Schur triples x_a + x_b + x_c ≤ 2, and x_a + x_{2a} ≤ 1 |
| Copies | graph embeddings | injective maps preserving the pattern's Schur triples (Freiman-type) |
| Lean domain predicate | `GT.TriangleFree`, `G4.C4Free` | `SF.SumFree` (new trusted module `SFDefs`) |
| Pattern statements | over pairwise-distinct vertices | over values satisfying the pattern's additive relations |

## Result

- **Generation.** The procedure kept 17 patterns:
  - 214 candidate sets;
  - 133 with every element in a Schur triple;
  - 100 already implied by the Schur rows;
  - 16 implied by earlier patterns.
  The first are {1,2,3,4} and {1,2,4,5} (ex 2, LP 2.5). The largest is {1,2,3,4,5,6,8} (ex 3; Schur LP 4.0, 3.5
  with the earlier patterns).
- **Screen.** No counterexample among the 20 obligations: three base lemmas and 17 pattern bounds.
- **Lean.** **All 20 obligations are CHECKED.**
  - The base lemmas: the indicator bound, the Schur bridge and the double bridge.
  - Every pattern bound, by `lp-certificate-sum`.
  - 17 of 17 patterns are usable.
- **Package.** The theory package replays (`TP.replay`: REPLAYED; a tampered status gives DIFFERS).
  - Package identity: `7f19273f…`.
  - Construction: 267.5 CPU-s; checker CPU reported: 222.7 s.

## What this shows and what it does not

**What it shows.** The procedure ran unchanged on a second target with different objects and a different theorem
family, within a registered adaptation of one module (about 330 lines). Every row it invented is Lean-checked.
This is the procedural transfer step, the counterpart of B20_R46 for C4.

**What it does not show.** That the rows help on sum-free hosts. That is B20_R56.

**Disclosed development probes on hosts.** The builder ran these on scratch copies with a registry built from the
same statements, not from this package:
- The rows tighten the root LP a lot: on denser hosts, from 51 to 46 against an optimum of 45, and from 70 to 64
  against 62.
- Without separation they make node LPs heavy. On six hard hosts at 60 s, the rows tree certified 0 against the
  Schur-only tree's 2.
- B20_R56's design takes this into account.

**Structural caveat (unchanged).** Abstractly, sum-free sets are again the largest subset of a ground set with no
hyperedge of a 3-uniform hypergraph (the Schur triples). The objects and the theorem family differ; the abstract
structure does not. Whether this counts as structurally different for GV6 is the reviewer's decision
(B20R46-OPEN-1).

## Files

- `package.json`: the theory package (modules, statements, proofs, receipts).
- `summary.json`: the generation statistics, patterns, obligations, screen, CPU and code identity.
- `run.log`: the log.

## Tests

- **`tests_formal/test_sf_generator.py` (3).** The package replays and refuses a tampered status. The patterns are
  the generator's and every obligation is CHECKED. The statements are the generator's own texts, and the
  definitions are `cuts_sf.SOURCE`. Every kept pattern tightens the Schur LP.
- **`tests_genesis/test_cuts_sf.py` (7, no Lean).** The domain matches brute force (Schur triples, sum-freeness,
  ex). Copies match brute force. The kept rule holds. Every pattern has an exact rounding certificate. The
  obligations' models are sound, and the statement text is as expected.
