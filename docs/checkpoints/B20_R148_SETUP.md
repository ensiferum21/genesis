# B20_R148 setup (engineering), and the development looks behind its preregistration

- **Built by:** the builder, 26 Oct 2026, after Daniel's decision to adopt his report "Beyond Genesis-Ω" first
  (`docs/OMEGA_META_ADAPTIVE.md`). No claim, rule, comparator or package changes; the protected judge
  (`autonomy/feedback.py`) and the kernel are untouched.

## What was built

| Part | What it does | Tests |
|---|---|---|
| `src/genesis/autonomy/portfolio.py` | six discovery processes as resumable generators (best-of-N, hill climbing, annealing, Genesis's steady-state evolution, MAP-Elites, racing); arms that spend exactly B evaluations with validation charged (single process, uniform, successive halving across processes, UCB1 with reserved exploration, halving with tuned parameters); the answer is the best validated program; discovery curves at log-spaced checkpoints, normalised quality, AUDC; `tune_params` (G3) on development tasks only; CPU including native child processes | `tests_genesis/test_portfolio.py` (14) |
| `src/genesis/autonomy/portfolio_tasks.py` | three domains as tasks: acquisition rules on the hidden-cause benchmark (B20_R129's language and measure, theory model), max-cut engine programs (`mcx2`, the pinned binary, relative to REX, cuts checked twice), planted formulas (a known optimum) | same file |
| `scripts/b20r148_harness_portfolio.py` | the preregistered study (G0-G3, H1, T1-T3) | `tests_genesis/test_harness_portfolio.py` (11) |

Also in this setup: the mcx and mcx2 binaries were rebuilt here from the in-repository sources and match their pins
byte for byte; every other pinned tool matches its pin (`scripts/b20r98_repin.py`).

## Development looks (disclosed in the script; seeds 99994xxx and 99995xxx, never reused)

Look 1: one instance per domain (acquisition base with A 16, V 16, T 32 worlds; max-cut G(800, 0.06) with weights 1,
A 3, V 3, T 4 graphs at 0.02 s; formula large with 200 items per split), every arm, seed 1. Look 2: acquisition shift
and large with A 24, V 32, T 64 worlds; max-cut torus 28 x 28 and G(800, 0.06) with weights +-1, A 3, V 4, T 4; six
arms, B 1024, seed 1. AUDC is normalised within each look's task by its reference floor and the best any arm of that
look reached.

What the looks changed in the design:
- **Acquisition base saturated.** Many programs reach the best value within 16-64 evaluations, and the portfolio
  arms' answers, chosen on a 16-world V split, were worse on T than programs they had seen. So the study uses
  V 32 and T 64 worlds, and adds the harder shift and large families.
- **Max-cut with weights 1 was flat within noise.** Every arm ended within 0.998-1.001 of REX. So the study uses the
  +-1 families, whose random programs spread from about 0.90 to 1.007.
- **CPU accounting.** Process time did not count the native solver's CPU, which runs in a child process. CPU now
  includes finished children (`portfolio.cpu_now`).

| Look | Task | B | Arm | AUDC | Final | Curve (measured at B/32 ... B) |
|---|---|---|---|---|---|---|
| devlook1 | acquire:base | 512 | single:best_of_n | 0.91 | -3.75 | [-4.625, -3.875, -3.75, -3.75, -3.75, -3.75] |
| devlook1 | acquire:base | 512 | single:hill_climb | 0.75 | -3.8438 | [-4.1562, -4.1562, -4.1562, -4.1562, -3.8438, -3.8438] |
| devlook1 | acquire:base | 512 | single:anneal | 1.0 | -3.75 | [-3.75, -3.75, -3.75, -3.75, -3.75, -3.75] |
| devlook1 | acquire:base | 512 | single:evolution | 1.0 | -3.75 | [-3.75, -3.75, -3.75, -3.75, -3.75, -3.75] |
| devlook1 | acquire:base | 512 | single:map_elites | 0.835 | -3.8125 | [-4.125, -4.125, -4.0625, -3.8125, -3.8125, -3.8125] |
| devlook1 | acquire:base | 512 | single:racing | 0.925 | -3.8438 | [-3.8438, -3.8438, -3.8438, -3.8438, -3.8438, -3.8438] |
| devlook1 | acquire:base | 512 | uniform | 0.762 | -3.8438 | [-4.625, -4.1562, -4.1562, -3.8438, -3.8438, -3.8438] |
| devlook1 | acquire:base | 512 | halving | 0.762 | -3.8438 | [-4.625, -4.1562, -4.1562, -3.8438, -3.8438, -3.8438] |
| devlook1 | acquire:base | 512 | bandit | 0.762 | -3.8438 | [-4.625, -4.1562, -4.1562, -3.8438, -3.8438, -3.8438] |
| devlook1 | acquire:base | 512 | halving_tuned | 0.762 | -3.8438 | [-4.625, -4.1562, -4.1562, -3.8438, -3.8438, -3.8438] |
| devlook1 | acquire:base | 1024 | single:best_of_n | 0.99 | -3.75 | [-3.875, -3.75, -3.75, -3.75, -3.75, -3.75] |
| devlook1 | acquire:base | 1024 | single:hill_climb | 0.858 | -3.7812 | [-4.125, -4.0625, -4.0625, -3.7812, -3.7812, -3.7812] |
| devlook1 | acquire:base | 1024 | single:anneal | 1.0 | -3.75 | [-3.75, -3.75, -3.75, -3.75, -3.75, -3.75] |
| devlook1 | acquire:base | 1024 | single:evolution | 1.0 | -3.75 | [-3.75, -3.75, -3.75, -3.75, -3.75, -3.75] |
| devlook1 | acquire:base | 1024 | single:map_elites | 0.885 | -3.8125 | [-4.125, -4.0625, -3.8125, -3.8125, -3.8125, -3.8125] |
| devlook1 | acquire:base | 1024 | single:racing | 0.925 | -3.8438 | [-3.8438, -3.8438, -3.8438, -3.8438, -3.8438, -3.8438] |
| devlook1 | acquire:base | 1024 | uniform | 0.893 | -3.8438 | [-3.875, -4.125, -3.75, -3.8438, -3.8438, -3.8438] |
| devlook1 | acquire:base | 1024 | halving | 0.893 | -3.8438 | [-3.875, -4.125, -3.75, -3.8438, -3.8438, -3.8438] |
| devlook1 | acquire:base | 1024 | bandit | 0.893 | -3.8438 | [-3.875, -4.125, -3.75, -3.8438, -3.8438, -3.8438] |
| devlook1 | acquire:base | 1024 | halving_tuned | 0.893 | -3.8438 | [-3.875, -4.125, -3.75, -3.8438, -3.8438, -3.8438] |
| devlook1 | mcx2:erdos800 | 512 | single:best_of_n | 0.887 | 1.0004 | [1.0004, 1.0006, 1.0006, 1.0005, 1.0006, 1.0004] |
| devlook1 | mcx2:erdos800 | 512 | single:hill_climb | 0.628 | 1.0004 | [0.999, 1.0006, 1.0005, 0.9981, 1.0004, 1.0004] |
| devlook1 | mcx2:erdos800 | 512 | single:anneal | 0.964 | 1.0008 | [1.0008, 1.0008, 1.0006, 1.0007, 1.0008, 1.0008] |
| devlook1 | mcx2:erdos800 | 512 | single:evolution | 0.794 | 1.0002 | [1.0002, 1.0004, 1.0004, 1.0002, 1.0004, 1.0002] |
| devlook1 | mcx2:erdos800 | 512 | single:map_elites | 0.767 | 1.0001 | [1.0004, 0.9999, 1.0003, 1.0003, 1.0004, 1.0001] |
| devlook1 | mcx2:erdos800 | 512 | single:racing | 0.766 | 1.0002 | [1.0003, 1.0001, 1.0003, 1.0002, 1.0001, 1.0002] |
| devlook1 | mcx2:erdos800 | 512 | uniform | 0.794 | 1.0004 | [1.0004, 1.0004, 1.0002, 1.0004, 1.0002, 1.0004] |
| devlook1 | mcx2:erdos800 | 512 | halving | 0.805 | 1.0002 | [1.0006, 1.0006, 1.0002, 1.0002, 1.0002, 1.0002] |
| devlook1 | mcx2:erdos800 | 512 | bandit | 0.763 | 1.0002 | [1.0006, 1.0002, 1.0001, 1.0002, 1.0002, 1.0002] |
| devlook1 | mcx2:erdos800 | 512 | halving_tuned | 0.837 | 1.0007 | [1.0004, 1.0004, 1.0002, 1.0004, 1.0005, 1.0007] |
| devlook1 | formula:large | 512 | single:best_of_n | 0.649 | 0.6252 | [0.537, 0.5254, 0.5254, 0.6252, 0.6252, 0.6252] |
| devlook1 | formula:large | 512 | single:hill_climb | 0.806 | 0.827 | [0.537, 0.6853, 0.6921, 0.6921, 0.6921, 0.827] |
| devlook1 | formula:large | 512 | single:anneal | 0.688 | 0.7676 | [0.537, 0.537, 0.537, 0.6284, 0.6662, 0.7676] |
| devlook1 | formula:large | 512 | single:evolution | 0.697 | 0.791 | [0.537, 0.537, 0.537, 0.6434, 0.6736, 0.791] |
| devlook1 | formula:large | 512 | single:map_elites | 0.728 | 0.7421 | [0.5888, 0.5888, 0.5888, 0.5888, 0.7333, 0.7421] |
| devlook1 | formula:large | 512 | single:racing | 0.562 | 0.537 | [0.49, 0.49, 0.4967, 0.537, 0.537, 0.537] |
| devlook1 | formula:large | 512 | uniform | 0.7 | 0.6921 | [0.537, 0.537, 0.537, 0.6853, 0.6921, 0.6921] |
| devlook1 | formula:large | 512 | halving | 0.65 | 0.7333 | [0.537, 0.537, 0.537, 0.5888, 0.5888, 0.7333] |
| devlook1 | formula:large | 512 | bandit | 0.673 | 0.6921 | [0.537, 0.537, 0.537, 0.5888, 0.6921, 0.6921] |
| devlook1 | formula:large | 512 | halving_tuned | 0.65 | 0.7333 | [0.537, 0.537, 0.537, 0.5888, 0.5888, 0.7333] |
| devlook1 | formula:large | 1024 | single:best_of_n | 0.62 | 0.7541 | [0.5254, 0.5254, 0.6252, 0.6252, 0.6252, 0.7541] |
| devlook1 | formula:large | 1024 | single:hill_climb | 0.775 | 0.827 | [0.6853, 0.6921, 0.6921, 0.6921, 0.827, 0.827] |
| devlook1 | formula:large | 1024 | single:anneal | 0.625 | 0.7487 | [0.537, 0.537, 0.537, 0.6572, 0.6864, 0.7487] |
| devlook1 | formula:large | 1024 | single:evolution | 0.702 | 0.9114 | [0.537, 0.537, 0.6434, 0.6736, 0.791, 0.9114] |
| devlook1 | formula:large | 1024 | single:map_elites | 0.688 | 0.7284 | [0.5888, 0.5888, 0.5888, 0.7333, 0.7421, 0.7284] |
| devlook1 | formula:large | 1024 | single:racing | 0.522 | 0.5963 | [0.49, 0.4967, 0.537, 0.537, 0.537, 0.5963] |
| devlook1 | formula:large | 1024 | uniform | 0.701 | 0.6921 | [0.5254, 0.6853, 0.6853, 0.6921, 0.6921, 0.6921] |
| devlook1 | formula:large | 1024 | halving | 0.707 | 0.7421 | [0.5254, 0.6853, 0.6853, 0.6921, 0.6921, 0.7421] |
| devlook1 | formula:large | 1024 | bandit | 0.716 | 0.8102 | [0.5254, 0.6853, 0.6853, 0.6921, 0.6921, 0.8102] |
| devlook1 | formula:large | 1024 | halving_tuned | 0.707 | 0.7421 | [0.5254, 0.6853, 0.6853, 0.6921, 0.6921, 0.7421] |
| devlook2 | acquire:shift | 1024 | refs |  |  | low -7.625, high -5.8281, {'eig': -6.6875, 'dec': -6.75, 'degree': -7.875, 'decfall': -6.2031} |
| devlook2 | acquire:shift | 1024 | single:best_of_n | 0.941 |  | [-6.1875, -5.9062, -5.9062, -5.9062, -5.9062, -5.9062] |
| devlook2 | acquire:shift | 1024 | single:hill_climb | 0.88 |  | [-6.0938, -6.0469, -6.0469, -6.0469, -6.0625, -5.9375] |
| devlook2 | acquire:shift | 1024 | single:evolution | 0.862 |  | [-6.0938, -6.0938, -6.0938, -6.0312, -6.0781, -6.0781] |
| devlook2 | acquire:shift | 1024 | single:anneal | 0.874 |  | [-6.0938, -6.0938, -6.0938, -6.0938, -6, -5.8906] |
| devlook2 | acquire:shift | 1024 | halving | 0.891 |  | [-6.1875, -6.1875, -6.1875, -5.9062, -5.8281, -5.8281] |
| devlook2 | acquire:shift | 1024 | bandit | 0.9 |  | [-6.1875, -6.1875, -6.1875, -5.8281, -5.8281, -5.8281] |
| devlook2 | acquire:large | 1024 | refs |  |  | low -7.6172, high -5.875, {'eig': -6.625, 'dec': -6.7188, 'degree': -7.8281, 'decfall': -6.2344} |
| devlook2 | acquire:large | 1024 | single:best_of_n | 0.866 |  | [-6.2031, -6.125, -6.125, -6.125, -6.125, -5.875] |
| devlook2 | acquire:large | 1024 | single:hill_climb | 0.902 |  | [-6.1875, -6.1875, -5.9844, -5.9844, -5.9844, -5.9844] |
| devlook2 | acquire:large | 1024 | single:evolution | 0.857 |  | [-6.125, -6.125, -6.125, -6.125, -6.125, -6.125] |
| devlook2 | acquire:large | 1024 | single:anneal | 0.802 |  | [-6.5156, -6.1875, -6.1875, -6.1875, -6.1875, -6.1875] |
| devlook2 | acquire:large | 1024 | halving | 0.855 |  | [-6.2031, -6.1875, -6.1875, -6.1875, -5.9844, -5.9844] |
| devlook2 | acquire:large | 1024 | bandit | 0.874 |  | [-6.2031, -6.1875, -6.1875, -6.0156, -5.9844, -5.9844] |
| devlook2 | mcx2:torus800 | 1024 | refs |  |  | low 0.9886, high 1.0065, {'rex': 0.9991} |
| devlook2 | mcx2:torus800 | 1024 | single:best_of_n | 0.826 |  | [1.0, 1.0, 1.0037, 1.0056, 1.0051, 1.0051] |
| devlook2 | mcx2:torus800 | 1024 | single:hill_climb | 0.694 |  | [1.0028, 1.0028, 1.0028, 1.0028, 0.9959, 0.9991] |
| devlook2 | mcx2:torus800 | 1024 | single:evolution | 0.667 |  | [0.9995, 1.0, 0.9995, 1.0027, 1.0005, 1.0005] |
| devlook2 | mcx2:torus800 | 1024 | single:anneal | 0.867 |  | [1.0028, 1.0023, 1.0065, 1.0042, 1.0042, 1.0042] |
| devlook2 | mcx2:torus800 | 1024 | halving | 0.784 |  | [1.0014, 1.0014, 1.0014, 1.0014, 1.0056, 1.0051] |
| devlook2 | mcx2:torus800 | 1024 | bandit | 0.737 |  | [1.0014, 1.0014, 1.0014, 1.0014, 1.0014, 1.0051] |
| devlook2 | mcx2:erdos800pm | 1024 | refs |  |  | low 0.9851, high 1.003, {'rex': 0.9966} |
| devlook2 | mcx2:erdos800pm | 1024 | single:best_of_n | 0.779 |  | [0.9944, 0.9944, 1.0016, 1.0015, 0.9996, 1.0016] |
| devlook2 | mcx2:erdos800pm | 1024 | single:hill_climb | 0.692 |  | [0.9971, 0.9977, 0.9979, 0.998, 0.9964, 0.9975] |
| devlook2 | mcx2:erdos800pm | 1024 | single:evolution | 0.858 |  | [0.9994, 1.0005, 1.002, 1.0006, 0.9995, 0.9998] |
| devlook2 | mcx2:erdos800pm | 1024 | single:anneal | 0.851 |  | [0.9991, 0.9997, 1.0015, 1.0015, 0.999, 1.0008] |
| devlook2 | mcx2:erdos800pm | 1024 | halving | 0.677 |  | [1.0009, 0.9917, 0.9932, 1.0008, 1.0011, 0.9975] |
| devlook2 | mcx2:erdos800pm | 1024 | bandit | 0.777 |  | [0.9986, 0.9961, 0.9973, 0.9987, 1.003, 1.0013] |
