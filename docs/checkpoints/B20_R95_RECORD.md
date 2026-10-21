# B20_R95 record: the system configured its large-graph engine itself, and chose a simpler one

- **Run by:** the builder, on DEV; licenses nothing; decides only `tfxw-v1`'s configuration for the large-graph
  head-to-head. Script `scripts/b20r95_configure_tfxw.py`, preregistered with B20_R94 at `e443e8c` (SHA-256
  `31d2fd51…c8f0`, sent to Daniel before it ran), unchanged; `code_identity` `f29d62b2…`; alone on CPU 0, one segment
  (4,152 s, 576 evaluations). Evidence `evidence/configure_tfxw_b20r95/`; recomputed independently (match).

## Result

Successive halving over 64 configurations on 16 fresh 128- and 256-vertex hosts (planted and G(n, 0.5)), by the
MaxSAT Evaluation's anytime score at 1 and 5 s against 10 s targets, froze **#29**: cut descent warm starts only (no
simulated bifurcation, no mean-field annealing), a population of 6, probability acceptance (no parallel tempering),
two kicks per iteration choosing the least tight of four sampled edges, crossover every 5 iterations, path relinking
and restarts. Final means: #29 0.999133, #14 0.999051, DEFAULT 0.998802, B20_R89's configuration 0.998486.

## Against the expectation stated before running

| Expected | Found |
|---|---|
| B20_R89's configuration unlikely to win | it ranked 9th after round 0 and 4th of the final four |
| cut descent warm starts | yes (ws 2) |
| a population of 2–8 | 6 |
| kpick above 1 | 4 |
| no mean-field annealing | none |
| simulated bifurcation, parallel tempering, crossover open | no simulated bifurcation, no parallel tempering, crossover kept |
| DEFAULT unlikely in the final four | **wrong**: it came third |

With B20_R92 (no operator shown to help at n = 63) this is consistent: on these hosts and budgets the
physics-inspired warm start (simulated bifurcation) and replica exchange were not chosen; the biology-inspired crossover
and the relinking and restarts were. The margins between the final four are small (0.0006 of anytime score).

**Targets, descriptive:** at 10 s B20_R89's configuration set every target; PASMaxSAT-c and DeepDist reached it on no
host except one tie, and on G(256, 0.5) stayed 144–472 edges below. One seed each, binaries called directly: not the
preregistered comparison, which is B20_R97 (written by the research loop, B20_R96).

## Tests

`tests_genesis/test_configure_tfxw.py` (6): the five design tests and `RecordB20R95` (every score from the values and
targets, every round's survivors, the winner, the frozen configuration, the entrants' ranks).
