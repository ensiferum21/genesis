# B20_RX5: proposal headroom over a pipeline grammar (GV4 design step 1, DEV)

- **Script:** `scripts/b20rx5_proposal_pilot.py`, committed as `7adbece` before running.
- **Grammar:** (initialiser, split, finisher), giving 40 pipelines on triangle-free hosts and 25 on C4. The components are the B20_RX3 methods plus the R13 menu.
- **Budget:** 2.0 CPU s per host, children included.
- **Hosts:** the RX3 families with fresh seeds; RX3 and RX3b hosts excluded.
- **Proposers:** fixed enumeration, random sampling and successive halving, all with the same research budget.

## Result

**NO_PROPOSAL_HEADROOM in all three settings.** All 2,730 runs were valid and within budget.

| Setting | Pipelines within 0.5 of the best | Fixed enumeration | Random | Successive halving | ORACLE |
|---|---|---|---|---|---|
| C1 tf n30 p.3 | 25 of 40 | 95.44 | 95.43 | 95.44 | 95.44 |
| C2 tf n40 p.2 | 28 of 40 | 125.00 | 125.02 | 125.00 | 125.06 |
| C3 c4 n30 p.2 | 18 of 25 | 61.06 | 61.16 | 60.69 | 61.50 |

The worst pipelines are plain menu configurations: `rep:ordered_2`, `menu:multistart_tm` and `menu:exchange_tm` with no finisher.

## Reading

Once LP- and SAT-guided components are available as finishers, **good pipelines are plentiful**. Even the fixed enumeration's first few pipelines contain one, and random sampling finds them too. How pipelines are proposed does not matter in this grammar.

The capability gain of B20_RX3/RX3b therefore lives in the **components**, which are builder-written. It does not come from **composing** them.

## Consequence for GV4

Taken together, the DEV pilots narrow the better-improver question:

| Pilots | What they tested | Headroom |
|---|---|---|
| B20_R3, R6, R9 | equational research policies | none |
| B20_R13 | choosing among existing graph configurations | none |
| B20_RX3/RX3b | adding LP/SAT components | +0.6 to +1.4 edges per host, replicated |
| B20_RX5 | composing those components | none |

A better improver in graph construction would therefore have to **produce new components**: for example, discover that the LP relaxation is a good construction order, or invent a representation beyond the menu. That is the invention problem of handoff s15.3 and W22. It is not a search over compositions.

A GV4 study is only worth designing around research processes that propose components. `handoff/gv4/README.md` is updated accordingly.

**Claim ceiling.** These are DEV design diagnostics. They license no claim. Better-improver remains UNESTABLISHED.
