#!/usr/bin/env python3
"""R10: `genesis research loop <root>` on a completed world loop prints the stored
`loop_summary` STATE (and reports/world_loop.md keeps saying "Hosts with a
certified optimum: N") after the evidence behind those optima is revoked; the
kernel's effective levels are back at the floor. Same for a producer who simply
rewrites `loop_summary`/`best:<task>` with set_state.
  PYTHONPATH=src:. GENESIS_TOOLCHAIN=/home/claude/toolchain python3 -W ignore \
      audit/redteam_b14_round3/r10_world_loop_stale_summary.py
"""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from genesis.cli import main as cli  # noqa: E402
from genesis.kernel.evidence import EvidenceKernel  # noqa: E402
from genesis.store import Store  # noqa: E402
from genesis.worldstep import LoopConfig, ResearchLoop  # noqa: E402


def main():
    root = Path(tempfile.mkdtemp(prefix='r3-r10-')) / 'loop'
    with ResearchLoop(root, LoopConfig(seed=20261013, tasks=3, epochs=2, cpu_budget_per_epoch=30.0,
                                       verify_seconds=20)) as loop:
        summary = loop.run()
    print('loop: optimality_checked =', summary['optimality_checked'])
    with Store(root) as s:
        k = EvidenceKernel(s)
        opt = [c for c in k.claim_ids() if c.startswith('optimum:')]
        print('optimum claims before:', {c: k.levels(c)['math'] for c in opt})
        for nid in [n for (n,) in s.db.execute("SELECT id FROM entities WHERE kind='evidence_node'")
                    if k.node(n)['kind'] == 'verifier']:
            k.revoke(nid, 'pinned checker found unsound (illustrative revocation)', 'auditor')
        after = {c: k.levels(c)['math'] for c in opt}
        print('optimum claims after verifier revocation:', after)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        cli(['research', 'loop', str(root)])
    printed = json.loads(out.getvalue())
    print('CLI `research loop` prints: optimality_checked =', printed['optimality_checked'],
          '| task statuses', sorted({v['status'] for v in printed['tasks'].values()}))
    print('reports/world_loop.md:', (root / 'reports' / 'world_loop.md').read_text().splitlines()[2])
    stale = printed['optimality_checked'] > 0 and opt and all(v == 'UNCHECKED' for v in after.values())
    print('ATTACK_SUCCEEDED' if stale else 'ATTACK_BLOCKED (no optimum reached or summary re-derived)')


if __name__ == '__main__':
    main()
