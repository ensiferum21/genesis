# B20_R57: the transferred sum-free rows on hosts hard for the conventional route (GV6 second target; DEV)

- **Script:** `scripts/b20r57_sf_hard_certification.py`, preregistered in commit `a64952b`.
  SHA-256 `df93867e…e1cf13`.
- **Run:** the builder, pinned to one core, 5,633 s.
- **Code identity:** `d72ef9cd…`.
- **Status:** a DEV measurement. It licenses nothing, and nothing is wired.

## Question

B20_R56 found NO_CERTIFICATION_UTILITY for B20_R55's transferred rows on an unenriched sample. After the fact, the
rows did better where the conventional route struggled. As in B20_R32 → R35, this study tests that prospectively,
on a population defined by the conventional route alone:
- fresh candidates are drawn as in B20_R56;
- each gets the 10 s HiGHS witness;
- route a (Schur rows only) runs alone for 20 s, and a candidate is included only if route a does not certify it.

The screen included 40 of 72 candidates: 20 of 43 at (300, 0.6) and 20 of 29 at (360, 0.6). Both routes then ran
60 s each, as in B20_R56.

## Result: **CERTIFICATION_UTILITY** (primary) and **BOUND_UTILITY** (secondary)

| | a: Schur rows only (conventional = ablation) | c: with the transferred rows |
|---|---|---|
| Certified (of 40) | 14 | **22** |
| Certified by one route only | 0 | 8 |
| Median wall time | 60.0 s | 49.6 s |
| Total wall time | 2,010 s | 1,769 s |
| Median nodes | 520 | 121 |

The coverage rule's four tests:

| Test | Result | Passes |
|---|---|---|
| Soundness | Every certificate VALID, every witness sum-free, values agree | yes |
| Coverage | 22 ≥ 14 | yes |
| McNemar (one-sided) | p = 0.0039 | yes |
| Wall saving a − c | **+6.02 s per host**, 90% interval [2.50, 9.88] | yes |

**Certified bound (secondary).** The mean upper-bound difference a − c is **+6.875**, 90% interval [5.375, 8.475].
The minimum is 2, so it passes. c's certified bound is lower on 26 of 40 hosts; the other 14 are both certified at
the same value.

**By setting.**
- (300, 0.6): 13 vs 9 certified.
- (360, 0.6): 9 vs 5 certified.
- Each setting has 4 hosts certified by c only.
- On the 14 hosts both routes certify, c is faster on 8.

## Interpretation

On hosts the conventional route cannot certify in 20 s, the transferred, Lean-checked rows certify more optima
(22 vs 14, 8/0 discordant), faster, and with much tighter certified bounds. With B20_R56, this is the C4 pattern
(B20_R47 → R48) seen again in a different theorem family: the rows pay off where the conventional relaxation is
the bottleneck, and cost time where it is not.

**Scope.**
- The population is defined by the conventional route's 20 s screen (35% certified by a at 60 s).
- The attribution is direct: route a is the same tree without the rows (the registered ablation).
- This is a seventh certification attempt in the false-discovery family. Under Benjamini–Yekutieli at q = 0.1 over
  13 attempts, p = 0.0039 is below its step-up threshold (3 × 0.1 / (13 × 3.18) ≈ 0.0073).
- It is still DEV and builder-run. Whether a different theorem family with the same abstract structure counts as
  "structurally different" for GV6, and whether certification utility counts as "helps", are the reviewer's
  decisions (B20R46-OPEN-1, B20R35-OPEN-1).

## Files

- `screen.jsonl`: all 72 candidates with their witnesses and 20 s screen outcomes.
- `rows.jsonl`: per included host, both routes.
- `summary.json`: both verdicts, tallies, and the registry and checker identities.
- `certificates/`: the 8 certificates of hosts certified by c only.
- `run.log`: the log.

## Tests

`tests_genesis/test_sf_hard_certification.py` (7). The design tests check the constants, the screen with resume,
and both verdict rules. The record tests check:
- the screen's inclusion and the candidates;
- both verdicts recompute;
- the witnesses are sum-free;
- the kept certificates re-check VALID.
