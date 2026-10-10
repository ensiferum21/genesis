# End-to-end walkthrough (spec §40)

Steps 1–10 and 15 ran on public DEV material. Steps 11–13 used FIXTURE roles generated in this run (not independent custody). Step 14 was not performed: it needs an external release authority.

| Step | Action | Key result |
|---:|---|---|
| 1 | initialize campaign and validate config | `{"phase": "VALIDATED_CONFIG", "evidence": "L0 only"}` |
| 2 | load DEV tasks and contracts | `{"tasks": 32}` |
| 3 | run baselines | `{"comparisons": [{"claim": "DEV_ONLY", "confirmation_p_value": null, "exploratory_sign_p": 0.5, "family_deltas": {"bipartite": 0, "erdos_dense": 1}, "family_sen` |
| 4 | diagnose gap | `{"hypotheses": ["SEARCH_POLICY_LIMITED", "REPRESENTATION_LIMITED"], "next_experiment": "more_rounds"}` |
| 5 | spawn bounded worlds | `{"worlds": {"7c8a5613": "RETIRED", "e717bd4c": "RETIRED", "074e6a73": "DORMANT"}}` |
| 6 | builder/barrier execute (barrier_escape macro under grants) | `{"funded": [6, 5, 4]}` |
| 7 | independent check | `{"optimality_checked": 4, "of": 4}` |
| 7 | formal check of one witness (pinned Lean, sandboxed) | `{"lean": "CHECKED", "axioms": []}` |
| 8 | causal comparison (DEV ablation/placebo) | `{"controls": [{"ablation_loss": 0, "candidate_gain": 0, "causal_claim_supported": false, "placebo_delta": 0, "status": "DEV_INTERVENTION_DIAGNOSTIC"}, {"ablatio` |
| 9 | compile useful mechanism | `{"status": "COMPILED", "evidence": "DEV_ONLY"}` |
| 10 | freeze selected successor | `{"phase": "CANDIDATE_FROZEN", "request": "797343892f2e9a07"}` |
| 11 | leak scan / registration (custodian-built exposure registry, salted panel commitment) | `{"exposure_graphs": 148, "roles": "FIXTURE"}` |
| 12 | execute sealed panel (fixture operator, hard CONFIRM hosts, SAT-certified optima) | `{"rows": 12, "wins": 0, "losses": 0, "ties": 3, "outcome": "NOT_SUPPORTED"}` |
| 13 | independent judge (signed receipts verified against the role registry) | `{"phases": [["OK", {"from": "CANDIDATE_FROZEN", "to": "LEAK_SCAN_PASSED"}], ["OK", {"from": "LEAK_SCAN_PASSED", "to": "SEALED_RUNNING"}], ["OK", {"from": "SEALE` |
| 14 | release or reject — NOT PERFORMED (needs an external release authority) | `{"preflight": "BLOCKED", "reasons": ["preregistered superiority not supported (outcome NOT_SUPPORTED)", "custody independence not verified", "private evidence r` |
| 15 | meta-analysis | `{"calibration_error": 0.7443485447586109, "meta_gap_candidates": [[], ["dev-hard-20261013-0002", "dev-hard-20261013-0003"], []]}` |

Elapsed: 138.9 s. Promotion allowed: no.
