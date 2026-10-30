# PT-2's first attempt (B20_R177, from `a7303de`): stopped by defect B20R177-LIBRARY

- Ran on CPU 0 on 30 Oct 2026 from 20:23:09 to 21:04:12 SGT, from `/home/claude/pt2-wt`, and stopped with exit 1 in
  part 3's replay (`StopIteration` raised inside a generator while expanding a library macro; `run.log`).
- Only the log's traceback was read. It shows the attempt had reached part 3's replay, so its gate held, G
  certified a bound beyond the predecessor, and a procedure was extracted. Nothing else here was read, and these files
  are not used: PT-2 was amended (`scripts/b20r177_proving_test_2.py`, "Amendment") and runs again from scratch.
