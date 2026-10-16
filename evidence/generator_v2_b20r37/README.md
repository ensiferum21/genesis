# B20_R37 evidence: generator v2 (patterns on up to seven vertices) and certification coverage in the dense regime (DEV)

Builder-run. Nothing here is independently reviewed. It licenses no claim and changes no
evaluator.
- **Script:** `scripts/b20r37_generator_v2.py`. It was committed before running in `9e043b8`, and
  its SHA-256 was sent to the user beforehand.
- **Code:**
  - `src/genesis/invention/cuts_v2.py`;
  - the route options in `src/genesis/discovery/generated_certify.py`;
  - `formal_research.search.split_options`.
- **Log:** `run.log`, 3,049 s, in one go.

## Part A: generation and checking (`part_a.json`, `package.json`)

**Generation.** It searched 1,245 graphs on 4–7 vertices. Of these:
- 258 are connected with every edge in a triangle;
- 238 are implied by the triangle rows;
- 11 are implied by earlier patterns;
- **9 are kept**:
  - K5 (≤ 6) and the 5-wheel (≤ 7), as in B20_R31;
  - seven 7-vertex patterns with 13–21 edges, among them K7−e (≤ 12) and K7 (≤ 12).

ex(F) comes from HiGHS's MILP, and each value was re-checked as a triangle-free subset. The unit
tests check every value of 16 or fewer edges against exhaustive search.

**Lean.** All 12 obligations were screened (no counterexample) and CHECKED:
- `pc_adj_le_one`, the new `pc_adj_comm`, `pc_bridge`;
- the 9 pattern bounds. Each bound's proof is an integer rounding certificate from the pattern's
  LP dual (`lp-certificate-sum`): scaled instances of the bridge and earlier bounds, summed, then
  `omega`.

The proofs of K7−e and K7 have 20 and 21 atoms. They need more elaboration than the default
budget, so their recipe places `set_option maxHeartbeats 4000000 in` before the theorem. That is
an option the checker allows.

**Cost.** Construction 233.7 CPU s (the checker reported 170.8 s).

## Part B: certification coverage (`part_b.json`, `part_b_rows.jsonl`, `hosts.json`, `certificates/`)

**Design.** 40 fresh hosts, 20 per dense setting. Both routes start from the evaluator's seed
witness and get 60 s each.
- **v1:** B20_R35's route (K5 and W5).
- **v2:** this registry, with symmetry-breaking enumeration, densest patterns first, and a limit
  of 15 s, 50,000 copies per pattern or 80,000 in all.

| | v1 (K5, W5) | v2 (9 patterns) |
|---|---|---|
| Certified within 60 s | **30/40** | **33/40** |
| … planted n40 (0.8, 0.06) | 17/20 | **19/20 (meets the 90% limit)** |
| … erdos n30 p0.42 | 13/20 | 14/20 |
| Discordant | — | 4 for v2, 1 for v1 |
| Median wall time | 26.5 s | 34.0 s |
| Median LP rows | 34,420 | 80,325 |

| Test | Result | Passes |
|---|---|---|
| McNemar (one-sided) | p = 0.19 | no |
| Mean wall saving v1 − v2 | −3.7 s per host, 90% interval [−6.9, +0.2]: v2 is slower | — |
| Soundness | every certificate VALID, values agree | yes |

**Verdict: NO_COVERAGE_GAIN.**

**Detail:**
- v2's bound is lower than v1's on 5 hosts, and never higher.
- The one host v1 certified and v2 did not (`…711-0010`) ran out of time in v2's larger LP.
- Six hosts remain uncertified by both, with gaps of 1–3.
- The 4 certificates on hosts certified by v2 alone are kept in `certificates/`.

## What it means

- **The generator scales.** The invention loop extended itself to seven vertices. Lean checked
  every row it generated, including K7 and K7−e, via certificates derived from their own LP
  duals.
- **The extra rows add little at this budget.** v1 already certifies most of these hosts. Here
  that was 30/40, against 27/40 in B20_R35's sample. v2's larger LP costs time. On planted
  clusters v2 reaches 19/20, which meets the 90% limit, while v1 reaches 17/20. One setting of 20
  hosts is not enough to call that a gain, and the preregistered test fails.
- **For GV3 (B20R33-OPEN-1).** With either generated-row route, the dense planted regime is
  certifiable at roughly the 85–95% level within 60 s, against 1/20 for the evaluator alone in
  B20_R35. Whether a frozen candidate is beyond an exact MIP there is B20_R38. Using the regime in
  a real run would need the evaluator to adopt a generated-row route, which is a reviewed
  trust-path change (B20R35-OPEN-1).

The 40 hosts are in `hosts.json`, and the handoff exposure addenda list them
(`handoff/e1*/exposure_hosts_addendum_b20r37.json`).
