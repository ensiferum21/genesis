# B20_R19 record: generated relational decoders, version v2 (H06 s15.3, W10) — second attempt

- **Run by:** the builder, on DEV. Nothing here is independently reviewed, and nothing licenses a claim.
- **Commits:** `2d35aa9` (setup, pushed before the run) and the result commit that follows it.
- **Evidence:** `evidence/relation_invention_b20r19/` (see its README).

## What changed

`relations.VERSIONS` keeps version v1 exactly as B20_R17 ran it. It adds v2, which differs in two ways:
- **Bound:** the class bound is lifted to 4, by version. The reason is recorded: the v1 space is exhausted.
- **Equivalence:** twin classes are merged before comparing with the menu, so a twin-split of a menu decoder is never NEW. This is stronger than v1's equivalence.

v2 generates three decoders:
- `cross_2`, which is a menu decoder;
- the oriented 3-cycle, already evaluated in B20_R17 and excluded here;
- one new k = 4 decoder, `rel4_0102102330`.

Both of the new decoder's obligations are Lean-checked.

## Result: NO_UTILITY_AFTER_COST

The B20_R17 design was rerun on fresh DEV hosts (32 EVAL).

| Comparison | Mean (edges per host) | 90% interval | Wins / ties / losses |
|---|---|---|---|
| New vs the best menu decoder | +0.125 | [0.03, 0.25] | 3 / 29 / 0 |
| New vs the best time-matched DSL baseline | +0.34 | [−0.09, 0.78] | — |
| New vs the menu decoder with the construction CPU | +0.125 | — | — |

Against the menu, the decoder never loses and the interval excludes 0, but the mean is a quarter of the 0.5 minimum useful effect. Against the DSL baseline the result depends on the setting (S2 +1.63, S3 −0.94).

## Family status

There have been two attempts: B20_R17 (k ≤ 3) and B20_R19 (k ≤ 4). Both produced checked, transportable, machine-generated decoders outside the menu, and neither repays its construction on DEV. The relational family is retired as a utility source on these settings.

The s15.3 acceptance item "prospective utility after construction cost" remains unmet. A next family (partitions/quotients with proved transport, or decompositions) is a separately preregistered step.

## Also in this batch

The requirements ledger was reconciled with the work since B20_R11:
- W05: versioned study rules.
- W10: generated decoders.
- W21: version pointer and rollback.
- W22 and W23: implemented in the recovery work; previously shown as not started.
- GV3 blocker: the E1 design is UNDERPOWERED.
- §4.4 remaining items.
