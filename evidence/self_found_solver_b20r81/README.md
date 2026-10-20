# B20_R81 evidence: the system's own solver against the builder's engine, random programs and the state of the art

Builder-run on DEV. It licenses nothing.
- **Script:** `scripts/b20r81_self_found_solver.py`, preregistered at `e579deb` before B20_R79 and B20_R80 had run
  (SHA-256 `28cc40c3…b23f`). Alone, pinned to CPU 0. The container was restarted after 7 of 24 hosts (rows saved per
  host); the study resumed from its saved rows (it is resumable by design; `run.log` has both parts, and the first
  part's stdout is `run1_interrupted_stdout.log`). `code_identity` `538e9ff7…6c3b`, the committed tree at the run.
- **Programs tested:** found = B20_R79's (`discovered_program.json`, SHA-256 `513e5e7b…`), random = B20_R80's
  (`1dd0b895…`), both by `solver-program-v1`.
- **Hosts:** 24 fresh DEV planted-cluster hosts at n63 (433–499 edges), excluding 3,195 exposed identities (the
  training hosts included). 18 targets certified.

## Labels (preregistered; an independent recomputation from the rows agrees, and 10 other bootstrap seeds)

| Question | Label | Typical host (q 0.5) | Hard host (q 0.75) |
|---|---|---|---|
| GV4 headline: the system's solver against the builder's engine | **UNRESOLVED** | −2.32 [−2.32, **−1.00**] | −2.26 [−3.00, **−1.00**] |
| Search against random programs | **UNRESOLVED** | 0.00 [0.00, 1.26] | 0.06 [−0.74, 1.74] |
| The system's solver against BURER2002 and CP-SAT | **SELF_FOUND_BEATS_SOTA** | +10 [10, 10] both | +10 [10, 10] both |
| Replication of B20_R77 (the builder's engine against both tools) | **ENGINE_BEATS_SOTA** | +10 [10, 10] both | +10 [10, 10] both |

(log2 ratios, positive = the system's solver faster.) Against the builder's engine both intervals end exactly at −1.00:
the engine is about 5 times faster (median TTS* 0.1 s against 0.5 s; 75th percentile 0.25 s against 1.2 s), but the
preregistered rule needs the upper end strictly below −1, so the label is UNRESOLVED. B20_R76's per-host statistic,
a secondary, calls it BUILDER faster (−1.32 [−2.00, −1.32]).

## Descriptive

| Arm | reached within 2 s (of 24) | TTS* median / 75th pct (CPU s) |
|---|---|---|
| the builder's engine (`hybrid-swap-v1`) | 24 | **0.1 / 0.25** |
| simulated bifurcation | 24 | 0.1 / 0.5 |
| **the system's own solver** (B20_R79) | 24 | 0.5 / 1.2 |
| random-search program (B20_R80) | 24 | 0.5 / 1.25 |
| the system's B20_R76 engine | 20 | 1.25 / 2.0 |
| BURER2002 | 6 | ∞ / ∞ |
| CP-SAT (anytime) | 0 | ∞ / ∞ |

CP-SAT with 60 s reached 2 of 24 targets and proved none optimal; the checked reference certified 18.
Exploratory (not preregistered): the random-search program also beats both tools by the same rule ([10, 10] at both
quantiles). Against the system's B20_R76 engine and against dSB, the found program is UNRESOLVED (B20_R76's per-host
statistic: faster than neither; dSB faster).

## How to read it

- The system's own solver beats CP-SAT and BURER2002 on these hosts; so does a random program from the same language.
  What beats the tools is the language's parts (the system's own cut representation, descent, perturbation, sweeps),
  not the search. The search's swap-like step made no measurable difference on fresh hosts.
- The builder's engine remains about five times faster than the system's solver; the preregistered rule falls short
  of calling it by the boundary.
- **Expectation, stated before running:** found beats the B20_R76 engine and random search, loses to the builder's
  engine, MIXED against the tools. Observed: UNRESOLVED against both the engine and random, beats the tools.
- Scope: one host family, n63, anytime ≤ 2 s on one core, builder-run DEV.

## Tests

`tests_genesis/test_self_found_solver.py`: Record for B20_R81 (4).
