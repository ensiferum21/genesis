# B20_R44 evidence: a registered ablation of E1's discovered representation, with a Lean-certified null control (DEV)

Builder-run. Nothing here is independently reviewed, and nothing licenses a claim. The registered
transform awaits review.
- **Script:** `scripts/b20r44_e1d_ablation.py`. It was committed before the run in `c68d0bc`, together
  with the transform in `kernel/replay_contracts.INTERVENTIONS`. Its SHA-256 (`2c26d109…6311`) was
  sent to the user beforehand.
- **Log:** `run.log`. 646 s, on one pinned core.
- **Development look:** three B20_R41 hosts that were already exposed. It is disclosed in
  `development_looks.json`, and no new hosts were used.

## Design (fixed before running)

**The component.** E1d's candidate is represent-and-repair over `cross_2`, a representation that B18's
grammar proposed. Lean checked it, and DEV ranking chose it.

**The registered ablation: `cross_2` → `ordered_2`.** The grammar, encoder space, search, repair and
budget stay the same. Only the decoder changes, to one that is weaker. Lean checked that
`ordered_2_within_cross_2` holds and that the converse is DISPROVED. `ordered_2` is sound on
triangle-free hosts.

**The null control: `adjacent_2`.** Lean checked that it is *equal* to `cross_2`, in both directions.
The truth for this arm is known: no difference. It shows what the whole pipeline reports when there
is nothing to find. It is CLEAN iff the 90% interval of candidate − null lies inside ±0.5. The idea
of a null world comes from design material the user supplied.

**Hosts.** 30 fresh DEV hosts, 10 per E1d setting, drawn from the B20_R43 calibration record. They
exclude 2,641 named identities.

**Reference.** The generated-rows route at 120 s.

**Analysis.** B20_R41's procedure, with the ablation as the only comparator.

## Result (`pilot_summary.json`, `rows.jsonl`, `hosts.json`, `power_analysis_centred.json`, `summary.json`)

All 30 hosts were certified, with reference wall times of median 16.9 s and max 25.4 s. No run failed.

| Arm | Total | At optimum | Mean gap to optimum |
|---|---|---|---|
| **Candidate** (`cross_2`) | 3,503 | 29/30 | 0.03 |
| Null control (`adjacent_2`, Lean-equal) | 3,502 | 28/30 | 0.07 |
| Ablation (`ordered_2`, Lean-weaker) | 3,291 | 0/30 | 7.10 |

| Check | Result |
|---|---|
| Candidate − ablation | **+7.07 per host** [6.47, 7.70], p = 5 × 10⁻⁵; W/T/L **30/0/0** |
| By stratum | +7.1 (n38, 0.8, 0.07), +6.5 (n40, 0.7, 0.06), +7.6 (n40, 0.8, 0.06) |
| Cost ratio | 1.00. Same search and budget; only the decoder differs. |
| DRAFT plan dry run | SUPPORTED: every check passes |
| Centred power | 15 per stratum (45 in all), power 0.86; false-positive rate 0.015 at zero effect |
| **Verdict** | **READY_FOR_REVIEW** |
| **Negative control** | candidate − null **+0.03** [−0.02, +0.09], W/T/L 1/29/0: **NULL_CONTROL_CLEAN** |

## What it means

- **The discovered representation is what helps.** On fresh hosts, weakening only its decoder, to
  one that Lean shows keeps a strict subset of its output, costs 7.1 edges per host on every host.
  That accounts for most of E1d's lead over the exact MIP at four times the budget (+9.8 to +10.6).
  This is the causal evidence GV3 asks for: "Does removing the new concept remove the improvement?"
- **The pipeline does not invent effects.** On the Lean-certified null, the pipeline reports +0.03,
  with 29 of 30 hosts exactly tied. The one difference is timing noise in the budgeted search.

## Limits

- **DEV, builder-run.** The transform is builder-registered and awaits review.
- **What can be licensed.** The most this can license is ABLATION_SUPPORTED: no placebo is possible
  for this component, as the docstring explains. It still needs a custodian-signed ablation
  evaluation of the E1d claim.
- **What the ablation removes.** It removes the *decoder* of the discovered representation, not the
  whole represent-and-repair method. The claim is about the representation the grammar discovered.
- **Exposure.** The 30 hosts are in `handoff/e1*/exposure_hosts_addendum_b20r44.json`.
