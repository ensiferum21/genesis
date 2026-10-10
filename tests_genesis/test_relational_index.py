"""Derived §16.4 relational index over a real campaign."""
from pathlib import Path
import sqlite3
import tempfile
import unittest

from genesis.campaign import Campaign
from genesis.cli import main as cli_main
from genesis.models import Config
from genesis.store import Store


class RelationalIndex(unittest.TestCase):
    def test_index_tables_populated_from_campaign(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / 'c'
            Campaign.initialize(root, Config(generations=1, tasks_per_panel=3, proposals_per_epoch=2, research_trials=8))
            with Campaign(root) as c:
                c.run()
            cli_main(['store', 'index', str(root)])
            db = sqlite3.connect(root / 'reports' / 'index.sqlite3')
            counts = {t: db.execute(f'SELECT count(*) FROM {t}').fetchone()[0]
                      for t in ('campaigns', 'system_versions', 'artifacts', 'events', 'tasks', 'trials', 'attempts',
                                'worlds', 'modifications', 'lineage_edges')}
            for table, n in counts.items():
                self.assertGreater(n, 0, table)
            with Store(root) as s:
                self.assertEqual(counts['attempts'], s.db.execute('SELECT count(*) FROM attempts').fetchone()[0])
                head = s.verify()['head']
            self.assertEqual(db.execute('SELECT event_head FROM index_meta').fetchone()[0], head)
            splits = {r[0] for r in db.execute('SELECT DISTINCT visibility FROM tasks')}
            self.assertEqual(splits, {'RESEARCH_VISIBLE'})
            versions = db.execute('SELECT tool_manifests, config_hash FROM system_versions').fetchall()
            self.assertTrue(all('graph-dual-predicates' in v[0] for v in versions))


if __name__ == '__main__':
    unittest.main()
