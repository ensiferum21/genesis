# The open-record track: Gset max-cut (B20_R101 onward; DRAFT plan)

Daniel's ask of 22 Oct 2026 ("get inspired by the reality and make it extremely good") applied to one weakness:
every Genesis result so far is on hosts generated for its own studies. There, the best values are either reached
by every method (planted n63; development looks in `docs/DISCOVERY_PLAN.md` §3.1) or known only to the study itself.
A result on a public benchmark with published best-known values cannot be argued away that way. Nothing here is
preregistered.

## 1. Why Gset max-cut

- **Public and long-standing.** Gset G1–G54 (Helmberg and Rendl 2000, rudy generator; 800–3,000 vertices; random,
  planar and toroidal graphs, weights ±1) has been the standard max-cut benchmark for 25 years. Best-known values
  are published, and the methods that set them are published too: Burer, Monteiro and Zhang 2001 (BURER2002, already
  a pinned Genesis arm through MQLib), breakout local search (Benlic and Hao 2013), and later records.
- **The physics-inspired machines report on it.** Simulated bifurcation (Goto et al. 2019, 2021; `ising-dsb-v1` is
  its discrete form), coherent Ising machines and other Ising hardware publish time-to-target on G22, G39 and others.
  This is the "reality" comparison the physics plan (`docs/PHYSICS_INSPIRED_PLAN.md`) points to. Hardware
  differences must be stated: the published numbers come from GPUs, FPGAs and optical machines; ours are one CPU
  core.
- **It fits what exists.** Max cut is the cut representation Genesis already invented and licensed (`cross_2`, B18).
  The language programs (B20_R78 onward), dSB, BURER2002 and the tabu and extremal-optimization kinds all search
  cuts. Only the completion step (cut to triangle-free subgraph) is specific to the current domain.
- **It is a harder playground for the discovery loop.** Gset graphs are sparse and structured (toroidal grids,
  planar graphs). Local objects there, such as frustrated cycles and domain walls, are the kind of structure the
  note's loop is meant to find.

## 2. What it needs

1. **Data.** `set1.zip` (G1–G54) and `maxcut_bestvalues.xls` from the OPTSICOM max-cut page
   (grafo.etsii.urjc.es/maxcut). The workspace's proxy refuses the site, so Daniel downloaded them on 22 Oct 2026:
   `set1.zip` SHA-256 `18e00bfc…2e71` (54 well-formed instances, sizes as published) and `maxcut_bestvalues.xls`
   `1831bdc4…c018`. The spreadsheet is OPTSICOM's 2009 table; Benlic and Hao's breakout local search (2013) has since
   improved 18 of G1–G54 (for example G27 3341, G39 2408), so the best-known value per instance is the highest
   published one, with its source, cross-checked against the paper before any comparison.
2. **A domain `maxcut_v1` (engineering).** An adapter for weighted graphs up to 10,000 vertices, an exact cut-value
   checker in integers, and witness custody as in `triangle_free_large_v1`. Certification is out of scope: best-known
   values are lower bounds, and an upper bound would need an SDP. Results are stated against best-known values,
   never as optimality.
3. **Arms.**
   - BURER2002 (MQLib, pinned).
   - dSB.
   - The system's language programs run on the cut alone (the program's state without the completion step).
   - The builder's engine core (tightness-guided search, from `tfxw`), adapted to cuts, as a separate engine, never
     relabelled as the system's discovery.

## 3. Studies (to be preregistered one at a time)

- **B20_R101, engineering:** the domain, the data, the arms, tests (a hand-checked cut value per instance family).
- **B20_R102, where Genesis stands against the records:** fraction of best-known value and time-to-target at 1, 10
  and 60 s on G1–G54, against BURER2002 at equal time, and against published Ising-machine numbers as a stated
  external reference (different hardware, so not a paired comparison).
- **B20_R104, engineering:** Genesis's own max-cut engine, `mcx-v1` (iterated tabu search in the manner of breakout
  local search; an elite pool; restarts by a Houdayer cluster exchange or by renormalisation, which contracts every
  edge the elites agree on and searches the contracted problem), from source, pinned; graph families built as Gset's
  were (rudy's planar unions, rectangular tori), so that configuring never needs Gset.
- **B20_R105, the system configures the engine on generated graphs only:** two order parameters of the degree
  sequence place a graph in a class (random, toroidal, planar); per class and budget, successive halving over 32
  configurations on fresh graphs; held-out check against the default and BURER2002.
  **Result:** the system's choice beats BLS's published setting at 1 s and ties it at 10 s; both budgets ahead of
  BURER2002 on 24 held-out generated graphs (22-0, 17-2); `evidence/mcx_configure_b20r105/`.
- **B20_R106, once on Gset:** the configured engine at 1 s and 10 s on G1–G54 against B20_R102's recorded runs
  (BURER2002, dSB, the virtual best of twelve heuristics), sign tests; values above the table are flagged, never
  claimed. All three preregistered before B20_R102 ran.
- **Then the discovery loop on Gset**, if B20_R99 finds structured headroom. The test is whether concepts invented
  on toroidal and planar instances transfer to random ones, and the reverse. That is the note's "untouched family"
  inside one public benchmark.

## 4. Honesty rules for this track

- A Gset record claim requires the witness cut, its re-check, the instance's SHA-256, and the published best-known
  value with its source.
- Time comparisons with published hardware results are descriptive only.
- Losing to BURER2002 or to the records is a result, recorded as such.
