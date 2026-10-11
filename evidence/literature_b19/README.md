# B19 / W17 evidence: literature, priority and faithful formalization

Builder-generated, DEV material. Nothing here was reviewed independently, and nothing
here claims novelty.

## Inputs

- `retrieved/S1…S5_*.json`. The builder fetched these through its web tools on
  2026-10-11. Each file stores the tool's output exactly as received, together with the
  request (URL and prompt) and the time. The time is recorded to the minute.
- `retrieved/searches.json`. The four web searches (Q1–Q4) and the result lists they
  returned.
- The pinned Mathlib sources of the formal workspace, revision `d13f23b7…`. They are read
  directly, so these sources are VERBATIM.

The fetch tool excerpts and sometimes summarises; S4 and S5 say so in their own text.
Quotes from S1–S5 are therefore marked TOOL_SUMMARIZED with `quote_confirmed: false`.
A person must confirm them against the originals (ADJ-1).

## Records (`records/`)

| File | Content |
|---|---|
| `sources.json` | 5 retrieved and 2 library sources. Each has its text, SHA-256, fidelity, provenance and injection screen. None is quarantined. |
| `claims.json` | 8 claims. Each quote occurs in its source text exactly; offsets are recorded. Notation is resolved against `genesis.literature.NOTATION`. |
| `links.json` | 7 links (kinds below) and the Lean receipt. |
| `ambiguity.json` | 3 ambiguity records with distinguishing instances. |
| `adjudication_queue.json` | 4 questions for a person. All are PENDING_HUMAN. |
| `novelty.json` | 4 scoped novelty reports, with the searches they rest on. |

### Links

| Claim | Genesis side | Kind | Check |
|---|---|---|---|
| L1 Mathlib `Antitone` | `∀ P, RC.C0 P ↔ Antitone P` | EXACT | Lean theorem, CHECKED |
| L2 Mathlib lower set | `∀ P, RC.C0 P ↔ IsLowerSet {x \| P x}` | EXACT | Lean theorem, CHECKED |
| C2 monotone graph property (Alon–Shapira) | RC.C0 for isomorphism-invariant predicates | SPECIALIZATION | Both readings agree on every edge subset of K4, for 6 predicates |
| C3 every graph has a cut with ≥ m/2 edges | B18 `cross_2` representation | EXACT | Brute force on 60 random small graphs |
| C1 τ ≤ 2ν* (Krivelevich, via S1) | B19 LP certificate bound ⌊m − ν*⌋ | CONTEXT | Our readings of τ and ν* satisfy the quoted theorem on 60 random small graphs; the certificate bound is ≥ the optimum |
| C4, C5 ETP and Duper | B19 W16 Lean replay of E proofs | CONTEXT | none (prior work) |

The Lean links are compiled in the sandbox: GTDefs, HSDefs and RCDefs from the B18
package, a trusted statement module, and an untrusted proof module. The check stage binds
each proof to its statement and audits axioms.

### Ambiguities

- **"monotone".** Material. Alon–Shapira's monotone property is down-closed. In
  Mathlib, `Monotone` means order-preserving, and the down-closed predicate is called
  `Antitone`. The two readings differ on "bipartite".
- **"C4-free".** Material. Genesis means no 4-cycle subgraph, not no induced 4-cycle.
  K4 minus one edge separates the two readings.
- **"at least m/2".** Immaterial for integer cut sizes on the tested graphs.

### Novelty reports

Every report concludes **PRIOR_ART_FOUND**:

- **B18 concept.** The B18 recovered concept equals lower sets / `Antitone` predicates
  (Lean-checked), and is a monotone graph property.
- **B19 LP certificates.** Their mathematics is weak LP duality for fractional triangle
  packing and cover.
- **B18 cut representation.** This is the classical m/2 cut bound.
- **W16 replay.** Validating automated proofs in Lean, and reconstructing superposition
  proofs, are prior work (ETP, Duper).

The search record for each report is small: one or two web searches, one or two sources
read, and exact-text searches of pinned Mathlib. Every report carries the disclaimer
that absence of a hit proves nothing. Independent review is PENDING for all of them.

## Reproduce

```
GENESIS_TOOLCHAIN=… PYTHONPATH=src python3 scripts/b19_literature.py /tmp/lit
python3 -m unittest tests_genesis.test_literature
```
