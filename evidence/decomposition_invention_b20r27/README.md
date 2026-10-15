# B20_R27 evidence: decompositions with verified witness composition, attempt 1 of the family (DEV)

Builder-run. Nothing here is independently reviewed, and it licenses no claim.
- **Script:** `scripts/b20r27_decomposition_invention.py`, committed before running in `fb1703f`;
  its SHA-256 and that of `invention/decompositions.py` were sent to the user beforehand.
- **Log:** `run.log`.
- **Family:** decomposition. This is attempt 1.

## The family

A decomposition works in four steps:
1. A balanced m-way vertex partition, with cut-reducing swaps.
2. Each induced part is solved by the B20_RX3 exact components: LP-ordered greedy, then CaDiCaL
   climbing.
3. The part witnesses are composed.
4. The cut edges are repaired greedily under the domain checker.

## Part A (`part_a.json`, `package.json`)

`decomposition_union` is CHECKED in Lean:
`GT.TriangleFree S → GT.TriangleFree T → (vertex-disjoint) → GT.TriangleFree (S ∪ T)`.
Construction cost: 18.0 CPU s. NEW_CHECKED.

## Part B (`part_b.json`, `part_b_rows.json`, `hosts.json`)

**Hosts.** The B20_R17 design with fresh hosts. Excluded: 3,488 named hosts. These are
everything B20_R26 excluded, B20_R26's own hosts, and the three hosts the builder looked at
during development.

**Budget.** 1.0 CPU s per arm, children included.

**The added control.** `whole` runs the same exact components on the whole host. That
separates the decomposition from the components, which are an existing capability.

**SELECT.** decomp_2 scored 1,723 and decomp_3/4 1,718–1,719. The menu decoders scored up to
1,749 (adjacent_2) and low_cycle_tm 1,743.

**EVAL** (32 hosts):

| decomp_2 minus | mean | 90% interval | W / T / L |
|---|---|---|---|
| whole (same components, whole host) | **−2.53** | [−2.97, −2.13] | 0 / 3 / 29 |
| menu (adjacent_2) | −1.25 | [−1.66, −0.84] | 3 / 7 / 22 |
| conventional (low_cycle_tm) | −1.31 | [−1.84, −0.81] | 4 / 8 / 20 |
| matched (adjacent_2, 1.18 s) | −1.25 | [−1.66, −0.84] | 3 / 7 / 22 |

**Verdict: NO_UTILITY_AFTER_COST.**

**Why** (diagnostics, not part of the verdict):
- **Parts.** All 64 parts were solved to optimality: CaDiCaL returned UNSAT for one more edge.
- **The cut.** The balanced 2-way cut still crosses 46.4 edges on average. Composition keeps
  74.1 edges, and repair recovers only part of the cut: 106.2 in the end.
- **The whole host.** The same components on the whole host reach more edges in the same second,
  even though their SAT climb times out on 27 of 32 hosts.
- **Optimality inside parts does not pay** for the cut edges a decomposition gives up. A side
  observation: `whole` beats the menu decoder by +1.28 per host, consistent with B20_RX3's
  capability headroom from the components.

## Family status

One attempt, and NO_UTILITY_AFTER_COST. The balanced vertex partition is the weak point: the
motif hypergraph is essentially one component (the B20_RX1 H06 design probe found 90–96% of the
edges in the largest component). A further attempt would need a decomposition that keeps the cut
small, or one that solves the cut jointly.
