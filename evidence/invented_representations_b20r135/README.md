# B20_R135 evidence: representations Genesis chooses against the textbook ones (DEV)

Written by `scripts/b20r135_invented_representations.py` (preregistered `7040a3c`, SHA-256 `4b23e1a0…95cc5bd`),
alone on CPU 0 from a clean worktree of `f37e792`, 27 Oct 2026, 09:42–11:10 SGT, in one segment. The record is
`docs/checkpoints/B20_R135_RECORD.md`: verdict INVENTED_REPRESENTATION_BETTER (k = 3 and 4; k = 5 kept one-hot).

| File | What it holds |
|---|---|
| `summary.json` | the analysis (Part B per k: means, the primary sign test, Holm, chosen against the compiler and MaxSAT; Part C per family; Part A synthesis counts), validity, the cascade, the engine's median CPU, verdict, code identity |
| `choices.json` | Genesis's choice per k: the candidate code tables, their plans and pilot conflicts, the tables searched and feasible |
| `runs.jsonl` | Part B: 240 colouring runs (k, graph seed, arm): the colouring, conflicts by the family's checker and independently, CPU, solver information |
| `families.jsonl` | Part C: 160 runs (family, instance seed, arm): the assignment, satisfied constraints by the checker and independently, CPU |
| `synthesis.jsonl` | Part A: 60 relations: MILP and search results, ancillas, CPU, both checkers' verdicts, uniform gadgets |
| `family_library.json`, `cascade.json` | the four synthesised family gadgets; the parked specs, the cascade's reactivations, the null trigger, the overhead and the vault's verification |
| `vault.tar.xz` | the study's vault (13 artifacts, 58 events), packed after the run; restores and verifies |
| `run.log` | the study's log |

Re-check: `tests_genesis/test_invented_representations.py::RecordB20R135`.
