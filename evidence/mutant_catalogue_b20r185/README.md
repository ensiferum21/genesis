# B20_R185 (SR-2c): the fifth catalogue, drawn by random mutation

`scripts/b20r185_make_mutant_catalogue.py` (31 Oct 2026, about 12:55 SGT, CPU 1) enumerated the 437 single-place
mutants of the fifteen components' methods (`genesis.repairkernel.mutants`: deletion, arithmetic, comparison,
constant, argument swap, attribute and call operators), shuffled them with the seed 20261031, and examined them in that
order until 24 were real obstacles (the guard accepts the source, it is no hand-written catalogue's defect, every job
of seeds 11, 12 and 13 is interrupted, the verifier rejects it and accepts the correct source). 30 were examined: 3
were hand-written catalogue defects, 3 interrupted no job of seed 11. `selection.json` lists each, in order, with the
reason. The 24 are `src/genesis/repairkernel/defects5.py` (SHA-256
`59c4fc31a2500a4976a007f8f7fd66f548404f379a2600eba395f7eb910e3baa`): by operator, 9 constants, 6 deletions, 4
attributes, 2 arithmetic, 1 comparison, 1 swap, 1 call; by component, 8 in
the indexed heap (pq), 4 in stock, 3 in the ledger, 3 in the bag, 2 in the TTL cache, 1 each in lease, window, log
and stats.

It was written and sealed before any of SR-2c's research code. The builder saw, before sealing, the operators' output
on the bag component while testing the enumerator (a dozen descriptions), and after it the list of the 24 entries'
identifiers, components and operators printed by the script; not their text. Nothing was chosen by hand.
`tests_genesis/test_mutant_catalogue.py` re-runs the selection and gets the sealed file byte for byte.
