# B20_R89 record: the system configures its own engine

- **Run by:** the builder, as preregistered in `B20_R88_RECORD.md` (script at `9f8eecc`, SHA-256 `855dd786…a765`,
  sent to Daniel before the run). Alone, pinned to CPU 0, 1,827 s; `code_identity` equals the committed tree.
- **No claim, rule, comparator or package changes.** It decides only `tfx-v1`'s configuration for B20_R90.

## Result

Successive halving over 128 configurations of `tfx-v1` on 32 fresh n63 training hosts (3,072 evaluations; score:
mean gap to the host's target at 0.02, 0.05, 0.1 and 0.25 s). The builder's first design (DEFAULT) was eliminated in
round 1 (39th of 64); B20_R88's development pick reached the final four (4th). **The race froze #76** (mean gap
0.053; the next three 0.055, 0.057 and 0.064):

| Operator | In #76 | Origin |
|---|---|---|
| warm starts: simulated bifurcation (8 replicas) and cut descent | yes | physics (Goto et al. 2021); greedy |
| population of 12, three kicks per step, (1,2)-swaps | yes | iterated local search; Andrade, Resende and Werneck 2012 |
| Metropolis acceptance at temperatures 0.3–4, replica exchange every 20 | yes | statistical physics: parallel tempering |
| crossover (intersection, refill, improve) every 5 iterations | yes | biology: memetic algorithm |
| path relinking toward the best (20% of kicks) | yes | Glover 1997 |
| restarts after 50 stalled iterations | yes | |
| three-body mean-field annealing | no | physics (free-energy machine) |
| ant-colony edge memory | no (its weight is 0) | biology |

**Against the builder's expectation** ("probably no simulated bifurcation"): the system kept simulated bifurcation
and also chose parallel tempering and crossover. The margin is small, though: the final four are within 0.011 edges
of mean gap, and two of them use no simulated bifurcation. As expected, the ant-colony memory was not used.

Evidence: `evidence/configure_tfx_b20r89/` (README, `config.json`, `summary.json`, `race.jsonl`, `hosts.json`,
`targets.json`, `run.log`).

## Tests

`tests_genesis/test_beat_champions.py`: Record for B20_R89 (1): the frozen configuration is valid, is the summary's,
has the lowest final mean among the last four, and the race's evaluations and hosts are complete.
