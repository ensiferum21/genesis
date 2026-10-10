# Audit remediation and remaining acceptance requirements

Based on the saved audit `GENESIS_INDEPENDENT_INTEGRITY_AUDIT_20261009T190417Z.md`.
These are developer repairs, not withdrawal of an independent audit veto.

| Finding | Implemented work | Remaining |
|---|---|---|
| GI4-01 forged size/cost | Normalize witness, recompute size, reject negative/Boolean/fractional counts, retain edges. New DSL owns score/query computation. | Legacy query counts remain self-reported and non-promotable; new runtime needs independent audit. |
| GI4-02 false proof via reused ID | Preserve REV18 statement/proof/theory-snapshot checks and regressions in successor. | Historical accepted archive unchanged; acceptance requires external release. |
| GI4-03 semantic replay | Immutable custodian feature contract; identity excludes answer and approved irrelevant fields. Graph route reserves exact isomorphism identities across runs/domains. | Broader Lean semantic screening and external adjudication pending. |
| GI4-04 unsafe pickle | Preserve REV18 disabled unsafe cache loading. | Old accepted archive remains unsafe with untrusted caches. |
| GI4-05 custody/release | Separate operator CLI, signed requests/receipts, role pins, private records; no local release. | Independent accounts/hosts, identities and release operator missing. |
| GI4-06 missing old jobs | Preserve history; exclude historical incomplete/contaminated comparisons from new claims. | Eleven historical raw jobs cannot be reconstructed. |
| GI4-07 chronology | Persist request before evaluation; signed registration time; check signed ordering. | Operator timestamp is not independent public timestamp evidence. |
| GI4-08 raw evidence | Persist integer task predictions, failures, timing, costs; reconstruct aggregates. Graph route retains full witnesses, requests, exact checks and receipts. | Independent production replay remains required. |
| GI4-09 promotion prerequisites | Maintain blocked promotion and distinguish DEV generations from scientific generations. | Lean, external custody, prospective benefit and replication unestablished. |

Additional repairs: globally distinct research-world IDs; explicit version ancestry;
full graph witnesses; derived SQLite state checked against event history; consumed
failed evaluations never retried automatically; dependency versions pinned;
SIGKILL reported as RESOURCE_KILLED rather than presumed CPU exhaustion.

The fixed graph interpreter accepts data, not candidate Python/imports/commands.
It is not an OS isolation boundary. The coordinator account and dependencies are
trusted. A signature authenticates a configured key holder, not its independence.
The new development code has not received an independent acceptance audit.

## 10 October 2026 audit (GI6) — completion branch repairs

These are developer repairs on branch `completion-p0-p2`. They do not withdraw
the audit veto; an independent re-audit is still required.

| Finding | Implemented work | Test reproducing the attack | Remaining |
|---|---|---|---|
| GI6-10 custodian trusted the builder's exposure list | `exposure.py`: the custodian rebuilds an isomorphism registry from its own manifest of public sources (campaign stores/exports, JSON corpora, re-executed legacy generators, ladder hosts). Requests (schema v2) bind the campaign export's SHA-256; a declaration omitting any exported host is rejected. Screening is VF2 isomorphism after removing isolated vertices (works for all n ≤ 63), plus one-edge near-duplicates that block until a signed adjudication exists. Reservations are isomorphism-based. | `test_custodian_registry.py` (empty declaration with a reused relabelled legacy host; omitted export host; near duplicate; relabelled reuse; in-panel duplicates; missing source fails closed) | The operator must own the manifest and supply every public source; completeness of that list is an operator responsibility the code cannot verify. |
| GI6-11 caller-controlled pins produced READY | `release_preflight` no longer accepts pins. Roles come from `<trust_root>/roles.json`, signed by `<trust_root>/root.pub`. Preflight blocks when the research process is root, owns or can write any trust file, or the root key doubles as a role key. | `test_role_registry.py` (self-minted trust root blocked; READY only in a child dropped to UID 65534 with a root-owned read-only trust root; wrong root, shared keys and research-owned files blocked) | Real external control needs a separate operator account/host holding the root key. |

Finding while building the registry: in the 10 October DEV run
`dev_three_generations_v2`, seven panel tasks are isomorphic to earlier public
legacy hosts (the audit reported two of them, future-20261014-0000/0003; the
others are dev-20261010-0000, future-20361014-0001, future-20361016-0006,
future-20461016-0003, select-20461011-0000). Those panels were never sealed;
this confirms GI6-W03 and extends it.
