# B20_RX3b: fresh-seed replication of the capability pilot (DEV)

- **Script:** `scripts/b20rx3_capability_pilot.py --replication`. The replication mode was committed as `76aa47d` before any replication host existed.
- **What changed:** only the generator seeds (20261601+); every host of the first run was excluded.
- **What stayed the same:** the design, budgets and verdict rule of B20_RX3.

## Result: replicated

**DEPLOYABLE_CAPABILITY_HEADROOM in all three settings again.** All 2,236 runs were valid and within budget.

| Setting | First run (RX3): SH[all] − best menu-only | Replication: SH[all] − best menu-only | 90% bootstrap (replication) | Random proposals over menu + new − best menu-only |
|---|---|---|---|---|
| C1 tf n30 p.3 | +1.25 [0.81, 1.69] | **+0.88** | [0.50, 1.25] | +0.25 |
| C2 tf n40 p.2 | +0.75 [0.44, 1.06] | **+0.63** | [0.31, 0.94] | −0.27 |
| C3 c4 n30 p.2 | +0.81 [0.50, 1.13] | **+1.38** | [1.00, 1.75] | +0.99 |

Successive halving over the enlarged space picks an LP-based method every time: `lp_greedy`, or `lp_greedy+sat_25_75` on C4.

## Reading

**The capability effect replicates.** At matched CPU per host and matched research budgets, making LP- and SAT-guided construction available is worth about +0.6 to +1.4 edges per host on these families.

**Two observations matter for the GV4 design.**
1. **How methods are proposed matters.** Random proposals over the enlarged space do not reliably find the good methods (−0.27 on C2), but an adaptive proposer (successive halving) does. A GV4 study should compare proposers, not only method spaces.
2. **The good methods were handed over.** The components are builder-written and the improver only selected among them. Producing the methods is the open question (`handoff/gv4/README.md`).

**Claim ceiling.** These are DEV design diagnostics. They license no claim. Better-improver remains UNESTABLISHED.
