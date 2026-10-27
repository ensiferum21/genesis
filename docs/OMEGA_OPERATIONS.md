# Genesis Ω: operations (master implementation contract §18)

**Bootstrap** (a fresh container):

```
git clone <the repository> genesis && cd genesis && git checkout continuation-b20-rx
GENESIS_TOOLCHAIN=/srv/toolchain bash toolchain/install_tools.sh          # pinned tools (HANDOVER §2)
export GENESIS_TOOLCHAIN=/srv/toolchain PYTHONPATH=src
python3 -m unittest tests_genesis.test_no_llm tests_genesis.test_omega_boundary tests_genesis.test_vault \
    tests_genesis.test_science_design tests_genesis.test_compiler tests_genesis.test_interpret \
    tests_genesis.test_primitive_library tests_genesis.test_process_levels
python3 scripts/run_test_matrix.py --profile release --report /tmp/matrix.json     # the full matrix (~45 min)
```

The max-cut engines and the MaxSAT entrants are built from pinned sources (`scripts/b20r125_build_mcx2.py`,
`scripts/b20r153_build_mcx3.py`,
`b20r91_mse2026_tools.py`; HANDOVER §6.1).

**Run a study** (alone on one core, resumable):

```
taskset -c 0 python3 scripts/b20r<n>_<name>.py evidence/<name>_b20r<n>
```

- **Pause:** studies that run in slices exit 3 at the slice limit.
- **Resume:** run the same command again.
- **While a study runs, never edit `.py` files in its tree.** Commit new code through the index, or run the study
  from a clean worktree (`git worktree add --detach <dir> <commit>`).

**Discoveries:**

```
genesis discovery list ROOT [--type ProgramSpec] [--status dormant] [--failure context_limited]
genesis discovery show ROOT ID [--raw] [--lineage] [--evidence]
genesis discovery replay ROOT ID
genesis discovery export ROOT ID [--format json|source]
genesis discovery verify ROOT
```

ROOT is a vault directory, for example `evidence/cascade_b20r131/vault`. Copy it first, because opening a vault
takes its writer lock.

**Checkpoint, restore, verify:** `scripts/make_checkpoint.py` (HANDOVER §3.4); `genesis store backup|restore|verify`;
restore-verify and the driver rehearsal as in HANDOVER.

**Export a report:** each study's `summary.json` and evidence README; the ledgers `docs/OMEGA_RESULTS_LEDGER.md` and
`BATCHES.md`.
