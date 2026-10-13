# B20_R22: retention and negative transfer on a real DEV campaign lineage (demonstration)

- **Script:** `scripts/b20r22_retention_demo.py`, committed before it ran. Its rules are in the docstring.
- **Module:** `src/genesis/retention.py`.
- **Run:** 13 Oct 2026, 90 s. DEV only; it licenses no claim and moves no pointer.

## What was done

1. A c4_host_v2 DEV campaign was initialised (seed 20262301, 4 generations).
2. Before it ran, a **PROTECTED** retention protocol was frozen in its store:
   - `legacy`: 16 c4 hosts, erdos n12 p0.4 and bipartite n12 p0.5;
   - `transfer`: 8 triangle-free erdos n12 p0.45 hosts;
   - margin 0.5, 90% interval, budget 5.
3. The tasks live only in a private 0700 root, which is not published here. The store holds salted commitments.
4. After the run, each forward step of the active-version pointer was measured once, and so was the initial version against the final one.

## Result (`summary.json`)

| Step | Solver change | legacy (c4) | transfer (triangle-free) | Verdict |
|---|---|---|---|---|
| initial → g0 | `exchange` turned on | −0.25 [−0.50, 0.00], 1/10/5 | **−0.625 [−1.00, −0.25]**, 0/4/4 | **NEGATIVE_TRANSFER** |
| g0 → g1, g1 → g2, g2 → g3 | none (only the tool library grew) | 0.00, 0/16/0 | 0.00, 0/8/0 | RETAINED |
| initial → g3 (cumulative) | — | −0.25 [−0.50, 0.00] | **−0.625 [−1.00, −0.25]** | **NEGATIVE_TRANSFER** |

Each panel cell gives the mean, the 90% interval, and wins / ties / losses.

## Reading

- The campaign's first DEV-retained change (local exchange moves) was retained because of the public c4 SELECT panel. It costs edges on triangle-free hosts the research never targeted, and it is no gain on easier legacy c4 hosts.
- Under the protocol this is NEGATIVE_TRANSFER, which is evidence for a rollback decision (`versions.rollback`). Nothing was rolled back here: the decision belongs to an operator, and on a DEV demonstration nothing is at stake.
- Later generations changed no solver, so their measurements tie exactly.
- Each pair was measured once, and 5 of the 5 budgeted measurements are used. The protected material has now been used up, so it will not be measured again.
