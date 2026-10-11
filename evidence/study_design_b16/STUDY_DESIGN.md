# E1 study design: a DEV-only draft for independent review

This is a design, not a study. No candidate is frozen, no sealed task exists, and
no efficacy is claimed. `decision_record_DRAFT.json` stays in DRAFT status until
it is reviewed. The custodian refuses any registration whose record is not FROZEN.

## The ceiling problem

The B13 panel generator gave tasks with 5 to 7 vertices. On a fresh v1 DEV panel
of 24 tasks, the best fixed baseline reached the certified optimum on every task:
ceiling rate 1.0, mean headroom 0.0 (`../dev_calibration_b16/v1_panel_c4_measurement.json`).
No better-solver experiment could have shown anything on those tasks.

## Calibration (DEV only)

`genesis.calibration` measured 13 family settings for c4_host_v2 and 7 + 6 settings
for triangle_free_host_v1, using only freshly generated DEV tasks. The selection
rule, `calibration.SELECTION_RULE`, was frozen in code before any run. It requires:

- at least 90% of optima certified;
- a ceiling rate between 0.1 and 0.6;
- mean headroom of at least 2%;
- a median evaluator time of at most 15 s.

Every setting tried is in the records, including those not selected. The adopted
records are named by hash in `configs/dev_calibration.json`:

| Domain | Selected settings |
|---|---|
| c4_host_v2 | erdos n=20 p=0.25; erdos n=16 p=0.3; erdos n=12 p=0.45 (ceiling rates 0.375, 0.25, 0.5) |
| triangle_free_host_v1 | round 1 selected nothing. Round 2 kept the same rule and extended the grid to larger hosts; it selected erdos n=22 p=0.35 (ceiling rate 0.125). |

## Pilot (DEV only)

The pilot draws 60 fresh DEV tasks from the adopted c4 calibration, three
families of 20.

- **Candidate.** A fixed, illustrative DSL program: low-cycle priority with
  exchange. It is not a research output.
- **Comparator.** The strongest fixed baseline on the pilot was `low_cycle`; this
  mirrors the custodian's strongest-baseline rule.
- **Optima.** Every pilot task has a certified optimum, used for headroom.
- **Pilot difference.** The mean paired difference was +0.2 edges per task. It is
  reported, but it is not used to set the design effect.
- **Spread.** The per-family SD of the paired difference is about 0.6. Between 50%
  and 60% of tasks have headroom.

## Analysis plan v2 (draft)

| Item | Value |
|---|---|
| Primary endpoint | paired edge difference per task; estimand = mean of family means |
| Test | one-sided stratified sign-flip permutation (exact when small) |
| Interval | stratified bootstrap, 90% (its lower end is the one-sided 95% bound) |
| Minimum useful effect | 0.25 edges per task |
| Design effect (for power) | 0.5 edges per task. **This is an assumption to review**, not an estimate. |
| Multiplicity | Holm over the custodian-assigned family `sealed_evaluation:c4_host_v2`, declared size 3 |
| Stopping | a single analysis |
| Failures | a failed run scores 0 and stays charged |
| Unsupported tasks | excluded and reported, at most 5% of the panel |
| Cost bound | candidate CPU at most 3× the baseline's |
| Regression bound | no family mean below −1 edge |
| Sensitivity analyses | task sign test; leave one family out; failures excluded; family-level sign flip |

## Power (`power_analysis.json`)

**Effect model.** Improvements come in whole edges, and only on tasks with
headroom. The pilot differences are centred, so the pilot's own effect is removed.
Holm is applied at the worst rank, α/3.

**Design floor.** 10 tasks per family, a stated design choice. Smaller panels make
the sensitivity analyses degenerate.

**Result.** The floor is enough: 10 per family, 30 tasks in total, gives simulated
power of 0.946 at the design effect.

| Condition | Simulated rate |
|---|---|
| Power at the minimum useful effect | 0.39 |
| Rejections at zero effect (false-positive rate) | 0.006 |

The simulated decisions agreed with the exact registered analysis on 40 of 40
checks.

**Caveat.** A reviewer should weigh the effect model most heavily. If real
improvements are rarer or larger than assumed, the required sample changes. Larger
panels are cheap here: the median evaluator time is under 1 s per task.

## What a reviewer is asked to decide

1. Is the minimum useful effect (0.25 edges per task) meaningful for this domain?
2. Is the design effect (0.5) a reasonable planning assumption?
3. Is the custodian-assigned family (kind × domain at one custodian) the right
   multiplicity scope?
4. Are the floor and the exclusion and cost rules acceptable?

Only after that review, an independent custodian and a frozen candidate can the
record be FROZEN and a CONFIRM panel be drawn. The CONFIRM panel is drawn by the
custodian with `calibration.calibrated_panel`.
