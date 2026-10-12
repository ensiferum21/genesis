# CRPD-3 (B20_R2): orbit-sensitivity probe of E (DEV diagnostic)

`python3 scripts/b20r_orbit_probe.py evidence/orbit_probe_b20r` ran E (--auto, pinned) on fresh
targets under six presentations that are equivalent by construction (goal sides swapped, axioms
reversed, variables cycled in goal and axioms, all combined) plus two identical repeats, each a
bounded, cgroup-metered attempt on an otherwise idle host. Decision rule fixed in the script before
running: REPORTED iff the share of targets with mixed outcomes across presentations exceeds the
share across repeats by at least 0.10.

| System | Targets | Limit | Proved (every presentation) | Mixed across presentations | Mixed across repeats | Median CPU max/min (presentations / repeats) | Verdict |
|---|---|---|---|---|---|---|---|
| ba_sheffer | 20 | 1 s | 11 | 0.00 | 0.00 | 1.37 / 1.20 | NOT_DETECTED |
| ba_wolfram | 10 | 3 s | 0 | 0.00 | 0.00 | n/a | NOT_DETECTED |
| ba_huntington | 20 | 1 s | 18 | 0.00 | 0.00 | 1.32 / 1.16 | NOT_DETECTED |

Reading:
- E's outcome did not depend on these presentations for any of the 50 targets. CRPD v3 §4.1
  (symmetry-guided concept search from presentation sensitivity) has no measured headroom on these
  families; its kill switch applies here. Other transformations (theory-dependent ones, premise
  selection) were not tested.
- Identical repeats agreed on every outcome. On a quiet host, fixed-limit E outcomes were
  deterministic for these targets, consistent with B20-OPEN-3 attributing the hard-system noise to
  load. Wolfram proves nothing at 3 s here, so research-run noise on Wolfram is not measured by this.
- The targets (seeds 401-403) are listed under `exposure` in probe.json so later studies exclude them.

DEV only; E's outcomes are prover claims; nothing was admitted as a proof.
