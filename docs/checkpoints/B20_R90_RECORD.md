# B20_R90 record: the system's configured engine against the strongest anytime MaxSAT solvers

- **Run by:** the builder, as preregistered in `B20_R88_RECORD.md` (script at `9f8eecc`, SHA-256 `afcaa588…8e0c`,
  sent to Daniel before B20_R89 ran; unchanged). Alone, pinned to CPU 0; `code_identity` equals the committed tree
  (`15aa2a3`). Evidence: `evidence/beat_the_champions_b20r90/`.
- **Interruption, disclosed:** the session's 2-hour limit on a background job stopped the run after 19 of 24 planted
  hosts, during host P 0019. Rows are written per host; the run was resumed, so P 0019 was redone from its start with
  the same seeds. Nothing else changed.
- **No claim, rule, comparator or package changes.** A DEV diagnostic; it licenses nothing.

## Verdict: every preregistered label is the strongest outcome (valid; recomputed independently)

| Label | Result | Meaning |
|---|---|---|
| champions_P | **TFX_BEATS_EVERY_CHAMPION** | more than twice as fast as each of the five, at the typical (q 0.5) and the hard (q 0.75) host |
| vbs_P | **TFX_BEATS_VBS** | more than twice as fast as the per-host best of all five (an oracle no single solver is) |
| champions_D | **TFX_BEATS_EVERY_CHAMPION** | the same on G(63, 0.5), a structure tfx was never developed or configured on |
| vbs_D | **TFX_BEATS_VBS** | |
| long_budget | **NO_CHAMPION_FINDS_MORE** | given 10 s, no champion found more than tfx found within 2 s, on any of 36 hosts |

Validity: median CPU at 0.5 s 0.68–1.03 s for every arm; no failed run in any arm, in Part A or C.

**Time to solution** (TTS*, s; 24 planted n63 hosts, P, and 12 G(63, 0.5) hosts, D):

| Arm | P reached ≤ 2 s | P median | P q0.75 | D reached ≤ 2 s | D median | D q0.75 |
|---|---|---|---|---|---|---|
| **tfx (B20_R89's configuration)** | **24** | **0.05** | **0.05** | **12** | **0.05** | **0.05** |
| DeepDist (ECAI 2025) | 24 | 0.25 | 0.25 | 12 | 2.0 | 2.5 |
| SPB-MaxSAT-c-FPS (MSE 2024 winner) | 24 | 1.2 | 2.0 | 6 | 24 | — |
| NuWLS-c-IBR (MSE 2024 podium) | 23 | 1.25 | 6.0 | 5 | — | — |
| TT-Open-WBO-Inc 2024 | 20 | 2.0 | 6.0 | 3 | — | — |
| Aperture (SOFT 2026) | 11 | — | — | 0 | — | — |
| champions' virtual best | 24 | 0.25 | 0.25 | 12 | 2.0 | 2.5 |
| B20_R77 engine (Python) | 24 | 0.25 | 0.25 | | | |
| BURER2002; MQLib virtual best (4 heuristics) | 13; 13 | 0.6; 0.5 | — | | | |
| CP-SAT (8 workers, one core) | 0 | — | — | | | |

tfx against the closest champion, DeepDist (equal to the VBS on these quantiles): log2 ratio 2.32 at both quantiles
on P (intervals [2.32, 2.32] and [2.32, 4.59]): at least 5× faster; 5.32 and 5.64 on D ([3.32, 5.64], [5.32, 6.91]):
40–50×. Host by host, tfx was faster than every champion on every host, apart from one tie with DeepDist and one
with TT-Open-WBO-Inc (both P). Long budget: at 10 s tfx and SPB-MaxSAT-c reached every target; DeepDist all on P and
11 of 12 on D; NuWLS-c, TT-Open-WBO-Inc and Aperture missed many (D: 2, 0 and 1 of 12). CP-SAT at 60 s reached 2 of
24 planted targets and none on D (6–29 edges short there).

Secondary (preregistered, not part of the labels): tfx against B20_R77's engine: A_FASTER at q 0.75, UNRESOLVED at
q 0.5 (interval [1.0, 2.32]: the lower end sits exactly on the 2× line); against BURER2002 and MQLib's virtual best,
UNRESOLVED at q 0.5 (they fail on half the hosts, so the typical-host quantile is unstable) and A_FASTER at q 0.75;
against CP-SAT A_FASTER. B20_R77's question again: the engine against CP-SAT A_FASTER, against BURER2002 A_FASTER at
q 0.75 and UNRESOLVED at q 0.5 (B20_R77 had both A_FASTER).

**Against the builder's expectation:** it expected DeepDist to be COMPARABLE or UNRESOLVED at q 0.75 (champions_P
MIXED about as likely as TFX_BEATS_EVERY_CHAMPION) and family D to be open. Both came out stronger than expected.

## Limits (stated with the result; read them before quoting it)

1. **A floor, not a measure:** tfx reached the target at the ladder's shortest time, 0.05 s, on 33 of 36 hosts
   (105 of its 108 runs at 0.05 s), so every ratio above is a lower bound; the ladder cannot show how much faster.
2. **Specialist against generalists.** The champions are general MaxSAT solvers, tuned over years for the
   Evaluation's benchmark mix, run here on this one problem's exact encoding with their published configurations.
   tfx is built for this problem (64-bit vertex bitsets, moves on edge sets). The result is that, on this problem,
   the system's specialist beats the best general solvers by a wide margin; it says nothing about MaxSAT in general.
3. **Regime:** n ≤ 63 (the task model's maximum), one core, anytime ≤ 2 s (plus the 10 s check), two host families.
   The problems saturate within seconds for the strongest solvers; the contest is time to solution.
4. **Targets:** 16 of 24 planted targets are certified optima; the other 8 and all 12 on D are best known values
   (every arm is judged against the same values; on every host tfx's 0.05 s result equals the best known value).
5. **Not included:** the 2026 Evaluation's entrants (its archive is refused by this workspace's proxy; Daniel was
   asked for it), Loandra (does not build here), Gurobi (licence).
6. **DEV, builder-run.** The configuration was chosen by the system (B20_R89), the operators and the space by the
   builder. A claim needs a reviewer's scope decision, a frozen descriptor, an independent custodian and replication
   (B20R90-OPEN-1).

## Independent recomputation

`rows.jsonl` was re-analysed with separate code (own TTS*, nearest-rank quantiles, the same paired bootstrap):
every interval, verdict and label matches, the per-host counts above come from it, and every target is at least
every recorded value.

## Tests

`tests_genesis/test_beat_champions.py`: Record for B20_R90 (1): labels, validity, host counts and the floor
disclosure are reproduced from the rows.
