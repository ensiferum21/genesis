# B20_R92 evidence: the system's configured engine against the MaxSAT Evaluation 2026 and 2024 anytime champions

Builder-run on DEV. It licenses nothing.
- **Script:** `scripts/b20r92_vs_mse2026.py`, preregistered at `9602505` (SHA-256 `10b8ee0c…6d89`, sent to Daniel
  before it ran; unchanged). Alone, pinned to CPU 0. `code_identity` `92437ec2…`, the committed tree (`9602505`).
- **Interrupted twice, disclosed:** the session's 2-hour limit on a background job stopped it during host P 0013
  (after 13 hosts, 6,962 s) and during host D 0003 (after 27 hosts, 7,181 s); Daniel chose to resume to the end. Each
  time it resumed from `rows.jsonl` (rows are written per host) with the hosts reloaded from `hosts.json`, so the
  interrupted host was run again from its start with the same seeds; the last 9 hosts took 3,483 s.
- **Engine:** `tfx-v1` with B20_R89's frozen configuration (`config.json` SHA-256 `0962450e…`).
- **Champions:** the eight 2026 entrants built from their sources (B20_R91) and B20_R90's five; VBS = per host, the
  lowest TTS* of all thirteen.
- **Hosts:** P: 24 fresh planted n63 (seed 20269201; 433–478 edges; 15 targets certified). D: 12 fresh G(63, 0.5)
  (seed 20269202; 964–1013 edges; targets are best known values, uncertified; CP-SAT 60 s never reaches them).
  Excluded: the 3,303 identities of every earlier study's hosts.
- **Validity:** every arm's median CPU at 0.5 s 0.676–0.689 s; no failed run in any arm.

## Result

| Label | Result |
|---|---|
| champions_P | **TFX_BEATS_EVERY_CHAMPION** |
| champions2026_P | **TFX_BEATS_EVERY_CHAMPION** |
| vbs_P | **UNRESOLVED** (more than 2× faster at the median, not resolved at q0.75) |
| champions_D | **TFX_BEATS_EVERY_CHAMPION** |
| champions2026_D | **TFX_BEATS_EVERY_CHAMPION** |
| vbs_D | **TFX_BEATS_VBS** |
| long_budget | **NO_CHAMPION_FINDS_MORE** |
| ablation_no_dsb, _no_pt, _no_cross, _no_relink_restart, _first_design | **UNRESOLVED** (all five) |

TTS* (s), median and 75th percentile over hosts; "reached" = hosts reached within 2 s:

| Arm | P: reached | P: median | P: q0.75 | D: reached | D: median | D: q0.75 |
|---|---|---|---|---|---|---|
| **tfx** | **24** | **0.02** | **0.05** | **12** | **0.01** | **0.01** |
| PASMaxSAT-c | 24 | 0.25 | 0.5 | 11 | 2.0 | 10 |
| DeepDist | 24 | 0.25 | 0.5 | 12 | 3.0 | 6.0 |
| NuWLS-c-2026-UB | 23 | 0.5 | 3.0 | 0 | — | — |
| TT-Open-WBO-Inc | 22 | 0.6 | 2.5 | 4 | — | — |
| SGAT-NuWLS-c | 22 | 1.2 | 3.0 | 3 | — | — |
| NuWLS-c-2026 | 23 | 1.2 | 3.0 | 2 | — | — |
| Aperture-IBI | 23 | 1.2 | 2.0 | 1 | — | — |
| SPB-MaxSAT-c-FPS | 23 | 1.2 | 6.0 | 4 | — | — |
| NuWLS-c-IBR | 22 | 1.2 | 3.0 | 2 | — | — |
| Aperture-GBG | 24 | 1.25 | 6.0 | 1 | — | — |
| Aperture-KBG | 22 | 2.0 | 2.5 | 2 | — | — |
| Aperture (hermax) | 12 | 24 | — | 0 | — | — |
| DeepDist-c | 0 | — | — | 0 | — | — |
| champions' VBS | 24 | 0.06 | 0.24 | 12 | 2.0 | 2.0 |

**Against the VBS.** P: log2 ratio 1.585 at the median (3×; interval [1.585, 3.585], so 3–12×: A_FASTER) and 2.263
at q0.75 (interval [0.263, 3.585]: UNRESOLVED); B20_R76's per-host statistic 2.32 [1.585, 3.585] (faster). Per host,
tfx is faster than the VBS on 21 hosts, tied on 1, slower on 2. D: log2 7.64 at both quantiles (about 200×;
intervals [7.64, 7.64] and [7.64, 8.23]). Against each champion alone: more than twice as fast at both quantiles on
both families, faster on every host except one tie each with DeepDist and NuWLS-c-IBR and one or two hosts each
where NuWLS-c-2026-UB or TT-Open-WBO-Inc was faster (P).

**The floor is gone:** tfx reached its target at the shortest run time (0.005 s) on 3 of 24 and 2 of 12 hosts (B20_R90:
33 of 36 at 0.05 s), so these margins are measured, not bounds.

**Long budget (10 s, one seed):** no champion found more than tfx found within 2 s on any of the 36 hosts; tfx's 10 s
value is the target on every host. Champions reaching the target at 10 s: P: PASMaxSAT-c, DeepDist and SPB 24,
Aperture-GBG and -KBG 23, NuWLS-c-2026-UB and SGAT-NuWLS-c 17; D: PASMaxSAT-c 11, DeepDist and Aperture-KBG 10,
Aperture-GBG 9, SPB 8, NuWLS-c-2026-UB 1, SGAT-NuWLS-c 0.

**Ablations (P), all UNRESOLVED.** The point estimates lean the other way: without simulated bifurcation the engine
was faster on 12 hosts and slower on 4 (8 tied; log2 −1.0 at both quantiles, intervals [−1, 0] and [−1.32, 0]);
without crossover faster on 13, slower on 8; without parallel tempering faster on 11, slower on 8; without relinking
and restarts faster on 11, slower on 6. The first design (what the race replaced) was slower than tfx on 13 hosts and
faster on 1 (log2 0 and 1.0, intervals [0, 1.32] and [0, 2.32]). At these budgets on these hosts no operator is shown
to matter, and the race's configuration is not shown to beat the first design.

**DeepDist-c** ended near 69% of the target at every run time from 0.005 to 2 s (median 0.691 at 0.005 s, 0.692 at
2 s) and reached no target: it does not respond to the run time in this range (B20_R91 noted its first phase is
SAT-based search; its 2026 score was at 60 s).

Recomputed independently from `rows.jsonl` (own code; labels, intervals and counts match).
