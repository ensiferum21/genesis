"""Several domains as one, so that the Frontier allocates across them (research plane; `docs/OMEGA_FRONTIER.md`
§7, F6's "the engine's other domains as direction sources").

`MultiDomain({name: domain})` offers the public calls of every member under one namespace. A problem is
'<name>/<problem>', and each call is routed to the member that owns it:
  * problems: every member's problems, prefixed;
  * statement: the member's statement, prefixed with the member's name, so that the engine's digest order and the
    relabelling audit treat the members as distinct;
  * approaches, step, abstract, derive and successors: the member's answer, with problem ids prefixed in and out;
  * neighbours: the member's own neighbours (members do not share problems).
Artifacts keep the member's fields; their 'problem' is prefixed. `multi_verifier({name: verify})` is the matching
kernel-side composition: a study builds it from the members' own verifiers, and it strips the prefix before
asking the member.

Each member is held behind its own `PublicDomain`, so the composition reaches only public calls. The members are
unchanged, and nothing about any member is visible to another except through the engine's own allocation,
convergence and procedures.
"""
from .manifest import PublicDomain

SEP = '/'


def _split(pid):
    parts = pid.split(SEP, 1)
    return (parts[0], parts[1]) if len(parts) == 2 else (parts[0], '')


def _with(name, art):
    out = dict(art)
    if 'problem' in out:
        out['problem'] = f'{name}{SEP}{out["problem"]}'
    return out


class MultiDomain:
    def __init__(self, members):
        if any(SEP in name for name in members):
            raise ValueError(f'member names may not contain {SEP!r}')
        self.members = {name: PublicDomain(d) for name, d in members.items()}      # members' public calls only

    def problems(self):
        return sorted(f'{name}{SEP}{p}' for name, d in self.members.items() for p in d.problems())

    def statement(self, pid):
        name, inner = _split(pid)
        return f'{name}: {self.members[name].statement(inner)}'

    def approaches(self, pid):
        name, inner = _split(pid)
        return self.members[name].approaches(inner)

    def neighbours(self, pid):
        name, inner = _split(pid)
        return [f'{name}{SEP}{q}' for q in self.members[name].neighbours(inner)]

    def step(self, pid, d, seed, t, quantum):
        name, inner = _split(pid)
        pts, arts = self.members[name].step(inner, dict(d, problem=inner), seed, t, quantum)
        return pts, [_with(name, a) for a in arts]

    def abstract(self, pid, fingerprint):
        name, inner = _split(pid)
        return self.members[name].abstract(inner, fingerprint)

    def derive(self, pid, representation, seed):
        name, inner = _split(pid)
        return self.members[name].derive(inner, representation, seed)

    def successors(self, pid, artifact):
        name, inner = _split(pid)
        art = dict(artifact)
        if art.get('problem', '').startswith(name + SEP):
            art['problem'] = _split(art['problem'])[1]
        return [f'{name}{SEP}{q}' for q in self.members[name].successors(inner, art)]


def multi_verifier(verifiers):
    """The kernel side's composition: verify(pid, artifact) asks the owning member's verifier, prefix stripped."""
    def verify(pid, art):
        name, inner = _split(pid)
        if name not in verifiers:
            return 0.0
        a = dict(art)
        if str(a.get('problem', '')).startswith(name + SEP):
            a['problem'] = _split(a['problem'])[1]
        return verifiers[name](inner, a)
    return verify
