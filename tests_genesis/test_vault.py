"""Genesis Ω contract §3, §7, §8, §16.5-16.6: the discovery vault. Exact bytes survive a restart; identical content
has one ID; tampering is detected; statuses move only along the allowed transitions and promotion needs recorded
evidence; explanation is separate; edges, queries and lineage; reactivation selects only matching dormant artifacts,
never retries unchanged, and a cascade stays bounded on cycles and fan-out; a null trigger reactivates nothing."""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from genesis import vault as V  # noqa: E402


def prog(k, parents=()):
    return V.Vault.record('ProgramSpec', {'language': 'acquire', 'source': {'agg': 'sum', 'expr': f'f{k}'}},
                          domain='causal', creator={'process': 'test'}, parents=parents)


class Vault(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.v = V.Vault(Path(self.tmp.name) / 'vault')

    def tearDown(self):
        try:
            self.v.close()
        except Exception:
            pass
        self.tmp.cleanup()

    def test_exact_bytes_identity_and_restart(self):
        a = self.v.put(prog(1))
        self.assertEqual(self.v.put(prog(1)), a)                       # one ID for identical content
        self.assertEqual(len(self.v.history(a)), 1)
        raw = self.v.raw(a)
        self.v.close()
        self.v = V.Vault(Path(self.tmp.name) / 'vault')               # restart
        self.assertEqual(self.v.raw(a), raw)
        self.assertEqual(self.v.get(a)['content']['source']['expr'], 'f1')
        self.assertEqual(self.v.verify()['artifacts'], 1)

    def test_tampering_is_detected(self):
        a = self.v.put(prog(2))
        h = self.v.store.db.execute("SELECT object_hash FROM entities WHERE kind='artifact' AND id=?",
                                    (a,)).fetchone()[0]
        path = Path(self.tmp.name) / 'vault' / 'objects' / 'sha256' / h
        path.chmod(0o600)
        path.write_bytes(path.read_bytes().replace(b'f2', b'f3'))
        with self.assertRaises(RuntimeError):
            self.v.raw(a)

    def test_transitions_and_evidence(self):
        a = self.v.put(prog(3))
        with self.assertRaises(V.VaultError):
            self.v.annotate(a, status='promoted', reason='skip')       # not from generated
        self.v.annotate(a, status='exploratory', reason='ran')
        self.v.annotate(a, status='reproducible', reason='replayed')
        with self.assertRaises(V.VaultError):
            self.v.annotate(a, status='verified', reason='no evidence')
        bad = self.v.put(V.Vault.record('EvidenceRecord', {'study': 'b20r999'}, domain='causal',
                                        creator={'process': 'test'}))
        with self.assertRaises(V.VaultError):
            self.v.annotate(a, status='verified', evidence=[bad], reason='no record test')
        ev = self.v.put(V.Vault.record('EvidenceRecord', {'study': 'b20r999', 'record_test': 'RecordB20R999'},
                                       domain='causal', creator={'process': 'test'}))
        self.v.annotate(a, status='verified', evidence=[ev], reason='recorded')
        self.v.annotate(a, explanation='conjectural', reason='a guess')
        st = self.v.status(a)
        self.assertEqual((st['status'], st['explanation']), ('verified', 'conjectural'))
        self.v.annotate(a, status='promoted', evidence=[ev], reason='scope: dev')
        with self.assertRaises(V.VaultError):
            self.v.annotate(a, status='exploratory', reason='back')
        with self.assertRaises(V.VaultError):
            self.v.put(prog(4), status='verified')
        with self.assertRaises(V.VaultError):
            self.v.annotate(a, failure='nonsense', reason='x')

    def test_edges_queries_lineage(self):
        a = self.v.put(prog(5))
        b = self.v.put(prog(6, parents=[a]))
        c = self.v.put(prog(7, parents=[b]))
        with self.assertRaises(V.VaultError):
            self.v.put(prog(8, parents=['0' * 64]))
        self.assertEqual(self.v.ancestors(c), sorted([a, b]))
        self.assertEqual(self.v.descendants(a), sorted([b, c]))
        self.v.edge('improves', b, a, confidence=0.6, scope='dev', provenance={'study': 'x'})
        self.assertEqual(len(self.v.edges(kind='improves', src=b)), 1)
        with self.assertRaises(V.VaultError):
            self.v.edge('loves', b, a, confidence=0.5, scope='dev', provenance={})
        self.assertEqual(self.v.query(type='ProgramSpec', status='generated'), sorted([a, b, c]))

    def _dormant(self, k, tag, score):
        a = self.v.put(prog(100 + k))
        self.v.annotate(a, status='exploratory', reason='tried')
        self.v.annotate(a, status='dormant', failure='missing_prerequisite', reason='limited')
        self.v.edge('failed_due_to', a, 'tag:' + tag, confidence=0.5, scope='dev', provenance={}, score=score)
        return a

    def _cap(self, name, unlocks):
        return self.v.put(V.Vault.record('CapabilityRecord', {'name': name, 'unlocks': unlocks}, domain='causal',
                                         creator={'process': 'test'}))

    def test_reactivation_selective_bounded_no_retry(self):
        hi = self._dormant(1, 'interpretation', 0.9)
        lo = self._dormant(2, 'interpretation', 0.1)
        other = self._dormant(3, 'instrument', 0.99)
        live = self.v.put(prog(4))
        self.v.edge('failed_due_to', live, 'tag:interpretation', confidence=0.5, scope='dev', provenance={})
        trig = self._cap('global interpretation', ['interpretation'])
        null = self._cap('nothing new', [])
        self.assertEqual(self.v.opportunities(null, 10), [])                 # negative control
        self.assertEqual(self.v.opportunities(trig, 10), [hi, lo])           # matching dormant only, best first
        self.assertEqual(self.v.opportunities(trig, 1), [hi])                # fuel
        self.v.reactivate(hi, trig, reason='test')
        self.assertEqual(self.v.status(hi)['status'], 'exploratory')
        self.assertEqual(self.v.opportunities(trig, 10), [lo])
        with self.assertRaises(V.VaultError):
            self.v.reactivate(hi, trig, reason='again')                      # no unchanged retry
        self.assertNotIn(other, self.v.opportunities(trig, 10))

    def test_cascade_bounded_on_cycles(self):
        for k in range(6):
            self._dormant(10 + k, 'interpretation', k / 10)
        t1 = self._cap('one', ['interpretation'])
        calls = []

        def retest(aid, trig):
            calls.append(aid)
            return [t1]                                                     # a cycle: produces the same trigger
        log = self.v.cascade([t1], retest, fuel=4, depth=5)
        self.assertEqual(len(log), 4)                                       # fuel bounds the fan-out
        self.assertEqual(len(calls), 4)                                     # the cycle does not re-run the trigger


class CLI(unittest.TestCase):
    def test_discovery_commands(self):
        import contextlib
        import io
        import json
        from genesis import cli
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / 'vault'
            with V.Vault(root) as v:
                a = v.put(prog(1))
                b = v.put(prog(2, parents=[a]))
            def call(*argv):
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    cli.main(['discovery', *argv])
                return buf.getvalue()
            out = json.loads(call('list', str(root), '--type', 'ProgramSpec'))
            self.assertEqual(sorted(x['id'] for x in out['artifacts']), sorted([a, b]))
            shown = json.loads(call('show', str(root), b, '--lineage', '--evidence'))
            self.assertEqual(shown['ancestors'], [a])
            with V.Vault(root) as v:
                raw = v.raw(b)
            buf = io.BytesIO()
            class W:
                buffer = buf
            import sys as _s
            old = _s.stdout
            _s.stdout = W()
            try:
                cli.main(['discovery', 'show', str(root), b, '--raw'])
            finally:
                _s.stdout = old
            self.assertEqual(buf.getvalue(), raw + b'\n')                      # the exact bytes
            self.assertEqual(json.loads(call('export', str(root), b, '--format', 'source'))['source'],
                             {'agg': 'sum', 'expr': 'f2'})
            self.assertEqual(json.loads(call('verify', str(root)))['artifacts'], 2)


if __name__ == '__main__':
    unittest.main()
