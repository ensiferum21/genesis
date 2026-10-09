"""Red-team regression: no untrusted pickle execution and no sealed cache spill."""
import os
import pickle
import tempfile
import unittest
from pathlib import Path

from gap_engine.adapters.induction.adapter import build_world_from_suite


class _Payload:
    def __init__(self, marker):
        self.marker = marker

    def __reduce__(self):
        return (Path(self.marker).write_text, ('EXECUTED_UNTRUSTED_PICKLE',))


class WorldCacheBoundaryTests(unittest.TestCase):
    def test_legacy_pickle_not_loaded_or_replaced(self):
        texts = ['plus x Z = x', 'double x = plus x x',
                 'len (rev xs) = len xs', 'sum (rev xs) = sum xs']
        with tempfile.TemporaryDirectory() as td:
            marker = Path(td) / 'pwned'
            # The suite's old cache naming is derived from input; first get
            # the exact key without caching or touching any sealed judge.
            baseline = build_world_from_suite('cache-negative', texts, seed=37,
                                              conj_size=3, cache_dir=None)
            key = baseline.meta['cache_key']
            cache = Path(td) / key
            payload = pickle.dumps(_Payload(str(marker)))
            cache.write_bytes(payload)
            candidate = build_world_from_suite('cache-negative', texts, seed=37,
                                               conj_size=3, cache_dir=td)
            self.assertEqual(candidate.meta['cache_key'], key)
            self.assertFalse(marker.exists(), 'untrusted cache executed code')
            self.assertEqual(cache.read_bytes(), payload, 'legacy cache was overwritten')
            self.assertEqual(candidate.meta['world_cache_policy'],
                             'DISABLED_NO_PICKLE_NO_SEALED_CACHE')
            self.assertEqual([p.name for p in Path(td).iterdir()], [key])

    def test_new_world_never_writes_sealed_payload(self):
        texts = ['plus x Z = x', 'double x = plus x x',
                 'len (rev xs) = len xs', 'sum (rev xs) = sum xs']
        with tempfile.TemporaryDirectory() as td:
            world = build_world_from_suite('no-sealed-spill', texts, seed=41,
                                           conj_size=3, cache_dir=td)
            self.assertTrue(world.sealed._items)
            self.assertEqual(list(Path(td).iterdir()), [])
            self.assertEqual(world.meta['world_cache_policy'],
                             'DISABLED_NO_PICKLE_NO_SEALED_CACHE')
