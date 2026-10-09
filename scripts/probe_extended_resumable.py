#!/usr/bin/env python3
"""DEV-only bounded, resumable per-theme probe. No sealed access or promotions.

Each theme is an isolated subprocess, with a hard wall-time budget. Completed
results are immutable-by-hash cache entries and can be reused only with matching
source/config/history fingerprints. An interrupted theme is never called complete.
The aggregate is screened against historical *statements*, never outcomes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from gap_engine.adapters.induction.extended import EXTENDED_THEMES, extended_theory
from scripts.screen_fresh_pool import screen

ROOT = Path(__file__).resolve().parents[1]
# Include all checker, solver, theory, task, and screen sources in the cache key;
# otherwise a code change could silently reuse stale results.
INPUT_SOURCES = sorted({
    *(str(p.relative_to(ROOT)) for p in (ROOT / 'src/gap_engine/adapters/induction').glob('*.py')),
    'src/gap_engine/kernel/sealed.py',
    'scripts/probe_extended_families.py',
    'scripts/probe_extended_resumable.py',
    'scripts/screen_fresh_pool.py',
})


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(p: Path) -> str:
    return sha(p.read_bytes())


def atomic_json(path: Path, data: dict) -> None:
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')
    os.replace(tmp, path)


def config_fingerprint(history: list[Path], *, max_size: int, max_terms: int,
                       seed: int, weak_fuel: int = 150, strong_fuel: int = 5000) -> tuple[str, dict]:
    evidence = {
        'schema': 'genesis-resumable-theme-v1',
        'params': {'max_size': max_size, 'max_terms': max_terms, 'seed': seed,
                   'weak_fuel': weak_fuel, 'strong_fuel': strong_fuel},
        'source_hashes': {s: sha_file(ROOT / s) for s in INPUT_SOURCES},
        'history_sha256': {str(p.resolve()): sha_file(p) for p in history},
    }
    return sha(json.dumps(evidence, sort_keys=True).encode()), evidence


def cache_valid(meta: Path, pool: Path, proof: Path, fingerprint: str, theme: str) -> bool:
    if not (meta.exists() and pool.exists() and proof.exists()):
        return False
    try:
        m = json.loads(meta.read_text())
        data = json.loads(pool.read_text())
        ps = json.loads(proof.read_text())['proofs']
        return (m.get('status') == 'COMPLETE_DEV_ONLY'
                and m.get('config_sha256') == fingerprint
                and m.get('theme') == theme
                and m.get('pool_sha256') == sha_file(pool)
                and m.get('proof_sha256') == sha_file(proof)
                and data['params']['themes'] == [theme]
                and len(data['tasks']) == len(set(data['tasks']))
                and set(data['tasks']) <= set(ps))
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return False


def run_resumable(outdir: Path, history: list[Path], *, max_size: int = 7,
                  max_terms: int = 1800, seed: int = 424246, timeout: float = 40,
                  themes: list[str] | None = None, max_new_themes: int | None = None) -> dict:
    if timeout <= 0 or max_size < 1 or max_terms < 1:
        raise ValueError('positive limits required')
    chosen = list(EXTENDED_THEMES) if themes is None else list(themes)
    if not chosen or len(set(chosen)) != len(chosen) or any(t not in EXTENDED_THEMES for t in chosen):
        raise ValueError('themes must be a nonempty unique subset')
    outdir.mkdir(parents=True, exist_ok=True)
    fingerprint, evidence = config_fingerprint(history, max_size=max_size, max_terms=max_terms, seed=seed)
    # Preserve a fingerprinted record; never overwrite an incompatible run's outputs.
    runroot = outdir / fingerprint[:16]
    runroot.mkdir(parents=True, exist_ok=True)
    atomic_json(runroot / 'inputs.json', {'fingerprint': fingerprint, **evidence})
    counts, completed, failed, resumed = {}, [], [], []
    new_count = 0
    for theme in chosen:
        base = runroot / theme
        pool = base.with_suffix('.json')
        proof = runroot / f'{theme}_proofs.json'
        fresh = runroot / f'{theme}_freshness.json'
        meta = runroot / f'{theme}.meta.json'
        if cache_valid(meta, pool, proof, fingerprint, theme):
            completed.append(theme)
            resumed.append(theme)
            counts[theme] = json.loads(pool.read_text())['counts'][theme]
            continue
        if max_new_themes is not None and new_count >= max_new_themes:
            failed.append({'theme': theme, 'reason': 'NOT_STARTED_BUDGET'})
            continue
        new_count += 1
        for tmp in (pool, proof, fresh, meta):
            # Remove incomplete output for this fingerprint, never accepted artifacts.
            if tmp.exists():
                tmp.unlink()
        cmd = [sys.executable, '-m', 'scripts.probe_extended_families', '--out', str(pool),
               '--history', *(str(p) for p in history), '--max-size', str(max_size),
               '--max-terms', str(max_terms), '--seed', str(seed), '--themes', theme]
        env = dict(os.environ)
        env['PYTHONPATH'] = str(ROOT / 'src') + os.pathsep + str(ROOT) + os.pathsep + env.get('PYTHONPATH', '')
        started = time.monotonic()
        try:
            r = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, timeout=timeout)
            elapsed = round(time.monotonic() - started, 3)
            if r.returncode != 0 or not pool.exists() or not proof.exists():
                failed.append({'theme': theme, 'reason': 'WORKER_ERROR', 'returncode': r.returncode,
                               'elapsed_seconds': elapsed, 'stderr_tail': r.stderr[-1500:]})
                continue
            data = json.loads(pool.read_text())
            ps = json.loads(proof.read_text())['proofs']
            if data['params']['themes'] != [theme] or set(data['tasks']) - set(ps):
                failed.append({'theme': theme, 'reason': 'INCOMPLETE_PROOF_RECORD'})
                continue
            atomic_json(meta, {'theme': theme, 'status': 'COMPLETE_DEV_ONLY',
                               'config_sha256': fingerprint, 'pool_sha256': sha_file(pool),
                               'proof_sha256': sha_file(proof), 'elapsed_seconds': elapsed})
            counts[theme] = data['counts'][theme]
            completed.append(theme)
        except subprocess.TimeoutExpired:
            failed.append({'theme': theme, 'reason': 'TIMEOUT', 'timeout_seconds': timeout})
    tasks, proofs = [], {}
    for theme in completed:
        pool = runroot / f'{theme}.json'
        proof = runroot / f'{theme}_proofs.json'
        data = json.loads(pool.read_text())
        ps = json.loads(proof.read_text())['proofs']
        for task in data['tasks']:
            if task not in proofs:
                tasks.append(task)
                proofs[task] = ps[task]
    # An incomplete collection can be used for DEV diagnostics, NEVER for prereg.
    aggregate = runroot / 'aggregate_dev.json'
    aggregate_proofs = runroot / 'aggregate_dev_proofs.json'
    atomic_json(aggregate, {'tasks': tasks, 'params': evidence['params'],
                            'themes_completed': completed, 'themes_requested': chosen,
                            'status': 'DEV_ONLY_PARTIAL' if failed else 'DEV_ONLY_COMPLETE'})
    atomic_json(aggregate_proofs, {'theory': extended_theory().name, 'proofs': proofs})
    freshness = screen(aggregate, history, theory=extended_theory(), minimum=300)
    atomic_json(runroot / 'aggregate_dev_freshness.json', freshness)
    report = {
        'status': 'DEV_ONLY_PARTIAL' if failed else 'DEV_ONLY_COMPLETE',
        'preregistration_allowed': False, 'promotion_allowed': False,
        'run_dir': str(runroot), 'config_sha256': fingerprint,
        'completed_themes': completed, 'reused_themes': resumed,
        'failed_or_pending_themes': failed, 'unique_tasks': len(tasks),
        'statement_fresh': freshness['fresh_count'],
        'minimum_required': 300, 'counts': counts,
        'note': 'No sealed outcomes read. Proof objects are not Lean verified; template/semantic quality and independence are not established.',
    }
    atomic_json(runroot / 'progress.json', report)
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--outdir', type=Path, required=True)
    ap.add_argument('--history', nargs='+', type=Path, required=True)
    ap.add_argument('--max-size', type=int, default=7)
    ap.add_argument('--max-terms', type=int, default=1800)
    ap.add_argument('--seed', type=int, default=424246)
    ap.add_argument('--timeout', type=float, default=40)
    ap.add_argument('--themes', nargs='+', choices=list(EXTENDED_THEMES))
    ap.add_argument('--max-new-themes', type=int)
    args = ap.parse_args()
    print(json.dumps(run_resumable(args.outdir, args.history, max_size=args.max_size,
                                   max_terms=args.max_terms, seed=args.seed, timeout=args.timeout,
                                   themes=args.themes, max_new_themes=args.max_new_themes), indent=2))


if __name__ == '__main__':
    main()
