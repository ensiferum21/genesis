# B20_R22 record: legacy retention and negative transfer under a frozen protocol (H08 s20.6)

Builder-run engineering batch with a DEV demonstration. Nothing here is independently reviewed.

## What changed

`src/genesis/retention.py` lets a campaign freeze one retention protocol (write-once) before any measurement. The protocol holds:
- named panels, usually `legacy` and `transfer`;
- the material, either DEV_PUBLIC or PROTECTED. PROTECTED tasks live only in a private 0700 root, and the campaign store and its exports hold only salted commitments;
- the margin, interval level and resamples;
- a measurement budget.

`measure(store, from, to)` reads both versions' frozen solver programs from the content-addressed `system_version` entities. It runs them on every panel task with seeds the protocol fixes. Each pair is recorded once, within the budget, so the material is never re-used. The verdict per panel is NEGATIVE_TRANSFER, RETAINED or INCONCLUSIVE.

With this, H08 s20.6 is complete in engineering terms: B20_R16 added the pointer, rollback and revocation, and this batch adds retention and negative transfer.

## Demonstration

`evidence/retention_b20r22/` used a real 4-generation DEV campaign. The first retained change (local exchange moves) is NEGATIVE_TRANSFER on triangle-free hosts, −0.625 [−1.00, −0.25]. Later generations changed no solver and retain exactly.

## Tests

`tests_genesis/test_retention.py` (4, real executions):
- a gain is RETAINED and a loss is NEGATIVE_TRANSFER;
- the protocol is frozen once, each pair is measured once, and the budget holds;
- commitments are checked;
- protected material stays out of the store, private permissions are required, and tampering is detected.

## Still open

- Paired research lineages for `sealed_improver_evaluation`, which need a GV4 domain with headroom.
- Protected retention material held by a custodian rather than by the operator's private root.
