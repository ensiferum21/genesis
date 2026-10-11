# B17 review brief: formal research workspace and the first theory package

The B17 exit is "real generated reusable Lean artifacts replay". This brief names what
to check and how to reproduce it. The builder wrote it, so it is a map, not evidence.

## Reproduce

```
unzip GENESIS_COMPLETION_CHECKPOINT_B17.zip -d b17 && cd b17/genesis
export GENESIS_TOOLCHAIN=/srv/toolchain PYTHONPATH=src PYTHONPYCACHEPREFIX=$(mktemp -d)
bash toolchain/install_tools.sh          # pinned tools, Lean 4.34.1 and the Mathlib workspace
python3 toolchain/build_formal_workspace.py check $GENESIS_TOOLCHAIN/formal-workspace
python3 -m unittest tests_formal.test_formal_research          # needs root for the sandbox
```

The workspace build fetches Mathlib and its eight Lake dependencies at the commits in
`toolchain/FORMAL_WORKSPACE.json`, from GitHub. It then builds the 699-module import
closure of `Mathlib.Data.Finset.Powerset` offline, with Lake's cache disabled. On a
2-core host this takes about 12 minutes. Compare your `artifact_identity` with the
one in `evidence/formal_research_b17/summary.json`. Two builds on the builder's host
gave identical bytes, but a second machine has not been tried.

To replay the package from its sources alone:

```
python3 -c "import json,sys; from genesis.formal_research import theory_package as TP; \
  r = TP.replay(json.load(open('evidence/formal_research_b17/package/package.json'))); \
  print(r['verdict'], r['differences'])"
```

## What to check

| Question | Where to look |
|---|---|
| Can a proof module weaken its statement, add an axiom, use `sorryAx`, shadow a trusted name, import `Lean` metaprogramming or set unsafe options, and still be accepted? | `formal_research/checker.py` (`prescreen`, `accept`); `test_formal_research.Acceptance` |
| Does acceptance ever reuse what a search compiled? | `checker.accept` compiles from source; `theory_package.run` keeps the acceptance cache separate from `Session` |
| Is every imported Mathlib artifact the pinned one? | `workspace.audit` (re-hash, no extra files or symlinks; pins and Lean binary); `WorkspaceAudit` tests |
| Are the generated lemmas reused, and is that visible? | `package.json` → `dependencies` (bound_union uses down_closed); `task_certificates[].uses_package_lemmas` |
| Are the outcome classes honest? | `statements`: CHECKED, DISPROVED (with a Lean-checked counterexample), UNRESOLVED, UNSUPPORTED |
| What did search contribute, and what did the recipes contribute? | each proof's `recipe`; `costs.attempts` (every candidate, failed ones too) |
| Does the executable method use only checked material? | `theory_package.compile_method` (fails closed); `method_evaluation` (DEV, compared with the certified optima) |

## Known limits

- **The recipes are builder-written.** The search picks among them and fills in the
  binder names and library lemmas, but it does not invent proof strategies.
- **The mathematics is elementary rediscovery.** The gadget-packing bound is a known
  idea. On DEV tasks it is sound but not tight. No usefulness claim is made.
- **The Lean statement domain is not registered for sealed receipts.**
- **Exposure identity is by normalised text.** It is not semantic equivalence.
- **No independent replay yet.** Only the builder has replayed the package.
