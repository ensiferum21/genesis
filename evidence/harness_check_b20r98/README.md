# B20_R98 evidence: the harness check of DeepDist-c and NuWLS-c-2026 on large hosts: NOT_THE_HARNESS

Builder-run on DEV. It licenses nothing.
- **Script:** `scripts/b20r98_harness_check.py`, preregistered at `779831c` (SHA-256 `52369b92…57bb`).
- **Run:** alone on CPU 0, 1,729 s, on 23 Oct 2026. `code_identity` `ce39e57b…`, the committed tree.
- The kind descriptors are B20_R97's own: `pre_r98_id` of each equals B20_R97's recorded id, and the script refuses
  otherwise.

| File | What |
|---|---|
| `runs.jsonl` | 80 runs: 4 hosts x 4 solvers x 5 conditions. Each has the value of the parsed model (re-checked against every hard clause), the solver's own last "o" claim, its "v" lines, how it stopped, and B20_R97's value for the same host and solver |
| `summary.json` | Labels per solver, the headline, best known values, descriptors |
| `run.log` | The run |

## Result: NOT_THE_HARNESS

No condition under our control changes either solver's result. For DeepDist-c and NuWLS-c-2026:
- **The output is read correctly.** In every direct run, the value we read equals the solver's own last reported cost
  (`claimed`).
- **The input, the sandbox and the stop make no difference.** Pipe and file give identical values. The sandbox (C0)
  matches the direct pipe run. Letting DeepDist-c stop itself on its own timeout alarm gives the same value as SIGTERM.
- **C0 reproduces B20_R97** on 7 of the 8 (host, solver) pairs, exactly. The eighth is DeepDist-c on the n128
  G(n, 0.5) host: 1,168 against 1,174.

| Host (best known) | DeepDist-c 10 s / 60 s | NuWLS-c-2026 10 s / 60 s | DeepDist (control) 10 s | NuWLS-c-2026-UB (control) 10 s |
|---|---|---|---|---|
| planted n128 (1,170) | 720 / 738 | 1,162 / 1,164 | 1,165 | 1,162 |
| G(128, 0.5) (2,302) | 1,172 / 1,197 | 2,239 / 2,256 | 2,276 | 2,233 |
| planted n256 (4,506) | 2,268 / 2,316 | 2,325 / 2,329 | 4,471 | 4,466 |
| G(256, 0.5) (8,948) | 3,595 / 3,595 | 3,590 / 3,610 | 8,515 | 8,467 |

DeepDist-c reaches 40–62% of the best known value on every host. NuWLS-c-2026 reaches 97–99% at n128 and 40–52% at
n256. Both are near flat from 10 s to 60 s. NuWLS-c-2026-UB is the same code with an upper-bounding phase, built from
its own archive, and it does not collapse. So the collapse is these two solvers' own search on these instances at these
budgets, not our harness. B20_R97's margins over them stand as what these solvers do here.

They are not a statement about the solvers in general:
- the Evaluation's instances are other families;
- the Evaluation used other hardware;
- its budgets are 60 and 300 s.

**Disclosed, beside the labels.** On the n256 G(n, 0.5) host the two controls ended 3% below their B20_R97 values at
10 s: DeepDist 8,515 against 8,777, and NuWLS-c-2026-UB 8,467 against 8,733. Given 5 s more (C3), they reached
B20_R97's values exactly.
- Encoding this host takes the harness about a second, and its parse takes the solver longer, so on the densest
  instance a 10 s wall-clock budget sits on the edge of where these solvers improve.
- Run-to-run machine speed then decides a few hundred edges.
- This held on one host of four, below the preregistered 3-of-4 rule. It is a caveat for any 10 s comparison on
  G(256, 0.5): such comparisons should allow for a 3% band.

## Tests

`tests_genesis/test_harness_check.py`: Record (3). The labels recompute from the runs, the descriptors are B20_R97's,
and every direct run's value equals the solver's own claim.
