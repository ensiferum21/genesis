#!/usr/bin/env python3
"""H08 audit: run the lineage validator on the stored three-generation DEV campaign export.

    python3 audit/lineage_b20r/audit_campaign_lineage.py

Reads evidence/v2-public-campaign.zip only (no execution) and writes report.json here: the
problems the validator finds and what each means for counting generations (B14-OPEN-3).
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))

from genesis import lineage as LN  # noqa: E402

MEANING = {
    'SELECTION_UNVERIFIABLE': 'the campaign chose the child by SELECT totals that the export does not contain',
    'LEDGER_INCOMPLETE': 'research candidates are not bound to attempts in the journal',
    'BUDGET_UNACCOUNTED': 'no per-run resource account is exported',
    'DECLARED_CHANGES_MISMATCH': 'the modification record names a component that differs from the actual version diff',
}


def main():
    ex = LN.export_from_campaign_zip(ROOT / 'evidence' / 'v2-public-campaign.zip')
    problems = LN.lineage_problems(ex)
    chain = LN.accepted_chain(ex)
    by = {}
    for p in problems:
        by.setdefault(p['code'], []).append(p)
    diffs = []
    for t in ex['transitions']:
        a, b = ex['versions'].get(t['from_version'], {}), ex['versions'].get(t['to_version'], {})
        diffs.append({'index': t['index'], 'decision_mapped_from_dev_retention': t['decision'],
                      'actual_changes': LN.substantive(LN.version_diff(a, b)), 'declared': t['declared_changes']})
    report = {'schema': 'genesis-lineage-audit-v1', 'export': 'evidence/v2-public-campaign.zip',
              'versions': len(ex['versions']), 'transitions': len(ex['transitions']),
              'problem_counts': {k: len(v) for k, v in sorted(by.items())},
              'meaning': {k: MEANING.get(k, '') for k in sorted(by)}, 'changes': diffs,
              'qualifying_chain_length': len(chain['transitions']),
              'conclusion': 'today\'s campaign export cannot support counting generations: the custodian must keep '
                            'refusing sealed_generation_evaluation until the export carries selection scores, '
                            'attempt-bound candidates and per-run accounts (B14-OPEN-3)'}
    (Path(__file__).with_name('report.json')).write_text(json.dumps(report, indent=1, sort_keys=True) + '\n')
    print(json.dumps({k: report[k] for k in ('problem_counts', 'changes', 'qualifying_chain_length')}, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
