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
| B20_R130 | **CHOICE**: Genesis's scientist (B20_R129's choice, decfall) beats random under the global estimator by 0.165 hidden-cause F1 (p 7.5e-26; transfer p 1.9e-9); with every experiment the global estimator reaches 0.69 against the per-pair framework's 0.61 |
| B20_R129 | **ADAPTIVE_SCIENTIST**: Genesis's scientist needs 4.49 experiments against random's 6.81 (p 1e-27). Adapting is worth 0.70. Its own rule `inv1` beats every established acquisition (4.34 against eig's 4.98, preregistered; the others exploratory, Holm) and ties the builder's `decfall` (p 0.16), which Genesis chose on validation (4.42 against 4.59). `inv1` was a random initial program, not released by the judge. Exploratory: `inv1` has the higher F1 after 4 experiments (+0.054 test, +0.077 transfer, Holm p 0.008); reconciliation `evidence/r129_reconciliation/`. Four as good as eight holds on the shifted family only. Information gained does not predict accuracy gained |

## Failures and negative results (recorded)

| Batch | Result |
|---|---|
| B20_R111, R112, R115 | Autonomous invention of a better algorithm: NOT_DEMONSTRATED |
| B20_R86 | Generations do not compound in the earlier language: NO_COMPOUNDING |
| B20_R130 | The global interpretation against the per-pair one at the preregistered measure (F1 averaged over 2-8 experiments): NO_DIFFERENCE (p 0.52), directed F1 worse; it helps only from 6 experiments. The invented instrument ties. Four as good as eight NOT_SHOWN (needs 6) |
| B20_R127 | The system's own engines against human designs: NOT_SHOWN (Gset 10 s: 16–11 against MCX, p 0.44; 9–18 against REX; 28–5 against BLS). The judge released nothing in nine searches: training gains +0.04–0.23% against tau 0.75–2.45%; no compounding; no mechanism credited |
| B20_R120, R122, R124 | Genesis's choice of experiments no better than random (four times; these chose from fixed observational scores; B20_R129's adaptive scientist then beat random) |
| B20_R72, R92, R97 | Physics move rules show no measurable effect in the invention engine |

## Exploratory (development looks, 24 Oct 2026; disclosed in B20_R129 and R130)

| Look | Result |
|---|---|
| Adaptive choice of experiments, R129's framework (confirmed by B20_R129's test above) | Experiments needed: random 7.5, eig 4.5, decfall 4.0, oracle 3.0. One dev search found its own rule (3.96) |
| Interpretation is the limit | Per-pair framework ceiling 0.51; joint re-analysis 0.59; the established LLC estimator 0.71–0.77; multi-regime ML 0.69. Under ML at 8 experiments, the scientist's choice 0.65 against random 0.49 |
| Instruments | Richer per-pair tests do not move the ceiling (0.49–0.53) |
| Question set | A third of hidden causes are never asked about, because FCI separates them on near-unfaithful partial correlations (median 0.03) |
| Problem Compiler at 2 s | Genesis's engine ties the MaxSAT 2026 champion on independent set, Max-2-SAT and max-cut; loses on colouring (15–19 against 7–10 conflicts); HiGHS behind everywhere |
| Difficulty probes | Planted coupling answered by renormalisation (+16 against +4); natural Gset classes give weak probe signals |

## Running or preregistered (no result yet)

| Batch | State |
|---|---|
| B20_R128 | Improving the inventor. Preregistered |
| B20_R133 | The Problem Compiler against the specialists. Preregistered `e8bc181` |
| B20_R132 | The four bottlenecks of invention. Preregistered `c0431f6` |
| B20_R131 | The cascade on a real case. Preregistered `22385f7`; R130 did not verify its trigger, so by its protocol it records NO_VERIFIED_TRIGGER and runs only the null trigger and comparators |

## Unrun plans

| Batch | Plan |
|---|---|
| B20_R134 | The Difficulty Cartographer, redesigned |
| Ω7 | The interpretation engine |
| Ω10 | The allocator |
| Ω12 | Longitudinal autonomy |
