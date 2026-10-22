# B20_R85 evidence: generation 3 of the program search, with generations 1 and 2 callable

Builder-run on DEV. It licenses nothing. Judged on fresh hosts in B20_R86.
- **Script:** `scripts/b20r83_generation_search.py b20r85`, preregistered at `9aad649` (SHA-256 `8b2443f7…f9f4e`),
  deferred on 20 Oct 2026 and run unchanged on 22 Oct 2026. Alone on CPU 0, 6,397 s (6,162 CPU s);
  `code_identity` `7ac76c0b…7609`, the committed tree at the run (no code changed during it).
- **Disclosed: the other core.** From about 30 minutes in, it was busy with the builder's work, at the lowest priority:
  - rebuilding the state-of-the-art toolchain (the 2024 and 2026 MaxSAT solvers, an Aperture rebuild check);
  - development looks for B20_R99 (exchange enumeration and CP-SAT region solves on exposed hosts);
  - fitting the knowledge map's prototype for B20_R100.

  This search's fitness is metered in CPU time on its own core, so the other core changes its throughput only through
  shared caches and memory. Its values are not timing results.
- **Training hosts:** 16 fresh DEV planted-cluster hosts at n63 (seed 20268501), excluding 3,339 exposed identities.
- **Library:** two entries: generation 1's body (B20_R79, `["macro", 0]`) and generation 2's body (B20_R83,
  `["macro", 1]`, which itself calls entry 0).

## Result

149 generations, 1,497 evaluations, 1,201 distinct programs. Frozen: size 13, on cross_2, final mean **290.00** at
0.25 and 1.0 s with 2 fresh seeds. The four finalists scored 289.84–290.00.

```
rep cross_2
macro 0 (generation 1)
split 25% / 75%:
  first 25%:  repeat until no new best (stall 1): loop { macro 1 (generation 2); macro 0 }; descent
  last 75%:   macro 1; descent; macro 1
repeat until 10 runs find no new best: descent; macro 0
```

The frozen program calls both earlier generations. So do all 16 programs of the final population, and every finalist
calls generation 2. It adds no new move: it is a schedule of the two earlier discoveries with descent.

Fitness is measured on this study's own training hosts, so 290.00 is not comparable with B20_R83's 291.59 or B20_R84's
291.61. B20_R86 compares the generations and the control on common fresh hosts.

## Tests

`tests_genesis/test_generations.py`: Record for B20_R85 (2).
