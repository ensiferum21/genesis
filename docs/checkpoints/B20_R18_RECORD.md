# B20_R18 record: DEV comparison rows bound to their executions (B20R8-OPEN-1)

Builder-run engineering batch, commit `35c2807`. Nothing here is independently reviewed.

## What changed

Before this batch the `dev_comparison` contract replayed only the analysis: its rows were producer data. A row could state any value.

`genesis-dev-comparison-v2` adds `arms` (the two solver identities) and binds every row to two executions in the store's attempt journal, one per arm. For each, the kernel re-reads the attempt and checks:
- the attempt exists and finished;
- its request is a solver request for the row's task, the task is DEV, and the solver is the arm's (the DSL program digest, or the descriptor id);
- the run status and the CPU equal the terminal receipt's;
- a successful run's witness re-checks (`graphs.check_witness`) to the row's value. A failed run scores zero.

Two more rules hold across rows: no attempt is used twice, and both arms of a row ran the same task. The recorded result must still equal the kernel's own analysis, and that analysis must decide SUPPORTED.

`genesis-dev-comparison-v1` is retired: it licenses nothing, and the refusal says why. Nothing in the repository's evidence used it.

`replay_contracts.dev_comparison(store, plan, candidate_rows, baseline_rows)` builds a v2 payload from journalled trial rows (as `campaign.Campaign.trial` writes them). It reads values, runs and CPU back from the receipts, never from the rows.

## Limits

- The journal and its receipts are the producer's store. The contract checks that the rows agree with recorded executions and that the witnesses are valid; it does not re-execute the solver. A DEV level still never satisfies a confirmation.
- Descriptor-arm attempts are recognised by `descriptor_id`. Attempts are journalled in campaign stores; in-process script pilots (B20_R13 and later) do not write attempts, so their rows cannot be promoted to DEV_ONLY. They were never promoted.

## Tests

`tests_genesis/test_replay_contracts.py::DevOnly` (4 tests) uses 24 real journalled executions. It covers:
- a bound comparison that replays and stays DEV;
- a v1 payload refused;
- an inflated value, a reused attempt, swapped arms, another task's attempt, a missing attempt and a changed CPU, each refused;
- a forged result, non-DEV rows, and a same-solver comparison, each refused.
