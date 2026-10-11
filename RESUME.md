# Resuming the completion batches

1. Extract the latest `GENESIS_COMPLETION_CHECKPOINT_B<k>.zip`.
2. `git clone genesis/source-history.bundle genesis-work && cd genesis-work && git checkout continuation-b14`
3. Read `batch_state.json`: `completed` lists finished batches, `next` is the one to start.
4. Run `python3 scripts/run_test_matrix.py --quick` (or the suites listed in
   `batch_state.json`) to confirm a green start.
5. Continue with the next batch in `BATCHES.md`. Finish it with
   `python3 scripts/make_checkpoint.py --batch <k>`.

External tools are rebuilt with `toolchain/install_tools.sh`:

- zstd, CaDiCaL, drat-trim and E are byte-reproducible builds from their pinned
  commits, made with `toolchain/build_reproducible.sh`;
- Lean comes from its pinned release tarball.

Pins change only through `toolchain/revise_pins.py`, which keeps a hash-chained
`PINS_HISTORY.jsonl`. Check a host with `genesis platform check`. To reproduce a
checkpoint on another machine, follow `deployment/DEPLOYMENT.md` §5.

From B14 on, the plan follows the reviewer roadmap. Read `docs/BLOCKING_DEFECTS.md`
(open defects) and `docs/REQUIREMENTS_LEDGER.md` (dispositions) before
starting; regenerate the ledger with `python3 scripts/build_ledger.py` whenever a
row changes.
