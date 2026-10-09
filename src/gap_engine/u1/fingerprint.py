"""U1 effect fingerprints.

A fingerprint is the set of probe tasks whose behaviour a candidate changes, measured by
a short cheap run. Two lessons from the prototype are built in:

* a candidate's effects count only when its touch count exceeds the expected false-touch
  count by a calibrated margin (a fixed ">= 2 tasks" rule filtered almost nothing);
* fingerprints are best at *proposing pairs*: overlap of two fingerprints well above the
  chance overlap is the pair proposal used by blocked dropout (U2).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy import stats as sps

from ..kernel.budget import BudgetBroker, BudgetExceeded
from ..kernel.records import FingerprintRecord


@dataclass
class FingerprintSet:
    F: np.ndarray                       # (n, T_probe) bool
    measured: np.ndarray                # (n,) bool - members actually probed
    false_rate: float                   # estimated per-task false-touch probability
    cost: float
    records: list[FingerprintRecord] = field(default_factory=list)

    def active(self, z: float = 2.0) -> np.ndarray:
        """Members whose touch count exceeds the chance count by z binomial SDs."""
        T = self.F.shape[1]
        mu = self.false_rate * T
        sd = np.sqrt(max(T * self.false_rate * (1 - self.false_rate), 1e-9))
        return self.measured & (self.F.sum(1) > mu + z * sd)

    def overlap(self) -> np.ndarray:
        Fi = self.F.astype(np.int32)
        return Fi @ Fi.T

    def pair_proposals(self, min_ov: int | None = None, cap: int | None = 80,
                       alpha: float = 1e-3) -> list[tuple[int, int, int]]:
        """Pairs whose overlap exceeds chance. If `min_ov` is None, the threshold is the
        (1 - alpha) quantile of the overlap expected between two independent members with
        the observed touch counts (hypergeometric approximation by binomial)."""
        ov = self.overlap()
        n, T = self.F.shape
        cnt = self.F.sum(1)
        out = []
        for i in range(n):
            if not self.measured[i]:
                continue
            for j in range(i + 1, n):
                if not self.measured[j]:
                    continue
                o = int(ov[i, j])
                if o == 0:
                    continue
                if min_ov is not None:
                    ok = o >= min_ov
                elif self.false_rate <= 1e-9:
                    ok = o >= 1                      # exact fingerprints: any shared touch counts
                else:
                    p = (cnt[i] / T) * (cnt[j] / T)
                    thr = sps.binom.ppf(1 - alpha, T, p)
                    ok = o > max(1, thr)
                if ok:
                    out.append((i, j, o))
        out.sort(key=lambda x: -x[2])
        return out[:cap] if cap else out


def measure_fingerprints(adapter, broker: BudgetBroker, seed: int,
                         members: list[int] | None = None, null_probes: int = 3,
                         category: str = "fingerprint") -> FingerprintSet:
    """Probe every pool member (or `members`) within the fingerprint budget cap.

    The false-touch rate is estimated from `null_probes` probes of a no-op (the base
    library re-run with fresh seeds) when the adapter supports `null_fingerprint`; else it
    falls back to the adapter's declared rate or a robust estimate from the data."""
    n = len(adapter.pool_ids())
    T = adapter.fingerprint(0, seed).shape[0]
    F = np.zeros((n, T), bool)
    measured = np.zeros(n, bool)
    recs = []
    cost = 0.0
    todo = list(range(n)) if members is None else list(members)
    unit = adapter.fingerprint_cost()
    for i in todo:
        try:
            broker.charge(category, unit, purpose=f"fingerprint {i}")
        except BudgetExceeded:
            break
        F[i] = adapter.fingerprint(i, seed)
        measured[i] = True
        cost += unit
        recs.append(FingerprintRecord(candidate_id=adapter.pool_ids()[i], probe_suite="DEV-probe",
                                      touched=[int(t) for t in np.nonzero(F[i])[0]], cost=unit))
    if hasattr(adapter, "null_fingerprint"):
        rates = []
        for k in range(null_probes):
            try:
                broker.charge(category, unit, purpose="null fingerprint")
            except BudgetExceeded:
                break
            cost += unit
            rates.append(adapter.null_fingerprint(seed + 101 * (k + 1)).mean())
        false_rate = float(np.mean(rates)) if rates else getattr(adapter, "declared_false_rate", 0.03)
    elif hasattr(adapter, "spec") and hasattr(adapter.spec, "fp_false"):
        false_rate = float(adapter.spec.fp_false)
    else:
        counts = F[measured].sum(1)
        false_rate = float(np.median(counts) / T) if len(counts) else 0.03
    return FingerprintSet(F, measured, false_rate, cost, recs)
