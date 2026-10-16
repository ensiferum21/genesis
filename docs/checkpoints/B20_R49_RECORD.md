# B20_R49 record: the transferred rows are responsible for the tree route's utility (ROWS_RESPONSIBLE)

- **Run by:** the builder, on DEV. Nothing here licenses a claim, and no evaluator was changed.
- **Commits:**
  - `c6eae14` (setup): the script and its design tests, committed before the run. The SHA-256 was sent
    to the user beforehand.
  - The result commit that follows it.
- **Evidence:** `evidence/c4_rows_ablation_b20r49/`.

## Why

B20_R48's tree route adds a builder-written method, branching, to the rows the system invented.
A transfer claim needs the utility to come from the invented component.

## Result

40 fresh C4 hosts at 60 s, same route and checker:

| Item | With B20_R46's rows | Ablation (4-cycle rows only) |
|---|---|---|
| Certified | **36/40** | 24/40 |
| Certified by one arm only | **12** | 0 |
| Search nodes | 13,294 | 186,574 |

- **McNemar:** p = 0.00024.
- **Wall saving:** +19.6 s per host [14.2, 25.3].
- **Soundness:** every certificate of both arms VALID.
- **Verdict: ROWS_RESPONSIBLE.**

## What it means

The preregistered chain B20_R46 → R49 shows, on DEV, a system-invented and Lean-checked component
whose transfer to a near domain causes a certification utility there. GV6 still needs a structurally
different formal domain.

## Tests

`tests_genesis/test_c4_rows_ablation.py` (6).

## Open

B20R46-OPEN-1 and B20R48-OPEN-1 are updated: the utility is attributable to the transferred rows.
