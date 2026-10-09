# Reference custodian — development only

This package demonstrates **data-only candidate evaluation** and authenticated aggregate evidence. It is not an independently operated custodian, a Lean checker, a production sandbox, or proof that mathematical discovery occurred.

A separately controlled operator must deploy the evaluator and hold the private Ed25519 key and sealed pool. Research agents receive only the frozen candidate grammar and aggregate receipts. Do not share private pool/key directories, task-level outcomes, or evaluator process memory with research. A Linux UID access test is necessary but not sufficient: same-host root, container escapes, side channels, adaptive queries, and operator conflicts require an independent threat-model audit.

All four arms D/U/V2n/V2p must be frozen by a preregistration containing their exact file SHA-256 hashes, the private pool SHA-256 hash, a campaign ID and a fixed per-arm budget before evaluation. The prototype charges one evaluation per sealed task per arm. It does **not** implement theorem proving, Lean replay, adaptive research loops, matched resource accounting for heterogeneous solver strategies, or statistical promotion.

Signed evidence includes the exact prereg, pool, candidate-map, evaluator, aggregate and manifest hashes. Verifiers must pin the public key out of band and check all expected hashes. A valid signature alone does not establish isolation or independence. No current Genesis promotion gate is satisfied by this reference package.
