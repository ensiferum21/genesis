# B20_R84 evidence: generation 2's control (the same search, hosts and budget, no library)

Builder-run on DEV. It licenses nothing. Judged on fresh hosts in B20_R86.
- **Script:** `scripts/b20r83_generation_search.py b20r84`, preregistered at `9aad649`. Alone, pinned to CPU 0,
  6,241 s. `code_identity` `225ed652…c208`, the committed tree at the run. **Disclosed:** during the last ~40 minutes
  the builder did light work on the other core (compiling and briefly running a C prototype for B20_R87, about four
  minutes of CPU in all, at the lowest priority); the search's fitness is CPU-time-budgeted on its own core.
- **Hosts:** B20_R83's 16 training hosts (copied into `hosts.json` with its role); no new host, no addendum.
- **Library:** none.

## Result

149 generations, 1,497 evaluations, 1,201 distinct programs. Frozen (size 17; final mean **291.61**; finalists
291.52–291.61), on adjacent_2: an iterated local search over cuts (annealed relabels and descent, restarts, return to
the best) with an annealed edge-drop sweep. Generation 2 (B20_R83), on the same hosts with generation 1 callable:
**291.59**. On the training hosts the library made no difference (0.02 edges per host the other way).

## Tests

`tests_genesis/test_generations.py`: Record for B20_R84 (1).
