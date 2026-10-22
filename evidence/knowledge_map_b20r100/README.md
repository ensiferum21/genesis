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

The `score` step writes `summary.json` and `cells.jsonl` here after B20_R86 is recorded.
