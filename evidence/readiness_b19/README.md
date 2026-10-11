# B19 evidence: E1 and E2 readiness (DEV only)

These are designs for review. Nothing here was frozen, registered or sealed. No efficacy
is claimed.

Run: `scripts/b19_readiness.py` (`run.log`: the pilot, 60 fresh DEV tasks). The design was
then recomputed from the recorded pilot rows with `--design-only`, for the reason below.

## E1: the candidate and the pilot (`e1/`)

**Candidate.** B18's represent-and-repair solver, with the cut representation `cross_2`,
greedy triangle-free repair and 0.5 CPU seconds. It is identified by the SHA-256 of its
module source and its parameters (`summary.json` → `candidate_identity`).

**Pilot.** 60 fresh DEV hosts from the adopted triangle-free calibration (erdos n = 22,
p = 0.35), each with a certified optimum. The comparator is the strongest fixed DSL
baseline on the pilot, `low_cycle`.

| | Candidate | Strongest baseline |
|---|---|---|
| Total edges | 3,588 | 3,512 |
| Optimum reached | 36 / 60 | 13 / 60 |

The mean paired difference is +1.27 edges per task: 41 wins, 9 ties, 10 losses. This is a
DEV estimate, and it is not used to set the design effect.

**Power.** The minimum useful effect (0.5 edges per task) and the design effect (1.0) were
fixed in the script before the pilot ran.

- **The B16 power model** (`power_analysis_b16_model.json`) reports INFEASIBLE. It lets
  simulated gains use the headroom of the pilot candidate itself, which is already at the
  optimum on 36 of 60 tasks. But the simulation perturbs the *centred* candidate: the pilot
  difference minus its mean. That candidate has more headroom. The mismatch did not
  matter in B16, where the pilot mean was +0.2; here it decides the outcome.
- **The B19 correction** (`power.required_sample(..., headroom='centred')`) measures
  headroom for the centred candidate. The default stays the B16 model, so B16's evidence
  is unchanged. With the correction, 25 tasks give power 0.83 at the design effect. Power
  at the minimum useful effect is 0.23, and the false-positive rate at zero effect is
  0.015. The simulated decisions agree with the exact analysis on 40 of 40 checks.
- The DRAFT decision record embeds the corrected analysis. **A reviewer must accept or
  reject the correction** (B19-OPEN-4).

**Not ready for a sealed run.** The custodian's evaluator executes DSL programs only and
cannot run this candidate (B19-OPEN-3). Candidate CPU was measured in-process; the
baselines' CPU was measured in the sandbox worker.

## E2: the design draft (`e2/design_DRAFT.json`)

**Arms.** Concept enabled, removed, placebo, an equivalent-information alternative (a
manual `Antitone`), an effort control (4× heartbeats) and retrieval. They are paired by
statement. The primary endpoint is a statement CHECKED within the per-statement budget.

**DEV results.** Proved out of 16 fresh statements:

| none | retrieval | concept | manual | placebo | effort |
|---|---|---|---|---|---|
| 4 | 4 | 8 | 8 | 4 | 4 |

**What is still missing.** A custodian-side statement generator and a sealed statement
panel, a statement-level power analysis, and independent review.

The design separates "helps this prover" from "new mathematics". The second is not
claimed, because W17 links the concept to `Antitone` and `IsLowerSet` with Lean-checked
equivalences.
