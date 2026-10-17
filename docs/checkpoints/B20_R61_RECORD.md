# B20_R61 record: the statistician's brief (B19-OPEN-4)

- **Built by:** the builder. Documentation and recomputation from committed files; no new evidence, nothing
  adopted.
- **Files:**
  - `docs/STATISTICIAN_BRIEF.md`;
  - `scripts/b20r61_statistician_brief.py`;
  - `tests_genesis/test_statistician_brief.py`.

## Why

Every GV3 package waits on a statistician's sign-off of the registered analysis and of the centred power model
(B19-OPEN-4). The material was spread across packages, scripts and records. The brief gathers it, flags what the
builder found, and lists the questions.

## What the recomputation found

**All nine stored power analyses reproduce exactly from their pilot rows.** This covers E1, E1b, E1b's two causal
follow-ups, E1b-C4 and its two, E1d, and E1d's ablation. Both the digest and the result match.

**Five findings for the statistician:**
1. **E1b-C4's placebo design is underpowered at its chosen size.** The stored power is 0.800 at 10 per stratum.
   With 10,000 simulations under the custodian's placebo family it is **0.764**. E1d, the other borderline row,
   holds at 0.821.
2. **Four causal power analyses are bound to the wrong hypothesis family.** They are E1b's ablation and placebo
   (B20_R28) and E1b-C4's (B20_R50). Each is bound to `sealed_evaluation`, while the custodian assigns
   `ablation`/`placebo` and refuses any other.
   - **The fix.** They must be recomputed before those follow-ups can be registered, as B20_R45 did for E1d.
   - **Recomputed:** 1.000, 0.980 and 0.992 at 10 per stratum; E1b-C4's placebo needs 12 (0.879).
3. **The claim wording outruns the rule.** Each `exact_claim` says "by at least the minimum useful effect", but the
   rule requires a point estimate of at least 0.5, not a lower bound.
4. **The stratum-level sign-flip sensitivity cannot fall below 0.125** with three strata (0.25 with two).
5. **Unsupported hosts cluster in one stratum.** All of E1d's are in planted_cluster:9491bde8, while the 5% cap is
   global.

The brief also asks about:
- the symmetric null of the sign-flip test;
- the unadjusted interval in a Holm-adjusted decision;
- the family sizes;
- the design effect;
- comparator selection;
- the certification studies' rules and the BY attempt family.

## Tests

`tests_genesis/test_statistician_brief.py` (7, about 90 s). It checks:
- the nine reproductions;
- the decision records against their power analyses;
- that the tables and every derived number appear verbatim in the brief;
- the family mismatches;
- the sign-flip floor;
- the Monte Carlo rule.

## Nothing changed in the packages

The four mismatched power analyses and the E1b-C4 placebo size are flagged, not fixed. They live in DRAFT packages
and records whose fix belongs to the freeze the reviewer authorises.

## Open

B19-OPEN-4 is updated: the brief is ready for an independent statistician.
