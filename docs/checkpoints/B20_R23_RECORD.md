# B20_R23 record: construction pipelines as candidates, and E1b readiness (GV3 path)

Builder-run engineering batch with two preregistered DEV pilots. Nothing here is independently reviewed, and nothing licenses a claim.

## What changed

**Candidate kind `construct-pipeline-v1`** (`src/genesis/candidates.py`). This was the GV4 draft's first blocked item.
- A pipeline is data-only: `{init, frac, finish, cpu_seconds, seed}`.
- Each domain has a closed list of `init` components:
  - `lp_greedy`, `random_greedy`, `lp_shuffled_greedy`;
  - the time-matched DSL programs (`dsl:<name>`);
  - on triangle-free hosts, the licensed menu representations (`rep:<id>`, SUFF/EQ only).
- There are three `(frac, finish)` shapes: `(1.0, none)`, `(0.5, lp_restarts)` and `(0.25, lp_restarts)`.
- It runs in the OCI sandbox under the same profile and cgroup meter as every other arm. BLAS threads are pinned to 1, because the child may not create threads (RLIMIT_NPROC 0). For the same reason the SAT finisher, which needs a subprocess, is not a v1 component.
- Its implementation identity binds `candidates.py`, `discovery/construct.py`, `invention/representations.py`, `dsl.py`, `graphs.py` and `models.py`.

**Registered interventions** (`kernel/replay_contracts.INTERVENTIONS`). The LP guidance of an `lp_greedy` initialiser (component `init`) is now registered:
- **ablation** `random_greedy`: random-order restarts, no LP;
- **placebo** `lp_shuffled_greedy`: the same LP solve and restarts, with the LP values permuted among the edges (seeded).

The existing custodian and kernel checks therefore reach ABLATION_SUPPORTED and PLACEBO_CONTROLLED for a pipeline candidate, with no change to those checks.

## DEV pilots (rules in each script's docstring, committed before the run)

The GitHub push was unavailable (no credentials in the session). So each script's commit and SHA-256 were also sent to the user in the conversation before it ran, as an external anchor.

| Pilot | Commit, SHA-256 | Triangle-free (C1 n30 p0.3, C2 n40 p0.2) | C4 (C3 n30 p0.2) |
|---|---|---|---|
| E1b readiness: candidate vs the strongest time-matched DSL baseline, E1's decided design | `8d47cf8`, `82936b95…` | +1.79 per host (18 / 6 / 0), CPU ratio 1.02, candidate at the optimum on 22/24, power 12 per stratum: **READY_FOR_REVIEW** | +1.00 (4 / 5 / 0), 9/12 certified, power 20: **READY_FOR_REVIEW** |
| E1b causal readiness: candidate vs ablation, candidate vs placebo | `d1f415a`, `90dbdd75…` | ablation +1.42 (15 / 4 / 0), placebo +2.53 (19 / 0 / 0): both **READY_FOR_REVIEW** | 7/10 certified: **UNSETTLED_REFERENCE** |

**Common setup.**
- Hosts: fresh DEV hosts, screened against every graph host named in `evidence/` and `handoff/` plus the regenerated E1 set (1,018 identities, then 1,054).
- Arms: every arm through `candidates.run(isolation='runc')`.
- Reference: `obstruction.certify` with 120 s per host.

**Further findings.**
- On triangle-free hosts the candidate also beats E1's own `cross_2` candidate at the same 2.0 s budget, by +1.375 per host (21 / 3 / 0).
- The placebo scores below the ablation. PLACEBO_CONTROLLED would therefore speak about this placebo only.

Evidence: `evidence/e1b_readiness_b20r23/` and `evidence/e1b_causal_readiness_b20r23/`, each with a README.

## Handoff package `handoff/e1b/` (DRAFT)

Built by `scripts/b20r23_e1b_package.py`. Per domain, it contains:
- the candidate, time-matched baseline and intervention descriptors;
- a real frozen DEV campaign export with the candidate frozen in it;
- a DRAFT decision record, whose frozen copy has no structural problems;
- the power analysis.

It also contains 1,084 exposure hosts.

The custodian's SELECT step is **BLOCKED**: there is no study calibration `e1b`, and nothing was relaxed to make one.

## What this means

- E1b is the first candidate on this line whose E1-design pilot can be powered, together with its causal follow-ups. That holds on triangle-free hosts. E1 itself stays UNDERPOWERED (B20R12-OPEN-1).
- The candidate is builder-written, so E1b is a GV3 path. GV4 still needs components that a research process invents.
- **New open item, B20R23-OPEN-1: E1b's host family.** `e1-hard-v1` applies to E1 only, by the user's decision. The options are listed in `handoff/e1b/README.md`.

## Tests

`tests_genesis/test_candidate_custody.py::ConstructPipeline` (3 tests):
- parameters are typed and bounded;
- each domain's init list is closed;
- a representation is refused on C4;
- pipelines run in runc with checked witnesses and charged CPU, and also on the process path;
- the ablation and placebo are registered;
- every non-registered variant is refused (wrong transform, two components changed, seed, a non-LP init);
- the placebo runs in runc.

`tests_genesis/test_b14_open4_contracts.py` passes unchanged.

## Still open

- B20R23-OPEN-1, the E1b family decision.
- B20R12-OPEN-1, the E1 design decision.
- The statistician's sign-off of the centred power model (B19-OPEN-4).
- An independent custodian.
- The SAT finisher as a pipeline component, which would need the runner to allow one supervised child process.
