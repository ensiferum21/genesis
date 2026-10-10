# Resuming the completion batches

1. Extract the latest `GENESIS_COMPLETION_CHECKPOINT_B<k>.zip`.
2. `git clone genesis/source-history.bundle genesis-work && cd genesis-work && git checkout continuation-b14`
3. Read `batch_state.json`: `completed` lists finished batches, `next` is the one to start.
4. Run `python3 scripts/run_test_matrix.py --quick` (or the suites listed in
   `batch_state.json`) to confirm a green start.
5. Continue with the next batch in `BATCHES.md`. Finish it with
   `python3 scripts/make_checkpoint.py --batch <k>`.

External tools are rebuilt with `toolchain/install_tools.sh` (Lean via elan,
CaDiCaL, drat-trim, E prover from their GitHub sources). Their pinned
revisions are recorded in `toolchain/PINS.json` once a batch depends on them.

From B14 on, the plan follows the reviewer roadmap. Read `docs/BLOCKING_DEFECTS.md`
(open defects) and `docs/REQUIREMENTS_LEDGER.md` (dispositions) before
starting; regenerate the ledger with `python3 scripts/build_ledger.py` whenever a
row changes.
