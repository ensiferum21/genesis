"""Joint re-analysis of the observational data and the experiments done so far (B20_R130; Genesis Ω, Ω1):
FCI re-run with a conditional-independence test that pools every regime.

Why. A third of the planted hidden causes are never asked about in `active3`, because FCI on the observational data
separates the pair: the population partial correlation given the separating set it found is small (median 0.03 on
development worlds), below what 3,000 samples can see. The experiments add samples. A regime in which neither tested
variable nor any conditioning variable was intervened on keeps the conditional independences of the observational
model or adds to them (an intervention removes edges only), so a dependence found in any such regime is a dependence
of the model.

Test. For indep(i, j, S): in each regime (the observational environments, and every experiment do(t) with t not in
{i, j} union S), Fisher's z of the partial correlation of X_i and X_j given X_S; the z's are combined by Stouffer's
method weighted by sqrt(n); independent if the two-sided p-value exceeds alpha. With only the observational regime,
this is `methods.fisher_z` on that regime. Prior art: joint causal inference (Mooij, Magliacane and Claassen 2020);
combining datasets (Tillman and Spirtes 2011; Triantafillou and Tsamardinos 2015).
"""
import math

import numpy as np
from scipy import stats

from . import fci as F
from . import methods as PCM


def pooled_test(regimes):
    """regimes: {key: X}; a key ('do', t) marks an experiment on t, anything else an observational regime."""
    cors = [(key, np.corrcoef(X, rowvar=False), X.shape[0]) for key, X in sorted(regimes.items(), key=repr)]

    def indep(i, j, S, alpha):
        num = den = 0.0
        for key, C, n in cors:
            if isinstance(key, tuple) and key[0] == 'do' and key[1] in (i, j, *S):
                continue
            idx = [i, j, *S]
            P = np.linalg.pinv(C[np.ix_(idx, idx)])
            r = -P[0, 1] / math.sqrt(abs(P[0, 0] * P[1, 1]))
            r = min(0.999999, max(-0.999999, r))
            z = 0.5 * math.log((1 + r) / (1 - r)) * math.sqrt(max(1, n - len(S) - 3))
            w = math.sqrt(n)
            num += w * z
            den += w * w
        if den == 0:
            return True
        return 2 * stats.norm.sf(abs(num / math.sqrt(den))) > alpha
    return indep


def fci(regimes, p, alpha=PCM.ALPHA):
    """FCI's answer and graph on the pooled test."""
    g, _ = F.run(p, pooled_test(regimes), alpha)
    return F.to_answer(g), g
