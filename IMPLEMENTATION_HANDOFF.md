# Genesis integrated development checkpoint — 10 October 2026

## Delivery status

The bounded graph research implementation is built. The complete Genesis grand
vision is **not** implemented or scientifically established. This delivery adds
a coherent runnable system to the restored REV18 and Batch 42 branches, repairs
specific audit findings, and preserves both failed and successful development
evidence. It does not replace an accepted checkpoint or lift an independent audit
veto. The full requirements map is `docs/REQUIREMENTS_AND_GAPS.md`.

The authoritative final campaign is `runs/dev_three_generations_v2`. Its final
verification results are in `evidence/VALIDATION_SUMMARY.json`. The older run with
`wal_reopen_failed` in its name is retained as failure evidence, not as the verified
checkpoint. See `evidence/DEVELOPMENT_FAILURES.md`.

## What changed

The new `src/genesis` package integrates strict configuration, a fixed graph solver
language, bounded subprocess execution, immutable content-addressed artifacts,
event-backed state, explicit version ancestry, reproducible public tasks, and a
single command line. Witness edge counts and validity are recomputed by the
checker; candidate data cannot set its own score or query counter. Limits cover
queries, wall time, CPU, address space and output size. This is a data-only
executor, not a sandbox for arbitrary candidate Python.

Two domains are supported: C4-free host subgraphs and triangle-free host subgraphs.
Independent algorithm structures compute small-instance exact optima; distinct
predicates check witnesses. Exact graph canonicalization rejects reused
isomorphic hosts across task IDs and domains within the recorded exposure set.
Search limits yield an unresolved outcome rather than invented certification.
The exact reference solver has separately recorded checking cost; it is not a
resource-matched heuristic competitor.

All sixteen Research IR operations have concrete handlers and execution tests in
declared narrow graph/data scopes. Exact MRDL expressions include graph features,
induced graphs, complements, partitions, orbits, bounded trace powers and PB
encodings. World births, hybrids, actions, depth and lifetime have explicit caps.
The runtime records Pareto observations, diagnoses failures, compiles reusable
solver/trace capabilities and records rollback ancestry. Broad names such as
SYNTHESIZE and REFLECT do not imply unrestricted invention or general reasoning.

Research compares uniform and adaptive proposal policies under equal outer trial
budgets. DEV outcomes update bounded mutation preferences; SELECT chooses a
candidate and a strong baseline. A full successor version freezes before newly
generated public future tasks. Actual ablation and placebo executions, transfer to
the second graph domain, and successive DEV generations are recorded. Future
outcomes do not select the current candidate or train its mutation preferences.

Audit repairs cover forged witness sizes, invalid reported costs, semantic replay
under irrelevant features, missing private per-task records and unsafe legacy
cache loading. REV18's reused-proof-ID and theory-snapshot protections remain.
Legacy cost claims are explicitly non-promotable. The mapping to all nine critical
findings is `docs/AUDIT_REMEDIATION.md`; historical missing jobs remain missing.

A separate operator interface persists registration before evaluation, reserves
private task identities before execution, records private inputs/witnesses/costs,
and signs aggregate receipts. Release preflight checks distinct externally pinned
roles and chronology. It always leaves actual promotion to an external authority.
Local fixture signatures prove protocol behavior, not operator independence.

## Verification and measured meaning

| Suite | Executed | Passed | Skipped | Result |
|---|---:|---:|---:|---|
| Restored REV18 regression suite | 282 | 280 | 2 | Pass with environment limitations |
| Restored Batch 42 regression suite | 262 | 262 | 0 | Pass |
| New integration and audit suite | 74 | 72 | 2 | Pass with environment limitations |

These are **618 test executions, 614 passing and four skipped**, not a claim of
618 unique independent tests: the integration suite also inherits some custody
tests. The separate-UID test skips because this host cannot switch to the research
UID. Skips do not establish isolation. Logs are included, including earlier failures.

Graph checking includes all 1,099 labeled simple hosts on one through five
vertices in both domains, complete hosts through six vertices, additional random
larger hosts, exact encoding/predicate comparisons, relabeling, score fraud,
corrupted evidence, resource exhaustion, and real subprocess execution. Storage
tests include large-state snapshot/reopen and committed-state recovery after an
abrupt process exit.

The three-generation experiment uses seed 20261010, eight tasks per panel, four
proposals per policy, 32 research trials per policy per generation, and a 60-query,
one-CPU-second limit per solver invocation. Public task generation is bounded to
small hosts with at most 18 edges. The final measured comparison is recorded in
the campaign's `reports/report.md` and machine-readable `reports/results.json`.
No public development outcome counts as a sealed scientific confirmation.

| Generation | Candidate wins / losses / ties vs baseline | Adaptive wins / losses / ties vs uniform | Transfer wins / losses / ties |
|---|---|---|---|
| 0 | 2 / 0 / 6 | 0 / 0 / 8 | 0 / 0 / 8 |
| 1 | 0 / 0 / 8 | 0 / 0 / 8 | 1 / 0 / 7 |
| 2 | 0 / 0 / 8 | 0 / 0 / 8 | 1 / 2 / 5 |

All 600 original attempts succeeded: 504 solver invocations and 96 exact-check
attempts. Ten additional replay invocations succeeded and matched. The final live
database and four snapshots passed SQLite integrity checks; all 2,770 entries in
the public campaign export passed hash and archive checks. These are internal
engineering checks. The adaptive policy had no measured advantage over uniform
on these future panels, and the controls did not support a causal improvement
claim. Scientific generations confirmed: **zero**.

The first completed run exposed live-database corruption on reopen even though
its snapshots were readable. The precise cause is unresolved. The single-writer
store now uses rollback journaling, avoids WAL/SHM sidecars for durable state,
checks structural integrity on reopen and validates snapshots. The final fresh
campaign passed its own reopen and replay checks. This mitigation is not a
claim that every storage-host failure has been ruled out.

Timings include shared-host noise, and some earlier tests ran concurrently with
the first campaign. This delivery makes no speedup claim. Deterministic replay
compares witnesses, edge values, query counts and traces, excluding time.

## Run and inspect

Use Python 3.12 and install `requirements.lock` in an isolated virtual environment.
The lock records observed package versions; it is not a wheel-hash lock or a
pinned container image. The source/environment identity is recorded alongside
each campaign, and changing either requires a new campaign.

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.lock
export PYTHONPATH=src
python -m genesis doctor
python -m genesis smoke runs/my_smoke
python -m genesis init runs/my_campaign --config configs/offline.json
python -m genesis campaign run runs/my_campaign
python -m genesis trial replay runs/my_campaign --limit 10
python -m genesis evidence show runs/my_campaign
python -m genesis freeze candidate runs/my_campaign --tasks 300
python -m genesis export replication-bundle runs/my_campaign my_campaign.zip
```

Use a new empty directory for each run. Interrupted campaigns preserve attempts
and require a new identity; they do not automatically retry consumed evaluations.
Replay adds separately recorded attempts. The campaign report's original 600
attempt count therefore differs from the post-replay ledger count.

The frozen request at
`runs/dev_three_generations_v2/exports/evaluation_request.json` is a reviewable
input to independent evaluation. A 300-task request is a default, not an adequate
power calculation or evidence that any private panel exists.

## How far from the grand vision

| Milestone | Current status | Remaining evidence/work |
|---|---|---|
| Independently trusted checker | Local differential/exhaustive checks and repaired boundaries | Independent audit, accepted OS separation and externally pinned checker deployment |
| Formal correctness | Existing Lean adapters; finite Lean source exporter | Actual pinned Lean execution, canaries, semantics/axiom review and theorem replay |
| Clean prospective experiment | Request freeze, private reservation and receipt mechanisms | Independent operators, unseen panel, external chronology and complete private replay |
| Useful discovery | Public finite graph diagnostics | Prospective benefit over strong matched baselines, novelty assessment and replication |
| Better improver | Real uniform/adaptive policy experiment | Repeated sealed evidence that the successor research policy improves outcomes |
| Compounding generations and transfer | Three executable DEV generations and a second graph domain | Independently confirmed gains across generations, transfer retention and causal evidence |

None of those scientific milestones is marked accepted solely by this delivery.
The dependency order matters more than an invented percentage-complete estimate.

There are also substantial implementation gaps, not just missing credentials:
general ontology invention, foundation lifting, the TPTP G9 study, broad
literature-to-checked-claim compilation, neural training and mechanism extraction,
general proof-carrying compression, SAT/interval certificate integrations,
transitive evidence revocation, arbitrary-code containment, physical instruments
and general cognitive primitive invention. See the section-by-section map before
treating any macro name as implemented.

## External continuation

First reproduce this package under an independently controlled environment and
review the storage incident and critical audit fixes. Install and pin the Lean
toolchain; the generated `formal/generated_k4/Main.lean` is explicitly
`SOURCE_GENERATED_NOT_CHECKED`, not a proof result. This host had neither Lean nor
Docker and did not provide a verified separate-UID boundary.

An independent operator must provision its own owner-only private directory,
private pool and Ed25519 keys outside the research worker. The operator uses
`scripts/genesis_custodian.py register` and `evaluate` with distinct preregistration
and custodian signing roles. A separate auditor and release authority must supply
externally pinned identities, raw-evidence replay and acceptance. The operator's
signed timestamp alone is not independent public time anchoring. No production
keys or sealed tasks are included in this package.

Only after those prerequisites should a preregistered, sufficiently powered
prospective campaign assess benefit and allow external scientific release.
Engineering completion, private evaluation, mathematical proof and research
usefulness remain separate statuses throughout.
