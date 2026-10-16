# B20_R33 record: strong-baseline audit of E1 and E1b (GV3; B20R32-OPEN-2)

- **Run by:** the builder, on DEV. Nothing here is independently reviewed, and nothing licenses
  a claim. No package or comparator was changed.
- **Commits:**
  - `b03e429` (setup): the script, committed before the run; its SHA-256 was sent to the user
    beforehand.
  - The result commit that follows.
- **Evidence:** `evidence/strong_baseline_audit_b20r33/`.

## Why

B20_R32's post-hoc MILP cross-check showed that HiGHS proves the optimum of the hardest `e1b`
hosts in under a second. E1 and E1b compare their candidates only with time-matched fixed DSL
programs. GV3 asks for help "beyond strong baselines". This step measures an exact MIP arm at
each candidate's own budget, against the frozen descriptors, on fresh hosts.

## Result

60 fresh `e1b`/`e1-v2` hosts, all certified by the evaluator's reference. The MIP arm proved
optimality on every host, with at most 0.36 CPU s, on one pinned core.

| Study | MIP − candidate | Candidate − best DSL baseline | Candidate at optimum | Verdict |
|---|---|---|---|---|
| E1 (0.5 s) | +0.75 [+0.58, +0.92], never below | +2.08 | 27/60 | **MIP_DOMINATES** |
| E1b (2.0 s) | +0.20 [+0.12, +0.30], never below | +2.27 | 49/60 | **NO_MATERIAL_DIFFERENCE** |

## What it means for GV3

Both candidates really do beat their DSL comparators, by about 2 edges per host.

On the decided family, however, an off-the-shelf exact solver is always optimal, so no candidate
can beat it:
- E1 is dominated by it;
- E1b is within 0.2 edges of it, below the minimum useful effect.

A SUPPORTED E1 or E1b outcome would therefore be a better-solver statement against time-matched
DSL baselines only. That is the packages' present scope, and it is not "beyond strong
baselines".

This is a decision for the reviewer and Daniel, recorded as B20R33-OPEN-1, with three options:
1. accept the narrower scope;
2. add a MIP comparator, which E1 would fail and E1b could at best tie;
3. look for settings where an exact solver does not finish within the candidate's budget but
   the evaluator still certifies.

The third option runs into the 200-edge bound on SAT certificates (`CERTIFICATE_MAX_EDGES`).
Whether such settings exist is an open DEV question. A calibration probe for it would be the
next step, if wanted.

## Tests

`tests_genesis/test_strong_baseline_audit.py` (4 tests) checks:
- the arms are the frozen descriptors;
- the contrasts and verdicts follow from the rows;
- no arm exceeds a certified optimum, and the overrun flags are right;
- the hosts are fresh and listed in the addenda.

## Open

**B20R33-OPEN-1 (new).** E1 and E1b fall short of "beyond strong baselines" on the `e1b` family.
B20R32-OPEN-2 is answered by this measurement.
