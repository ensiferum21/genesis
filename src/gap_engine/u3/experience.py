"""Persistent experience store: verified usefulness labels carried across campaigns and
worlds, so proposer generations need not start from scratch.

Writing: labels come only from kernel-side evidence (dropout bundles that survived FDR
control, citations in checked proofs) for kernel-verified statements, admitted through
`admit_dataset` with a verifier against the source world's LemmaStore (INV-20).
Reading into another world: items are re-admitted through `admit_dataset` with a verifier
for THAT world (truth re-derived by its checker), screened against its sealed store and its
held-out gate tasks, so experience can never carry a sealed or held-out statement, or a
false one, into a new campaign. The file's sha256 detects casual edits only; a
preregistration pins it (round 2b) so a re-hashed forgery is detected too.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from ..kernel.ledger import Ledger, _canonical, sha256_hex
from ..kernel.records import HarvestRecord
from .admission import admit_dataset
from .proposer_model import LemmaRanker


@dataclass
class ExperienceStore:
    items: list[dict] = field(default_factory=list)       # {"text", "label", "source"}
    sources: dict = field(default_factory=dict)           # source -> {"n", "positives", "cost"}

    def add_world_labels(self, world, labels: dict[str, int], source: str, cost: float, ledger: Ledger) -> int:
        recs = [HarvestRecord(text=world.statement(c), source_task=source, kind="byproduct_lemma",
                              kernel_verified=True, label=float(v)) for c, v in labels.items()]
        known = {e.text() for e in world.store.verified_subset(world.store.order).values()}
        man = admit_dataset(f"experience-{source}", recs, world.sealed, ledger, verifier=lambda t: t in known)
        for it in man.items:
            self.items.append({"text": it.text, "label": int(it.label), "source": source})
        self.sources[source] = {"n": len(man.items), "positives": int(sum(it.label for it in man.items)),
                                "cost": cost, "manifest": man.hash}
        return len(man.items)

    def save(self, path: str) -> str:
        body = {"items": self.items, "sources": self.sources}
        h = sha256_hex(_canonical(body))
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w") as fh:
            json.dump({**body, "sha256": h}, fh, indent=1)
        return h

    @classmethod
    def load(cls, path: str) -> "ExperienceStore":
        with open(path) as fh:
            doc = json.load(fh)
        if sha256_hex(_canonical({"items": doc["items"], "sources": doc["sources"]})) != doc["sha256"]:
            raise ValueError("experience store was modified after it was written")
        return cls(doc["items"], doc["sources"])

    def ranker_for(self, world, template: LemmaRanker, ledger: Ledger, gen_id: str = "gen-prior",
                   prove_fuel: int = 3000) -> LemmaRanker:
        """Fit a ranker for `world` on stored experience.

        Carried items enter as training data only through `admit_dataset` (INV-20), with a
        verifier that re-derives truth IN THE TARGET WORLD: a statement counts as verified if
        the target's LemmaStore already holds it, or if the prover finds a proof that the
        trusted checker accepts against the target's verified lemmas. Sealed items and
        near-duplicates are screened by the kernel inside `admit_dataset`; held-out gate tasks
        (SELECT/CONFIRM) are then excluded by the world's pool screen. The usefulness LABELS
        cannot be re-derived in another world; their integrity rests on the file hash, which
        a preregistration pins (round 2b)."""
        from ..adapters.induction.checker import CheckError, check_proof
        from ..adapters.induction.prover import Prover
        from ..adapters.induction.theory import Equation
        P = world.theory.parser()
        lib = world.store.verified_subset(world.store.order)
        known = {e.text() for e in lib.values()}

        def verify(text: str) -> bool:
            if text in known:
                return True
            try:
                eq = Equation(*P.parse_eq(text))
                att = Prover(world.theory, lib, fuel=prove_fuel, max_depth=2, seed=1).prove(eq)
                return bool(att.proved and check_proof(world.theory, lib, eq, att.proof))
            except (SyntaxError, CheckError, KeyError, ValueError):
                return False

        recs = [HarvestRecord(text=it["text"], source_task=str(it.get("source", "")), kind="byproduct_lemma",
                              kernel_verified=False, label=float(it["label"])) for it in self.items]
        man = admit_dataset(f"experience-into-{world.name}-{gen_id}", recs, world.sealed, ledger, verifier=verify)
        kept = [it for it in man.items if world.screen_reason(it.text) is None]
        ledger.append("experience.load", {"items": len(self.items), "kept": len(kept),
                                          "rejected_sealed": man.rejected_sealed,
                                          "rejected_unverified": man.rejected_unverified,
                                          "rejected_held_out": len(man.items) - len(kept),
                                          "manifest": man.hash, "gen": gen_id})
        eqs, ys = [], []
        for it in kept:
            try:
                eqs.append(Equation(*P.parse_eq(it.text)))
                ys.append(int(it.label))
            except SyntaxError:
                continue
        if not eqs:
            return template                          # nothing admissible: keep the prior model
        return template.fit(eqs, ys, gen_id=gen_id)
