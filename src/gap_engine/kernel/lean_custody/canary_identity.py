"""Verify the actual canary sources and manifests, not just claimed receipt hashes.

DEV guard only; not Lean provenance or independent proof validation.
"""
from pathlib import Path
import hashlib
import json
from .replay_package import audit

POSITIVE = b'theorem genesis_canary_positive : (2 : Nat) + 2 = 4 := by decide\n'
NEGATIVE = b'theorem genesis_canary_negative : (2 : Nat) + 2 = 5 := by decide\n'


def verify(positive_project, negative_project, positive_manifest, negative_manifest,
           positive_pin, negative_pin):
    result={'status':'BLOCKED','promotion_allowed':False,'reason':'unverified'}
    try:
        for label, project, manifest, pin, expected in (
            ('positive',positive_project,positive_manifest,positive_pin,POSITIVE),
            ('negative',negative_project,negative_manifest,negative_pin,NEGATIVE)):
            project=Path(project)
            if project.is_symlink() or not project.is_dir():
                raise ValueError(label+' unsafe project')
            manifest=Path(manifest)
            if manifest.is_symlink() or not manifest.is_file():
                raise ValueError(label+' unsafe manifest')
            raw=manifest.read_bytes()
            audit(project,raw,pin)
            actual=(project/'Main.lean').read_bytes()
            if actual!=expected:
                raise ValueError(label+' canary source differs from audited control')
            parsed=json.loads(raw)
            if parsed['files']['Main.lean']!=hashlib.sha256(expected).hexdigest():
                raise ValueError(label+' control source hash mismatch')
        result.update(status='DEV_CANARY_SOURCES_VERIFIED',reason='both controls exactly match fixed sources; provenance not established')
    except (ValueError,OSError,KeyError,TypeError) as exc:
        result['reason']=str(exc)
    return result
