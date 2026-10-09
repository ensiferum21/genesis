#!/usr/bin/env python3
"""Fail-closed *preflight*, not a substitute for independent replication.

No promotion may rely solely on this tool; it checks documented prerequisites.
It intentionally blocks the current Batch 1 DEV branch and historical sealed run.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from gap_engine.kernel.custody import CustodyError, verify_external_attestation
from scripts.evidence_manifest import verify_manifest

REQUIRED = ('candidate_sha256', 'preregistration_sha256', 'pool_sha256',
            'results_manifest_root_sha256', 'evaluator_sha256')


def preflight(state: dict, audit: dict, sealed_evidence: dict | None = None,
              *, custodian_public_key_pem: bytes | None = None,
              evidence_root: Path | None = None) -> dict:
    reasons = []
    if state.get('status') != 'READY_FOR_PROMOTION':
        reasons.append('campaign is not READY_FOR_PROMOTION')
    if state.get('current_batch') != 1:
        # This preflight is deliberately Batch-1-specific until reviewed for later batches.
        reasons.append('preflight schema only reviewed for Batch 1')
    if audit.get('audit_status') not in ('PASS', 'PASS_WITH_NOTES'):
        reasons.append('latest independent audit is not passing')
    if any(x.get('severity') == 'CRITICAL' for x in audit.get('findings', [])):
        reasons.append('unresolved CRITICAL audit finding')
    if sealed_evidence is None:
        reasons.append('no fresh preregistered sealed evidence')
    else:
        if sealed_evidence.get('historical_pool_reused') is not False:
            reasons.append('fresh sealed pool not attested')
        if sealed_evidence.get('fresh_task_count', 0) < 300:
            reasons.append('fewer than 300 independently screened fresh tasks')
        if sealed_evidence.get('completed_jobs') != sealed_evidence.get('preregistered_jobs') or not sealed_evidence.get('completed_jobs'):
            reasons.append('raw sealed job records incomplete')
        if sealed_evidence.get('matched_baselines_passed') is not True:
            reasons.append('matched baseline gate missing')
        if sealed_evidence.get('regression_passed') is not True:
            reasons.append('regression gate missing')
        if sealed_evidence.get('near_duplicate_scan_passed') is not True:
            reasons.append('near-duplicate screen missing')
        if sealed_evidence.get('checker_replay_passed') is not True:
            reasons.append('independent checker replay missing')
        expected = {k: sealed_evidence.get(k, '') for k in REQUIRED}
        if not custodian_public_key_pem or not sealed_evidence.get('custody_attestation'):
            reasons.append('independent evaluator custody signature missing')
        else:
            try:
                verify_external_attestation(sealed_evidence['custody_attestation'],
                                            custodian_public_key_pem, expected)
            except CustodyError as exc:
                reasons.append(f'invalid evaluator custody attestation: {exc}')
        if evidence_root is None or not (evidence_root / 'EVIDENCE_MANIFEST.json').exists():
            reasons.append('independent evidence manifest missing')
        else:
            manifest = json.loads((evidence_root / 'EVIDENCE_MANIFEST.json').read_text())
            issues = verify_manifest(evidence_root, manifest)
            if issues or manifest['root_sha256'] != expected['results_manifest_root_sha256']:
                reasons.append('raw evidence manifest failed: ' + '; '.join(issues[:3]))
    # The research process can generate its own state, audit JSON, manifest and
    # Ed25519 key. Therefore a passing *local* preflight cannot authenticate the
    # external custodian or independent reviewer. A separately controlled release
    # authority is required; this utility never returns promotion permission.
    ready = not reasons
    return {
        'status': ('PREFLIGHT_PREREQUISITES_PRESENT_NOT_PROMOTION' if ready else 'BLOCK'),
        'prerequisites_present': ready,
        'promotion_allowed_by_this_preflight': False,
        'promotion_blocker': 'independent release authority and out-of-band custodian identity required',
        'reasons': reasons,
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--state',type=Path,required=True)
    ap.add_argument('--audit',type=Path,required=True)
    ap.add_argument('--evidence',type=Path)
    ap.add_argument('--evidence-root',type=Path)
    ap.add_argument('--custodian-public-key',type=Path)
    args=ap.parse_args()
    evidence=json.loads(args.evidence.read_text()) if args.evidence else None
    public=args.custodian_public_key.read_bytes() if args.custodian_public_key else None
    r=preflight(json.loads(args.state.read_text()),json.loads(args.audit.read_text()),
                evidence,custodian_public_key_pem=public,evidence_root=args.evidence_root)
    print(json.dumps(r,indent=2))
    # A zero exit must not be interpreted as promotion authorization.
    raise SystemExit(2)

if __name__=='__main__':
    main()
