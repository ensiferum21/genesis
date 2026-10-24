"""`genesis discovery ...`: deterministic, structured retrieval of vault artifacts (Genesis Ω contract §9, §18).

    genesis discovery list ROOT [--type T] [--status S] [--failure F] [--domain D]
    genesis discovery show ROOT ID [--raw] [--lineage] [--evidence]
    genesis discovery export ROOT ID [--format json|source]
    genesis discovery replay ROOT ID        recompute the artifact's recorded behaviour (registered replayers only)
    genesis discovery verify ROOT

Reports are built from stored data only (no generated prose). `--raw` prints the exact stored bytes of the artifact.
"""
import json
import sys

from .vault import Vault


def run(args):
    with Vault(args.root) as v:
        if args.action == 'verify':
            return v.verify()
        if args.action == 'list':
            ids = v.query(type=args.type, status=args.status, domain=args.domain, failure=args.failure)
            out = []
            for a in ids:
                rec, st = v.get(a), v.status(a)
                out.append({'id': a, 'type': rec['type'], 'domain': rec['domain'], **st})
            return {'artifacts': out}
        if args.id is None:
            raise SystemExit(f'discovery {args.action} needs an ID')
        if args.action == 'show':
            if args.raw:
                sys.stdout.buffer.write(v.raw(args.id) + b'\n')
                return None
            out = {'id': args.id, 'record': v.get(args.id), 'status': v.status(args.id),
                   'history': v.history(args.id)}
            if args.lineage:
                out['ancestors'], out['descendants'] = v.ancestors(args.id), v.descendants(args.id)
            if args.evidence:
                out['edges_out'] = v.edges(src=args.id)
                out['edges_in'] = v.edges(dst=args.id)
            return out
        if args.action == 'replay':
            from .replayers import replay
            return {'id': args.id, **replay(v.get(args.id))}
        if args.action == 'export':
            rec = v.get(args.id)
            if args.format == 'source':
                return {'id': args.id, 'source': rec['content'].get('source', rec['content'])}
            return {'id': args.id, 'raw': v.raw(args.id).decode(), 'status': v.status(args.id),
                    'history': v.history(args.id)}
    raise SystemExit(f'unknown action {args.action}')


def add_parser(subs):
    from pathlib import Path
    p = subs.add_parser('discovery')
    p.add_argument('action', choices=['list', 'show', 'export', 'replay', 'verify'])
    p.add_argument('root', type=Path)
    p.add_argument('id', nargs='?', default=None)
    p.add_argument('--type', default=None)
    p.add_argument('--status', default=None)
    p.add_argument('--failure', default=None)
    p.add_argument('--domain', default=None)
    p.add_argument('--raw', action='store_true')
    p.add_argument('--lineage', action='store_true')
    p.add_argument('--evidence', action='store_true')
    p.add_argument('--format', choices=['json', 'source'], default='json')


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(prog='genesis')
    add_parser(ap.add_subparsers(dest='command', required=True))
    out = run(ap.parse_args(argv))
    if out is not None:
        print(json.dumps(out, indent=2, sort_keys=True))
