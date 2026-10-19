# B20_R67 record: registry v2's kind map leaves the core; a standard max-cut baseline kind

- **Run by:** the builder. Engineering only; no study, no claim, no rule, comparator or package decision changes.
- **Why now:** the B20_R65 handover review (two findings) and the next study, B20_R68, which needs the new kind.

## Problem 1: adding a v2 kind re-identified every other v2 kind

`docs/CANDIDATE_REGISTRY_V2.md` states that adding a kind module changes no other kind's identity. In the code the
kind map `KINDS` was a dict inside `candidates_v2.py`, and that file is one of the three core files hashed into every
v2 descriptor's implementation identity. Adding any kind therefore edited the core and changed every v2 descriptor
id, including the E1d package's `milp_highs_4x` (its comparator) and `milp_highs_tm`. B20_R63's `arms()` refuses to
run if HiGHS at 2 s differs from the package's `milp_highs_4x`, so every later E1d study would have broken.

**Fix.**
- The map moved to `src/genesis/candidate_kinds/kinds.py`, which is in no identity.
- So that the map cannot silently re-point a kind, `implementation_identity` now requires a kind module's first
  declared file to be its own source (`candidate_kinds/<module>.py`, resolved against the imported module's path)
  and hashes it. A kind name pointed at another module gets that module's identity, so every frozen descriptor of
  the kind is refused (`implementation identity differs from this code`). A module that declares another module's
  file raises `MALFORMED_KIND`.

**One-time cost.** Moving the map edited the core once, so the two stored v2 descriptors were re-identified once:

| Descriptor | Before (`4341806`) | After |
|---|---|---|
| `milp_highs_4x` | `1815deba…e976` | `a95b8040…cb5c` |
| `milp_highs_tm` | `9b737159…3c39` | `5aa4cc68…df26` |

Only `candidates_v2.py`'s digest changed; `candidate_kinds/milp_highs.py`, `graphs.py` and `models.py` have the same
digests, so what each descriptor runs is unchanged. `scripts/b20r67_refresh_v2_ids.py` rebuilt them from their own
kind, parameters and profile, refused to proceed unless the stored id is exactly the rebuilt descriptor with the
pre-R67 core digest, and recorded old -> new in `handoff/e1d/package_index.json` (`v2_identity_refresh_b20r67`).

**Evidence is not rewritten.** Record tests of pre-R67 evidence (B20_R41, R63, R64; B20_R66 ran on `4341806`)
compare the ids they recorded with `b20r67_refresh_v2_ids.pre_r67_id(descriptor)`: the id of exactly the descriptor
this code builds, with the pre-R67 core digest (`git show 4341806:src/genesis/candidates_v2.py`, SHA-256
`2f0d7341…41ed`). Any other difference still fails.

## Problem 2: E1d has no baseline from its own field

The review found that E1's frozen candidate, `represent-and-repair-v1` with the `cross_2` decoder, is exactly
one-flip max-cut local search from random two-colourings followed by a greedy triangle-free completion
(`invention/representations.py::represent_and_repair`). On dense hosts the largest triangle-free subgraph is close
to a maximum cut, so this is the classical approach to the problem. E1d's five baselines are an exact MILP and four
DSL programs; none is a max-cut heuristic.

**New kind `maxcut-tabu-v1`** (`candidate_kinds/maxcut_tabu.py`): repeated tabu search over one-vertex flips from
random two-colourings (best non-tabu flip; aspiration when a tabu flip beats the run's best; tenure n/10 +
U{0..n/10}; a run ends after 10n steps without a new best), each run's best cut completed greedily exactly as the
candidate completes its cut. Parameters `{cpu_seconds}` in (0, 60]; triangle-free domain only. It is a domain
baseline, not an exact one: it is not in `EXACT_BASELINE_KINDS`, so no comparator selection changes.

## Tests

- `tests_genesis/test_maxcut_tabu.py` (4): the map is outside every identity and dispatch is bound (adding a kind
  keeps the other identity; re-pointing a name changes it; a module declaring another's file is MALFORMED_KIND);
  parameters are closed; known optima (K10 gives 25, Turán; a bipartite host is kept whole); a runc run is metered by
  the cgroup, spends its budget and its witness re-checks.
- Record tests of B20_R41, R63 and R64 now compare recorded ids through `pre_r67_id`.
