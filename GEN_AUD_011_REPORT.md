# Genesis sprint — GEN-AUD-011 unsafe world-cache boundary (DEV)

UTC timestamp: 2026-10-08T14:36:15.691575+00:00

## Finding (CRITICAL in original code)

The induction adapter's `build_world` and `build_world_from_suite` loaded `.pkl` world caches from a caller-provided `cache_dir` with `pickle.load` and wrote entire `InductionWorld` instances with `pickle.dump`. The serialized world contains a `SealedStore` holding private test payloads. A deterministic cache filename is **not** an authenticity or confidentiality boundary. If a research-writable cache is reused, it can execute arbitrary code before a checker is invoked, and stored worlds can disclose sealed data.

## Independent local reproduction

Using a **new synthetic four-statement DEV-only suite** and a harmless pickled payload that writes a marker file, I exercised the *actual original adapter code* from the previous checkpoint and then the patched adapter with the same payload:

- Original: `marker_executed=true`, `load_outcome=RETURNED`.
- Patched: `marker_executed=false`, `load_outcome=RETURNED`.
- No old sealed jobs were run, loaded, or reused.

Evidence: `audit/GEN_AUD_011_before.json`, `audit/GEN_AUD_011_after.json`, and `audit/cache_attack_repro.py` inside the new source checkpoint.

## Implemented DEV mitigation

1. Removed both `pickle.load` paths and both `pickle.dump` paths from the induction adapter.
2. `cache_dir` is accepted for backwards API compatibility but **ignored**; a world is regenerated rather than loaded or written. Deterministic `cache_key` remains metadata only.
3. `world_cache_policy=DISABLED_NO_PICKLE_NO_SEALED_CACHE` is recorded on new worlds.
4. Added two regression tests: malicious pre-existing pickle is neither executed nor overwritten; a newly generated world does not persist its sealed task payloads.
5. The checkpoint excludes historical and private task pools and all world caches; it contains only code, tests, manifests, DEV audit evidence and handoff.

## Regression evidence

`PYTHONPATH=src python -m unittest discover -s tests -q`: **145 run, 144 pass, 1 skip**. Original checkpoint SHA-256: `3b29a70d963e03e53a91612e2e1f0c27adcc222ef81d65a74e1b87844ed0950c`. New source ZIP has a SHA-256 content manifest, verified after extraction, but **no external signature**.

## Remaining risks and constraints

- Existing `.pkl` caches may already contain sealed data and must be quarantined, **not reused**. Historical contamination cannot be disproven by this patch.
- Research and sealed data remain in the same Python process during DEV world construction; **GEN-AUD-002 is unresolved**. This patch does not establish independent custody.
- Disabling caches increases CPU and wall-time consumption. Any experiment must account for the change in the frozen resource profile.
- GEN-AUD-001/008/009 DEV proof repairs still require independent acceptance. The previous historical 11/20 missing raw jobs cannot be recovered by rerunning old sealed tasks.
- No external Lean, no new prospective sealed mathematical runs, no accepted batch, no independent scientific result. The new patch requires independent red-team review before promotion.

**Decision:** `FAILED_REPAIR_REQUIRED`; promotion **BLOCKED**. No evidence gates, alpha, split definitions, or prior results changed.
