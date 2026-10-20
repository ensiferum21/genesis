# B20_R80 evidence: random programs, the control for the system's program search

Builder-run on DEV. It licenses nothing. Its frozen program is tested on fresh hosts in B20_R81.
- **Script:** `scripts/b20r80_random_program_control.py`, preregistered at `e579deb` before B20_R79 had run
  (SHA-256 `61679fdc…2fc3`). Alone, pinned to CPU 0, 6,258 s; sampling CPU 6,160 s. `code_identity` `76e347ca…d8ad`,
  the committed tree at the run (`14bfe59`).
- **Hosts:** B20_R79's 16 training hosts (the same task ids, read from its `hosts.json`); no new host was drawn, so
  there is no exposure addendum.

## Result

1,495 random programs from B20_R78's language (the fixed generator), each evaluated once as in the search (0.25 s per
host); mean 273.6 edges, best single evaluation 287.31. The same final choice as the search's (4 finalists at 0.25
and 1.0 s, 2 fresh seeds) froze a 2-statement program on adjacent_2 (the cut):

```
relabel 100 random vertices with annealing acceptance; relabel the best single vertex (sideways)   (repeated)
```

an iterated local search over cuts in its simplest form, with no edge step (32% of the sampled programs had a
swap-like step; 5 of the 20 best single evaluations). Final means of the finalists: **287.30**, 287.28, 287.22, 287.19.

## Against B20_R79 on the same training hosts (descriptive)

B20_R79's search froze a program with a final mean of 287.34; random sampling, with the same budget and choice,
287.30. On the hosts both were chosen on, the search's advantage is 0.04 edges per host, inside the noise of four
runs per host. The expectation (random weaker) is not borne out on the training hosts. B20_R81 compares the two on
fresh hosts, where the question is decided.

## Tests

`tests_genesis/test_self_found_solver.py`: Record for B20_R80 (2): the frozen program is in the language, its
descriptor rebuilds and it is the best finalist; the history has only first evaluations of distinct programs on
B20_R79's hosts.
