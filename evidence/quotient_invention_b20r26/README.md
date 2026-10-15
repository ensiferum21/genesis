# B20_R26 evidence: quotient representations, attempt 1 of the family (DEV)

Builder-run. Nothing here is independently reviewed, and it licenses no claim.
- **Script:** `scripts/b20r26_quotient_invention.py`, committed before running in `3679ec3`; its
  SHA-256 and that of `invention/quotients.py` were sent to the user beforehand.
- **Log:** `run.log`.
- **Family:** quotient. This is attempt 1. The relational family (B20_R17, B20_R19) is retired.

## The family

For each host, the method builds a quotient:
- a partition q of the vertices into K blocks;
- the exact best pattern Q on the blocks. Q is a relation with no (a,b), (b,c), (a,c), and the
  weight of (a,b) counts host edges u<v from block a to block b. Q is found by branch and bound.

The partition is improved by vertex moves under Q. The lift `QT.lift q Q H` keeps the host edges
whose block pair is in Q, and greedy completion under the domain checker adds what it can.

## Part A (`part_a.json`, `package.json`)

The two obligations are CHECKED in Lean and stated over the repository definitions, for every q,
Q and H:
- `QT.lift q Q H ⊆ H`;
- `GT.TriangleFree Q → GT.TriangleFree (QT.lift q Q H)`, the transport condition.

The package replays from its sources. Construction cost: 29.0 CPU s (checker report 15.3 s).
NEW_CHECKED.

## Part B (`part_b.json`, `part_b_rows.json`, `hosts.json`)

**Hosts.** The B20_R17 design, unchanged, with fresh hosts: S2 (erdos n30 p0.3) and S3 (erdos n40
p0.2), with 8 SELECT and 16 EVAL hosts each. Excluded: 3,437 named hosts. These are every host in
the B20_R13..RX5 evidence, every E1 host, everything in `handoff/e1` and `handoff/e1b`
`exposure_hosts_all.json`, and every B20_R17 and B20_R19 host.

**Budget.** 1.0 CPU s per arm and host.

**SELECT.** quotient_5 was chosen as the new arm, scoring 1,718. That ties the menu decoders
cross_2, adjacent_2 and adjacent_3; quotient_3, _4 and _6 scored 1,714–1,717.

**EVAL** (32 hosts):

| new (quotient_5) minus | mean | 90% interval | by setting (S2 / S3) | W / T / L |
|---|---|---|---|---|
| menu (cross_2) | −0.22 | [−0.38, −0.06] | −0.06 / −0.38 | 1 / 24 / 7 |
| conventional (low_cycle_tm) | −0.03 | [−0.38, 0.31] | +1.06 / −1.13 | 9 / 10 / 13 |
| matched (cross_2, 1.29 s) | −0.28 | [−0.44, −0.16] | −0.13 / −0.44 | 0 / 24 / 8 |

**Verdict: NO_UTILITY_AFTER_COST.** The quotient never beats the menu by the 0.5 minimum useful
effect. Against the menu decoder it is slightly *worse*, and the 90% interval excludes 0.

**Diagnostics** (not part of the verdict):
- the chosen patterns had 10–12 arcs on 5 blocks (12 on 18 hosts);
- the lift decoded 99.8 edges on average, and repair added 7.0 more;
- the per-host pattern optimisation reaches the same values as a fixed bipartition (cross_2).
  On these settings it adds search cost without adding size.

## Family status

One attempt. The representation is new in that its pattern is chosen per host, and it is checked
by one parametric transport theorem. On DEV it has no utility after cost. The family stays open
for a later, separately preregistered attempt, which counts as attempt 2.
