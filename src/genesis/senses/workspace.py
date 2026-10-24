"""The perceptual workspace: typed observations of one problem instance, with provenance
(`docs/OMEGA_RECURSIVE_INVENTION.md` §4.3; Batch R2).

Each observation is the output of a research object run on the instance (or on earlier observations), stored with:
  * its producer's identity;
  * the observations it was derived from;
  * its effect: accessibility, or information with its source;
  * its cost (fuel).
`observe` runs a sense object on the instance; `derive` runs an object on named observations, provided their types
fit its inputs (and records the dependency). `missing(needed)` lists the input names and types a planned object
needs that the workspace cannot yet supply: the question the experiment designer answers next. Observations are not
concatenated: an object takes the observations it declares, by name and type.
"""
from ..objects import core as O
from ..objects import types as TY


class Workspace:
    def __init__(self, instance, instance_type='Graph', types=TY.SEED):
        if not TY.check(instance, instance_type, types):
            raise ValueError(f'the instance is not a {instance_type}')
        self.types = types
        self.obs = {'instance': {'value': instance, 'type': instance_type, 'producer': None, 'from': [],
                                 'effect': 'given', 'cost': 0}}

    def observe(self, name, obj, fuel, input_name='graph'):
        return self.derive(name, obj, {input_name: 'instance'}, fuel)

    def derive(self, name, obj, bindings, fuel):
        """Run obj with inputs bound to observations ({input name: observation name})."""
        if name in self.obs:
            raise ValueError(f'observation {name!r} exists')
        inputs = {}
        for arg, src in bindings.items():
            if src not in self.obs:
                raise KeyError(f'no observation {src!r}')
            inputs[arg] = self.obs[src]['value']
        res = O.run(obj, inputs, fuel, self.types)
        if not res['ok']:
            raise ValueError(f"{name}: {res['violations']}")
        (out, ty), = obj['outputs'].items() if len(obj['outputs']) == 1 else ((None, None),)
        if out is None:
            raise ValueError('a workspace observation comes from a single-output object')
        self.obs[name] = {'value': res['outputs'][out], 'type': ty, 'producer': O.oid(obj),
                          'from': sorted(bindings.values()), 'effect': obj['effect'] or 'accessibility',
                          'cost': res['fuel_spent']}
        return self.obs[name]['value']

    def missing(self, needed):
        """needed: {input name: type}. The names no observation of that type can supply."""
        have = {}
        for n, o in self.obs.items():
            have.setdefault(str(o['type']), []).append(n)
        return {k: t for k, t in needed.items() if str(t) not in have and not (t == 'Any' and self.obs)}

    def lineage(self, name):
        """Every observation `name` depends on, transitively."""
        out, todo = set(), [name]
        while todo:
            x = todo.pop()
            for p in self.obs[x]['from']:
                if p not in out:
                    out.add(p)
                    todo.append(p)
        return sorted(out)


__all__ = ['Workspace']
