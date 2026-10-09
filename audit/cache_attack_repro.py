"""Harmless marker proof-of-execution against DEV synthetic world caches."""
import json, pickle, tempfile
from pathlib import Path
from gap_engine.adapters.induction.adapter import build_world_from_suite

class Marker:
    def __init__(self, p): self.p=p
    def __reduce__(self): return (Path(self.p).write_text, ('MARKER',))

texts=['plus x Z = x','double x = plus x x','len (rev xs) = len xs','sum (rev xs) = sum xs']
with tempfile.TemporaryDirectory() as td:
    marker=Path(td)/'executed'
    a=build_world_from_suite('cache-attack',texts,seed=7,conj_size=3,cache_dir=None)
    path=Path(td)/a.meta['cache_key']
    path.write_bytes(pickle.dumps(Marker(str(marker))))
    try:
        b=build_world_from_suite('cache-attack',texts,seed=7,conj_size=3,cache_dir=td)
        outcome='RETURNED'
    except Exception as e:
        outcome=type(e).__name__
    print(json.dumps({'marker_executed':marker.exists(),'load_outcome':outcome,'pickle_bytes_changed':path.read_bytes()!=pickle.dumps(Marker(str(marker)))}))
