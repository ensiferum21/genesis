# B20_R45 record: E1d's ablation evaluation rehearsed through the v5 custody path (SUPPORTED, judge agrees)

- **Run by:** the builder, on DEV, with fixture keys. Nothing here licenses a claim.
- **Commits:**
  - `5981c21` (setup), committed before the run. Its SHA-256 was sent to the user beforehand.
  - The result commit that follows it.
- **Evidence:** `evidence/e1d_ablation_rehearsal_b20r45/`.

## Why

A causal level (ABLATION_SUPPORTED) is licensed only by a custodian-signed evaluation of evidence kind
`ablation`. B20_R44 showed the effect on DEV. This step runs the custody path for that evidence kind
once.

## Result

| Item | Result |
|---|---|
| Request | v5 ablation request; baseline = the registered ablation (`cross_2` → `ordered_2`), re-checked by the custodian |
| Panel | 45 CONFIRM hosts (the power choice, recomputed for the ablation plan); 44 certified |
| Wins / losses / ties | **44 / 0 / 0** |
| Estimate | **+6.64 per host** [6.03, 7.29] |
| Cost ratio | 1.00 |
| Outcome | **SUPPORTED** |
| `judge.recompute` | agrees |

## What it means

On DEV, every piece of E1d's GV3 evidence has now been carried through the opt-in v5 custody path:
- utility against an exact MIP at four times the budget (B20_R43);
- causal attribution to the discovered representation (B20_R44, and this rehearsal).

What remains is external:
- the reviewer's adoption decisions (B20R41-OPEN-1, B20R44-OPEN-1, B20R35-OPEN-1, B20R40-OPEN-1);
- a statistician;
- an independent custodian.

## A design point found before the run

A power analysis is bound to its plan core, and the custodian's hypothesis family is part of that core.
An ablation plan therefore needs its own power analysis, recomputed from the same pilot rows. A design
test caught this before the run, and the script recomputes it.

## Tests

`tests_genesis/test_e1d_ablation_rehearsal.py` (3) checks:
- the ablation plan's family, and that its decision record is clean against its recomputed power;
- that the rehearsal went through v5 with kind `ablation`: the arms, route, rows, judge and log;
- that the hosts are fresh and in the addenda.

## Open

B20R41-OPEN-1 is updated.
