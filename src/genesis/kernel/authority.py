"""Execution grants with leased, non-duplicable budgets (spec §2.4, §5.6, §17).

    Capability_{t+1} > Capability_t   is allowed.
    Authority_{t+1} <= Authority_t    unless an external controller changes it.

A grant carries resource budgets and permissions. Children are carved out of
a parent's remaining budget, so branching cannot multiply authority; their
permissions can only be a subset of the parent's. Every charge is recorded in
the store, including failures, so the ledger reconciles with receipts.
"""
from ..common import digest, utcnow

BUDGET_FIELDS = ('cpu_seconds', 'wall_seconds', 'attempts', 'output_bytes', 'paid_api_usd')
PERMISSIONS = {'execute_fixed_dsl', 'execute_sandboxed_code', 'read_public_tasks', 'call_provider_broker',
               'network', 'write_release'}
# Never grantable from inside the system, whatever the parent holds.
EXTERNAL_ONLY = {'network', 'write_release', 'call_provider_broker'}


class AuthorityError(PermissionError):
    pass


class GrantLedger:
    def __init__(self, store):
        self.s = store

    def _grant(self, gid):
        g = self.s.state(f'grant:{gid}')
        if g is None:
            raise AuthorityError(f'unknown grant {gid}')
        return g

    def root_grant(self, budgets, permissions, *, issuer, external_authorization=None):
        """Only the campaign root grant is created from nothing; it records who issued it."""
        if set(budgets) != set(BUDGET_FIELDS) or any(type(v) not in (int, float) or v < 0 for v in budgets.values()):
            raise AuthorityError('root grant needs every budget field, non-negative')
        permissions = set(permissions)
        if permissions - PERMISSIONS:
            raise AuthorityError('unknown permission')
        if permissions & EXTERNAL_ONLY and not external_authorization:
            raise AuthorityError('network/release/provider permissions need an external authorization record')
        if self.s.state('grant_root') is not None:
            raise AuthorityError('campaign already has a root grant; authority cannot be re-issued internally')
        grant = {'parent': None, 'budgets': dict(budgets), 'remaining': dict(budgets),
                 'permissions': sorted(permissions), 'issuer': issuer,
                 'external_authorization': external_authorization, 'issued_at': utcnow()}
        gid = digest(grant)
        self.s.save('grant', gid, grant)
        self.s.set_state(f'grant:{gid}', grant)
        self.s.set_state('grant_root', gid)
        return gid

    def child(self, parent_id, budgets, permissions, *, purpose):
        """Lease part of a parent's remaining budget to a child (a world, trial or worker)."""
        parent = self._grant(parent_id)
        permissions = set(permissions)
        if not permissions <= set(parent['permissions']):
            raise AuthorityError('a child cannot hold permissions its parent lacks')
        if set(budgets) - set(BUDGET_FIELDS):
            raise AuthorityError('unknown budget field')
        leased = {k: budgets.get(k, 0) for k in BUDGET_FIELDS}
        for k, v in leased.items():
            if type(v) not in (int, float) or v < 0:
                raise AuthorityError('budgets must be non-negative numbers')
            if v > parent['remaining'][k] + 1e-12:
                raise AuthorityError(f'child {k} {v} exceeds parent remaining {parent["remaining"][k]}')
        parent = dict(parent, remaining={k: parent['remaining'][k] - leased[k] for k in BUDGET_FIELDS})
        self.s.set_state(f'grant:{parent_id}', parent)
        grant = {'parent': parent_id, 'budgets': leased, 'remaining': dict(leased),
                 'permissions': sorted(permissions), 'purpose': purpose, 'issued_at': utcnow()}
        gid = digest(grant)
        self.s.save('grant', gid, grant)
        self.s.set_state(f'grant:{gid}', grant)
        return gid

    def require(self, gid, permission, **needed):
        g = self._grant(gid)
        if permission not in g['permissions']:
            raise AuthorityError(f'grant lacks permission {permission}')
        for k, v in needed.items():
            if g['remaining'][k] < v:
                raise AuthorityError(f'grant {k} exhausted ({g["remaining"][k]} < {v})')
        return g

    def charge(self, gid, receipt_hash, **used):
        """Charge actual usage. Overshoot is recorded (never hidden) and leaves the grant at zero."""
        g = self._grant(gid)
        remaining = dict(g['remaining']); overshoot = {}
        for k, v in used.items():
            if k not in BUDGET_FIELDS or type(v) not in (int, float) or v < 0:
                raise AuthorityError('invalid charge')
            if v > remaining[k]:
                overshoot[k] = v - remaining[k]
            remaining[k] = max(0, remaining[k] - v)
        self.s.set_state(f'grant:{gid}', dict(g, remaining=remaining))
        self.s.event('GRANT_CHARGED', {'grant': gid, 'receipt': receipt_hash, 'used': used, 'overshoot': overshoot})
        return remaining

    def total_authority(self):
        """Sum of root budgets: the invariant upper bound on everything ever leased."""
        root = self.s.state('grant_root')
        return self._grant(root)['budgets'] if root else None
