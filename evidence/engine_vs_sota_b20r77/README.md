# B20_R77 evidence: the system's new engine against CP-SAT and BURER2002 (powered): **ENGINE_BEATS_SOTA**

Builder-run on DEV. It licenses nothing.
- **Script:** `scripts/b20r77_engine_vs_sota.py`, preregistered at `b295c2a` (SHA-256 `9da9935d…c1e0`, sent to Daniel
  before the run; unchanged since). Alone, pinned to CPU 0, 5,475 s; 2,520 runs in runc plus Part B. `code_identity`
  `da5a78a6…76c9`, the committed tree.
- **Tools:** MQLib BURER2002, binary `9e760cb7…c4e3`; OR-Tools CP-SAT 9.15.6755, tree `fb5ef9ac…67f9`, 8 workers on
  the one core. **Engine:** `hybrid-swap-v1` (B20_R77).
- **Hosts:** 24 fresh DEV planted-cluster hosts (p_in 0.8, p_out 0.06) at n63, 440–486 edges, none in any earlier
  study (B20_R76's, on which the engine was developed, included).

## Verdict: **ENGINE_BEATS_SOTA** (preregistered rule; recomputed independently from the rows)

Valid: every arm's median CPU at t = 0.5 s was 0.667–1.002 s (threshold 0.45 s) and no run failed.

Primary: log2(TTS*_tool(q) / TTS*_engine(q)) over the 24 hosts (positive = the engine faster; ±10 = one side never
reaches the target within 2 s), paired bootstrap 90% interval:

| Tool | typical host (q = 0.5) | hard host (q = 0.75) |
|---|---|---|
| BURER2002 | 10.0 [**1.32**, 10.0] ENGINE_FASTER | 10.0 [10.0, 10.0] ENGINE_FASTER |
| CP-SAT (anytime) | 10.0 [10.0, 10.0] ENGINE_FASTER | 10.0 [10.0, 10.0] ENGINE_FASTER |

The narrowest margin is against BURER2002 on the typical host: its lower end, 1.32, means at least 2.5 times as
fast, above the preregistered 2 times. B20_R76's statistic (median over hosts of the per-host ratio) agrees: ENGINE_FASTER
against both (BURER2002 10.0 [2.45, 10.0]). Independent code (no study code) gives the same values, intervals and
verdicts, and 20 other bootstrap seeds the same verdict for every primary pair.

## Descriptive

| Arm | reached within 2 s (of 24) | TTS* median / 75th pct (CPU s) | share of 2 s runs reaching it |
|---|---|---|---|
| **engine** (`hybrid-swap-v1`) | **24** | **0.1 / 0.25** | 0.94 |
| simulated bifurcation | 21 | 0.1 / 2.5 | 0.78 |
| the system's B20_R76 engine | 19 | 1.25 / 10 | 0.67 |
| tabu search | 15 | 2.0 / ∞ | 0.57 |
| E1d's frozen candidate | 15 | 10 / ∞ | 0.36 |
| BURER2002 | 10 | ∞ / ∞ | 0.21 |
| CP-SAT (anytime) | 0 | ∞ / ∞ | 0 |

- **The engine's best equals the best known value on every host.** On three hosts no other method reached it, CP-SAT
  with 60 s included; two of those values are certified optimal (292 and 303), the third is one below its upper bound.
- **CP-SAT with 60 s** reached the target on 3 of 24 hosts, claimed optimality on none, and ended 1–6 edges short on
  the others. The checked reference certified 16 of 24 targets (median 42 s); the other 8 are within 1–2 edges of
  their upper bounds.
- **Did the new engine improve the system?** Against the system's B20_R76 engine: yes, ENGINE_FASTER at both
  quantiles (log2 3.64 [2.26, 4.58], about 12 times, and 5.32 [3.00, 10.0], about 40 times). Against simulated
  bifurcation alone: UNRESOLVED (q = 0.5: 0.0 [−1.32, 1.32]; q = 0.75: 3.32 [0.0, 6.58]); B20_R76's statistic calls
  it COMPARABLE. The engine reaches more targets (24 against 21), but this study cannot show it is faster.
- **Simulated bifurcation alone also beats both tools** on the primary statistic (ENGINE_FASTER in the secondary
  table, both quantiles). Much of the advantage over the state of the art is therefore dSB's (B20_R69); the system's
  representation engine, tabu search and E1d's candidate are UNRESOLVED against BURER2002.
- **Start-up is even across arms:** median cgroup CPU at t = 0.05 s was 0.216–0.246 s for every heuristic arm,
  the engine 0.240 (interpreter and imports), so the nominal run times compare fairly. CP-SAT's 0.56 s is its import,
  outside its budget.

## Exploratory checks after the run (not preregistered)

- **Certified hosts only (16):** the same four ENGINE_FASTER verdicts (BURER2002 typical host [1.32, 10.0]).
- **"Within one edge of the best known value" as the target:** against CP-SAT nothing changes; against BURER2002 the
  hard host stays ENGINE_FASTER ([2.58, 10.0]) but the typical host becomes UNRESOLVED (−1.0 [−1.0, 10.0]): BURER2002
  gets within one edge on 14 of 24 hosts, often at 0.05 s. The engine's advantage there is in reaching the last edge.

## How to read it

- In the regime tested (anytime, up to 2 CPU s, one core, these hosts) the engine reaches the best known value faster
  than both state-of-the-art tools on the typical and the hard host, by the preregistered rule, with a narrow margin
  against BURER2002 on the typical host.
- Neither tool is used where it is strongest. CP-SAT is built to prove optimality with time and many cores; here it
  ran CPU-matched on one core for up to 2 s (with 60 s it still proved nothing optimal on these hosts). BURER2002
  solves max-cut, a relaxation of this problem, and is completed greedily as every cut-based arm is.
- Scope: one host family, n63 only, 24 DEV hosts, builder-run; the target is the best value any method found
  (including the engine), certified on 16 hosts. **Expectation, stated before running:** ENGINE_BEATS_SOTA or MIXED,
  MIXED slightly more likely. The result is the stronger of the two.
- A nit, left as run: the script's docstring contains `TTS\*`, which Python 3.13 reports as an invalid escape
  (a SyntaxWarning on import, no effect on the run). The script is kept byte-identical to the preregistered one.

## Tests

`tests_genesis/test_engine_vs_sota.py`: Design (7); Record (5): valid, and the analysis and verdict recompute (with
the narrowest margin and B20_R76's statistic); who reached the target, the engine's best on every host, the three
engine-only hosts; values bounded and isolated; the tools and descriptors are the pinned and recorded ones; the hosts
are fresh (disjoint from B20_R76's) and in the e1/e1b exposure addenda.
