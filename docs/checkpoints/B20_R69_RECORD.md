# B20_R69 record: two physics-inspired domain-baseline kinds, and a plan drawn from physics and how science is done

- **Run by:** the builder. Engineering only; no study, claim, rule, comparator or package change.
- **Why:** Daniel asked (19 Oct 2026) for improvements drawn from physics, the world and people. The B20_R65 review
  and B20_R68 showed where they are needed: E1d had no baselines from its own field, and the system's repair
  engine stops at local optima.

## What was built

- **`docs/PHYSICS_INSPIRED_PLAN.md`:** five ideas, each tied to a weakness in the evidence, a gate and a batch,
  with sources: time-to-solution scaling as in quantum-annealing benchmarking (Rønnow et al. 2014); physics-built
  solvers as strong baselines (Goto et al. 2019/2021; Boettcher and Percus 2000/2001; Dunning et al. 2018 on fair
  heuristic comparison); a physics-grade move rule for the system's own invented representations; phase
  transitions and finite-size scaling; and from scientific practice, quality-diversity, multiverse analysis and
  blind analysis.
- **`ising-dsb-v1`** (`candidate_kinds/ising_dsb.py`): discrete simulated bifurcation. Max cut as the ground state
  of an antiferromagnetic Ising model (J = −A); 32 replicas of coupled oscillators integrated through a slow
  pitchfork bifurcation (a0 = 1, linear pump over 400 steps, c0 = 0.5 / (rms(J) √n), inelastic walls at |x| = 1),
  spins read as sgn(x), each cut completed by the candidate's own greedy triangle-free completion. One CPU, BLAS
  limited to one thread.
- **`maxcut-eo-v1`** (`candidate_kinds/maxcut_eo.py`): τ-extremal optimization (Bak–Sneppen-style): flip a vertex
  chosen by rank of cut fraction with P(k) ∝ k^−τ, τ = 1 + 1/ln n; restart after 20n steps without a new best; the
  same completion.
- Both are domain baselines, not exact ones, so no comparator selection changes. Thanks to B20_R67 their
  registration changed no other kind's identity.

## A defect found and fixed before any study used the kinds

With time step dt = 1 (as some later SB papers state), dSB is unstable on dense hosts: on one B20_R66 n60 host
(420 edges, degree about 14) the coupling force per step exceeds the wall distance and the readout cut was 51 of
420 edges, below a random cut (211). At dt = 0.5 it reaches 259, and with completion the certified optimum.
dt = 0.5 is fixed in the kind, and `test_dense_hosts_are_solved_as_well_as_by_tabu_search` detects the unstable
step (with dt = 1 it fails on an n60 test host: 207 against tabu's 264).

**Development look, disclosed.** To check the kinds before B20_R70, the builder ran tabu, dSB and EO in-process
at 0.5 s on the first three B20_R66 hosts (evidence hosts, not any future study's). Values: tabu 263/279/266, dSB
264/280/267, EO 263/279/266; the candidate scored 262/279/266 there, and the certified or reference bounds are
264, [279, 280], 267. dSB reached the optimum on all three. This is three hosts and a look; B20_R70 is preregistered
with it disclosed.

## Tests

`tests_genesis/test_physics_kinds.py` (9): registration and module binding; closed parameters; known optima
(K10: 25, C5 kept whole, a planted bipartition); τ's scaling; the SB constants; the budget bounds the run; the
dynamics guard on an n60 host (and that it catches dt = 1); a metered runc run for each kind with a re-checked
witness. `test_maxcut_tabu` now allows later kinds in the map.
