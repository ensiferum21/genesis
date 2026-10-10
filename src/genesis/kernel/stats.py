"""Trusted statistics used to re-derive signed outcomes (kernel.receipts).

Lives in the kernel so the judge of a receipt does not import research-side code.
"""
from math import comb


def sign_test(wins, losses):
    """One-sided exact sign test: P(X >= wins) for X ~ Binomial(wins + losses, 1/2)."""
    if type(wins) is not int or type(losses) is not int or min(wins, losses) < 0:
        raise ValueError('counts')
    n = wins + losses
    return sum(comb(n, k) for k in range(wins, n + 1)) / 2 ** n if n else 1.0
