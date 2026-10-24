"""The kind registry of research objects (`docs/OMEGA_RECURSIVE_INVENTION.md` §1, §3.3).

A kind says what an object of that kind does: its group, its effect (`accessibility`: a deterministic function of its
inputs, adding no information; `information`: it draws new data, at a declared cost; `meta`: it produces or changes
other objects), and the vault artifact type it is stored as. The seed kinds are the architecture's seed set, not a
limit: `register` admits a new kind as data (a name, a group, an effect, a storage type) with lineage, returning a new
registry value that names its parent.
"""
import copy

from ..common import digest

EFFECTS = ('accessibility', 'information', 'meta')
GROUPS = ('perception', 'fusion', 'representation', 'mathematics', 'method', 'strategy', 'self-knowledge',
          'self-improvement', 'language', 'other')
STORAGE = {'perception': 'ObservableSpec', 'fusion': 'ProgramSpec', 'representation': 'WorldSpec',
           'mathematics': 'DiscoveryRecord', 'method': 'ProgramSpec', 'strategy': 'ProcessSpec',
           'self-knowledge': 'ProgramSpec', 'self-improvement': 'ProcessSpec', 'language': 'WorldSpec',
           'other': 'ProgramSpec'}

_SEED = {
    'Sense': ('perception', 'accessibility'), 'Instrument': ('perception', 'information'),
    'ExperimentDesign': ('perception', 'meta'), 'Composition': ('fusion', 'meta'),
    'Representation': ('representation', 'accessibility'), 'Encoding': ('representation', 'accessibility'),
    'Relation': ('representation', 'accessibility'), 'Gadget': ('representation', 'accessibility'),
    'Transformation': ('representation', 'accessibility'), 'Decoder': ('representation', 'accessibility'),
    'Concept': ('mathematics', 'accessibility'), 'Invariant': ('mathematics', 'accessibility'),
    'Bound': ('mathematics', 'accessibility'), 'Conjecture': ('mathematics', 'accessibility'),
    'Theorem': ('mathematics', 'accessibility'), 'ProofProcedure': ('mathematics', 'meta'),
    'Operator': ('method', 'accessibility'), 'Algorithm': ('method', 'accessibility'),
    'Solver': ('method', 'accessibility'), 'Synthesizer': ('method', 'meta'),
    'AttackStrategy': ('strategy', 'meta'), 'Workflow': ('strategy', 'meta'), 'Allocator': ('strategy', 'meta'),
    'Diagnoser': ('self-knowledge', 'meta'), 'Predictor': ('self-knowledge', 'accessibility'),
    'Improver': ('self-improvement', 'meta'), 'Primitive': ('language', 'accessibility'),
    'TypeConstructor': ('language', 'meta'), 'Measure': ('self-knowledge', 'accessibility'),
}


def _version(kinds):
    return digest({'schema': 'genesis-object-kinds-v1', 'kinds': kinds})[:16]


def _seed():
    kinds = {k: {'group': g, 'effect': e, 'storage': STORAGE[g], 'lineage': {'seed': True}}
             for k, (g, e) in _SEED.items()}
    return {'parent': None, 'kinds': kinds, 'version': _version(kinds)}


SEED = _seed()


def register(reg, name, group, effect, lineage=None):
    if name in reg['kinds']:
        raise ValueError(f'kind {name!r} exists')
    if group not in GROUPS or effect not in EFFECTS:
        raise ValueError(f'group in {GROUPS}, effect in {EFFECTS}')
    kinds = copy.deepcopy(reg['kinds'])
    kinds[name] = {'group': group, 'effect': effect, 'storage': STORAGE[group], 'lineage': lineage or {}}
    return {'parent': reg['version'], 'kinds': kinds, 'version': _version(kinds)}


__all__ = ['EFFECTS', 'GROUPS', 'STORAGE', 'SEED', 'register']
