# B20_R168 record: PT-1's part 1 ablation, one size cap for program representations, and the PT-1 study drafted (engineering; DEV)

**Engineering, by the builder, on CPU 1, 28 Oct 2026, while B20_R157 (F4) ran on CPU 0.** Nothing here ran on
family A, B or C. It licenses nothing.

## What was built

1. **Part 1's usefulness ablation, a candidate protocol** (`src/genesis/frontier/ablation.py`; open item 4 of
   `docs/handoff/PT1_DESIGN_DRAFT.md`).
   - `credit` names the representation the discovering branch searched, how it was made (derivation or
     abstraction), and its lineage back to a starting representation. A discovery in a starting representation
     credits nothing.
   - `ablate` re-runs the discovering approach through the domain's public `step`. Each run gets the branch's
     compute when it verified, which the engine's `verified` event now records as `t`. It uses k fresh seeds, the
     same in every arm, in the credited representation, its lineage, and every starting representation.
   - *Useful* iff only the created representation verifies. The ablation's compute is returned so that a study can
     charge it.
   - 6 tests (`tests_genesis/test_frontier_ablation.py`), on a toy domain with a known answer and on invented
     bounds.
   - The forbidden-concept audit caught an identifier while this was built: `discovery` contains the stem "cover".
     It was renamed; the audit was not changed.
2. **One size cap for every program representation.** `GammaRep`, `GammaPlus` and `GammaLib` take `max_n`, and
   `ConjectureDomain(program_max_n=...)` passes one cap to all three. The default, attack.MAX_N = 64, is unchanged.
   This answers the draft's item 7:
   - as built, both of part 1's allowed mechanisms stopped at 64 vertices;
   - family A's known counterexamples have 158–352 vertices;
   - the proposal is one cap of 400 (the templates' existing cap) for every arm. An evaluation costs about 11 ms
     at 400 vertices;
   - the item was written knowing A's sizes, and that is disclosed.
   Tests: `test_operations.Cap` (3). The operations test file's misplaced main guard was also moved.
3. **PT-1, the study, drafted and not preregistered** (`scripts/b20r159_proving_test.py`; 8 design tests on
   invented families, `tests_genesis/test_proving_test_study.py`).
   - It has every stage of the design draft.
   - `PREREGISTERED` is False, and a registered run is refused.
   - Its PROVISIONAL constants are the draft's open items, fixed at preregistration after B20_R158.
   - Family C pools several data draws. One draw gave 7 tasks on a development seed, too few for part 5's
     statistics.

## Also in this window (separate commits)

- **Record test drafts written before the studies run:** RecordB20R158 (F5) and RecordB20R167.
- **The PT-1 draft's other open items:**
  - a family C candidate (Hansen and Lucas 2010);
  - a proposal for part 4's statistic;
  - the builder's reading that a sum-type derivation space adds no reachable graph;
  - whether a template counts for part 1.
- **The record test of B20_R152 no longer skips.** It asserts that no confirmation ran because nothing was admitted,
  because an undeclared skip fails the release matrix.
- **F3's forecasts are diagnosed after recording** (a disclosed development look; `B20_R156_RECORD.md`). The
  misses are mostly above the interval, and a degrees-of-freedom correction was tried and not adopted.

## Prior art

None is claimed. Ablation by substitution is standard. The residual bootstrap's correction tried for the forecasts
is Davison and Hinkley (1997), §6.3.
