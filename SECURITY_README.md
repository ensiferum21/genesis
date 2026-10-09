# Genesis DEV source checkpoint

This ZIP deliberately excludes `experiments/`, `.pkl` world caches, sealed tasks and private evaluation datasets. It is a development source snapshot, **not** a completed research system or independently signed release. The previous full DEV checkpoint SHA-256 is 3b29a70d963e03e53a91612e2e1f0c27adcc222ef81d65a74e1b87844ed0950c and is required to reconstruct the historical experiment files separately under proper custody.

To run regression tests: `PYTHONPATH=src python -m unittest discover -s tests -q`. To check the manifest: `python scripts/evidence_manifest.py . --verify`.

`cache_dir` is ignored for world building; do not load old pickle caches. `SealedStore` remains in-process in DEV and must not be used for a prospective sealed claim.
