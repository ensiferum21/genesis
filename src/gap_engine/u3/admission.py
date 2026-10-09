"""Kernel-controlled training-data admission (INV-20).

Only kernel-verified items enter a dataset. Items that match or nearly match a sealed
item are removed and counted; with `strict=True` the whole dataset is rejected instead.
The manifest hash is ledgered so any later change to the training data is detectable.
"""
from __future__ import annotations

from ..kernel.invariants import InvariantViolation, inv20_training_admission
from ..kernel.ledger import Ledger, _canonical, sha256_hex
from ..kernel.records import DatasetManifest, HarvestRecord
from ..kernel.sealed import SealedStore


def admit_dataset(name: str, items: list[HarvestRecord], sealed: SealedStore, ledger: Ledger,
                  strict: bool = False, verifier=None) -> DatasetManifest:
    """`verifier(text) -> bool` re-derives verification from the kernel's store; when given,
    the records' own `kernel_verified` flags are not trusted."""
    if verifier is not None:
        items = [it.model_copy(update={"kernel_verified": bool(verifier(it.text))}) for it in items]
    verified = [it for it in items if it.kernel_verified]
    rejected_unverified = len(items) - len(verified)
    kept_idx, rej_idx = sealed.screen([it.text for it in verified])
    if strict and rej_idx:
        ledger.append("dataset.rejected", {"name": name, "sealed_hits": len(rej_idx)})
        raise InvariantViolation(f"INV-20: dataset {name!r} has {len(rej_idx)} sealed/near-duplicate items")
    kept = [verified[i] for i in kept_idx]
    inv20_training_admission([it.kernel_verified for it in kept], sealed_hits=0)
    man = DatasetManifest(name=name, items=kept, rejected_sealed=len(rej_idx),
                          rejected_unverified=rejected_unverified, contamination_class="DEV")
    man.hash = sha256_hex(_canonical([it.model_dump() for it in kept]))
    ledger.append("dataset.admitted", {"name": name, "n": len(kept), "hash": man.hash,
                                       "rejected_sealed": len(rej_idx),
                                       "rejected_unverified": rejected_unverified})
    return man
