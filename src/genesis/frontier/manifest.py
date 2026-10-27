"""The manifest: the only way inputs reach the research plane (the No-Handholding Protocol, `docs/OMEGA_FRONTIER.md`
§3). A study builds one from a domain and a verifier; the engine sees only the domain's public calls through
`PublicDomain`, and the verifier as an opaque callback. The manifest's digest (the domain's public description, the
budget, the quantum, the verification cost and the engine's parameters) is recorded with every run.
"""
import hashlib
import json

PUBLIC = ('problems', 'statement', 'approaches', 'neighbours', 'step', 'abstract', 'successors', 'derive')
OPTIONAL = ('derive',)                          # a domain without it answers None


def _none(*args, **kwargs):
    return None


class PublicDomain:
    """Exposes only the public calls of a domain object; anything else raises AttributeError."""

    __slots__ = ('_calls',)

    def __init__(self, domain):
        calls = {name: (getattr(domain, name, None) or _none) if name in OPTIONAL else getattr(domain, name)
                 for name in PUBLIC}
        object.__setattr__(self, '_calls', calls)

    def __getattr__(self, name):
        calls = object.__getattribute__(self, '_calls')
        if name in calls:
            return calls[name]
        raise AttributeError(f'{name} is not part of the public domain API')

    def __setattr__(self, name, value):
        raise AttributeError('the public domain is read-only')


class Manifest:
    def __init__(self, domain, verify, budget, quantum=10, verify_cost=1, description=None):
        self.domain = PublicDomain(domain)
        self._verify = verify
        self.budget, self.quantum, self.verify_cost = budget, quantum, verify_cost
        self.description = description or {}
        self.sources = []                       # the teaching ban: where every datum the engine learns from came from

    def verify(self, problem, artifact):
        return self._verify(problem, artifact)

    def log_source(self, what, origin):
        self.sources.append({'what': what, 'origin': origin})

    def digest(self, params=None):
        body = {'description': self.description, 'budget': self.budget, 'quantum': self.quantum,
                'verify_cost': self.verify_cost, 'params': params or {}}
        return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()
