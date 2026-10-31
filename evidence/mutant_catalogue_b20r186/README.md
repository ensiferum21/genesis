# B20_R186: the sixth catalogue, a fresh draw of random mutants

`scripts/b20r186_make_mutant_catalogue.py` (31 Oct 2026, about 16:20 SGT, CPU 1) used the fifth catalogue's rules
(`genesis.repairkernel.mutants`; `scripts/b20r185_make_mutant_catalogue.py`) with a new seed (20261186), new job seeds
(14, 15, 16) and 36 entries, excluding every hand-written defect and every mutant of the fifth catalogue. Of the 437
mutants, shuffled, 43 were examined; `selection.json` lists each, in order, with the reason it was kept or passed
over. The 36 are `src/genesis/repairkernel/defects6.py` (SHA-256
`a4cb0c9976022378c70ce6b4ecf0cab8f1203a7b8c67af4893a6bae20feeca5e`).

It was drawn after B20_R185 was recorded and before B20_R186 (the replication) was preregistered. This time the script
printed only the counts; the builder looked at the operator and component counts of the kept mutants (below), not at
the entries. `tests_genesis/test_mutant_catalogue.py` re-runs the draw to the sealed file byte for byte.
By operator: 14 constant, 7 delete, 5 arith, 4 attribute, 2 swap, 2 compare, 2 call. By component: 11 pq, 6 ledger, 4 stock, 4 lease, 2 ttl, 1 graph, 1 bimap, 1 bag, 1 memo, 1 window, 1 lru, 1 registry, 1 calendar, 1 log.
