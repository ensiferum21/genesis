# B20_R19: generated relational decoders, version v2 (k ≤ 4, twins merged). Verdict: NO_UTILITY_AFTER_COST

- **Script:** `scripts/b20r19_relation_invention_v2.py`, committed and pushed as `2d35aa9` before it ran.
- **Generator:** version `v2` in `src/genesis/invention/relations.py`.
- **Run:** 13 Oct 2026, 351 s. DEV only; licenses no claim.
- **Family history:** this is the second attempt in the family, after B20_R17. Both count.

## Part A (`package.json`, `part_a.json`)

Version v2 lifts the class bound to 4, by version and with the reason recorded, and merges twin classes before comparing with the menu. It generated:

| Decoder | Relation | Status | Lean: image / soundness |
|---|---|---|---|
| `rel2_0110` | 0↔1 | equals cross_2 = adjacent_2 = adjacent_3 (after twin merging) | CHECKED / CHECKED |
| `rel3_011220` | 0→1→2→0 | evaluated in B20_R17, excluded here | CHECKED / CHECKED |
| `rel4_0102102330` | 0→1, 0→2, 1→0, 2→3, 3→0 | **NEW** | CHECKED / CHECKED |

Construction cost charged: 63.6 CPU s (the checker reported 44 s).

## Part B (`part_b.json`, `part_b_rows.json`, `hosts.json`)

The B20_R17 design was kept unchanged except for fresh seeds (20262201 and 20262202; bootstrap 20262299) and one more exclusion: B20_R17's hosts. That gives 32 EVAL hosts of S2 and S3, at 1.0 CPU s per arm. The matched arm had 1.64 s.

**SELECT totals** (16 hosts):

| Arm | Total |
|---|---|
| new `rel4_0102102330` | 1771 |
| menu `adjacent_3` | 1771 (chosen) |
| menu `adjacent_2` | 1771 |
| menu `cross_2` | 1770 |
| menu `ordered_2` | 1673 |
| `low_cycle_tm` | 1780 (chosen) |
| `multistart_tm` | 1740 |
| `exchange_tm` | 1725 |

**EVAL** (new minus the other arm, edges per host):

| Comparison | Mean | 90% interval | S2 / S3 | Wins / ties / losses | Passes |
|---|---|---|---|---|---|
| new − menu | +0.125 | [0.03, 0.25] | +0.19 / +0.06 | 3 / 29 / 0 | no (below 0.5) |
| new − conventional | +0.34 | [−0.09, 0.78] | +1.63 / −0.94 | 10 / 10 / 12 | no |
| new − matched | +0.125 | [0.03, 0.25] | +0.19 / +0.06 | 3 / 29 / 0 | no (below 0.5) |

## Reading

The new decoder never loses to the best menu decoder, and wins on 3 of 32 hosts. That is a real but small difference: the interval excludes 0, but the mean is a quarter of the 0.5 minimum useful effect. Against the conventional baseline it depends on the setting, as in B20_R17 (better on S2, worse on S3).

Two attempts in this family (B20_R17, B20_R19) found checked, transportable decoders that do not repay their construction on DEV. The family is retired as a utility source on these settings. A next s15.3 family (partitions/quotients, decompositions) is a separately preregistered step.
