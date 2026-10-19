# Ideas from physics, nature and how people do science, applied to Genesis (B20_R69 onward; DRAFT plan)

Asked for by Daniel on 2026-10-19: improve the system with ideas taken from physics, the world and people. Each
idea below is tied to a specific weakness found in the evidence, a gate it serves, and a batch that tests it. Every
batch follows the usual protocol (preregistered, DEV, run alone, nothing promoted). Sources are listed at the end.

## 1. Benchmark like the quantum-annealing community: scaling of time-to-solution, not one fixed budget

**Weakness.** E1d's evidence uses one fixed candidate budget (0.5 s) at every host size and asks at which HiGHS
budget the advantage ends (B20_R63, R64, R66). Rønnow et al. (2014) showed that a fixed run time at all sizes can
fake or hide a scaling advantage: at small sizes the fixed time is wastefully long, which flattens the curve. They
require the *optimal* run time at each size, compare *time-to-solution* TTS99 = t · ⌈ln 0.01 / ln(1 − s)⌉ (s the
per-run success probability at run time t), and read the comparison at quantiles of instance hardness.

**Their taxonomy names our situation exactly.** A speedup against a chosen baseline is only a *potential* speedup,
which a weak baseline inflates; a speedup claim needs the best *known* method. E1d's
result so far is a potential speedup over an exact MILP. B20_R68 adds the best-known kind of baseline (max-cut
heuristics).

**Batch (B20_R70, DEV).** For E1d's candidate and the domain heuristics, measure TTS99 to the best known value at
n = 40, 50, 60 with a ladder of run times and repeated seeds, take the optimal run time per size, and compare the
median and upper-quartile TTS and their growth with n. This replaces "advantage up to k× budget" with a scaling
statement, which is the form a speed claim should take (GV3).

**Against the best known methods (B20_R75, R76).** The same measure against MQLib's BURER2002 and OR-Tools CP-SAT
(B20_R76, after B20_R75 was invalidated by a kind defect) is **UNRESOLVED** on 6 hosts per size: CP-SAT run anytime
for up to 2 s never reached the best known value; BURER2002 is the fastest method when it succeeds but succeeds on
5 of 12 hosts; simulated bifurcation and the system's engine succeed most often (11 and 10 of 12). So no speed
claim against the best known methods can be made yet; a powered replication is the next step.

## 2. Physics-inspired solvers as strong domain baselines

**Weakness.** Until B20_R67 E1d had no baseline from its own field. Dunning, Gupta and Silberholz (2018) found
that only 14% of max-cut/QUBO heuristic papers compared methods under identical termination criteria, and that no
single heuristic is best everywhere. Genesis's custodian already enforces identical criteria; what it lacked was
the field's methods.

**Batch (B20_R69, engineering).** Two physics-derived kinds join `maxcut-tabu-v1`, all with the candidate's own
greedy triangle-free completion so that only the cut search differs:
- `ising-dsb-v1`: **discrete simulated bifurcation** (Goto et al. 2019, 2021). Max cut is the ground state of an
  antiferromagnetic Ising model; SB integrates the classical equations of motion of coupled oscillators driven
  slowly through a bifurcation, so all spins settle at ±1 together. A whole-configuration, continuous search,
  unlike one-flip moves.
- `maxcut-eo-v1`: **τ-extremal optimization** (Boettcher and Percus 2000, 2001), from the Bak–Sneppen model of
  self-organized criticality: always flip one of the worst-adapted vertices, chosen by a power law over fitness
  ranks (τ = 1 + 1/ln n). It never freezes and rearranges at all scales.
These become part of B20_R70's arms; whether any joins E1d's strong-baseline set is a reviewer's decision (review
brief item 1).

## 3. Give the system's own inventions a physics-grade search (GV4 direction)

**Weakness.** `represent_and_repair`, the engine that turns an invented representation into a solver, uses
zero-temperature one-flip descent: it stops at the first local optimum. B20_R66 shows the cost at n60 (optimal on
4 of 10 certified hosts). Every representation the system invents inherits that weakness.

**Batch (B20_R71, engineering + DEV).** A v2 kind that runs any registered representation with an extremal or
annealed move rule in place of descent, leaving the frozen v1 candidate untouched. If it helps across the
representation menu (cross_2, adjacent_k, ordered_k), that is a component improvement the system can apply to
whatever it invents next, rather than a fix for one problem.

**Result (B20_R72): NO_GENERAL_IMPROVEMENT.** Neither move rule helps (cross_2, adjacent_3: no material difference;
ordered_2: worse). What helps is speed (the same descent with a faster repair: +0.45 over the frozen candidate) and
whole-configuration dynamics (simulated bifurcation, best overall). Revised next step: a faster engine or an
SB-style search over encodings.

## 4. Where hard problems live: phase transitions and finite-size scaling

**Weakness.** Several families had no headroom (E3, the equational target, MIP-dominated E1/E1b settings), and the
calibration rules search for headroom setting by setting. Statistical physics locates hard instances near phase
transitions (Cheeseman, Kanefsky and Taylor 1991; Monasson et al. 1999) and reads behaviour through how it scales
with size.

**Use.** Report gaps as functions of n (and density) with fitted exponents, and choose study settings from the
scaling picture rather than one calibrated size. B20_R70's design follows this.

## 5. From people: keep variety, and test robustness to analysis choices

- **Quality-diversity** (MAP-Elites, Mouret and Clune 2015; novelty search, Lehman and Stanley 2011): keep the best
  representation in each behavioural niche instead of one overall best, so the invention search does not settle
  on the max-cut reduction it rediscovered. A candidate design for GV4 once B20_R71 shows which moves help.
- **Many-analysts / multiverse analysis** (Silberzahn et al. 2018; Steegen et al. 2016): report how a DEV verdict
  changes across reasonable analysis choices (MUE, interval method, stratification). Cheap, and it addresses the
  statistician's open questions (B19-OPEN-4) without changing any frozen rule.
- **Blind analysis** (Klein and Roodman 2005, particle physics): the judge recomputes results without knowing which
  arm is the candidate. Genesis already preregisters; blinding the arm labels would remove the last analyst
  degree of freedom on DEV studies.

## What none of this changes

No frozen package, rule, comparator, bound or threshold changes. New kinds are baselines or DEV tools until a
reviewer decides otherwise. Independence (custodian, statistician, replication) is still required for any claim.

## Sources

- T. F. Rønnow et al., "Defining and detecting quantum speedup", Science 345, 420 (2014); arXiv:1401.2910.
- I. Dunning, S. Gupta, J. Silberholz, "What works best when? A systematic evaluation of heuristics for Max-Cut
  and QUBO", INFORMS J. Computing 30(3), 608 (2018).
- H. Goto, K. Tatsumura, A. R. Dixon, "Combinatorial optimization by simulating adiabatic bifurcations in
  nonlinear Hamiltonian systems", Sci. Adv. 5, eaav2372 (2019); H. Goto et al., "High-performance combinatorial
  optimization based on classical mechanics", Sci. Adv. 7, eabe7953 (2021).
- S. Boettcher, A. G. Percus, "Nature's way of optimizing", Artificial Intelligence 119, 275 (2000);
  "Optimization with extremal dynamics", Phys. Rev. Lett. 86, 5211 (2001); arXiv:cond-mat/0010337.
- W. Wang, J. Machta, H. G. Katzgraber, "Comparing Monte Carlo methods for finding ground states of Ising spin
  glasses: population annealing, simulated annealing and parallel tempering", Phys. Rev. E 92, 013303 (2015);
  arXiv:1412.2104.
- P. Cheeseman, B. Kanefsky, W. M. Taylor, "Where the really hard problems are", IJCAI 1991; R. Monasson et al.,
  "Determining computational complexity from characteristic 'phase transitions'", Nature 400, 133 (1999).
- J.-B. Mouret, J. Clune, "Illuminating search spaces by mapping elites", arXiv:1504.04909 (2015); J. Lehman,
  K. O. Stanley, "Abandoning objectives", Evolutionary Computation 19(2) (2011).
- R. Silberzahn et al., "Many analysts, one data set", AMPPS 1(3) (2018); S. Steegen et al., "Increasing
  transparency through a multiverse analysis", Perspect. Psychol. Sci. 11(5) (2016).
- J. R. Klein, A. Roodman, "Blind analysis in nuclear and particle physics", Annu. Rev. Nucl. Part. Sci. 55, 141
  (2005).
