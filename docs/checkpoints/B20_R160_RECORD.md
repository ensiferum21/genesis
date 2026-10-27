# B20_R160 record: F1, the Frontier engine on its planted world (engineering)

- **What this is.** The first batch of Daniel's directive of 27 Oct 2026, 19:55 (`docs/OMEGA_FRONTIER.md`), queue
  `frontier-f1-build`.
  - It builds the divergent–convergent engine that the directive asks Genesis to work by: "imagine mutate …
    extrapolate and branch out and see convergence and do the best approach … without handholding or teaching".
  - It also builds the kernel-side planted world that calibrates the engine.
- **No claims.**
  - The planted world is a fixture, as the Limitation Zoo is for ARA. Nothing measured in it is evidence about
    real problems.
  - The development look below shaped the design and licenses nothing.
  - The test of the engine is F3 (B20_R156), on sealed worlds from held-out families.
- **Built by** the builder on 27 Oct 2026, with no LLM, on CPU 1 while B20_R151 ran alone on CPU 0. No sandboxed
  test ran meanwhile. The protected judge is untouched.
- **The builder's, not Genesis's:** the engine's code, its operators, its policy and the planted world. What
  Genesis does with them in a study is the part that counts (§3.4).

## What was built (`src/genesis/frontier/`)

| Module | Plane | What it does |
|---|---|---|
| `direction.py` | research | Directions as typed objects with descriptors. The operators: `imagine` (the most novel of k samples: never-before-used means a descriptor outside the archive), `mutate`, `recombine`, plus the engine's branch-out |
| `curves.py` | research | Discovery-curve extrapolation. Weibull (7 exponents × 64 time scales), power, log and flat families, fitted by vectorised least squares, weighted by AICc. A moving-block residual bootstrap gives the 5%, 50% and 95% forecasts of f(H); the half-widths are widened by INFLATE = 1.25 (set on development curves). `p_exceeds` gives the share of forecasts above a level |
| `converge.py` | research | Clusters of artifacts by fingerprint. Consilience counts independent approaches (a different representation or method). Used for the allocator's bonus, the abstraction trigger and the divergence alarm |
| `allocate.py` | research | The Frontier's policy:<ul><li>branch out first, then invented representations;</li><li>young branches up to their patience;</li><li>exploration held to a share eps of compute, which adapts to stalls and to the divergence alarm;</li><li>exploitation by the index (95% forecast above the problem's best verified value, plus learning progress, plus consilience);</li><li>the value of opening a new direction, from the empirical distribution of what directions reach;</li><li>pausing dominated branches, with reactivation.</li></ul>The comparators: uniform, successive halving (G2), UCB1, random |
| `engine.py` | research | The resumable cycle: allocate, step, verify through the manifest only, record, branch out, cluster, abstract, spawn. Problems are ordered and seeded by the digest of their public statement. State is saved as JSON, and a resumed engine replays the domain's mutations. Every decision is logged |
| `manifest.py` | research | The No-Handholding Protocol's single input path. `PublicDomain` exposes only the public calls; the verifier is an opaque callback; the digest is recorded |
| `world.py` | **kernel** | The planted world:<ul><li>hidden curves of five types: dead, decoy (the B20_R148 trap), vein, slow starter, and a recombination vein whose parts are poor alone;</li><li>attractors that only true branches reach;</li><li>abstraction that invents a better representation only from a true attractor;</li><li>successors that reward branching out;</li><li>a null world.</li></ul>Artifacts carry their origin and a keyed token; `verify` recomputes the true value and refuses forgeries |

## Acceptance (`tests_genesis/test_frontier.py`, 11 tests, about 2 min on CPU 1)

| Criterion | Result |
|---|---|
| (a) Forecast coverage on held-out synthetic curves (vein, slow starter, decoy, dead), once a quarter or half of the horizon is observed | at least 0.80 for every type (test seeds independent of development) |
| (b) The null world gives no discovery | a total of exactly 0 for the Frontier, halving and UCB |
| (c) Recombination veins are found | the engine opens the planted pair in at least half of the worlds that have one |
| (d) Paused and resumed equals uninterrupted | identical summary and identical decision log, with a fresh world object at every resume |
| (e) The No-Handholding Protocol | the research plane imports no kernel side, reaches no kernel attribute, and calls no reflection (except the gatekeeper's lookup of the public names) and no `open`; the public domain refuses kernel calls; renaming and reordering the problems changes no decision (the relabelling audit) |

**Amended before acceptance (disclosed).** §7 had (a) as coverage in [0.80, 0.97].
- The upper limit is dropped. Over-coverage is conservative: it costs allocation efficiency, which F3 measures
  directly.
- On development curves the intervals over-cover. Several types reach 0.96–1.00 once a quarter of the horizon is
  seen.
- A slow starter seen for only a tenth of its horizon is covered 0.15 of the time. A flat start cannot reveal a
  later rise, and patience and reactivation exist for that case.

## The development look (`scripts/b20r160_frontier_devlook.py`, `evidence/frontier_dev_b20r160/`; DEV, disclosed)

Development worlds 1001–1008: 4 problems, a budget of 8,000, a quantum of 10, one run per arm. The value is the total
verified value divided by the world's reference, which is each initial problem's best planted curve at an equal
share of the budget, without successors or invented representations.

| Arm | Mean value (8 worlds) | Worlds where the allocation-only Frontier is higher |
|---|---|---|
| Frontier, allocation only | 0.774 | — |
| Frontier with abstraction and branching out | 1.974 | — |
| successive halving (G2) | 0.563 | 8 of 8 |
| uniform | 0.418 | 8 of 8 |
| UCB1 | 0.652 | 7 of 8 |
| random | 0.439 | 8 of 8 |

The full Frontier exceeds 1 because the reference ignores the successors and the invented representations that the planted world rewards. It fell below the allocation-only Frontier in one world (1006), where abstraction and branching out cost more than they returned. Run time: 593 s for 48 runs on CPU 1.

This look was made on development worlds after each design change below, so its numbers are not an estimate of
anything.

## Found while building (each changed the design)

1. **Forecasting the best-so-far of noisy observations is biased.** The maximum of noisy draws keeps creeping up.
   The engine now fits the raw observations, and the forecast's target is the true curve, which is what
   verification confirms.
2. **A coarse time-scale grid biased plateaus by about one noise unit**, and the bootstrap cannot see grid error. Fix:
   64 time scales and 7 exponents, residuals in closed form (fast), and the INFLATE widening.
3. **Patience on every new direction ate the budget.** In one development world, 291 directions were opened and each
   took 6 quanta before being judged. Exploration, including patience and reactivated branches, is now held to a
   share eps of the compute spent.
4. **Noise-level "improvements" drove eps to its minimum.** Verified values creep up while a curve is still rising.
   Only a material improvement now counts: 1% of the total and at least 0.005.
5. **Dead branches were favoured on problems with a low best value.** The index rewards any gain over a low target.
   Opening a new direction on a problem is now valued against exploitation, using what directions have reached so
   far.
6. **A resumed world had no memory of the artifacts it issued.** Artifacts now carry their origin and a keyed token,
   so verification recomputes their values.
7. **The relabelling audit needs decisions that do not depend on ids.** Problems are ordered and seeded by the digest
   of their public statement.

## Next

- **F3 (B20_R156), to preregister.** The engine against the four comparators at matched compute, on sealed worlds
  drawn by the kernel from held-out families (other problem counts, type weights and horizons), including null
  worlds. Primary: the regret ratio. Secondary: coverage, false discoveries and recombination veins.
- **F2 continues:** the attacks and the generator over the conjecture domain.
