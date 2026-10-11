# B19 evidence: useful discovery, part 1 (W13–W15)

Builder-generated, DEV material only. Nothing here was reviewed independently. There is
no sealed task, no promoted claim and no novelty claim; W17 found prior art for the
mathematics, see `../literature_b19/`.

Run: `scripts/b19_discovery.py` (`run.log`, 2,355 s on 2 cores), then
`scripts/b19_active_v2.py` (`active_v2/`). The seeds are in the scripts. All three
packages replay from source (`replay.json`).

## W13 — construction meets obstruction (`obstruction/`)

**Relaxation.** For the largest motif-free subgraph, Genesis uses the LP relaxation
x(M) ≤ |M| − 1 over motifs M. Its dual is solved by scipy/HiGHS, which is an untrusted
producer. The dual is turned into exact rationals and repaired, and an independent
checker re-checks it in exact arithmetic (`discovery/obstruction.py`).

**Checked relation.**
- **Validity of the inequalities.** Lean proves `tri_not_all` and `c4_not_all`, both
  CHECKED, in `obstruction/package.json`.
- **Objective direction and weak duality.** These are stated in the checker; every
  certificate is checked for dual feasibility edge by edge.

**Joint method.** A construction (B18 represent-and-repair, 1 s), then the LP
certificate, then SAT/DRAT on whatever gap remains. It is compared with the reference
(greedy start, then the SAT/DRAT loop) under the same 60 s wall budget, on 12 fresh hard
DEV hosts (n = 30, 36, 40):

| | Optimum certified | Mean gap (upper − lower) |
|---|---|---|
| reference | 6 / 12 | 21.2 |
| joint | 11 / 12 | 0.08 |

- Where both certified an optimum, the optima agree (0 disagreements).
- Every joint upper bound came from an LP certificate that was re-checked VALID.
- On one task the joint method ended at 99..100: the LP bound is 100, but the SAT
  search did not find a 100-edge witness within the budget. The reference found that
  witness but could not bound it below 142.
- The reference once overran its budget (107 s). This is a property of the B13
  reference loop and is recorded as it happened.

## W14 — active experiments and identifiability (`active/`, `active_v2/`)

**Setup.**
- **Hypotheses.** For each of three task families, which method reaches the certified
  optimum most often. An action runs one method on one fresh task.
- **Observation model.** Beta–Bernoulli per (method, family). Calibration on held-out
  halves: mean absolute error 0.13.
- **Identifiability.** `rr_cross_2` and `rr_adjacent_2` are the same decoder by B18's
  checked theorems. They are collapsed and reported UNRESOLVED within their class; they
  are never separated by a tie-break. Their per-task values differ only because their
  seeds differ.

**First evaluation (`active/`).** 3 families, 43 certified tasks, 40 repetitions:

| Budget (share of pool CPU) | eig P(correct) / regret | round-robin | random |
|---|---|---|---|
| 20% | 0.708 / 0.059 | 0.858 / 0.018 | 0.875 / 0.024 |
| 40% | 0.942 / 0.005 | 0.992 / 0.001 | 0.958 / 0.006 |

The EIG policy lost to both fixed and random selection. This result is kept. A likely
cause:
- the entropy of the arg-max, estimated by Monte Carlo and divided by cost, prefers the
  cheap actions (low_cycle and multistart cost about 0.18 s, the repair methods 0.5 s);
- its estimates are noisy at 100 draws.

**Second evaluation (`active_v2/`).** Two policies were added after the first result:
- `kg`, an exact lookahead knowledge gradient per unit cost;
- `top_two`, top-two Thompson sampling.

Because they were designed after seeing that result, they were evaluated on fresh pools
from a new seed (46 certified tasks), alongside the original three:

| Budget | eig | round-robin | random | **kg** | top_two |
|---|---|---|---|---|---|
| 20% | 0.742 / 0.053 | 0.783 / 0.039 | 0.808 / 0.033 | **0.933 / 0.010** | 0.842 / 0.040 |
| 40% | 0.942 / 0.008 | 0.925 / 0.011 | 0.958 / 0.008 | **1.000 / 0.000** | 0.942 / 0.020 |

Each cell is P(correct class) / mean regret.

On the fresh pools, kg reduces downstream regret below both fixed and random selection
at both budgets. EIG still loses to random at 20%. This is W14's done-when, met on DEV
by a policy chosen after one failed evaluation. A sealed comparison would freeze kg
first.

## W15 — causal catalysis (`catalysis/`)

**Solver factorial.** 24 fresh DEV tasks: erdos n=22 from the adopted calibration, and
erdos n=30. Cells are encoding optimisation × repair, with matched CPU (0.5 s):

| Arm | Mean edges | Optimum hits |
|---|---|---|
| full (optimised cut + repair) | 77.04 | 10 |
| cut only | 75.71 | 4 |
| placebo (random cut + repair) | 73.88 | 0 |
| random cut | 70.04 | 0 |
| removal: repair only (no representation) | 74.67 | 1 |
| effort: repair only at 4× CPU | 75.38 | 1 |
| effort: full at 4× CPU | 77.04 | 10 |
| conventional: DSL low_cycle | 75.46 | 3 |

Differences from the full arm:

| Comparison | Effect |
|---|---|
| full − placebo | +3.17 |
| full − removal | +2.38 |
| full − (removal at 4× CPU) | +1.67 |
| full − conventional | +1.58 |

The gain survives removal, the placebo, the effort control and the conventional
alternative on both families. The two factors interact negatively (−2.5): the repair
step matters less once the cut is optimised. Four times the CPU does not help the full
arm.

**Concept controls.** The same 16 fresh statements and the same recipes as in B18:

| Arm | Proved | Disproved | Unresolved |
|---|---|---|---|
| none (B18) | 4 | 4 | 8 |
| retrieval (B18) | 4 | 4 | 8 |
| **concept (B18)** | **8** | 4 | 4 |
| manual Antitone (B18) | 8 | 4 | 4 |
| placebo concept (B19: reversed order, same shape) | 4 | 4 | 8 |
| effort (B19: no concept, 4× heartbeats) | 4 | 4 | 8 |

The concept's gain survives the placebo and the effort control. The equivalent-
information alternative (the manual arm) does exactly as well, so the gain belongs to
the abstraction, not to the recovery procedure. The abstraction is the classical lower
set (W17).
