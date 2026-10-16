# B20_R40 record: candidate registry v2, with a time-matched exact-MIP baseline kind (built, not wired)

- **Run by:** the builder. This is engineering only, with no study. Nothing is wired into the
  custodian or into evaluation requests.
- **Commit:** the B20_R40 commit.
- **Design note:** `docs/CANDIDATE_REGISTRY_V2.md`.

## Why

B20_R33 and B20_R38 show that GV3's "beyond strong baselines" needs an exact-MIP comparator. A
custodian can only compare with registered descriptors, and registry v1 cannot take a new kind
without changing the frozen E1/E1b descriptor ids. This is NEXT_ACTIONS engineering item 2.

## What was built

**`src/genesis/candidates_v2.py`.** Registry v2.
- **Schema:** `genesis-candidate-descriptor-v2`.
- **Closed kind map:** one module per kind under `src/genesis/candidate_kinds/`.
- **Per-kind identity:** the v2 core, the kind's files, `graphs.py` and `models.py`. It does not
  include `candidates.py`.
- **Runner:** v1's discipline, re-implemented. It has runc with cgroup metering and process
  rlimits, the child sees only the view, output is strictly decoded, and the domain checker
  re-checks the result.
- **Mutual refusal:** each registry refuses the other's descriptors.

**`src/genesis/candidate_kinds/milp_highs.py`, `milp-highs-v1`.** The exact MILP run by HiGHS,
pinned to one core in the child, with the best incumbent returned at the time limit. Triangle-free
only.

**A check run during development:** a `milp-highs-v1` descriptor ran in both isolations on a
B20_R38 host, which is already exposed:
- runc: SUCCESS, cgroup-metered;
- process: SUCCESS;
- the frozen E1/E1b descriptors still rebuild under v1 with no problems.

## Tests

`tests_genesis/test_candidates_v2.py` (6) checks:
- descriptors rebuild, and any alteration is refused;
- the identity is per kind and excludes registry v1, and the frozen E1/E1b descriptors are
  unchanged;
- each registry refuses the other's descriptors;
- the MILP kind is exact on K6 (9 edges), and its witness is checked;
- the child sees only the candidate view;
- the decoder is strict.

## Open

Wiring v2 into requests, receipts and the custodian is a reviewed change. So is naming the MIP
comparator in a plan. Kinds with registered interventions and a supervised SAT child can now be
added as separate v2 modules, without touching the frozen packages.
