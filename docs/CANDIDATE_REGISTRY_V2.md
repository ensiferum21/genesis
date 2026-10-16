# Candidate registry v2 (B20_R40; built, not wired)

## Why

Registry v1 (`src/genesis/candidates.py`) is closed. Every v1 descriptor's implementation
identity includes `candidates.py`, so adding a kind changes the descriptor ids of all frozen v1
candidates. That includes the E1 and E1b packages, which are READY_FOR_REVIEW. Two needs were
blocked by this:
1. **A time-matched exact-MIP baseline.** B20_R33 found that HiGHS is always optimal on the
   decided family. B20_R38 found a dense regime where E1's frozen candidate beats it. A custodian
   can compare a candidate with a baseline only if that baseline is a registered descriptor run
   by the custodian's runner.
2. **Kinds with registered interventions, and a supervised child** (NEXT_ACTIONS engineering
   item 2). One example is a pipeline with a SAT finisher.

## Design

- **Schema.** `genesis-candidate-descriptor-v2`, with the same fields as v1.
- **One module per kind**, under `src/genesis/candidate_kinds/`. Each declares its domains,
  `check_parameters`, the child `solve(view, params, cpu_seconds, seed)`, and `FILES`.
- **Identity.** A v2 descriptor's identity covers `candidates_v2.py`, the kind's own files,
  `graphs.py` and `models.py`.
  - Adding a kind module changes no other kind's identity.
  - Changing the v2 core changes every v2 identity, on purpose.
  - v1 files are not part of v2 identities.
- **Runner.** v1's discipline, re-implemented in `candidates_v2.py`:
  - **Isolation:** a closed kind map (no module name, path or code comes from data), with the
    runc sandbox and cgroup metering, or process rlimits on DEV.
  - **What the child sees:** only the candidate view, the data parameters and the limits.
  - **Checking the output:** a strict decoder, then the domain checker recomputes the value.
- **Mutual refusal.** Each registry refuses the other's descriptors.

## First kind: `milp-highs-v1`

The exact MILP for the largest triangle-free subgraph, run by HiGHS through the pinned scipy.
- **Parameters:** `{cpu_seconds}`.
- **Single core:** the child pins itself to one CPU before importing scipy, so the cgroup meter
  stays comparable with single-threaded arms.
- **Domain:** triangle-free only.
- **Output:** the best incumbent at the time limit, re-checked by the domain checker.

## What wiring it in would take (a reviewer's decision)

1. **Requests.** Evaluation requests (v4) and receipts must accept v2 descriptors beside v1,
   with the registry named in the receipt.
2. **Custodian.** `custodian.check_request_against_export` must rebuild v2 descriptors with
   `candidates_v2.descriptor_problems`.
3. **Comparators.** The analysis plan must name which v2 baselines are comparators. For a dense
   E1 study, that would be `milp-highs-v1` at the candidate's budget, or at a multiple fixed in
   advance.
4. **Exposure.** Exposure and leak checks are unchanged: the child sees only the candidate view.

None of this changes the frozen E1/E1b packages or their descriptor ids.
