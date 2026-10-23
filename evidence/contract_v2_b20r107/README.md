# B20_R107 evidence: the feedback contract, version 2: V2_FIXES_POWER

Builder-run on DEV (the second level improving the first: the judge that decides what counts as progress is itself
improved and tested). It licenses nothing.
- **Script:** `scripts/b20r107_contract_v2.py`, preregistered at `f844e1e` (SHA-256 `8adeb70f…`); the contract,
  `src/genesis/autonomy/feedback.py` (SHA-256 `2ff4a5ab…`).
- **Run:** alone on CPU 0, 242 s, on 23 Oct 2026 (15:15–15:19 SGT). `code_identity` `11a61541…`, the committed tree
  (`f844e1e`).
- **The other core.** While it ran, the builder wrote B20_R106's record (documents, two test runs of under a second
  each).

| File | What |
|---|---|
| `searches.jsonl` | 1,080 searches: signal (none, planted) x quirk sd (0, 1, 2 x sigma_e) x protocol (open, v1, v2) x 60 replicates |
| `summary.json` | sigma_e, the table per condition, the labels |

sigma_e = 0.149 edges, as in B20_R103.

## Result: V2_FIXES_POWER

**The threshold** (mean tau, in sigma_e):

| Quirk sd | v1 (A − B calibration, 1 host) | v2 (B − C calibration, 4 hosts) |
|---|---|---|
| 0 | 5.1 | 2.5 |
| 1 sigma_e | 7.3 | 3.6 |
| 2 sigma_e | 11.3 | 5.7 |

**Power** (mean true gain with the planted signal, as a fraction of the open protocol's):

| Quirk sd | v1 | v2 |
|---|---|---|
| 0 | 59% | **93%** |
| 1 sigma_e | 40% | **77%** |
| 2 sigma_e | 17% | **63%** |

**Honesty with no signal:**
- **False releases:** 1 of 180 searches for v1 and 1 of 180 for v2.
- **Mean claimed gain:** at most 0.013 edges (0.09 sigma_e) for either version.
- **Final optimism of v2's held-out numbers:** +0.05, +0.05 and -0.11 sigma_e, each within one standard error of zero.
- **Early stops:** every contract search stopped before its budget. v2 used about 700–870 evaluations, v1 about
  490–540, of 1,500.
- **The open protocol, by contrast,** over-reported by 0.5, 3.5 and 6.7 sigma_e, as in B20_R103.

**Labels (all against the truth):**
- **v2: WORKS.** It holds and keeps power: 63% of the open protocol's real gain even at the largest quirk.
- **v1: LEAKS by the preregistered bias tolerance.** Its mean final optimism is +0.30 sigma_e at quirk 0 and -0.29 at
  quirk 2, against a tolerance of ±0.25 sigma_e. Those means are 2.3 and 0.9 standard errors from zero. The
  tolerance was set below the standard error of a mean of 60 single held-out evaluations (up to 0.34 sigma_e at quirk
  2), so it partly tests luck. v1's power is lost either way (17% at quirk 2).
- **Headline: V2_FIXES_POWER** (v2 WORKS, v1 does not keep power).

## Against the expectation (stated before running)

| Expectation | What happened |
|---|---|
| v1 holds and is TOO_STRICT under the truth-based rule | Power lost (TOO_STRICT's half); HOLDS failed on the bias tolerance, within the noise described above, so LEAKS |
| v2 holds | Yes |
| v2's threshold about 2.5, 3.6 and 5.7 sigma_e | 2.5, 3.6 and 5.7 |
| v2 keeps at least half the real gain at quirks 0 and 1, and about half at quirk 2 | 93%, 77% and 63% |
| V2_FIXES_POWER slightly more likely than V2_TOO_STRICT | V2_FIXES_POWER |

## What it means

- **The judge can now be both honest and useful.** Calibrating on its own noise (two confirmation splits), with
  confirmation on several hosts, removes the worker's training quirks from the threshold. The threshold halves, and
  real progress is released even where the data are quirky. False releases stay at 1 in 180.
- **The price is evaluations**: about 50% more than v1, still about half the open protocol's budget, and it stops on
  its own.
- **Next.** Adopt v2 as the contract for any search that improves itself on repeated feedback. A later battery should
  test bias with a confidence interval, not a fixed tolerance below the standard error.
