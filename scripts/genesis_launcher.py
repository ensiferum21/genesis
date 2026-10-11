#!/usr/bin/env python3
"""Run the privileged sandbox launcher (root only). See genesis/launcher.py and deployment/DEPLOYMENT.md.

  genesis_launcher.py serve --config /etc/genesis/launcher.json
  genesis_launcher.py verify-log --config /etc/genesis/launcher.json [--anchors anchors.json]
  genesis_launcher.py roles --worker-uid UID --socket S --log L --trust-root T [--secret P ...] [--evidence E ...]
"""
import argparse
import json
from pathlib import Path
import signal
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis.launcher import Launcher, LauncherConfig, role_separation_report, verify_log  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('serve'); s.add_argument('--config', type=Path, required=True)
    v = sub.add_parser('verify-log'); v.add_argument('--config', type=Path, required=True)
    v.add_argument('--anchors', type=Path, help='JSON list of [log_seq, log_head] pairs taken from worker receipts')
    r = sub.add_parser('roles'); r.add_argument('--worker-uid', type=int, required=True)
    r.add_argument('--socket'); r.add_argument('--log'); r.add_argument('--trust-root')
    r.add_argument('--secret', action='append', default=[]); r.add_argument('--evidence', action='append', default=[])
    a = ap.parse_args(argv)
    if a.cmd == 'roles':
        report = role_separation_report(worker_uid=a.worker_uid, socket_path=a.socket, log_path=a.log,
                                        secret_paths=a.secret, trust_root=a.trust_root, evidence_roots=a.evidence)
        print(json.dumps(report, indent=1))
        return 0 if report['ok'] else 1
    config = LauncherConfig.model_validate_json(a.config.read_bytes())
    if a.cmd == 'verify-log':
        anchors = json.loads(a.anchors.read_text()) if a.anchors else ()
        head, n = verify_log(config.log_path, anchors=anchors)
        print(json.dumps({'ok': True, 'entries': n, 'head': head}))
        return 0
    launcher = Launcher(config)
    signal.signal(signal.SIGTERM, lambda *_: launcher.stop())
    print(json.dumps({'serving': config.socket_path, 'worker_uid': config.worker_uid}), flush=True)
    try:
        launcher.serve_forever()
    except KeyboardInterrupt:
        launcher.stop()
    return 0


if __name__ == '__main__':
    sys.exit(main())
