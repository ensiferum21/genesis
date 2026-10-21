# B20_R95 evidence: the system configures its large-graph engine

Builder-run on DEV; it licenses nothing and decides only `tfxw-v1`'s configuration for the large-graph head-to-head.
- **Script:** `scripts/b20r95_configure_tfxw.py`, preregistered at `e443e8c` (SHA-256 `31d2fd51…c8f0`, sent to Daniel
  before it ran; unchanged). Alone, pinned to CPU 0; `code_identity` `f29d62b2…` (the committed tree). One segment,
  4,152 s; 576 evaluations.
- **Hosts:** 16 fresh training hosts in `triangle_free_large_v1` (seed 20269501–20269504, one per cell): planted_cluster
  (p_in 0.8, p_out 0.06) and G(n, 0.5), each at n = 128 and 256, four per cell.
- **Targets** (computed first, 10 s): the best of B20_R89's configuration (two seeds), PASMaxSAT-c and DeepDist (one
  seed each). B20_R89's configuration set every target (DeepDist tied it on one planted n128 host); at 10 s neither
  champion reached the target anywhere else (on G(256, 0.5) they stayed 144–472 edges below, e.g. 8,966 against
  PASMaxSAT-c's 8,822 and DeepDist's 8,743). These are target runs, not the preregistered comparison: one seed per
  champion, the binaries called directly.

## Result: frozen #29

| Round | Hosts × seeds | Kept (best first) |
|---|---|---|
| 0 | 4 × 1 | 16: #14, #29, #63 (DEFAULT), #33, #25, #3, #50, #36, #62 (B20_R89's), … |
| 1 | 8 × 1 | 8: #14, #29, #63, #50, #33, #25, #62, #3 |
| 2 | 16 × 2 | 4: #29, #14, #63, #62 |
| 3 | 16 × 3 | final means: **#29 0.999133**, #14 0.999051, #63 0.998802, #62 0.998486 |

**#29**: cut descent warm starts only (ws 2: no simulated bifurcation, no mean-field annealing), population 6,
probability acceptance (pw 0.2; no parallel tempering), two kicks per iteration with the least tight of four samples
(kpick 4), crossover every 5 iterations, path relinking 20%, restarts after 200 stalled iterations. The runner-up (#14)
also starts from descent only but uses parallel tempering and the edge-frequency memory.

The margins are small (the top four differ by 0.0006 in anytime score, about 0.06%): every configuration is close to
the targets, which B20_R89's configuration set. B20_R89's own configuration ranked 9th after round 0 and 4th at the end;
DEFAULT reached the final four.

Recomputed independently from `race.jsonl`, `targets.json` and `hosts.json` (own code): every score, every round's
survivors and the winner match.
