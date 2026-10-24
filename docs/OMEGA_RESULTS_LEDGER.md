# Genesis Ω: results ledger (master implementation contract §18)

Results are kept apart by status:
- **verified** (a recorded, preregistered study whose record test recomputes it; DEV scope, internal, not
  independently replicated);
- **exploratory** (development looks, disclosed in the next preregistration);
- **failures and negative results**;
- **unrun plans**.

Nothing here is an independent or sealed result.

## Verified (preregistered, recorded; DEV, internal)

| Batch | Result |
|---|---|
| B20_R102–R123 | Gset max-cut: 45 of 54 best-known values matched over all runs, none beaten; a "record" on G38 was a known 2013 max-bisection value |
| B20_R103, R107 | The feedback contract stops on zero-signal problems; version 2 keeps 63–93% of real gains |
| B20_R113 | Renormalisation, chosen by the system's selection, carries to Gset's planar instances (13–2 at 60 s) |
| B20_R118 | Hidden confounders mislead the established methods (CONFOUNDING_MISLEADS) |
| B20_R122 | On non-Gaussian data the observational residual flag marks hidden causes: F1 0.47 against FCI's 0.21 |
| B20_R124 | With Gaussian data only experiments find hidden causes (EXPERIMENTS_NEEDED); the oracle's 4 equal random's 8 |

## Failures and negative results (recorded)

| Batch | Result |
|---|---|
| B20_R111, R112, R115 | Autonomous invention of a better algorithm: NOT_DEMONSTRATED |
| B20_R86 | Generations do not compound in the earlier language: NO_COMPOUNDING |
| B20_R120, R122, R124 | Genesis's choice of experiments no better than random (four times) |
| B20_R72, R92, R97 | Physics move rules show no measurable effect in the invention engine |

## Exploratory (development looks, 24 Oct 2026; disclosed in B20_R129 and R130)

| Look | Result |
|---|---|
| Adaptive choice of experiments, R129's framework | Experiments needed: random 7.5, eig 4.5, decfall 4.0, oracle 3.0. One dev search found its own rule (3.96) |
| Interpretation is the limit | Per-pair framework ceiling 0.51; joint re-analysis 0.59; the established LLC estimator 0.71–0.77; multi-regime ML 0.69. Under ML at 8 experiments, the scientist's choice 0.65 against random 0.49 |
| Instruments | Richer per-pair tests do not move the ceiling (0.49–0.53) |
| Question set | A third of hidden causes are never asked about, because FCI separates them on near-unfaithful partial correlations (median 0.03) |
| Problem Compiler at 2 s | Genesis's engine ties the MaxSAT 2026 champion on independent set, Max-2-SAT and max-cut; loses on colouring (15–19 against 7–10 conflicts); HiGHS behind everywhere |
| Difficulty probes | Planted coupling answered by renormalisation (+16 against +4); natural Gset classes give weak probe signals |

## Running or preregistered (no result yet)

| Batch | State |
|---|---|
| B20_R127 | The system's own engines against human designs. Running; the judge released nothing in any class or generation |
| B20_R129 | The adaptive scientist. Running |
| B20_R130 | Choice, instrument and interpretation separated. Preregistered `f812701` |
| B20_R128 | Improving the inventor. Preregistered |

## Unrun plans

| Batch | Plan |
|---|---|
| B20_R131 | The cascade on a real case |
| B20_R132 | The Difficulty Cartographer |
| — | A Problem Compiler study |
| Ω7 | The interpretation engine |
| Ω10 | The allocator |
| Ω12 | Longitudinal autonomy |
