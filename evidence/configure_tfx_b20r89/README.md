# B20_R89 evidence: the system configures its own engine (successive halving over `tfx-v1`'s operators)

Builder-run on DEV. It licenses nothing; it decides only the configuration B20_R90 judges.
- **Script:** `scripts/b20r89_configure_tfx.py`, preregistered at `9f8eecc` (SHA-256 `855dd786…a765`, sent to Daniel
  before the run). Alone, pinned to CPU 0, 1,827 s. `code_identity` `6f1ba967…`, the committed tree.
- **Hosts:** 32 fresh n63 planted (0.8, 0.06) training hosts, seed 20268901 (`hosts.json`); targets in `targets.json`
  (best of DEFAULT at 5 s, two seeds, and DeepDist at 5 s). On one host (0007) DeepDist found 279 and DEFAULT 278.
- **Race:** 128 configurations (126 drawn, seed 20268902; DEFAULT #126; DEV_PICK #127), 3,072 evaluations
  (`race.jsonl`), score = mean gap at 0.02, 0.05, 0.1 and 0.25 s.

## Result

| Round | Hosts × seeds | Kept | Best (mean gap) | DEFAULT | DEV_PICK |
|---|---|---|---|---|---|
| 0 | 4 × 2 | 64 | several at 0 | 22nd (0.094) | 6th (0) |
| 1 | 8 × 2 | 32 | #76 0.109 | 39th, out (0.25) | 7th |
| 2 | 16 × 2 | 16 | #38 0.070 | | 4th |
| 3 | 32 × 2 | 8 | #76 0.055 | | 5th |
| 4 | 32 × 4 | 4 | #76 0.053 | | 4th (0.064) |

**Frozen: #76** (`config.json`): warm starts from simulated bifurcation (8 replicas, 400 steps) and cut descent;
a population of 12; three kicks per step; acceptance by Metropolis at per-member temperatures 0.3–4 with replica
exchange every 20 iterations (parallel tempering); crossover every 5 iterations; path relinking 20%; restarts after 50
stalled iterations. Not used: mean-field annealing, the ant-colony memory (rho 0.1 with pherw 0 has no effect).
The final four are close (0.053–0.064); two of them use no simulated bifurcation.
