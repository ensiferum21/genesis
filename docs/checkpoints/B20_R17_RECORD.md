# B20_R17 record: a machine-generated representation outside the menu (H06 s15.3, W10)

- **Run by:** the builder, on DEV. Nothing here is independently reviewed, and nothing licenses a claim.
- **Commits:** `14c77be` (setup: generator, tests, script; pushed before the run) and the result commit that follows it.
- **Evidence:** `evidence/relation_invention_b20r17/` (see its README).

## What was built

`src/genesis/invention/relations.py` adds one new representation family, generated rather than hand-listed: **oriented relational decoders**, decode_R c H = {(u, v) ∈ H : (c u, c v) ∈ R} over k ≤ 3 classes. k ≤ 3 is the grammar's existing bound, and it was not lifted.

The generator works in four steps:
1. It enumerates every relation.
2. It keeps the exactly sound ones. Triangle-free soundness holds exactly when no x, y, z have R x y ∧ R y z ∧ R x z; a test checks this against exhaustive decoding.
3. It keeps the inclusion-maximal ones.
4. It reduces symmetry (one representative per class-relabelling orbit, after unused classes are removed) and compares the result with the menu.

Lean definitions and obligations are generated too. `representations.represent_and_repair` runs the decoders unchanged.

## Result

**Part A.** Three decoders were generated:
- `rel2_0110` (= `cross_2` = `adjacent_2`);
- `rel3_01021020` (= `adjacent_3`);
- `rel3_011220`, the oriented 3-cycle. This one is **NEW**.

All six obligations (image, triangle-free soundness) are CHECKED in Lean. Construction cost: 64.3 CPU s.

**Part B: NO_UTILITY_AFTER_COST.** This used fresh DEV hosts of S2 and S3, 32 for evaluation, at 1.0 CPU s per arm. The new decoder against:
- the best menu decoder (`adjacent_3`): **+0.19**, interval [−0.03, 0.44];
- the best time-matched DSL baseline (`low_cycle_tm`): **−0.03**, interval [−0.41, 0.34];
- the menu decoder with the construction CPU amortised over 100 hosts: **+0.16**, interval [−0.06, 0.41].

None reaches the 0.5 minimum useful effect.

## Against the s15.3 acceptance

| Requirement | Status |
|---|---|
| A machine-generated representation outside the hard-coded menu | met (`rel3_011220`) |
| Checked semantics | met (Lean: image and soundness) |
| A valid decoder/transport path | met (image + soundness theorems; checker re-validation) |
| Prospective utility after construction cost | **not met** (DEV, fair, preserved) |

Following the declared policy, relational decoders at k ≤ 3 are retired as a utility source on these settings. A next family is a new, separately preregistered step, and all attempts count. Candidates are:
- a versioned k ≤ 4 expansion, whose two NEW maximal oriented relations are already enumerable;
- partitions/quotients with proved transport;
- decompositions.

## Tests

- `tests_genesis/test_relations.py` (6): exact soundness equals exhaustive decoding; random-host soundness; invariances; the generator output and novelty; the bounds; and the method's valid witness.
- `tests_formal/test_relation_invention.py` (3): the package replays from its sources; the record matches the code; the verdict follows from the rows.
