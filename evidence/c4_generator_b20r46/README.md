# B20_R46 evidence: the row-invention procedure transferred to C4-free subgraphs (generator and Lean checks; DEV)

Builder-run. Nothing here is independently reviewed. It licenses no claim and changes no
evaluator.
- **Script:** `scripts/b20r46_c4_generator.py`. It was committed before running in `9413087`, and
  its SHA-256 was sent to the user beforehand.
- **Code:** `src/genesis/invention/cuts_c4.py`. This is the adaptation: about 300 lines, of which the
  search and the kept rule are generator v2's.
- **Log:** `run.log`, 1,458 s, in one go. The code identity it records (`94eed072…`) is that of the
  setup commit.
- **Files:**
  - `package.json`: the theory package (37 statements, 41 modules), `package_sha256` `7a081e4a…`;
  - `summary.json`: counts, per-pattern LP values, statuses and the screen.

## Why

The clearest thing the system has invented so far is a *procedure*:
1. enumerate small graphs;
2. keep those whose LP exceeds their extremal number;
3. prove each bound in Lean from the LP's own dual.

In the triangle-free domain it produced the rows that make dense hosts certifiable (B20_R35, R37,
R41). GV6 asks whether a learned capability helps in a structurally different domain within a
registered adaptation budget. This step asks the narrower question first: does the procedure itself
carry over, with only its motif-specific parts changed? The motif-specific parts are:
- 4-cycle rows with 3 on the right;
- a Lean bridge lemma with the distinctness that `G4.C4Free` needs;
- pattern statements over pairwise-distinct vertices.

## Generation

It searched every graph on 4–6 vertices (201 graphs). Of these:
- 48 are connected with every edge in a 4-cycle;
- 10 are implied by the 4-cycle rows;
- 4 are implied by earlier patterns;
- **34 are kept.**

The kept patterns include:

| Pattern | ex(F) | LP, 4-cycle rows | LP, with earlier patterns |
|---|---|---|---|
| K4 | 4 | 4.5 | 4.5 |
| K_{2,3} | 4 | 4.5 | 4.5 |
| K5 | 6 | 7.5 | 6.67 |
| K_{2,4} | 5 | 6.0 | 5.33 |
| K6 | 7 | **11.25** | **7.5** |

The other 29 are 6-vertex graphs with 9 to 14 edges, each with ex(F) = 7.

ex(F) comes from HiGHS's MILP, and each value was re-checked as a C4-free subset. The unit tests
check every value on up to 5 vertices against exhaustive search.

## Lean

- **Screen.** All 37 obligations were screened by sampling against their Python models. No
  counterexample was found.
- **Checks.** All 37 are CHECKED.
- **Base lemmas.** Each was proved by its own recipe:
  - `p4_adj_le_one`, by `adj-split`;
  - `p4_adj_comm`, by `comm-or-swap`;
  - `p4_bridge`, the 4-cycle bridge with distinct opposite vertices, by `c4-bridge-verts`.
- **Pattern bounds.** All 34 were proved by `lp-certificate-sum`, the integer rounding certificate
  from the pattern's LP dual: scaled instances of the bridge and of earlier bounds, summed, then
  `omega`.
- **Heartbeats.** The four largest patterns (P4P34–P4P37: two with 13 edges, the 14-edge pattern and
  K6) need more elaboration than the default budget. As in B20_R37, their recipe places
  `set_option maxHeartbeats 4000000 in` before the theorem.

**Cost.** Construction 1,366.6 CPU s; the checker reported 1,006.0 s.

**Statements.** Each says "for every C4-free edge set S and every injective assignment of the
pattern's vertices, the adjacency sum over the pattern's edges is at most ex(F)". The package's
definitions are:
- the trusted `GTDefs`;
- B18's `G4Defs` (the c4_host_v2 contract's `G4.C4Free`);
- `P4Defs`, the 0/1 adjacency `P4.adj`.

## What it means

The procedure transferred: the same search, kept rule and proof method produce Lean-checked bounds in
a domain whose motif, bridge lemma and distinctness conditions all differ. The rows are much stronger
than the evaluator's 4-cycle rows on dense patterns (K6: 11.25 → 7.5, against ex = 7).

Whether they are *useful* on C4 hosts is a separate, prospective question. B20_R47 asks it as a
certification-coverage study, with its own exact checker.

## Tests

- `tests_genesis/test_cuts_c4.py` (4): the generator, the rounding certificates, the screen and the
  recipes.
- `tests_formal/test_c4_generator.py` (3) checks:
  - that the package replays (REPLAYED), and that a tampered package DIFFERS;
  - that its patterns are the generator's, that the usable list is exactly the CHECKED patterns, and
    that every statement is the generator's own text;
  - that every kept pattern beats both the 4-cycle LP and the LP with earlier patterns.
