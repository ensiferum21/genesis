# B20_R80 record: random programs nearly match the system's program search on its training hosts

- **Run by:** the builder. DEV only. **Setup:** `e579deb` (before B20_R79 had run). Alone, pinned, 6,258 s.
- **Evidence:** `evidence/random_program_control_b20r80/`.

## Result

Random sampling from the same language for the same 6,000 CPU s on B20_R79's training hosts, chosen the same way,
froze `relabel 100 random (anneal); relabel best (sideways)` on the cut, final mean **287.30**, against the search's
**287.34**. The language itself, not the search, does most of the work on these hosts: a two-statement iterated local
search is easy to draw at random. The builder expected random search to be weaker; on the training hosts it is not,
measurably.

What the search found that random sampling did not keep is the swap-like edge sweep (B20_R79's program has one, this
one does not). Whether that matters on unseen hosts is B20_R81's preregistered question (`found_vs_random`).

## Tests

`tests_genesis/test_self_found_solver.py`: Record for B20_R80 (2).
