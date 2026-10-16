# B20_R45 evidence: a same-operator rehearsal of the E1d ablation evaluation through the v5 path (DEV)

Builder-run, with fixture keys. Nothing here is independently reviewed, and nothing licenses a claim. The
registered transform awaits review (B20R44-OPEN-1).
- **Script:** `scripts/b20r45_e1d_ablation_rehearsal.py`. It was committed before the run in `5981c21`,
  and its SHA-256 (`1a3315a0…0b06`) was sent to the user beforehand.
- **Log:** `run.log`. 1,038 s, on one pinned core.

## What was done (fixed before running)

1. **A campaign.** A fresh frozen DEV campaign with E1's frozen candidate. Its E1d sealed_evaluation
   request was frozen as v5, but not registered.
2. **The ablation claim.**
   - A DRAFT decision record in the custodian's ablation family (`ablation:triangle_free_host_v1`),
     with a REHEARSAL copy.
   - **Its power analysis.** It is B20_R44's centred model, recomputed from B20_R44's rows for this
     plan, and saved as `power_analysis_centred_ablation_plan.json`. It chose 15 per stratum, 45 in
     all, with power 0.84. A design test caught the need for this before the run: a power analysis
     is bound to its plan core, and the family is part of the core.
3. **The request and pool.** `cli.followup_request(campaign, 'ablation', …)` produced a v5 ablation
   request whose baseline is the registered ablation (`cross_2` → `ordered_2`). The CONFIRM pool has
   45 hosts drawn from the B20_R43 calibration record, excluding 2,671 named identities.
4. **The custody path.** Register: the custodian re-checked the intervention's provenance. Then
   evaluate, verify, the registration-log check, and `judge.recompute`.

## Result (`rehearsal_summary.json`, `rehearsal_receipt.json`, `decision_record_ablation_DRAFT.json`)

| Step | Result |
|---|---|
| Registration | accepted: the baseline is the registered ablation of the frozen candidate |
| Reference | 44 of 45 certified by the LP over generated rows, median 16.6 s; 1 unsupported (2.2%) |
| Rows | 88 of 88 expected, with no execution failures |
| Wins / losses / ties | **44 / 0 / 0** |
| Estimate | **+6.64 per host** [6.03, 7.29], p = 5 × 10⁻⁵ |
| By stratum | +6.40 (n38, 0.8, 0.07), +6.73 (n40, 0.7, 0.06), +6.79 (n40, 0.8, 0.06) |
| Cost ratio | 1.00 |
| Outcome | **SUPPORTED** |
| `judge.recompute` | **agrees**: 88 witnesses re-checked, fairness clean |

## What it means

**The causal control for E1d has now gone through the whole custody path.** That path is a
custodian-registered ablation request, re-checked for provenance, evaluated on a sealed pool, and
recomputed by the judge. Its outcome agrees with B20_R44's re-pilot: +6.64 here, against +7.07 there.
The opt-in v5 path has now carried both evidence kinds that E1d needs: the sealed evaluation
(B20_R43) and the ablation (here).

## Limits

- One operator played every role, with fixture keys.
- The transform is builder-registered (B20R44-OPEN-1).
- ABLATION_SUPPORTED needs an independent custodian's signed evaluation, and the kernel's promotion
  of it.
- **Exposure.** The 45 hosts are in `handoff/e1*/exposure_hosts_addendum_b20r45.json`.
