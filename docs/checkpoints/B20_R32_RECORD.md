# B20_R32 record: certification with generated rows, prospective (s15.3 / W10, W13; GV4 and GV3 path)

- **Run by:** the builder, on DEV. Nothing here is independently reviewed, and nothing licenses
  a claim. No evaluator was changed.
- **Commits:**
  - `d695705` (setup): the checker, the route, the script and the unit tests, committed before
    the run. The script's SHA-256 was sent to the user beforehand.
  - The post-hoc MILP cross-check script, committed before it ran.
  - The result commit.
- **Evidence:** `evidence/generated_certification_b20r32/`.

## Why

B20_R31's float diagnostic suggested that its generated rows let the LP close the certification
gap on 10 of the 18 B20_R30 hosts that needed SAT. This step builds the exact route and measures
it, preregistered, on fresh hosts.

## What was built

**`verification/lp_dual_rows.py`.** An exact checker for LP dual certificates whose rows may be
copies of generated patterns. Its registry admits a pattern only from a CHECKED statement of an
intact theory package, and three conditions bind it to what Lean checked:
- the package uses the trusted `GTDefs`;
- it defines `PC.adj` exactly as 0/1 adjacency;
- the statement's text is verbatim the checked conjecture, of the exact pattern-bound form.

The v1 checker, its identity and the certificate bundles are unchanged.

**`discovery/generated_certify.py`.** The evaluator's joint certification, with the generated
rows in the LP step. It is not wired into the evaluator.

## Result

On 90 fresh `e1b` hosts, both routes certify all 90.

| Measure | Evaluator route | With generated rows |
|---|---|---|
| Upper bound from an exact LP dual | 87 hosts | 89 hosts |
| Total wall time | 192 s | 87 s |

The checks:

| Check | Result | Passes |
|---|---|---|
| Discordant hosts (LP-certified by one route only) | 2 against 0, McNemar p = 0.25 | no |
| Mean wall saving per host | +1.17 s, 90% interval [−0.10, +3.22] | no |
| Soundness | every certificate VALID, values agree | yes |

**Verdict: NO_CERTIFICATION_UTILITY.**

**Why.** The rows closed 2 of the 3 SAT-needing hosts. But this sample had only 3 such hosts, where
B20_R30's had 18. On the 87 easy hosts the rows cost +0.11 s per host.

**Why the samples differ.** The share of SAT-needing hosts varies sharply between samples of the
same settings: planted_cluster 10/30 in B20_R30 against 0/30 here, Fisher p ≈ 0.0004. No
structural cause was found.

**Post-hoc cross-check.** Every SAT/DRAT-certified optimum (21 hosts) was re-solved with HiGHS's
exact MILP and re-checked by the domain checker. All 21 agree, so the evaluator is not at fault.

## Findings for the reviewer

1. **Certification components.** On this evidence, the generated rows are a sound certification
   component that works where it applies: they closed 12 of 21 SAT-needing hosts across the two
   samples. On a fresh sample, the benefit was too rare to show prospectively. A study powered on
   SAT-needing hosts would have to enrich for them. One way is to screen fresh hosts by their
   float LP gap against a known witness, with the screen fixed in advance.
2. **A strong-baseline question for E1 and E1b (GV3).** HiGHS's exact MILP finds and proves the
   optimum of these hosts in under 0.72 s wall. E1 and E1b compare their candidates only with
   time-matched fixed DSL programs. Whether "beyond strong baselines" is met needs a measured
   MIP arm. That measurement is B20_R33.

## Tests

| Test file | Tests | What they check |
|---|---|---|
| `tests_genesis/test_lp_dual_rows.py` | 6 | registry binding (definitions, texts, statuses); strict statement parsing; bounds on K6 and two disjoint W5; eight tamperings rejected, plus wrong task, domain and registry; the route certifies without SAT when the bound meets the witness |
| `tests_genesis/test_generated_certification.py` | 4 | the summary and verdict follow from the rows; kept certificates re-check VALID; the hosts are fresh and in the addenda |

## Open

- **B20R32-OPEN-1:** the certification route has no prospective utility on an unenriched sample.
- **B20R32-OPEN-2:** the strong-baseline question for E1 and E1b.
