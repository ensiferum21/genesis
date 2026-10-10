"""Which code routes may supply evidence for confirmation-level claims.

Promotion is fail-closed: a route not listed here, or listed as ineligible, can
never support a confirmation, transfer, improver, replication or novelty claim.
Retired routes stay runnable for debugging and history; they just cannot feed
the release gate. Source identities known to carry audited vulnerabilities are
revoked outright.
"""

ROUTES = {
    'genesis.custodian.evaluate': (True, 'custodian-built exposure registry; witnesses recomputed by dual checkers'),
    'genesis.verification.sat': (True, 'DRAT certificates replayed by an independent checker'),
    'genesis.verification.lean': (True, 'kernel replay under a pinned toolchain with axiom audit'),
    'genesis.campaign': (False, 'public DEV campaign; panels are research-visible'),
    'genesis.ladder': (False, 'public known-answer calibration'),
    'custody_reference.evaluator': (False, 'reference prototype for integer-feature tasks; superseded'),
    'legacy_batch42': (False, 'GI6-08: legacy scorer with self-reported query accounting'),
    'gap_engine': (False, 'accepted-base lineage: GI6-01 reused-ID proofs, GI6-02 pickle caches, GI6-03 replay'),
}

# Code identities (genesis.common.code_identity) or archive hashes whose evidence
# is revoked regardless of route.
REVOKED_SOURCES = {
    'fb81f1f00e2044a9c77e958c382f8bcdf4af44fb9e4f37050f5a1571732d43b8':
        'accepted checkpoint archive gap-engine-v2-incremental: reproduced GI6-01 and GI6-02',
}


def route_status(route):
    """Return (eligible, reason). Unknown routes are ineligible."""
    if not isinstance(route, str) or not route:
        return False, 'missing route'
    best = None
    for prefix, status in ROUTES.items():
        if route == prefix or route.startswith(prefix + '.'):
            if best is None or len(prefix) > len(best[0]):
                best = (prefix, status)
    if best is None:
        return False, f'unregistered route {route!r}'
    return best[1]


def source_status(source_hash):
    if source_hash in REVOKED_SOURCES:
        return False, 'revoked source: ' + REVOKED_SOURCES[source_hash]
    return True, None


def eligible_for_confirmation(route, source_hash):
    ok, reason = route_status(route)
    if not ok:
        return False, reason
    return source_status(source_hash)
