# B20_R93 evidence: the adaptation cell run over every time-to-solution study

Builder-run; it licenses nothing and changes no study. Produced by `scripts/b20r93_cell.py . evidence/adaptation_cell_b20r93
--today 2026-10-20` on the tree after B20_R92 was committed (`c3af5a7`) and the cell merged unchanged (`71df48c`; the
cell's concatenated digest `b5254e60…317a`, preregistered with the B20_R93 record at `7dbc1b1`).

| File | What |
|---|---|
| `caveats.json` | every discovered study's caveats as the receptors sensed them (B20_R70, R75, R76, R77, R81, R90, R92) |
| `ledger.json` | lineages, attempts with doses and outcomes, response memory, the designs read from the evidence, and the cell's account of what it inferred |
| `cost_model.json` | the per-run overhead fitted to the run logs (0.3495 s) and predicted against observed wall time per study |
| `capabilities.json` | what the code and the evidence show the system can do |
| `next_design.json`, `plan.json` | the next study the cell proposes, and why (chosen responses, marginal costs, the over-budget note, work orders) |
| `checkpoint.json` | the checkpoint on that proposal (pass) |
| `CAVEATS.md` | all of it for a reader (also copied to `docs/CAVEATS.md`) |

The preregistered prospective check on B20_R92 passed all nine statements (record: `docs/checkpoints/B20_R93_RECORD.md`;
tests: `tests_genesis/test_adaptation_cell.py::ProspectiveB20R92`).
