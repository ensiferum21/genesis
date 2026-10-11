"""Deterministic crash injection for recovery tests (roadmap W04).

`point(name)` does nothing unless GENESIS_FAULT names this point. Then the
process ends immediately with os._exit(FAULT_EXIT): no finally blocks, no
atexit handlers, no buffered writes - the closest a test can get to a power
loss or SIGKILL at that instruction. "name:N" crashes at the N-th hit.

Production hosts must not set GENESIS_FAULT; `genesis platform check` fails if
it is set.
"""
import os

FAULT_EXIT = 86
ENV = 'GENESIS_FAULT'
POINTS = (
    'cas.write',            # half of a content-addressed object written
    'store.commit',         # event row inserted, transaction not committed
    'store.committed',      # transaction committed, export not yet appended
    'store.export',         # half of the new export lines appended
    'campaign.trial',       # solver attempt started, no terminal receipt
    'campaign.frozen',      # DEV successor frozen mid-generation
    'campaign.generation',  # generation outputs committed, next generation not started
    'campaign.complete',    # CANDIDATE_FROZEN recorded, report not yet written
    'request.freeze',       # candidate_version saved, replication export not yet written
    'zip.write',            # half of an export/bundle zip written
    'custodian.reserve',    # panel reservation committed, evaluation not started
    'custodian.evaluate',   # some sealed rows executed
    'custodian.sign',       # receipt signed, not yet published
    'custodian.publish',    # receipt published, request state not yet COMPLETE
)
_hits = {}


def armed():
    return bool(os.environ.get(ENV))


def point(name):
    spec = os.environ.get(ENV)
    if not spec:
        return
    target, _, nth = spec.partition(':')
    if target != name:
        return
    _hits[name] = _hits.get(name, 0) + 1
    if _hits[name] == int(nth or 1):
        os._exit(FAULT_EXIT)
