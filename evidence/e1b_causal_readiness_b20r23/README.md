# E1b causal readiness pilot (B20_R23, DEV)

**Script:** `scripts/b20r23_e1b_causal_readiness.py`. Its rules are in the docstring and were written while the readiness pilot was still running.
- **Commit:** `d1f415a`, made before the run.
- **External anchor:** the script's SHA-256 (`90dbdd75…1b19e`) was sent to the user in the conversation before the run, because GitHub credentials were unavailable.

**Question.** Is the LP signal the active ingredient of the E1b candidate? A better-solver claim reaches the causal levels only through signed ablation and placebo evaluations of a registered intervention. This pilot asks whether those follow-ups would be ready for review.

**Registered intervention** (`replay_contracts.INTERVENTIONS`, component `init` of `construct-pipeline-v1`):

| Arm | `init` | What it does |
|---|---|---|
| candidate | `lp_greedy` | LP-ordered greedy, then LP-perturbed restarts, 2.0 CPU s |
| ablation | `random_greedy` | random-order greedy restarts for the same budget; no LP |
| placebo | `lp_shuffled_greedy` | the same LP solve and restarts, with the LP values permuted among the edges (seeded); the cost and the procedure stay, the signal goes |

Both intervened descriptors were checked with `intervention_problems` before any run. Every arm ran through `candidates.run(isolation='runc')` under the readiness pilot's profile and cgroup meter.

**Hosts.** 10 fresh DEV hosts per setting (C1 triangle-free erdos n30 p0.3, C2 triangle-free erdos n40 p0.2, C3 C4 erdos n30 p0.2). They are screened against 1,054 exposure identities, including the readiness pilot's 36 hosts.

**Reference optimum.** `obstruction.certify` with 120 s per host. Certified: C1 10/10, C2 9/10, C3 **7/10**. The rule requires 8 of 10.

## Result

| | triangle_free_host_v1 (19 scored) | c4_host_v2 |
|---|---|---|
| Candidate − ablation | **+1.42** per host (C1 +1.60, C2 +1.22), 15 / 4 / 0, CPU ratio 1.02 | not scored |
| Ablation: dry run, power | SUPPORTED, estimate 1.41 [1.03, 1.83]; power CHOSEN at 10 per stratum (0.99) | — |
| Candidate − placebo | **+2.53** per host (C1 +3.00, C2 +2.00), 19 / 0 / 0, CPU ratio 1.00 | not scored |
| Placebo: dry run, power | SUPPORTED, estimate 2.50 [2.01, 3.03]; power CHOSEN at 10 per stratum (0.85) | — |
| Hosts where the arm reaches the optimum, candidate / ablation / placebo | 17 / 4 / 0 | 1 / 0 / 0 (of 7) |
| **Verdicts** | ablation **READY_FOR_REVIEW**, placebo **READY_FOR_REVIEW** | ablation and placebo **UNSETTLED_REFERENCE** |

Diagnostics only, not verdicts:
- On C4, over all 10 hosts, candidate − ablation is +0.7 and candidate − placebo is +2.2.
- The placebo scores below the ablation on both domains (−1.1 on triangle-free, −2.0 on C4). A plausible reason, not tested here: shuffled LP values impose a fixed, uninformative order that the restarts' perturbation (noise 0.35 on values in [0, 1]) only partly breaks, so the placebo searches less widely than random order. A PLACEBO_CONTROLLED level would therefore show that *this* placebo does not reproduce the effect. It would not show that every cost-matched procedure falls short.

## What this means

- On triangle-free hosts, removing the LP ordering costs 1.4 edges per host, and scrambling it costs 2.5. Both follow-ups are powerable under E1's design. The LP signal is the active ingredient on DEV.
- On C4 n30 p0.2 the reference cannot be certified often enough at 120 s: 9 of 12 hosts in the readiness pilot, 7 of 10 here. A C4 study needs a certification budget or a family decided in advance, not one changed after this result.
- This is a DEV diagnostic. It licenses no claim, and a causal level needs signed custodian evaluations.

## Files

- `rows.jsonl`: per host, every arm's value, status, cgroup CPU and meter, and the certification result.
- `hosts.json`
- `pilot_rows_<domain>_<contrast>.json`
- `power_analysis_centred_<domain>_<contrast>.json`
- `summary.json`
- `console.log`, `run.log`
