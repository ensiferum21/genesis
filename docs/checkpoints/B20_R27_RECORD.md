# B20_R27 record: decompositions with verified witness composition (s15.3, W10) — family attempt 1

- **Run by:** the builder, on DEV. Nothing here is independently reviewed, and nothing licenses
  a claim.
- **Commits:** `fb1703f` (setup: family, tests and script, committed before the run; SHA-256s
  sent to the user beforehand) and the result commit that follows it.
- **Evidence:** `evidence/decomposition_invention_b20r27/` (see its README).

## What was built

`src/genesis/invention/decompositions.py`:
- a balanced m-way vertex partition with cut-reducing swaps;
- induced part tasks, each solved by the B20_RX3 exact components (LP-ordered greedy, then
  CaDiCaL climbing);
- vertex-disjoint composition;
- greedy repair of the cut edges.

CPU is charged with children (`discovery.construct.Budget`). A `whole` control runs the same
components on the whole host at the same budget.

**Lean.** One composition obligation, proved once for all edge sets: vertex-disjoint
triangle-free edge sets have a triangle-free union. It is CHECKED, by case analysis and `omega`.

## Result

**Part A: NEW_CHECKED.** Construction cost was 18.0 CPU s.

**Part B: NO_UTILITY_AFTER_COST**, on 32 fresh EVAL hosts with 3,488 named hosts excluded.
decomp_2 against:
- whole: **−2.53**, 90% interval [−2.97, −2.13]
- the menu decoder adjacent_2: −1.25, interval [−1.66, −0.84]
- low_cycle_tm: −1.31, interval [−1.84, −0.81]
- matched: −1.25, interval [−1.66, −0.84]

Every part was solved to optimality. Even so, the cut (46 of about 152 edges) costs more than
exact parts recover.

**Disclosure.** Before preregistration, the builder looked at three DEV hosts (decomposition 3–5
below `whole`). They were excluded, and the design was not changed.

## Against the s15.3 acceptance

| Requirement | Status |
|---|---|
| A machine-generated representation outside the menu | met (each host's decomposition is generated) |
| Checked semantics / transport | met (Lean composition theorem; checker re-validation) |
| Prospective utility after construction cost | **not met** (DEV, fair, preserved) |

## Tests

- `tests_genesis/test_decompositions.py` (6): the partition is balanced and never worse than
  its start; induced part tasks; the composition model, including that an overlap breaks it;
  the obligation; witness validity and bounds.
- `tests_formal/test_decomposition_invention.py` (3): the package replays and tampering is
  detected; the verdict follows from the rows, including the `whole` control; the hosts are
  fresh.

## Open

B20R27-OPEN-1: the decomposition family has one attempt and NO_UTILITY_AFTER_COST, with a
balanced vertex partition as the weak point.

After B20_R17, R19, R26 and R27, four representation attempts across three families have
checked semantics, and none has prospective DEV utility after cost. The GV4 study design
(`handoff/gv4`) is therefore still waiting on a component family with utility.
