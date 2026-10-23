# B20_R86 evidence: do the system's generations compound? NO_COMPOUNDING (DEV)

Builder-run on DEV. It licenses nothing.
- **Script:** `scripts/b20r86_generations_eval.py`, preregistered at `9aad649`, deferred, and run unchanged on 23 Oct
  2026.
- **Run:** alone on CPU 0, 4,348 s. `code_identity` `abae2b4b…`, the committed tree at the run (B20_R98's repin
  included; the programs are byte-identical to their recorded files).
- **Hosts:** 24 fresh DEV planted-cluster hosts at n63 (seed 20268601, 439–486 edges), excluding 3,355 exposed
  identities, including every generation's training hosts.
- **Targets:** CP-SAT given 60 s and the checked reference given 120 s. 19 of the 24 targets are certified.

| File | What |
|---|---|
| `rows.jsonl` | Per host: every arm's runs at 0.05, 0.1, 0.25, 0.5 and 2 s (3 seeds each), CPU, the target and its certification |
| `summary.json` | Labels, every pairwise comparison with its interval, per-arm time-to-target quantiles, validity, descriptors, the programs' SHA-256 |
| `hosts.json`, `run.log` | The hosts and the run |

## Result: NO_COMPOUNDING

| Comparison | Median ratio (log2) | 75th percentile (log2) | Label |
|---|---|---|---|
| generation 2 vs 1 | 0.00 [−1.00, +1.00] | +1.26 [−1.06, +1.32] | UNRESOLVED |
| generation 3 vs 2 | 0.00 [−1.00, 0.00] | −1.26 [−1.32, +0.74] | UNRESOLVED |
| generation 2 vs its no-library control | −1.00 [−1.00, 0.00] | +1.26 [−1.00, +1.26] | UNRESOLVED (library effect) |

Time to the target (TTS* over the ladder; median / 75th percentile; hosts reached within 2 s):

| Arm | Median | 75th percentile | Reached within 2 s |
|---|---|---|---|
| generation 1 | 0.5 s | 1.2 s | 23 of 24 |
| generation 2 | 0.5 s | 0.5 s | 23 of 24 |
| generation 3 | 0.5 s | 1.2 s | 23 of 24 |
| control | 0.25 s | 1.2 s | 22 of 24 |
| engine | 0.1 s | 0.25 s | 24 of 24 |

- **The generations do not compound.** No transition improves, none worsens, and the library's effect is unresolved.
  At the 75th percentile, generation 2 tends to be faster than generation 1 and than its control (+1.26 in log2,
  about 2.4×). Generation 3 tends to be slower than generation 2, by the same amount. Every interval reaches
  across −1.
- **The builder's engine is faster than every generation.** It is about 5× faster at the median (B_FASTER for every
  generation at q0.5), 0.1 s against 0.5 s.
- **What fits the whole line (B20_R79–R86).** The search over this language does no better than random programs of it
  (B20_R80, R81). Generation 2's library adds nothing on its training hosts (B20_R84). Generation 3 only schedules the
  earlier generations (B20_R85). On fresh hosts the three generations cannot be told apart. In this language, at this
  size, the system does not improve on itself across generations. The feedback-contract study (B20_R103) tests one
  likely reason: the differences at the top of these searches are about as large as the evaluation noise.

**Validity:**
- the median CPU at the 0.5 s run time was 0.65 s for every arm (the rule asks for at least 0.45);
- no run failed.

## Tests

`tests_genesis/test_generations.py`: Record for B20_R86 (3). The labels and comparisons recompute from the rows, the
programs are the recorded files, and the hosts are fresh and in the exposure addenda.
