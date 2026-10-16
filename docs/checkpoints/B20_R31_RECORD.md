# B20_R31 record: generated valid inequalities (s15.3 / W10, GV4; relaxation family, attempt 1)

- **Run by:** the builder, on DEV. Nothing here is independently reviewed, and nothing licenses
  a claim.
- **Commits:**
  - `c90f00f` (setup): the family, the script and the unit tests, committed before the run. The
    script's SHA-256 was sent to the user beforehand.
  - The result commit that follows it.
- **Evidence:** `evidence/relaxation_invention_b20r31/`. Its README has the full tables.

## Why

This is NEXT_ACTIONS engineering item 1: a component family with utility. Four representation
attempts in three families had Lean-checked semantics and no DEV utility after cost:
- relational ×2 (retired);
- quotient ×1;
- decomposition ×1.

The B20_R28 re-pilot showed that the LP signal carries E1b's gain. So this attempt invents
components for the LP itself: valid inequalities. It competes with the LP component directly,
not only with the menu.

## What was built

**`invention.cuts`.** A generator over every graph on at most six vertices. It keeps F when "a
triangle-free subgraph has at most ex(F) edges on any copy of F" is not implied by the triangle
rows or the patterns kept before it.
- It keeps K5 (≤ 6) and the 5-wheel (≤ 7).
- It rejects K6 and K6−e, which K5 implies.

**Lean obligations (`PCDefs`).** Four, all screened and CHECKED:
- 0/1 adjacency ≤ 1;
- a triangle bridge;
- one bound per pattern. Each is proved from bridge instances by integer rounding (`omega`),
  for every assignment of the pattern's vertices.

**The component.** The triangle LP plus every copy of the checked patterns, then the B20_RX3
LP-ordered greedy.

## Result

**Part B, utility after cost, on 48 fresh `e1b` hosts:**

| new − … | Mean per host | 90% interval | Passes |
|---|---|---|---|
| plain LP greedy (control) | +0.19 | [+0.06, +0.31] | no (minimum 0.5) |
| menu | +0.98 | — | yes |
| conventional | +3.21 | — | yes |
| matched (control with +0.47 s) | +0.19 | — | no |

**Verdict: NO_UTILITY_AFTER_COST.** The matched arm equals the control on every host.

**Part C, certification diagnostic, float LP, on B20_R30's 90 hosts:**
- The LP floor meets the certified optimum on 82 hosts with the generated rows, against 72 with
  the triangle rows alone.
- The 10 newly met hosts are all among the 18 that the evaluator had to certify with SAT/DRAT.
  They include two of the five hosts that took the evaluator over 100 s, at 126 s and 334 s.
- The mean LP − optimum gap falls from 0.55 to 0.32.

## What it means

- **As a construction component:** a small, consistent gain over the LP it strengthens (+0.19,
  interval above 0), below the minimum useful effect. This is attempt 1 of the relaxation family,
  and it counts.
- **As a certification component:** a promising diagnostic, not yet a result. Two things are
  missing:
  - an exact route that verifies the LP dual over the generated rows in rational arithmetic;
  - a preregistered measurement on fresh hosts.

  The rows' validity is already Lean-checked. Building and measuring that route is B20_R32.
- **For GV4:** the family invents components of a kind the improver was not handed: new LP rows
  with machine-checked validity. Whether certification benefits count toward GV4 is a design
  question for the reviewer of `handoff/gv4/README.md`. GV4 asks for better *successor solvers*.

## Exposure

B20_R30 and B20_R31 named 168 new DEV hosts, all in the `e1b` settings:
- B20_R30's 90 hosts;
- B20_R31's 72 study hosts;
- B20_R31's six development-look hosts, recorded in `development_look_hosts.json`.

`scripts/exposure_addendum.py b20r31` lists them in `handoff/e1*/exposure_hosts_addendum_b20r31.json`.
Both handoff READMEs now tell a custodian to list every exposure file. The frozen package files
are unchanged.

## Tests

| Test file | Tests | What they check |
|---|---|---|
| `tests_genesis/test_cuts.py` | 8 | the generator's kept and rejected patterns; extremal numbers; bounds on random triangle-free sets; copies; the component's budget and witnesses |
| `tests_formal/test_relaxation_invention.py` | 5 | the package replays; the verdict and Part C follow from the rows; the hosts are fresh and in the addenda |
| `tests_genesis/test_certification_budget.py` | 5 | B20_R30's record |

## Open

- **B20R31-OPEN-1 (new):** the relaxation family, attempt 1, NO_UTILITY_AFTER_COST in
  construction, with a certification signal.
- **B20R9-OPEN-1:** updated.
