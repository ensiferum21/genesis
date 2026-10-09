# Genesis Batch 30 — Prospective Attempt Accounting (DEV)
2026-10-09

Implemented `prospective_accounting.py` as a bounded, deterministic event-ledger validator tied to a development registration receipt. Requires both arms on each registered task; contiguous attempt numbering; explicit PASS/FAIL/TIMEOUT/CANCELLED/CHECKER_ERROR/UNSUPPORTED states; cost accounting for failures and cancellations; per-arm budget caps; no retries after success or invalid execution; SHA-256-shaped evidence references; and reproducible event-list digest. Invalid checker outcomes are excluded from wins rather than being counted as solver losses.

**Important:** This checks self-reported ledger structure only. It does not independently obtain events from a checker, authenticate evidence hashes, verify randomized ordering, verify a real Lean binary, or prove that a task roster corresponds to the registered sealed commitment. It cannot authorize a scientific claim. Any genuine prospective experiment must bind raw independently verified receipts and frozen sealed task IDs to the registered task roster.

The earlier real Lean blocker remains: no `lean`, `lake`, or `elan` executable found; the official GitHub release host cannot be resolved from this runtime. An externally provisioned trusted Lean environment is required.

Tests: `python -m unittest discover -q` (136 tests passing, 13 new). Scientific promotion: BLOCKED.
