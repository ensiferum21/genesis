# B20_R185 (SR-2c): the rehearsal, on development defects only

The dry run of `scripts/b20r185_space_invention.py --rehearse` (31 Oct 2026, about 14:19 to 14:41 SGT, from a worktree of
`652f36d` with the new code copied in, on CPU 1, which other jobs shared): an eight-defect curriculum (E3, N1, N2, S2, B2,
R1, K1, G2) and four other development defects (X2, K4, G3, X4) in place of the mutants; the loop never ran on a mutant.
A first rehearsal of an earlier version of the script (without the slice pauses, otherwise the same) gave the same
result.

Generation 1: version 3 repaired 4 of the 8 and the dream the other 4; 6 transformations were lifted and 3 admitted on
other families (`detect1-S2:before:rename-attr` by E3, `detect1-G2:transplant:map-meth-add-discard` by N2,
`dream1-E3:after:rename-attr` by S2). Generation 2: the inventor derived 6 candidates and 2 were admitted
(`g2-transfer:transplant:rename-attr` by E3, `g2-generalise:transplant:any-meth` by N1); the deriver's beliefs moved
for transfer and generalisation. No probe proposed a false repair. On the stand-ins: version 3 1 of 12, generations 1
and 2 3 each (all by a transformation), the grammar 3, enum 0; X2, which no arm reached in B20_R181 or B20_R182, was
repaired in all three jobs by the transformation Genesis lifted from its own dream of E3. The record test drafted for
B20_R185 passed on this directory (6 tests, 17 s). Its test numbers are not evidence: the stand-ins are development
defects.
