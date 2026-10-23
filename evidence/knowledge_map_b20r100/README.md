# B20_R100 evidence: the knowledge map's predictions for B20_R86, written before B20_R86 runs

Builder-run on DEV. It licenses nothing.

- **Script:** `scripts/b20r100_knowledge_map.py predict`, preregistered at `779831c`. Run on 23 Oct 2026, before
  B20_R86 had drawn its hosts. `code_identity` `ce39e57b…`, the committed tree.
- **Map:** `autonomy.kmap.Map` fitted on 10,154 cells of the eight studies the adaptation cell reads (B20_R70 to
  B20_R97; corpus SHA-256 `1fae5362…`). The sd scale is 2.51, learned from its own replay.

| File | What |
|---|---|
| `predictions_b20r86.json` | For each arm (gen1, gen2, gen3, control, engine) and run time (0.05–2 s): the predicted quality on a planted n63 host, with sd and the level it rests on (method, or class for methods it has never seen), on a density grid 0.18–0.30. Also the naive baseline per arm and the corpus identity |
| `replay.json` | Each recorded study predicted from the studies before it (development look, disclosed in the script) |

**What it predicts, at density 0.235.**

| Arm | Run times | Predicted quality | sd | Based on |
|---|---|---|---|---|
| gen1 | 0.05–2 s | 0.994–1.000 | 0.003 | method |
| engine | 0.05 s | 0.945 | 0.012 | method |
| engine | 0.1 s and longer | 0.998 and higher | 0.012 | method |
| gen2, gen3, control | all | 0.994–1.000 | 0.125 | class ("language programs") |

gen2, gen3 and control are methods the map has never seen. Its intervals for them are 10 to 40 times wider than for
the methods it has seen; that is the "knows what it does not know" property, scored after B20_R86.

## Result (scored on 23 Oct 2026, after B20_R86 was recorded): MAP_BETTER

`scripts/b20r100_knowledge_map.py score` writes `summary.json` and `cells.jsonl` (600 cells: 24 hosts x 5 arms x 5
run times).

| | Map's error | Baseline's error |
|---|---|---|
| all cells | 0.0020 | 0.0323 |
| seen methods (gen1, engine) | 0.0023 | 0.0095 |
| unseen methods (gen2, gen3, control) | 0.0018 | 0.0475 |

- **Primary statistic.** The mean of d (the baseline's error minus the map's) is +0.0303, with a host-stratified
  bootstrap 90% interval of [+0.0297, +0.0307]. The verdict is MAP_BETTER.
- **Coverage of the 90% intervals.** 97% of all cells fall inside: 93% for the seen methods and 100% for the unseen
  ones.
- **It knew what it did not know.** The unseen methods got intervals 17 times wider (0.41 against 0.024), and their
  coverage held.
- **No surprises.** No cell fell outside three times the scale.

**How strong this is.** The test was easy:
- the hosts are small, and 46% of the cells reached quality 1;
- most of the map's lead on the unseen methods comes from knowing they are language programs on easy hosts, where the
  baseline uses the mean over every recorded cell, harder studies included;
- on the seen methods, the fair comparison, it is 4 times more accurate (0.0023 against 0.0095).

It is a first prospective success at the simplest level. The test that matters is prediction on hard studies (large
hosts, Gset), where outcomes differ between methods.

Record tests (2): the score recomputes from the committed predictions and B20_R86's rows, and the predictions were
committed before B20_R86's first row.
