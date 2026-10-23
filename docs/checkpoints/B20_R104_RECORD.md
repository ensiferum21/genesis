# B20_R104 record (engineering): Genesis's max-cut engine `mcx-v1`; setup of B20_R105 and B20_R106

- **Run by:** the builder, on 23 Oct 2026.
- No claim, rule, comparator or package changes.
- The open-record track of `docs/OPEN_RECORDS_PLAN.md`; Daniel's request of 23 Oct 2026 ("adapt them and make the
  solver more strong too").

## Why

B20_R101 put Gset under Genesis's discipline with two arms of others' methods (MQLib's heuristics, dSB). To stand on
a public benchmark Genesis needs an engine of its own, and the mechanisms of `docs/RECURSIVE_IMPROVEMENT_ARCHITECTURE.md`
need a solver to act on. This batch builds the engine and preregisters how the system configures it (B20_R105, on
generated graphs only) and how it is judged once on Gset (B20_R106). Both designs were fixed before B20_R102 ran.

## Engineering

**Kind `mcx-v1`** (`candidate_kinds/mcx.py`, `candidate_kinds/native/mcx.c`; max-cut domain only):
- **Search.** An iterated tabu search in the manner of breakout local search (Benlic and Hao 2013):
  - flip gains kept in bucket lists; steepest ascent to a local optimum;
  - a perturbation whose strength adapts (it grows on returning to the same optimum and resets after a new one),
    directed (best non-tabu moves, random tenure) with a probability that falls as the search stalls, otherwise
    random or recency-based flips;
  - **breakout local search's own rules** as a mode (`pert` 2), read from the authors' paper (Daniel's PDF, 23 Oct
    2026; Algorithms 1-3 and formula (2)): directed single flips and directed pairs (the best non-tabu vertex of each
    side) in equal shares with probability max(exp(-w / 1000), P0), random flips otherwise, one strong random
    perturbation after 1000 local optima without a new best, descent moves made tabu. **DEFAULT is BLS's published
    setting** (L0 = 0.01 n, P0 = 0.8, tenure 3 + up to n / 10, no restarts): the published method as adapted, our
    implementation, not the authors' code;
  - an elite pool of distinct local optima.
- **Restarts, after a set number of local optima without a new best** (configuration `rs`):
  - none;
  - a cluster exchange of two elites (Houdayer's move from spin-glass physics: whole domains of disagreement are
    swapped at once);
  - **renormalisation**: every edge whose relative orientation all elites agree on is contracted (a union-find with
    parity); the contracted graph is again a weighted max-cut problem; it is searched by the same method from the best
    elite; the result is projected back and polished. What the elites agree on is kept, the rest is searched at a
    coarser scale.
  - **MACUT's multi-parent grouping crossover** (Wu and Hao, PPSN 2012; read from the authors' paper, Daniel's PDF of
    23 Oct 2026): 2-4 elites; vertices grouped by their pattern of sides across the parents; the two largest groups
    kept whole on opposite sides, the rest random; then the search continues from the offspring.
- **Prior art.** Each part is published (tabu search, breakout perturbation, elite pools, cluster moves, multilevel
  coarsening); the builder combined them. Invention by the system is not claimed for the engine. What the system
  contributes, and is measured on in B20_R105-R106, is the configuration and the per-class choice.
- **Source** `native/mcx.c`, SHA-256 `6f164eff…9667`.
- **Configuration (data):** perturbation strength `L0`, directed-move floor `P`, tenure divisor `tt`, pool size,
  restart period, restart operator `rs`, perturbation rules `pert`: 5,184 configurations.
- **Binary.** Built from source by `scripts/b20r104_build_mcx.py` (gcc 13.3, `-O3 -std=gnu11 -static`); two builds
  are byte-identical; pinned SHA-256 `10825596…0978`. Malformed input and options exit 2; a weighted degree above 2^24 exits
  3 (the run fails, nothing is hidden). The printed cut is recomputed in Python and re-checked by the domain's two
  checkers.

**Runner.** Membership of the max-cut runner is now derived: a kind is admitted if its module declares the max-cut
domain (`candidates_maxcut.is_maxcut_kind`), so adding a kind no longer changes the runner file that every max-cut
identity hashes (as B20_R67 did for registry v2). This changed the max-cut identities once; no max-cut descriptor id
had been recorded (B20_R102 had not run).

**Graph families built as Gset's were** (`domains.MaxCutAdapter`), so that configuring never needs Gset:
- `planar2`, `planar2_pm1`: the union of two random planar graphs on shared vertex labels, each grown from a triangle
  by inserting every new vertex into a uniformly chosen face, then thinned to a density. Our reading of excerpts of
  rudy's source (Rinaldi; the copy served with Gset); Gset's planar graphs fit it: at n = 800 and density 0.99 this
  family has about 4,660 edges (Gset: 4,661-4,694) and its hubs at the first vertices with degrees 120-140 (Gset's
  G14: 132 at vertex 3).
- `torus2d`, `torus2d_pm1`: rectangular toroidal grids numbered as rudy's board; Gset's tori are 100 x 8 (G11-G13),
  100 x 20 (G32-G34), 50 x 60, 30 x 100 and 25 x 120 (G48-G50, weights 1), read from the data.

**Tests** (`tests_genesis/test_mcx_kind.py`, 11): deterministic pinned build; refusals by the binary and the
kind; every restart mode and perturbation type optimal on small weighted graphs (brute force); a run in the sandbox
with the cgroup meter; a 3,000-vertex graph; membership by declared domain; the planar layers are planar (networkx)
and maximal, hubs early, deterministic per seed; the tori numbered as Gset's (G11's vertex 0 has neighbours 1, 7, 8,
792). No test runs mcx on Gset.

**Development looks (disclosed).**
- 22 Oct 2026, before this batch: an earlier draft (cluster exchange only) ran in-process at 2 s on seven Gset
  instances (G1, G11, G14, G22, G32, G43, G48); disclosed in B20_R106.
- 23 Oct 2026, on generated graphs only (dev seeds 777001-777006; never Gset), the default (BLS's setting) against
  BURER2002 at 1 s: ahead on four graphs, tied on one, behind on planar2 (3045 vs 3047); at 10 s: ahead on three (torus2d_pm1 1368 vs 1348,
  planar2_pm1 2430 vs 2411, erdos 11717 vs 11714), tied on one, behind on two (erdos_pm1 3394 vs 3396, planar2 3045 vs
  3047). Restarts every 2,000 local optima hurt (on these graphs a restart every ~0.01 s), so the restart periods
  were widened to 2,000-200,000 before B20_R105 was fixed; restarts every 20,000 local optima did not help at 10 s.
  The binary's built-in defaults were set equal to DEFAULT (the kind always passes every option).

## The best-known table now holds the BLS and MACUT papers (Daniel's PDFs, 23 Oct 2026)

Daniel sent the authors' paper of breakout local search (Benlic and Hao, Eng. Appl. Artif. Intell. 26(3), 2013;
preprint of 6 Sept 2012, SHA-256 `da28d05c…a3f6`, not committed). Its Table 2 gives, for G1-G54, BLS's best of 20
runs and the best known value before BLS (from the paper's references). Both are now sources in
`data/gset/best_known.json`; the best known value is the highest source. **20 values rose:** G7-G10, G13, G16-G19,
G23, G24, G32-G35, G37 and G43-G46, among them the tori G32 (1410), G33 (1382) and G34 (1384). He then sent the
paper of the memetic algorithm MACUT (Wu and Hao, PPSN 2012; publisher's proof, SHA-256 `a2d0fee1…5fdc`, not
committed): its Table 1 (24 of G1-G54) raises G35 to 7686, G36 to 7679 and G37 to 7690. G30 differs between the BLS
authors' page (3413) and the paper (3412): both are kept, and the higher counts. Consequence: the draft's 1402 on
G32 is below the best known value and its 6660 on G43 equals it; the "above the table" readings of 22 Oct were the
2009 table's age, not records. The table changed before B20_R102 ran; B20_R102 records the table's SHA-256.

## Setup: B20_R105 (preregistered): the system configures the engine on generated graphs only

`scripts/b20r105_mcx_configure.py` (SHA-256 `8257845a…ef09`): three classes (random, toroidal, planar) rotating through
Gset's generator settings with fresh draws (Gset's identities excluded; the weight-1 tori never in Gset's shapes).
Order parameters (the degree sequence's coefficient of variation and log max/mean) place a graph in a class by
nearest centroids. Per class: a 1 s race (successive halving of DEFAULT and 31 drawn configurations over 16 graphs),
a 10 s race (the final three and DEFAULT over 8 more), and 8 held-out graphs with DEFAULT, the chosen configuration
and BURER2002 at 1 s and 10 s. Labels by Wilcoxon tests at alpha 0.025: TUNED_BETTER / TUNED_WORSE / NO_DIFFERENCE,
and MCX_AHEAD / MCX_BEHIND / COMPARABLE. Design tests: `tests_genesis/test_mcx_configure.py` (7).

## Setup: B20_R106 (preregistered): once on Gset

`scripts/b20r106_mcx_gset.py` (SHA-256 `257d7ea0…e7a5`): B20_R105's configurations, chosen per instance by its classifier,
at 1 s and 10 s on G1-G54, plus DEFAULT; against B20_R102's recorded runs (BURER2002 and dSB at 1 s and 10 s; the
virtual best of twelve heuristics at 10 s); seven sign tests at alpha 0.05 / 7; MCX_LEADS / MCX_COMPARABLE /
MCX_BEHIND; values above the table flagged RECORD_CANDIDATE, never claimed. Refuses to start unless B20_R102 and
B20_R105 finished validly and B20_R105's configurations are the recorded ones. Design tests:
`tests_genesis/test_mcx_gset.py` (5).
