# B20_R15 record: replay contracts for the causal, internal-replication and priority levels

Builder-run engineering batch (B14-OPEN-4, the rest). Commit `73493b4` on `r16-versions`, merged in `aced775`. Code recovered from the lost run's edits (session transcript) and completed. Fixture keys only; nothing here is independently reviewed, and no level was reached on real evidence.

## What changed

| Level | Evidence kind | What the kernel now re-derives itself |
|---|---|---|
| causality ABLATION_SUPPORTED | `ablation` (signed by the registry's `custodian_key`, receipt v4 only) | The arms the receipt commits to (`arms_sha256`; stored directly or inside the frozen request it names) rebuild as descriptors, share kind, domain, implementation and resource profile, and differ in exactly one registered component whose value is the registered ablation of the candidate's. |
| causality PLACEBO_CONTROLLED | `ablation` + `placebo` | As above for each, and the ablation and the placebo change the same component. |
| replication INTERNAL_INDEPENDENT | `internal_replication` (signed by the new optional registry role `internal_replicator_key`) | It repeats a supporting `sealed_evaluation` of the same claim: same arms, same analysis plan up to the family id the custodian assigns per kind and the decision record each registration names, same domain, another panel, another operator identity, registered after the original completed. |
| novelty REDISCOVERY / VARIANT / CANDIDATE_NOVEL | `priority_check` (route `equational-literature-v1`, unsigned, replayed) | Stored literature sources are re-hashed and re-screened for injected instructions; each quote must sit at its recorded span; each formalization is related to the claimed theorem (same variety and signature; EXACT, ALPHA or INSTANCE make it a REDISCOVERY, GENERALIZES a VARIANT). CANDIDATE_NOVEL additionally needs a preserved search record: at least one search, at least one search of the pinned library at the workspace's revision, each re-run by the kernel with identical hits, every hit covered by a stored verbatim excerpt. The declared level must equal the recomputed one and the level asked for. |

Registered interventions (`replay_contracts.INTERVENTIONS`), for `dsl-program-v1` and `dsl-time-matched-v1`:
- `program.weights`: ablation sets every weight to 0 (order by seeded jitter only); placebo rotates the weights onto other features.
- `program.exchange`, `program.componentwise`: ablation turns the move off; no placebo.

Other kinds (for example `represent-and-repair-v1`) have no registered intervention, so they cannot reach a causal level yet.

Custodian and research side:
- `register` refuses an `ablation`/`placebo` request unless its baseline is the registered intervention of the campaign's frozen candidate.
- An internal replicator accepts a comparator selection made by another custodian only under a public key its operator names (`register(accepted_selection_keys=...)`), and only for `internal_replication` requests.
- `cli.followup_request` derives ablation, placebo and replication requests from the campaign's frozen descriptor request; one claim binding covers all of them.

## Limits (recorded, not hidden)

- Distinct keys and operator identities are what code can check. Whether two operators are independent is not.
- The preregistration anchor role is shared: a replicator's anchors are signed by the registry's `prereg_key`.
- Priority relations are syntactic. A statement equivalent only modulo the theory's laws is not recognised as prior art, and formalizing a quote is producer work; both errors can only make a result look newer, which is why CANDIDATE_NOVEL stays a candidate. EXTERNALLY_CHECKED_NOVEL still needs the external priority reviewer.
- Library search replay reads the whole pinned Mathlib tree (about 8 s per pattern here).

## Tests

- `tests_genesis/test_b14_open4_contracts.py` (21 tests): interventions; schema and roles; custodian checks; kernel promotion for ABLATION_SUPPORTED, PLACEBO_CONTROLLED, INTERNAL_INDEPENDENT and the three priority levels, each with its failure cases; follow-up requests.
- `tests_genesis/test_candidate_custody.py::CausalAndReplicationCustody` (2 tests, OCI sandbox): an ablation registers and runs end to end only for a registered intervention; the replicator's selection-key rule.
- `tests_genesis/test_evidence_kernel.py`: the declared-verdict test now expects the new fail-closed reasons.
