# B20_R150 record: ARA-1, the Autonomous Research Architect built end to end on fixtures (engineering)

- **What this is.** The queue's next direction after B20_R135 (`ara-1-build`, priority 9; `docs/OMEGA_ARCHITECTURE_INVENTION.md` §16).
  Engineering on fixtures: it builds the mechanism the study B20_R141 will test.
- **No claims.**
  - Nothing here is a result.
  - The zoo is a calibration domain; nothing measured in it is evidence about real Genesis workflows.
  - The development look below is disclosed, not evidence.
- **Built by** the builder on 27 Oct 2026, with no LLM. The protected judge `autonomy/feedback.py` is untouched.

## What was built (`src/genesis/architecture/`)

| Module | Plane | What it does |
|---|---|---|
| `graph.py` | research | The Architecture Graph (§2): JSON with typed roles and ports, a versioned operator library, a closed kernel (the mandatory reattempt node), budget shares and conservation, deterministic execution under fuel with per-node charges, the diff classifier (TUNING, STRUCTURAL, LANGUAGE) |
| `policies.py` | research | What a graph runs: policy families (global, threshold, oblique, tree, knn), evaluator schemes (independent; paired, which cancels noise shared by an instance's options), search procedures (hill climb, restarts, exhaustive) |
| `zoo.py` | **kernel** | The Limitation Zoo (§12): random geometric and Erdős–Rényi graphs with matched mean degree; a hidden objective on a real graph statistic; one planted class per environment; dev splits from the environment seed, confirmation and sealed splits from the judge's seed; a `View` that exposes only the incumbent, the dev graphs and a unit-counting evaluator |
| `judge.py` | **kernel** | The harness (§7): correctness (type check, kernel closure, budget conservation); reproducibility (re-execution from the AG and seed); budget (units spent against the matched budget); the sealed decision (gain over the incumbent of at least MATERIAL, in units of the attainable range). The submitter sees only the verdict; the numbers go to a ledger for the study. Digest pinned |
| `diagnose.py` | research | The loss ladder by oracle substitution (§4.1). Exact paired tables are drawn once per dev split and shared by every stand-in; terms are valued on dev_b's held-out repeats; bootstrap intervals; MATERIAL relative to the attainable range, with no term material when the range's interval reaches zero; NONE and AMBIGUOUS |
| `rewrite.py` | research | The generative grammar (§5.1): INSERT, FUSE, GENERALISE, SPECIALISE, SUBSTITUTE, REALLOCATE, LIFT, RETRIEVE. Typed preconditions, the kernel never targeted. Holes are filled on dev_a only (senses by random search and mutation in `senses.graph`; fusion operators from the menu). Behavioural fingerprints mark rediscoveries. Bounded inversion (`followups`) |
| `model.py` | research | The architecture model (§3): every library operator probed on a fixture with a postcondition (OBSERVED_OK, FAILED, UNPROBED); evidence and failure patterns from the research queue; the assumption registry |
| `assumptions.py` | research | Generated assumptions (operators, constants, absent compatible edges); recorded ones (from B20_R128, R132, R133/R135, R148); protected ones, which are always refused |
| `ara.py` | research | The cycle (§0, §8): model, diagnose, propose, synthesise, evaluate on dev, submit, keep. Arms modify, solve and stop. The complexity tie-break. The blind-rewrite control (same generator, no ladder) and the tuning-only control (TUNING-class changes only) |

**Tests (49, all passing; with `test_omega_boundary`, 51):**
- `test_architecture_graph` (12): type errors refused before running, a cycle refused, the kernel closed under five kinds of change, budget conservation, determinism, per-node charges, bounded execution (depth, shares, the sense pool), the classifier, paired against independent evaluation, shared draws that save units but never charges.
- `test_architecture_judge` (9): sealed draws disjoint from dev, the view exposing no key, every incumbent well formed, the remedies helping where something is planted and nothing helping on NULL and DECOY, each of the judge's checks refusing what it should, the key for the study only, the pinned digest.
- `test_architecture_rewrite` (9): every operator where its precondition holds and nowhere else, each operator's class, SPECIALISE pruning, lineage, synthesis on dev_a only, the fusion menu, rediscovery by behaviour, an inadmissible result refused.
- `test_architecture_ara` (9): the ladder localising search and expressiveness and saying NONE on NULL and NO_HEADROOM (fixture environments), determinism, each cell drawn once, the battery; the cycle modifying and being promoted, solving when nothing qualifies, stopping on a tiny budget; the blind control; tuning-only changing only TUNING.
- `test_architecture_boundary` (10): the research plane imports neither zoo nor judge nor any protected module, never touches a view's private state (and the scan sees a planted reach); capabilities probed; a planted broken implementation FAILED; failure patterns found; generated assumptions outside the kernel; every protected assumption refused; recorded assumptions naming their studies.
- `test_omega_boundary` now covers the seven research-plane modules too.

## Choices made while building (disclosed; each changes the design document, §17 updated)

- **The oblique policy family** (a cut on a + s·b over two standardised features) was added to the library and to the
  ladder's flexible stand-in. It was added after a look at the zoo showed that the flexible stand-ins (threshold,
  tree, knn) could not express the diagonal boundary that FUSION_NEEDED plants. The family is generic, but the change
  was prompted by a zoo look.
- **The ladder's rich stand-in** always contains the current features, which keeps the information term from going
  negative by construction. No term is material when the attainable range's bootstrap interval reaches zero. Both
  changes were prompted by the same look (FUSION_NEEDED and NULL).
- **Sense units** are a second currency. The view counts evaluation units authoritatively, and ARA reports the sense
  units its own computations cost. The judge checks their sum; the sense units can be re-derived by re-running ARA,
  which is deterministic.
- **Not in ARA-1:**
  - RETRIEVE reads an archive list, not the vault.
  - REALLOCATE applies only where two nodes have shares, which the zoo's incumbents never have.
  - The judge's checks 5–8 (transfer, regressions on other classes, Holm across environments, ablation) are the
    study's: B20_R141 aggregates over environments.
  - Shapley attribution, synergy, questions as objects and allocation over roles are ARA-3 to ARA-6.

## Development look (disclosed; zoo indices 9000–9015, sealed seed 9090, never to be reused)

Two environments per class. Each ran ARA, the blind-rewrite control and the tuning-only control, at 4× the
incumbent's budget (36,000 units); the oracle-key arm was the reference. File: `evidence/ara1_development/`.

| | ARA | blind rewrite | tuning only |
|---|---|---|---|
| promoted (of 10 defect environments) | 9 | 10 | 4 |
| false releases on NULL, NO_HEADROOM, DECOY (6) | 0 (the judge refused 2 submissions) | 0 (3 refused) | 0 (1 refused) |
| units spent (median over the 16) | 1,730 | 9,870 | 2,370 |

- **Diagnosis by location:**
  - 9 of the 10 defect environments were localised correctly. One FUSION_NEEDED environment was diagnosed NONE, so
    ARA kept the incumbent there and the blind control did better.
  - All 4 NULL and NO_HEADROOM environments were diagnosed NONE.
  - Both DECOY environments were diagnosed as expressiveness, as they must be on dev, where the decoy is real. The
    judge refused both on the sealed tasks.
- Promoted gains were at or near the oracle-key arm's.

**What it says for B20_R141's design:**
1. **The blind control is strong when the grammar is small.** At 14 variants it reaches every fix that ARA reaches;
   what localisation saves here is units (ARA spent about a fifth of blind's). Experiment D ("better than tuning-only
   and blind at matched cost") therefore needs a constrained variant budget, or gains measured per unit, and its
   preregistration must say which.
2. **DECOY cannot count towards the NONE rate.** It is a defect on dev by construction. It should be judged by the
   false-release rate at the judge; the NONE rate should be computed on NULL and NO_HEADROOM.
3. **FUSION_NEEDED is the class the ladder sees least well** (also 1 of 5 in a ladder-only look).
4. **These seeds are spent.** B20_R141 draws fresh environments from new seeds.

## Tests

The 49 architecture tests above; `test_omega_boundary` (2) extended to the research-plane modules.
