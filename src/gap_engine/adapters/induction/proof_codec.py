"""Non-executable JSON transport for proof trees; never load pickle as evidence."""
from __future__ import annotations


def encode(obj):
    if isinstance(obj, tuple):
        return {'__proof_tuple_v1__': [encode(v) for v in obj]}
    if isinstance(obj, list):
        return [encode(v) for v in obj]
    if isinstance(obj, dict):
        if not all(isinstance(k, str) for k in obj):
            raise TypeError('proof JSON keys must be strings')
        return {k: encode(v) for k, v in obj.items()}
    if obj is None or isinstance(obj, (str, bool, int, float)):
        return obj
    raise TypeError(f'unsupported proof value: {type(obj)}')


def decode(obj):
    if isinstance(obj, dict):
        if set(obj) == {'__proof_tuple_v1__'}:
            return tuple(decode(v) for v in obj['__proof_tuple_v1__'])
        return {k: decode(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [decode(v) for v in obj]
    return obj
