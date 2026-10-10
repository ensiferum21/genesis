"""Theorem/procedure memory with the contamination firewall (spec §35, §37.3).

Nothing enters research-visible memory without an ALLOW from the evaluator's
screener. QUARANTINE holds an item out of view until adjudicated. A later
audit that finds an admitted item exposed a sealed target revokes its evidence
node, which invalidates every dependent claim transitively.
"""
from ..common import digest, utcnow


class TheoremMemory:
    def __init__(self, store, kernel):
        self.s = store
        self.k = kernel

    def _items(self):
        return self.s.state('memory_items', {})

    def admit(self, item_id, kind, text, *, parents, screener, route, source_hash):
        decision = screener({'kind': kind, 'text': text})
        items = self._items()
        if item_id in items:
            raise ValueError('memory item ids are immutable')
        record = {'kind': kind, 'text_sha256': digest(text), 'decision': decision['decision'],
                  'scanner_version': decision['scanner_version'], 'at': utcnow()}
        if decision['decision'] == 'ALLOW':
            node = self.k.record('memory_item', {'kind': kind, 'text': text}, parents=parents, route=route,
                                 source_hash=source_hash, verdict='ADMITTED')
            record.update(node=node, visible=True)
        else:
            record.update(node=None, visible=False)
        items[item_id] = record
        self.s.set_state('memory_items', items)
        self.s.event('MEMORY_SCREENED', {'item': item_id, **{k: v for k, v in record.items() if k != 'text'}})
        return record

    def visible(self):
        return {k: v for k, v in self._items().items() if v['visible']}

    def audit(self, screener, texts, *, auditor):
        """Re-screen admitted items against a (possibly newer) sealed index.

        `texts` maps item id -> text (memory stores only hashes in state). Exposed
        items are hidden and their evidence nodes revoked.
        """
        items = self._items()
        revoked = []
        for item_id, record in items.items():
            if not record['visible']:
                continue
            if digest(texts[item_id]) != record['text_sha256']:
                raise ValueError(f'audit text for {item_id} does not match the admitted item')
            decision = screener({'kind': record['kind'], 'text': texts[item_id]})
            if decision['decision'] != 'ALLOW':
                self.k.revoke(record['node'], f'leak audit ({decision["decision"]}) by {auditor}', auditor)
                record.update(visible=False, revoked_at=utcnow(), audit_decision=decision['decision'])
                revoked.append(item_id)
        self.s.set_state('memory_items', items)
        return revoked
