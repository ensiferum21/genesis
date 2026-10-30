# PT-2's second attempt (B20_R177, from the first amendment `25eadb7`): stopped by defect B20R177-SEEN

- Ran on CPU 0 on 30 Oct 2026 from 21:15:05 to 22:08:03 SGT, from `/home/claude/pt2b-wt`, and stopped with exit 1 in
  the arm loop of parts 4 and 5, in family B's domain (`KeyError` in `Statement.score`'s memo; `run.log`).
- Only the log's traceback was read. It shows the attempt had reached parts 4 and 5, so its gate held, part 2
  passed, and part 3 extracted a procedure. Nothing else here was read, and these files are not used: PT-2 was
  amended a second time (`scripts/b20r177_proving_test_2.py`, "Second amendment") and runs again from scratch.
