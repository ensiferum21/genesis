# B20_R35 record: generated-row certification where the evaluator fails (s15.3 / W13; GV4 and GV3 paths)

- **Run by:** the builder, on DEV. Nothing here is independently reviewed, and nothing licenses
  a claim. No evaluator was changed.
- **Commits:**
  - `50e567a` (setup): the script; the route's optional separation budget, with defaults
    unchanged; and tests. All were committed before the run, and the SHA-256s were sent to the user
    beforehand.
  - The result commit that follows it.
- **Evidence:** `evidence/dense_certification_b20r35/`.

## Why

B20_R32 found that the generated-row certification route is sound but has no prospective utility
on an unenriched sample, because hosts the evaluator could not certify were rare there
(B20R32-OPEN-1). B20_R34 then found two settings where the evaluator's 60 s certification mostly
fails. A look at three of those hosts showed something further: the Lean-checked K5 rows alone
bring the LP floor down to the optimum, against triangle-LP gaps of 8. This step preregisters the
enriched study.

## Result

On 40 fresh hosts, 20 per setting, both routes ran at 60 s from the same seed witness.

| Measure | Evaluator | With generated rows |
|---|---|---|
| Certified | 7 | 27 |

| Test | Result | Passes |
|---|---|---|
| Discordant hosts (certified by one route only) | 20 against 0, McNemar p ≈ 1 × 10⁻⁶ | yes |
| Mean wall saving per host | +18.5 s, 90% interval [+13.9, +23.3] | yes |
| Soundness | every certificate VALID, values agree | yes |

**Verdict: CERTIFICATION_UTILITY.**

## What it means

**For GV4.** This is the first machine-generated, Lean-checked component in this project with a
prospective, preregistered DEV utility. The utility is in certification:
- the generator enumerated every graph on at most six vertices and kept the non-redundant
  bounds;
- Lean checked them;
- an exact checker verifies the certificates built from them.

Whether a certification component counts toward "better improver" is the open question for the
GV4 design reviewer (B20R31-OPEN-1, B20R9-OPEN-1). No construction component has yet shown
utility.

**For GV3 and the strong-baseline question (B20R33-OPEN-1).** The route widens what the evaluator
could certify. But in these dense settings it reaches 27/40 at 60 s, below the 90% limit. To be
used, it would need four things:
- reviewed wiring into the evaluator, with a new checker identity and the Lean package in custody;
- a higher budget, or more generated rows (for example, 7-vertex patterns) to reach the limit;
- a versioned family rule and calibration;
- a comparison with stronger certifying baselines.

**No novelty claim.** The bounds are classical. What is new is that the system generated and
checked them, and that they were then useful on fresh tasks.

## Tests

| Test file | Tests | What they check |
|---|---|---|
| `tests_genesis/test_dense_certification.py` | 4 | the settings and hosts; the summary and verdict follow from the rows; the 20 kept certificates re-check VALID at the certified value; the hosts are fresh and in the addenda |
| `tests_genesis/test_lp_dual_rows.py` | +1 | limited separation (size order, a per-pattern cap, a stop) still yields valid certificates |

## Open

**B20R35-OPEN-1 (new).** A positive DEV certification result, pending review. Questions:
- whether a certification component counts toward GV4;
- whether to wire the generated-row checker into the evaluator (a trust-path change);
- comparison with stronger certifying baselines;
- coverage below the 90% limit.

**B20R32-OPEN-1** is answered by this enriched study.
