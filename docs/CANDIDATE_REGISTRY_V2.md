# Candidate registry v2 (B20_R40; built; wired opt-in in B20_R42, not adopted)

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
  - Adding a kind module changes no other kind's identity. (Until B20_R67 this was not true: the
    kind map sat in `candidates_v2.py`, so adding a kind edited the core. See below.)
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

## The wiring (B20_R42; opt-in, pending review)

- **One entry point.** `genesis/candidate_registry.py` picks the registry by the descriptor's
  schema. The custodian runs every evaluation arm and every SELECT-panel baseline through it. A
  v1 descriptor takes exactly the v1 path.
- **Requests.** A v4 request still takes registry-v1 arms only. An evaluation request v5 (a v4
  request plus a named reference route) also takes registry-v2 arms. All arms share one resource
  profile, as before.
- **Comparators.** `custodian.select_comparator` accepts an exact registry-v2 baseline
  (`candidate_registry.EXACT_BASELINE_KINDS`, today `milp-highs-v1`) only when the study's
  adopted calibration rule names it (`EXACT_BASELINES_BY_RULE`).
  - The only rule that names it is the DRAFT `e1-hard-v3-draft` (B20_R41), and no study adopts
    it.
  - Under every adopted rule, selection is unchanged.
  - A request's baseline must still be the custodian's selected comparator, checked by
    descriptor id at registration.
- **Fairness.** In an evaluation, a v2 arm must share the candidate's resource profile. So a "4×
  budget" MIP is expressed by its `cpu_seconds` parameter within that profile: 2.0 s inside E1's
  2 s profile, whose sandbox limit is 3 s.
- **What stays unchanged.** `candidates_v2.py` still says "not wired". Its text is part of every
  v2 identity, so the B20_R41 descriptor ids are kept and the wiring lives in
  `candidate_registry.py`.

## B20_R67: the kind map leaves the core; a second kind

- **The defect.** The kind map `KINDS` was a dict in `candidates_v2.py`, and that file is hashed
  into every v2 identity. Adding a kind therefore changed the core, and with it every v2 descriptor
  id, including the E1d package's `milp_highs_4x` and `milp_highs_tm`. The design statement above
  was false in practice.
- **The fix.** The map moved to `candidate_kinds/kinds.py`, which is in no identity. To keep the
  map from silently re-pointing a kind, `implementation_identity` now requires a kind module's
  first declared file to be its own source (`candidate_kinds/<module>.py`, resolved against the
  imported module) and hashes it. A kind name pointed at another module gets another identity, so
  every frozen descriptor of that kind is refused; a module declaring another module's file is
  `MALFORMED_KIND`. Tests: `tests_genesis/test_maxcut_tabu.py::KindMap`.
- **The one-time cost.** Moving the map edited the core once, so every stored v2 descriptor was
  re-identified once. What each runs is unchanged (`candidate_kinds/milp_highs.py`, `graphs.py`
  and `models.py` have the same digests). `scripts/b20r67_refresh_v2_ids.py` rebuilt the two
  stored descriptors in `handoff/e1d/baselines.json` and recorded old -> new in
  `handoff/e1d/package_index.json` (`v2_identity_refresh_b20r67`). Evidence is never rewritten:
  record tests of pre-R67 evidence compare the ids they recorded with
  `b20r67_refresh_v2_ids.pre_r67_id(descriptor)`, the id of exactly this descriptor with the
  pre-R67 core digest (`git show 4341806:src/genesis/candidates_v2.py`).
- **The second kind, `maxcut-tabu-v1`** (`candidate_kinds/maxcut_tabu.py`): a standard max-cut
  tabu search over one-vertex flips (aspiration; tenure n/10 + U{0..n/10}; restart after 10n
  steps without a new best), each run's cut completed greedily to a triangle-free subgraph, as E1's
  candidate completes its cut. Parameters `{cpu_seconds}`; triangle-free domain only (a bipartite
  graph can contain 4-cycles). It is a domain baseline for E1d, which the B20_R65 review found
  lacked one: the frozen candidate is itself one-flip max-cut local search plus the same greedy
  completion. It is not an exact baseline and is not in `EXACT_BASELINE_KINDS`, so no comparator
  selection changes.

## B20_R69: physics-inspired kinds

- **`ising-dsb-v1`** (`candidate_kinds/ising_dsb.py`): discrete simulated bifurcation (Goto et al. 2019, 2021) on the
  antiferromagnetic Ising model of the host (J = −A), 32 replicas, 400 steps, dt = 0.5, c0 = 0.5 / (rms(J) √n), spins
  read as sgn(x), the candidate's completion. One CPU, BLAS limited to one thread. dt = 1 is unstable on dense hosts
  (B20_R69 record).
- **`maxcut-eo-v1`** (`candidate_kinds/maxcut_eo.py`): τ-extremal optimization (Boettcher and Percus), τ = 1 + 1/ln n,
  the same completion.
- Both are domain baselines with parameters `{cpu_seconds}` on the triangle-free domain; neither is an exact baseline.
