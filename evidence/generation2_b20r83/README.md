# B20_R83 evidence: generation 2 of the program search, with generation 1 callable

Builder-run on DEV. It licenses nothing. Judged on fresh hosts in B20_R86.
- **Script:** `scripts/b20r83_generation_search.py b20r83`, preregistered at `9aad649` (SHA-256 `8b2443f7…f9f4e`).
  Alone, pinned to CPU 0, 6,237 s. `code_identity` `03353700…546c`, the committed tree at the run.
- **Training hosts:** 16 fresh DEV planted-cluster hosts at n63 (seed 20268301), excluding 3,219 exposed identities.
- **Library:** one entry, B20_R79's frozen body (generation 1), callable as `["macro", 0]`.

## Result

149 generations, 1,498 evaluations, 1,202 distinct programs. Frozen (final mean 291.59 at 0.25 and 1.0 s, 2 fresh
seeds; the four finalists 291.58–291.59):

```
rep cross_2
split 25% / 75%:
  first 25%:  descent; macro 0 (generation 1); force one edge in (keep if improved)
  last 75%:   split 90% / 10%: drop one edge (anneal) | descent; macro 0
              relabel 100 random vertices (sideways)
              loop: macro 0; relabel the best vertex (anneal); descent
```

All 16 programs of the final population call generation 1. The program adds a kick (force, improve) and edge drops
around it. Fitness here is on this study's own training hosts, so it is not comparable with B20_R79's 287.34; B20_R86
compares the generations on common fresh hosts.

## Tests

`tests_genesis/test_generations.py`: Record for B20_R83 (2).
