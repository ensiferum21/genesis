# B20_R187: the seventh catalogue, a fresh draw of random mutants for a third generation

`scripts/b20r187_make_mutant_catalogue.py` (31 Oct 2026, about 18:30 SGT, CPU 1) used the fifth catalogue's rules with a
new seed (20261187), new job seeds (17, 18, 19) and 36 entries, excluding every hand-written defect and every mutant of
the fifth and sixth catalogues (9 such were passed over; 1 interrupted no job of seed 17; 46 examined;
`selection.json`). The 36 are `src/genesis/repairkernel/defects7.py` (SHA-256
`9836c54d9be1738def9f04089f45857e35c8e852b0666645a264aa66741c9572`). It was drawn after B20_R186 was recorded and before
any code of B20_R187 (SR-2d) existed. The script printed counts only; the builder looked at the operator and component
counts below, not at the entries. `tests_genesis/test_mutant_catalogue.py` re-runs the draw to the sealed file.

By operator: 11 attribute, 11 delete, 6 constant, 4 arith, 3 compare, 1 call. By component: 7 stock, 5 ttl, 4 ledger,
4 pq, 3 bag, 3 lease, 2 log, 2 graph, 2 bimap, 2 calendar, 1 window, 1 stats.
