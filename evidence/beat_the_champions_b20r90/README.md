# B20_R90 evidence: the system's configured engine against the strongest anytime MaxSAT solvers

Builder-run on DEV. It licenses nothing.
- **Script:** `scripts/b20r90_beat_the_champions.py`, preregistered at `9f8eecc` (SHA-256 `afcaa588…8e0c`, sent to
  Daniel before B20_R89 ran; unchanged). Alone, pinned to CPU 0. `code_identity` `5291d1dc…`, the committed tree
  (`15aa2a3`). **Interrupted once, disclosed:** the session's 2-hour limit on a background job stopped it after 19
  of the 24 planted hosts (6,836 s), during host P 0019; it was resumed from `rows.jsonl` (rows are written per
  host), so P 0019 was run again from its start with the same seeds; the rest took 4,323 s.
- **Engine:** `tfx-v1` with B20_R89's frozen configuration (`config.json` SHA-256 `0962450e…`).
- **Champions** (B20_R87's pinned builds): DeepDist, SPB-MaxSAT-c-FPS, NuWLS-c-IBR, TT-Open-WBO-Inc 2024, Aperture.
- **Hosts:** P: 24 fresh planted n63 (seed 20269001; 16 targets certified); D: 12 fresh G(63, 0.5) (seed 20269002;
  targets are best known values, uncertified; CP-SAT 60 s stays 6–29 edges below them).
- **Validity:** every arm's median CPU at 0.5 s 0.68–1.03 s; no failed run in any arm.

## Result: every preregistered label is the strongest outcome

| Label | Result |
|---|---|
| champions_P | **TFX_BEATS_EVERY_CHAMPION** |
| vbs_P | **TFX_BEATS_VBS** |
| champions_D | **TFX_BEATS_EVERY_CHAMPION** |
| vbs_D | **TFX_BEATS_VBS** |
| long_budget | **NO_CHAMPION_FINDS_MORE** |

TTS* (time to the best known value with 99% confidence), median and 75th percentile over hosts:

| Arm | P: reached ≤ 2 s | P: median | P: q0.75 | D: reached ≤ 2 s | D: median | D: q0.75 |
|---|---|---|---|---|---|---|
| **tfx** | **24** | **0.05** | **0.05** | **12** | **0.05** | **0.05** |
| DeepDist | 24 | 0.25 | 0.25 | 12 | 2.0 | 2.5 |
| SPB-MaxSAT-c-FPS | 24 | 1.2 | 2.0 | 6 | 24 | — |
| NuWLS-c-IBR | 23 | 1.25 | 6.0 | 5 | — | — |
| TT-Open-WBO-Inc | 20 | 2.0 | 6.0 | 3 | — | — |
| Aperture | 11 | — | — | 0 | — | — |
| champions' VBS | 24 | 0.25 | 0.25 | 12 | 2.0 | 2.5 |
| B20_R77 engine | 24 | 0.25 | 0.25 | | | |
| BURER2002 / MQLib VBS | 13 / 13 | 0.6 / 0.5 | — | | | |
| CP-SAT | 0 | — | — | | | |

tfx against the closest, DeepDist (and the VBS): at least 5× faster at both quantiles on P (log2 2.32, interval
[2.32, 2.32] and [2.32, 4.59]); 40–50× on D (log2 5.32 [3.32, 5.64] and 5.64 [5.32, 6.91]). Per host: faster than
every champion on every host except one tie with DeepDist and one with TT-Open-WBO-Inc (P). Given 10 s, no champion
found more than tfx found within 2 s on any of the 36 hosts.

**Floor, disclosed:** tfx reached the target at the ladder's shortest time (0.05 s) on 33 of 36 hosts (105 of its 108
runs at 0.05 s reached it), so its ratios are lower bounds: the ladder cannot show how much faster it is.

Recomputed independently from `rows.jsonl` (own code; labels, intervals and counts match).
