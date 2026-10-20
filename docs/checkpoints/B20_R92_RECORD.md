# B20_R92 record: the system's engine beats each of the thirteen MaxSAT champions of 2026 and 2024; against their per-host best it is decided on dense hosts and not at the planted hosts' 75th percentile

- **Run by:** the builder, on DEV; licenses nothing. Script `scripts/b20r92_vs_mse2026.py`, preregistered at
  `9602505` with B20_R91 (SHA-256 `10b8ee0c…6d89`, sent to Daniel before it ran), unchanged; `code_identity`
  `92437ec2…` (the committed tree). Alone, pinned to CPU 0.
- **Interrupted twice, disclosed.** The 2-hour limit on a background job stopped it during host P 0013 (13 hosts done)
  and during host D 0003 (27 done); both times Daniel's choice was to resume to the end, and it resumed from its
  per-host rows with the hosts reloaded, rerunning the interrupted host from its start with the same seeds.
- **Validity:** every arm's median CPU at 0.5 s 0.676–0.689 s; no failed run.
- Evidence: `evidence/vs_mse2026_b20r92/` (README with the full tables). Recomputed independently from the rows (own
  code; every label, interval and count matches).

## Result

| Label | Result |
|---|---|
| champions_P, champions2026_P | **TFX_BEATS_EVERY_CHAMPION** |
| champions_D, champions2026_D | **TFX_BEATS_EVERY_CHAMPION** |
| vbs_P | **UNRESOLVED**: 3× faster at the median (log2 1.585, interval [1.585, 3.585]); at q0.75 log2 2.263, interval [0.263, 3.585] |
| vbs_D | **TFX_BEATS_VBS**: about 200× (log2 7.64 at both quantiles) |
| long_budget | **NO_CHAMPION_FINDS_MORE** (10 s, 36 hosts) |
| the five ablations | **UNRESOLVED** |

- **Each champion alone** is beaten by more than 2× at both quantiles on both families. On the planted hosts tfx's
  median TTS* is 0.02 s against PASMaxSAT-c's and DeepDist's 0.25 s (the closest two; about 12× at the median for
  both), NuWLS-c-2026-UB 0.5 s, TT-Open-WBO-Inc 0.6 s, the rest 1.2–2 s; DeepDist-c reached no target. On
  G(63, 0.5): tfx 0.01 s, PASMaxSAT-c 2 s, DeepDist 3 s; the other eleven reach at most 4 of 12 targets within 2 s.
- **Their per-host virtual best** on the planted hosts is 0.06 s at the median (PASMaxSAT-c is the fastest on 11
  hosts, DeepDist on 7, TT-Open-WBO-Inc on 6): tfx is faster on 21 hosts, tied on 1, slower on 2, and more than twice
  as fast at the median, but the 75th-percentile interval reaches down to 1.2×, so the label is UNRESOLVED.
- **The floor is gone:** tfx sits at the shortest run time (0.005 s) on 3 of 24 and 2 of 12 hosts (B20_R90: 33 of 36
  at 0.05 s); its margins are now measured, not bounded.
- **Saturation remains:** given 10 s, no champion finds more than tfx finds within 2 s, and tfx's 10 s value is the
  target on every host; the instances separate methods by speed only.
- **Ablations:** none resolved, and the point estimates lean against the operators at these budgets: without
  simulated bifurcation the engine was faster on 12 hosts and slower on 4 (8 tied); without crossover 13 against 8;
  without parallel tempering 11 against 8; without relinking and restarts 11 against 6. The first design (what
  B20_R89's race replaced) was slower on 13 and faster on 1, also UNRESOLVED.
- **DeepDist-c** ends near 69% of the target at every run time from 0.005 s to 2 s: it does not respond to run time
  in this range, so it adds nothing to the virtual best here (its 2026 score was at 60 s).

## Against the expectation stated before running

The champion labels came out as expected (as in B20_R90). The VBS margin on the planted hosts was expected to be
about 10×; it is 3× at the median, and the revised expectation (the 2026 entrants are much faster, so vbs_P
UNRESOLVED about as likely as TFX_BEATS_VBS) is what happened. The ablations were expected to be NO_MEASURABLE_EFFECT
or UNRESOLVED for most, with `first_design` the likeliest to show HELPS; all five are UNRESOLVED.

## What it means

On this problem at n = 63 and budgets up to 2 s, the system's engine is faster than every one of the strongest
anytime MaxSAT solvers of 2024 and 2026 taken one at a time, on both families, by more than 2× and up to two orders of
magnitude. Against the best of all thirteen on each host it is decisively faster on the dense hosts (about 200×) and
faster at the typical planted host (3×), but whether it is more than twice as fast at the harder planted hosts is not
resolved. At these sizes every strong method ends at the same value, so the comparison is about speed only: whether
the system finds better answers than the champions within the same budget is the large-graph milestone's question.
Which of the engine's physics and biology operators matter is not shown; at these budgets they may cost time.

Still not a claim: one problem, a problem-specific engine against general MaxSAT solvers on its exact encoding, n ≤ 63,
one core, 21 of the 36 targets uncertified (9 planted, all 12 dense), builder-run DEV with no independent custodian or replication
(B20R90-OPEN-1, updated).

## Tests

`tests_genesis/test_vs_mse2026.py` (6): the five design tests and `RecordB20R92` (the labels follow from the rows,
validity, the floor counts, no run above its target, tfx's 10 s value is the target, the frozen configuration).
