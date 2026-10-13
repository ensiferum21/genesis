# B20_R7 record: H05, sealed statement panels and frozen research successors (B20R5-OPEN-1)

- **Parent:** B20_R6 (commit `9424e75`). This batch is commit `b5388af`.
- **Run by:** the builder, with fixture keys. Not independently reviewed.

## Problem

Handoff s13.3: E2 and E3 need evaluation statements generated on the custodian side after freeze, with a defensible exposure history and preregistered inclusion rules. They also need a candidate kind for a frozen formal-research successor.

Before this batch:

- Equational research had no custodian path.
- The E3 studies were DEV only.

## Implementation

### `learning/statement_panels.py`

- **Spec.** A preregistered spec (`genesis-statement-panel-spec-v1`) fixes the system, node ranges (one stratum per range), statements per range, maximum term size, and an inclusion rule chosen from a closed set:
  - `valid-screened`;
  - `valid-screened-nontrivial`, which drops statements E proves from the axioms alone within a preregistered limit. This is an evaluator-side step; no arm's result is consulted.
- **Generation.** The custodian draws statements from a fresh private seed.
- **Screening.** The partition builder rejects anything related to what the research saw (EXACT, ALPHA or INSTANCE) and quarantines GENERALIZES. The same screen covers:
  - the custodian's public statement sources;
  - every statement already sealed at this custodian (new exposure route `sealed`; the research insertion screen refuses that route).
- **Reference obligation.** Every statement is decided true in its variety (two-element algebra or free group).
- **Record.** The generation record keeps every count and a residual pretraining-exposure note.
- **Insufficient material.** If a stratum cannot be filled, the result is `INSUFFICIENT_DISTINCT_MATERIAL` and nothing is registered.

### `learning/research_export.py`

Equational research is frozen as a hash-chained campaign export holding:

- the successor manifests and their proof objects;
- every research-visible statement;
- write-once frozen candidate and baseline descriptors, fixed before any panel exists.

### `candidates.py`: kind `formal-research-successor-v1`

- **What the child sees.** Only the statement and the library statements; no task id, stratum or panel.
- **Where E runs.** Inside the OCI sandbox, with the pinned prover and the pin file mounted read-only (the binary hash is re-checked inside).
- **Output.** A proof *claim* under a strict decoder. A claim is worth nothing until the evaluator replays it.
- **Isolation.** runc only.

### `kernel/receipts.py`

- New request form `genesis-statement-evaluation-request-v1`. It has a new name, so no request version number is reused with a different meaning.
- Statement domains `eq_<system>_v1`, whose contracts bind the exact axioms.
- `descriptor_arms()` replaces the R5 v4-only predicate.
- These evaluations use receipt v4.
- Graph routes refuse statement domains, and the statement route refuses graph domains.

### `custodian.py`

- **`register_statements`:**
  1. Rebuilds both arms and their custody (proof objects, uids, lemma truth, premise order) from the export.
  2. Generates the panel.
  3. Stores the panel, its record, the private seed and the export copy in the private root.
  4. Signs an anchor carrying a salted commitment.
  5. Writes the sealed statements where `screen_for_research` blocks them.
- **`evaluate_statements`:**
  - Reserves the panel's statements, which are never reused.
  - Refuses before reservation if the sandbox is missing.
  - Runs both arms in shuffled order.
  - Replays every claimed proof in Lean from custody as separately accounted verification.
- **`recover`:** handles statement evaluations.

### `judge.py`

- A statement scores 1 for an arm only when its replay is CHECKED. Finding no proof is a valid 0, not an execution failure.
- Every claim is re-bound and replayed again from the raw evaluation store alone.

## Evidence

`tests_genesis/test_statement_custody.py` (12 tests) covers:

- **Generator:** spec checks; determinism; exposure screening, including across axiomatizations of the same variety and signature; insufficient material refused; tampered panel detected.
- **Runner:** the formal kind refuses process isolation, a manifest mismatch and a domain mismatch. A real sandboxed run sees only the statement and the library. The output decoder is strict.
- **Refusals:**
  - graph routes refuse statement requests, and vice versa;
  - swapped arms → `NOT_THE_FROZEN_CANDIDATE`;
  - altered proof objects, a missing manifest, a false lemma, a rewritten descriptor and a wrong export hash are each refused;
  - insufficient material registers nothing;
  - with no sandbox, nothing is reserved;
  - a tampered stored panel is refused against its commitment.
- **End to end** (nontrivial inclusion):
  - research-visible statements never enter the panel;
  - the sealed statements are blocked for research;
  - receipt v4 is produced, and the registration log agrees;
  - the judge recomputes the result and replays every claim;
  - no second draw is allowed;
  - a second registration's panel is disjoint from the first.
- **Crash recovery:** a crash after rows gives no retry; `recover` yields an INVALID v4 receipt.

A manual fixture run outside the suite measured the following:

- Register: 13 s, with 25 trivial statements excluded.
- Evaluate: 93 s, 6 proof claims, all CHECKED.
- Judge: 78 s, 6 fresh replays.

## Limitations

- The fixture successor is a tiny fixed-policy run against the empty library. It shows the protocol, not efficacy.
- Verification CPU is not metered: replay reports wall time only (`cpu_unknown`).
- Public statement sources come from the operator's manifest. No literature search is performed.
- The insertion screen of research runs connects to the custodian's sealed statements only through `screen_for_research`. The equational research loop does not yet call it automatically.

## Consequence

H05 is done on DEV. The custodian can run real frozen candidates of three kinds: the DSL, represent-and-repair, and formal research successors. It can also generate sealed equational panels.

A sealed E3 study is now possible to run, but it would be premature: there is no family with headroom (B20R3-OPEN-1), and handoff s14.4 says not to launch such a study.
