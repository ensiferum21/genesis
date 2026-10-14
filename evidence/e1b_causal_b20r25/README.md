# E1b causal re-pilot and full causal rehearsal (B20_R25)

**Script.** `scripts/b20r25_e1b_causal.py`. Its rules are in the docstring. It was committed as `14acc23` before the first run. One deviation from the usual anchor: the commit and SHA-256 (`010f23eb…59a8`) reached the user about 30 seconds after the first run started, when 3 of the 30 pilot hosts had been logged.

**Why this step.** B20_R23's causal pilot ran on builder-chosen settings, but B20_R24 fixed E1b's family as study `e1b` (rule `e1-hard-v2`). No causal level had been rehearsed end to end on a real study. B20_R15 had tested the contracts on fixtures only.

## How the run went (three attempts, one result)

1. **First run.** Part A finished: 30 hosts, both contrasts READY_FOR_REVIEW. Part B then stopped at the custodian's SELECT step. The custodian's exposure screen refuses a JSON source with more than 1,000,000 values. The script had written every named host into one file without deduplicating: 2,741 entries for 1,574 distinct hosts.
   - **Fix** (`1132f16`, SHA-256 `5073569c…106c`, sent before the re-run): split the same hosts into sources of 400. Rules unchanged.
   - **Correction.** The packages' own deduplicated lists (1,544 hosts, about 587,000 values) were accepted. They were not defective, although the builder first said they were. B20_R25 still splits them as a precaution (`scripts/b20r25_package_exposure.py`).
2. **Second run.** It stopped after SELECT. The builder had added two helper scripts to the source tree while it ran, so the campaign refused to continue ("source changed after campaign initialization"). That is the campaign's frozen-environment guard working as designed.
   - The helper scripts were moved out of the tree until the run finished.
   - The 30 SELECT hosts that attempt drew are kept in `select_hosts_aborted_attempt.json`, so later pools exclude them. No result came from them.
3. **Third run.** The same committed script ran to the end. This is the result below.

**Part A rows were never re-run.** The resumable loop matched them by task id. A side effect needed repair:
- The first run wrote `pilot_hosts.json` inside the tree that the exposure walk scans. Later runs therefore excluded those hosts, drew other graphs under the same index-based task ids, and overwrote `pilot_hosts.json` with them.
- `scripts/b20r25_restore_pilot_hosts.py` regenerated the scored hosts from the first run's exclusion set (1,544 identities, as its log says). It checked each one against its row by task id, stratum and certified optimum: **30 / 30 match** (`restore_pilot_hosts.log`).
- The overwritten list is kept as `pilot_hosts_second_run_unscored.json`.
- The rows and the analysis were never affected.

## Part A: causal re-pilot on the e1b family (DEV)

30 fresh hosts, 10 per `e1b` setting, all certified. Every arm ran in runc under the E1b profile. The plan family for each follow-up is `ablation:` / `placebo:triangle_free_host_v1`.

| | Candidate − ablation (`random_greedy`) | Candidate − placebo (`lp_shuffled_greedy`) |
|---|---|---|
| Mean per host | **+1.80** (planted +1.9, n26 p0.35 +1.5, n30 p0.3 +2.0) | **+3.70** (planted +3.4, n26 p0.35 +3.0, n30 p0.3 +4.7) |
| Wins / ties / losses | 27 / 3 / 0 | 28 / 2 / 0 |
| CPU ratio | 1.02 | 1.00 |
| Dry run | SUPPORTED, 1.80 [1.47, 2.17] | SUPPORTED, 3.70 [3.17, 4.27] |
| Centred power | 10 per stratum, 30 in total (0.996) | 12 per stratum, 36 in total (0.865) |
| **Verdict** | **READY_FOR_REVIEW** | **READY_FOR_REVIEW** |

Hosts at the certified optimum: candidate 25, ablation 3, placebo 2. As on the B20_R23 settings, the placebo scores below the ablation (−1.9 per host).

## Part B: same-operator rehearsal of the whole causal path (fixture keys; licenses nothing)

All steps ran in one frozen DEV campaign with the E1b candidate frozen. The custodian's SELECT on 30 private hosts gave exchange 2628, low_cycle 2663 and multistart 2676, so the comparator is `multistart_tm`. The selection was recorded.

| Evaluation | Panel | W / L / T | Estimate [90%] | Cost ratio | Outcome | Judge |
|---|---|---|---|---|---|---|
| Main sealed evaluation (B20_R24 DRAFT, frozen rehearsal copy) | 30 CONFIRM, 30 certified | 30 / 0 / 0 | 3.03 [2.67, 3.43] | 1.023 | **SUPPORTED** | agrees (60 witnesses) |
| Ablation follow-up (`cli.followup_request`; the custodian re-checked the intervention) | 30, all certified | 28 / 0 / 2 | 1.97 [1.70, 2.23] | 1.019 | **SUPPORTED** | agrees (60) |
| Placebo follow-up | 36, all certified | 35 / 0 / 1 | 3.19 [2.78, 3.64] | 1.002 | **SUPPORTED** | agrees (72) |

Every arm ran in OCI runc, with 0 execution failures and complete raw evidence.

**The evidence kernel** ran over the campaign store with a FIXTURE role registry, pinning the rehearsal's prereg and custodian keys. It recorded every anchor and receipt and bound one claim to all three requests (claim binding v2, three baselines). Then:

| Promotion | Result |
|---|---|
| utility → CONFIRMED_SAME_DOMAIN | PROMOTED |
| causality → ABLATION_SUPPORTED | PROMOTED (the kernel replayed the intervention from the stored arms) |
| causality → PLACEBO_CONTROLLED | PROMOTED (ablation and placebo of the same component) |

Final levels: utility CONFIRMED_SAME_DOMAIN, causality PLACEBO_CONTROLLED, replication NONE, improver NOT_TESTED, novelty UNKNOWN, math UNCHECKED.

**These are rehearsal levels only.** A kernel built with a fixture registry stamps its decisions `registry: FIXTURE`. Release export, preflight and bundle verification build their own kernel from the externally pinned trust root, so fixture grants never reach an accepted path (`kernel/evidence.py`). The operator, keys and decision records are the builder's.

## What this shows

- The causal ladder runs end to end on a real study:
  - registered intervention;
  - follow-up request;
  - the custodian's re-check;
  - sandboxed evaluation;
  - the judge's recomputation;
  - kernel promotion with intervention replay.
- For E1b, the LP guidance carries most of the effect on this family, on DEV: removing it costs 1.8–2.0 edges per host, and scrambling it costs 3.2–3.7.

What it still needs is the same as GV3: a reviewer, a statistician and an independent custodian. Replication (INTERNAL_INDEPENDENT, EXTERNAL_REPRODUCTION) also needs a second operator.

## Files

| File | What |
|---|---|
| `rows.jsonl`, `pilot_hosts.json`, `pilot_rows_<contrast>.json`, `power_analysis_centred_<contrast>.json` | Part A |
| `request_<kind>.json`, `receipt_<kind>.json` | The three v4 requests and signed receipts |
| `decision_record_DRAFT_<contrast>.json` | The follow-up DRAFTs |
| `rehearsal.json` | Payloads, anchors, judge, fairness, SELECT and CONFIRM hosts, the kernel binding, nodes and promotions |
| `campaign_export.zip` | The rehearsal campaign's export |
| `select_hosts_aborted_attempt.json`, `pilot_hosts_second_run_unscored.json`, `restore_pilot_hosts.log` | The incidents above |
| `summary.json`, `console.log` (third run), `console_first_run.log`, `console_second_run.log`, `run.log` | Results and logs |

Keys and the custodian store were deleted after the run.
