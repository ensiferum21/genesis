# B20_R21 record: external reproduction repeats a supporting evaluation; replication handoff package (W24)

Builder-run engineering batch. Nothing here is independently reviewed.

## What changed

- **Kernel (stricter).** An `external_reproduction` receipt now licenses EXTERNAL_REPRODUCTION only if it repeats a supporting `sealed_evaluation` of the same claim, by the rule B20_R15 introduced for internal replication. That means the same arms, the same analysis (up to the custodian-assigned family id and the decision record), and the same domain, with another panel, another operator identity, and registration after the original completed. Before this batch, any supporting, correctly signed reproduction receipt bound to the claim counted. The verified original is now also counted as used evidence, so its upstream speculative effects are resolved like any confirming evaluation's.
- **Receipts and custodian.** `external_reproduction` may compare descriptors (v4). Both repetition kinds accept another custodian's comparator selection only under an operator-named key (`accepted_selection_keys`).
- **CLI.** `cli.followup_request` derives external-reproduction requests too.
- **Handoff.** `handoff/replication/README.md` sets out the full protocol for an internal replicator and for an external reproducer. It is BLOCKED until a SUPPORTED sealed evaluation and an independent operator exist.

## Tests

`tests_genesis/test_b14_open4_contracts.py::ExternalReproduction` (2):
- a reproduction of a supporting evaluation licenses the level;
- a reproduction alone, one by the same operator, and one with another plan do not.

The existing external-reproduction red-team tests are unchanged and pass.
