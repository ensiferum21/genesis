# B20_R46 record: the row-invention procedure transferred to C4-free subgraphs (34 patterns, all Lean-CHECKED)

- **Run by:** the builder, on DEV. Nothing here is independently reviewed, and nothing licenses a
  claim. No evaluator was changed.
- **Commits:**
  - `9413087` (setup): `invention/cuts_c4.py`, the script and the unit tests. All were committed
    before the run, and the SHA-256s were sent to the user beforehand.
  - The result commit that follows it.
- **Evidence:** `evidence/c4_generator_b20r46/`.

## Why

GV6 asks for meaningful transfer to a structurally different domain. The system's clearest
invention is a procedure: generate small-graph inequalities whose LP beats their extremal number,
and prove each one in Lean from the LP's dual. In the triangle-free domain it made dense hosts
certifiable (B20_R35, R37, R41).

The C4-free domain (c4_host_v2) is where the evaluator is weakest. Its LP over 4-cycle rows gives
11.25 on K6, against ex = 7. That is why no C4 setting could be calibrated under e1-hard-v2, and
why B20_R23's C4 causal pilot was UNSETTLED_REFERENCE.

## Result

| Item | Result |
|---|---|
| Graphs searched (4–6 vertices) | 201; 48 connected and cycle-covered |
| Implied by 4-cycle rows / by earlier patterns | 10 / 4 |
| **Kept** | **34**: among them K4 (4), K_{2,3} (4), K5 (6), K_{2,4} (5), K6 (7) |
| Screen | 0 counterexamples among 37 obligations |
| **Lean** | **37/37 CHECKED**: 3 base lemmas, 34 bounds by integer rounding certificates |
| K6 LP | 11.25 with 4-cycle rows → 7.5 with the earlier patterns |
| Construction | 1,366.6 CPU s (checker 1,006.0 s) |

The adaptation was registered before running: one module, about 300 lines. Its search and kept
rule are generator v2's unchanged. The motif-specific parts are the 4-cycle rows, the bridge lemma
with distinct opposite vertices, and statements over pairwise-distinct vertices.

## What it means

The procedure carries over to a structurally different motif with a registered adaptation. This is
transfer of the *procedure*, not yet of *utility*. B20_R47 measures utility prospectively: whether
these rows give the C4 evaluator a certification advantage.

## Tests

- `tests_genesis/test_cuts_c4.py` (4).
- `tests_formal/test_c4_generator.py` (3): replay, statuses and statement texts, LP strength.

## Open

B20R46-OPEN-1 (new): whether this counts toward GV6's "meaningful transfer", and what adaptation
budget a reviewer accepts. It is evidence of procedural transfer only; utility is B20_R47.
