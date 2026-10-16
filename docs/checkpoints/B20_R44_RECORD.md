# B20_R44 record: the discovered representation is causally responsible for E1d's gain (ablation READY_FOR_REVIEW; null control clean; DEV)

- **Run by:** the builder, on DEV. Nothing here licenses a claim. The registered transform awaits
  review.
- **Commits:**
  - `c68d0bc` (setup): the script and the transform, committed before the run. The script's SHA-256
    was sent to the user beforehand.
  - The result commit that follows it.
- **Evidence:** `evidence/e1d_ablation_b20r44/`.

## Why

GV3 asks that a *checked machine-produced discovery* helps, with controls. E1d shows a frozen
candidate beating an exact MIP at four times its budget (B20_R41, B20_R43). It did not yet show that
the discovered representation `cross_2` is the cause. No transform had been registered for that
component, so it could license no causal level.

## What changed

**`kernel/replay_contracts.INTERVENTIONS`** now registers the ablation `cross_2` → `ordered_2` for
represent-and-repair-v1's `representation`.
- **Basis:** B18's Lean checks. `ordered_2` is within `cross_2` (CHECKED); the converse is
  DISPROVED; `ordered_2` is sound on triangle-free hosts (CHECKED).
- **No placebo:** the only other sound decoder, `adjacent_2`, is Lean-checked equal to `cross_2`.
- **Descriptor ids** are unchanged.

**One older test is updated on purpose.** B20_R15's `test_b14_open4_contracts` asserted that this
kind had no registered intervention. It now asserts this ablation, the absence of a placebo, and the
refusal of every other representation.

## Result

30 fresh hosts in the E1d settings, all certified.

| Check | Result |
|---|---|
| Candidate − ablation | **+7.07 per host [6.47, 7.70], 30/0/0** |
| Cost ratio | 1.00 |
| Dry run | SUPPORTED |
| Power | 15 per stratum (45 hosts), power 0.86 |
| Verdict | **READY_FOR_REVIEW** |
| Null control (`adjacent_2`, Lean-equal) | +0.03 [−0.02, +0.09], 29 of 30 hosts tied: **NULL_CONTROL_CLEAN** |

## What it means

The E1d evidence now has, on DEV:
- utility against every registered baseline, including an exact MIP at four times the budget;
- a rehearsal of the custody path;
- causal attribution to the discovered representation's decoder;
- a negative control showing the pipeline does not invent effects.

On DEV, that covers what GV3 asks for (preregistered prospective utility, plus controls), short of
independent execution and replication.

## Tests

`tests_genesis/test_e1d_ablation.py` (8):
- the transform is exactly `cross_2` → `ordered_2`, with no placebo, and other representations and
  components are refused;
- it rests on the checked dominance and soundness;
- descriptor ids are unchanged;
- the null control's verdicts behave as specified;
- the verdicts follow from the rows;
- the arms are the registered ones, and no arm exceeds a certified optimum;
- the hosts are fresh and in the addenda.

`tests_genesis/test_b14_open4_contracts.py` is updated as described above.

## Open

**B20R44-OPEN-1:** review of the registered transform. **B20R41-OPEN-1** is updated: E1d now has a
causal control.

**Next:** an ABLATION_SUPPORTED level needs a custodian-signed ablation evaluation of the E1d claim,
of 45 hosts by the power choice. A same-operator rehearsal through the v5 path is the next
engineering step.
