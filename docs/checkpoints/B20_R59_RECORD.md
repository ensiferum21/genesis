# B20_R59 record: B20_R57's certification utility does not replicate; its bound utility does

- **Built and run by:** the builder. DEV, internal replication.
- **Setup commit:** `02415a8`.
- **Evidence:** `evidence/sf_replication_b20r59/`.

## Result: **NOT_REPLICATED**

The protocol is B20_R57's, on fresh seeds.

| | Result |
|---|---|
| Certified | a 21, c 23 |
| Certified by one route only | 0/2 (McNemar p 0.25) |
| Wall saving | +2.76 s [0.04, 5.37] |
| Certified bound | **+3.875 [2.675, 5.125]: BOUND_UTILITY replicates** |

The sample was easier for route a than B20_R57's (21 vs 14 of 40 certified).

## Disclosed

The run was interrupted once by disk exhaustion at host 23 and resumed from its saved rows.

## Consequence

- **What stands.** The sum-free transfer's robust result is stronger certified bounds, in both B20_R57 and R59.
- **What does not.** More certified optima: B20_R57's coverage effect did not replicate.

The GV6 draft, the review brief, the handover and B20R46-OPEN-1 are updated accordingly. The false-discovery entry
for B20_R57 stands as one attempt; its replication failed and is reported next to it.
