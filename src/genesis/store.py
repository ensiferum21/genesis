"""Single-writer SQLite journal, immutable CAS and recoverable append-only export.

Local hash integrity is not independent custody. The owning OS account remains trusted.
"""
import fcntl
import json
import os
from pathlib import Path
import sqlite3
import uuid
from .common import canonical, bytes_hash, utcnow


class Store:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = (self.root/'writer.lock').open('a+b')
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            self.lock.close()
            raise RuntimeError('campaign already has a writer')
        for name in ('objects/sha256','work','snapshots','reports','exports'):
            (self.root/name).mkdir(parents=True,exist_ok=True)
        self._export_seq = None; self._export_size = None
        if (self.root/'campaign.sqlite3-wal').exists() or (self.root/'campaign.sqlite3-shm').exists():
            # This store never uses WAL. Sidecars mean a legacy or interrupted
            # state; opening would let SQLite rewrite them and destroy evidence.
            self.lock.close()
            raise RuntimeError('WAL sidecar present; inspect it, then run `genesis store rebuild` '
                               '(rebuilds from events.jsonl and quarantines the database files)')
        self.db = sqlite3.connect(self.root/'campaign.sqlite3', isolation_level=None)
        self.db.execute('PRAGMA foreign_keys=ON')
        # A campaign has exactly one writer. Rollback journaling keeps durable
        # state in one database instead of depending on a WAL/SHM file set when
        # the workspace is checkpointed or transferred by the hosting runtime.
        self.db.execute('PRAGMA journal_mode=DELETE')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.executescript(SCHEMA)
        try:
            self.verify()
            self.recover_export()
        except BaseException:
            self.close()
            raise

    def close(self):
        self.db.close()
        fcntl.flock(self.lock, fcntl.LOCK_UN)
        self.lock.close()

    def __enter__(self): return self
    def __exit__(self,*args): self.close()

    def put_bytes(self, data):
        h = bytes_hash(data)
        path = self.root/'objects/sha256'/h
        if path.exists():
            if path.is_symlink() or path.read_bytes()!=data:
                raise RuntimeError('content-addressed object corruption')
            return h
        fd = os.open(path, os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o400)
        with os.fdopen(fd,'wb') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        return h

    def put(self, value): return self.put_bytes(canonical(value))

    def get_bytes(self,h):
        if len(h)!=64 or any(c not in '0123456789abcdef' for c in h):
            raise ValueError('invalid object identity')
        p=self.root/'objects/sha256'/h
        if p.is_symlink(): raise RuntimeError('object symlink')
        data=p.read_bytes()
        if bytes_hash(data)!=h: raise RuntimeError('object corruption')
        return data

    def get(self,h): return json.loads(self.get_bytes(h))

    def _event(self,kind,payload):
        ph=self.put(payload)
        last=self.db.execute('SELECT seq,hash FROM events ORDER BY seq DESC LIMIT 1').fetchone()
        body={'seq':last[0]+1 if last else 1,'timestamp':utcnow(),'kind':kind,
              'payload':ph,'prev_hash':last[1] if last else None}
        raw=canonical(body); h=bytes_hash(raw)
        self.db.execute('INSERT INTO events VALUES (?,?,?)',(body['seq'],h,raw))
        return h

    def event(self,kind,payload):
        with self.transaction(): h=self._event(kind,payload)
        return h

    def transaction(self):
        from contextlib import contextmanager
        @contextmanager
        def tx():
            self.db.execute('BEGIN IMMEDIATE')
            try:
                yield
                self.db.execute('COMMIT')
            except BaseException:
                self.db.execute('ROLLBACK'); raise
            self.recover_export()
        return tx()

    def save(self,kind,key,value):
        h=self.put(value)
        with self.transaction():
            existing=self.db.execute('SELECT object_hash FROM entities WHERE kind=? AND id=?',(kind,key)).fetchone()
            if existing and existing[0]!=h: raise ValueError('immutable entity identity reused')
            self.db.execute('INSERT OR IGNORE INTO entities VALUES (?,?,?)',(kind,key,h))
            self._event('ENTITY_COMMITTED',{'kind':kind,'id':key,'object_hash':h})
        return h

    def start(self,trial_id,request):
        aid=str(uuid.uuid4()); h=self.put(request)
        with self.transaction():
            self.db.execute('INSERT INTO attempts VALUES (?,?,?,?,NULL)',(aid,trial_id,'RUNNING',h))
            self._event('ATTEMPT_STARTED',{'attempt_id':aid,'trial_id':trial_id,'request':h})
        return aid

    def finish(self,aid,receipt):
        h=self.put(receipt)
        with self.transaction():
            row=self.db.execute('SELECT status FROM attempts WHERE id=?',(aid,)).fetchone()
            if not row or row[0]!='RUNNING': raise ValueError('attempt not running')
            self.db.execute('UPDATE attempts SET status=?,receipt=? WHERE id=?',(receipt['status'],h,aid))
            self._event('ATTEMPT_FINISHED',{'attempt_id':aid,'receipt':h})
        return h

    def interrupt_running(self):
        ids=[r[0] for r in self.db.execute("SELECT id FROM attempts WHERE status='RUNNING'")]
        for aid in ids:
            self.finish(aid,{'status':'INTERRUPTED','reason':'coordinator restart; no terminal receipt',
                             'cost_unknown':True,'automatic_retry':False})
        return ids

    def state(self,key,default=None):
        row=self.db.execute('SELECT value FROM state WHERE key=?',(key,)).fetchone()
        return json.loads(row[0]) if row else default

    def set_state(self,key,value):
        with self.transaction():
            self.db.execute('INSERT OR REPLACE INTO state VALUES (?,?)',(key,canonical(value)))
            self._event('STATE_UPDATED',{'key':key,'value':value})

    def recover_export(self, full=False):
        """Keep events.jsonl an exact, append-only rendering of the event table.

        On open (or if the file size differs from what this writer last wrote)
        the whole file is checked to be a prefix of the journal; otherwise only
        new events are appended. History is never truncated or rewritten.
        """
        path=self.root/'events.jsonl'
        if not full and self._export_seq is not None:
            size=path.stat().st_size if path.exists() else 0
            if size==self._export_size:
                rows=self.db.execute('SELECT seq,hash,body FROM events WHERE seq>? ORDER BY seq',
                                     (self._export_seq,)).fetchall()
                if rows:
                    data=b''.join(canonical({'hash':h,'event':json.loads(b)})+b'\n' for _,h,b in rows)
                    with path.open('ab') as f:
                        f.write(data); f.flush(); os.fsync(f.fileno())
                    self._export_seq=rows[-1][0]; self._export_size=size+len(data)
                return
        rows=self.db.execute('SELECT seq,hash,body FROM events ORDER BY seq').fetchall()
        lines=[canonical({'hash':h,'event':json.loads(b)})+b'\n' for _,h,b in rows]
        existing=path.read_bytes() if path.exists() else b''
        wanted=b''.join(lines)
        if not wanted.startswith(existing): raise RuntimeError('event export corruption')
        if len(existing)<len(wanted):
            # Append even a partially written final line; never truncate or rewrite history.
            with path.open('ab') as f:
                f.write(wanted[len(existing):]); f.flush(); os.fsync(f.fileno())
        self._export_seq=rows[-1][0] if rows else 0; self._export_size=len(wanted)

    def verify(self):
        if self.db.execute('PRAGMA quick_check').fetchall()!=[('ok',)]:
            raise RuntimeError('SQLite structural integrity failure')
        rows=self.db.execute('SELECT seq,hash,body FROM events ORDER BY seq').fetchall()
        count,prev,derived_state,derived_entities,derived_attempts=derive(rows,self.get)
        for (h,) in self.db.execute('SELECT object_hash FROM entities'):
            self.get_bytes(h)
        for req,receipt in self.db.execute('SELECT request,receipt FROM attempts'):
            self.get_bytes(req)
            if receipt:self.get_bytes(receipt)
        actual_state={k:json.loads(v) for k,v in self.db.execute('SELECT key,value FROM state')}
        actual_entities={(k,i):h for k,i,h in self.db.execute('SELECT kind,id,object_hash FROM entities')}
        actual_attempts={aid:(t,status,req,receipt) for aid,t,status,req,receipt in self.db.execute('SELECT * FROM attempts')}
        if actual_state!=derived_state or actual_entities!=derived_entities or actual_attempts!=derived_attempts:
            raise RuntimeError('derived SQLite state differs from immutable event history')
        self.recover_export(full=True)
        return {'events':count,'head':prev,'integrity':'LOCAL_HASH_CHECKED'}

    def snapshot(self,name):
        path=self.root/'snapshots'/name
        if path.exists(): raise FileExistsError(path)
        dest=sqlite3.connect(path)
        try:
            self.db.backup(dest)
            if dest.execute('PRAGMA integrity_check').fetchall()!=[('ok',)]:
                raise RuntimeError('snapshot structural integrity failure')
        finally:dest.close()
        return path


def derive(rows,get):
    """Check the hash chain and derive state/entities/attempts from (seq, hash, body) rows."""
    prev=None; count=0; derived_state={};derived_entities={};derived_attempts={}
    for seq,h,raw in rows:
        body=json.loads(raw); count+=1
        if seq!=count or body['seq']!=seq or body['prev_hash']!=prev or bytes_hash(raw)!=h:
            raise RuntimeError('journal corruption')
        payload=get(body['payload']);prev=h
        if body['kind']=='STATE_UPDATED':derived_state[payload['key']]=payload['value']
        elif body['kind']=='ENTITY_COMMITTED':
            key=(payload['kind'],payload['id']);value=payload['object_hash']
            if key in derived_entities and derived_entities[key]!=value:raise RuntimeError('conflicting entity history')
            derived_entities[key]=value
        elif body['kind']=='ATTEMPT_STARTED':
            aid=payload['attempt_id']
            if aid in derived_attempts:raise RuntimeError('duplicate attempt start')
            derived_attempts[aid]=(payload['trial_id'],'RUNNING',payload['request'],None)
        elif body['kind']=='ATTEMPT_FINISHED':
            aid=payload['attempt_id'];receipt=payload['receipt']
            if aid not in derived_attempts or derived_attempts[aid][1]!='RUNNING':raise RuntimeError('invalid attempt history')
            trial,_,request,_=derived_attempts[aid]
            derived_attempts[aid]=(trial,get(receipt)['status'],request,receipt)
    return count,prev,derived_state,derived_entities,derived_attempts


SCHEMA='''
CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY, hash TEXT UNIQUE NOT NULL, body BLOB NOT NULL);
CREATE TABLE IF NOT EXISTS attempts(id TEXT PRIMARY KEY, trial_id TEXT NOT NULL, status TEXT NOT NULL,
                                   request TEXT NOT NULL, receipt TEXT);
CREATE TABLE IF NOT EXISTS entities(kind TEXT NOT NULL, id TEXT NOT NULL, object_hash TEXT NOT NULL,
                                  PRIMARY KEY(kind,id));
CREATE TABLE IF NOT EXISTS state(key TEXT PRIMARY KEY, value BLOB NOT NULL);
'''


def rebuild_from_export(root):
    """Recover a campaign database from its append-only events.jsonl and CAS (spec §33.2).

    Every exported line is re-hashed and chained; every referenced object must be
    present and hash-correct. A partially written final line is dropped and
    reported. The unreadable database files are moved, never deleted, to
    quarantine/<UTC time>/ for forensic inspection. Returns a recovery record.
    """
    root=Path(root).resolve()
    export=root/'events.jsonl'
    if not export.is_file():raise FileNotFoundError('no event export to rebuild from')
    lock=(root/'writer.lock').open('a+b')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
        lock.close();raise RuntimeError('campaign has an active writer; refusing to rebuild')
    try:return _rebuild_locked(root,export)
    finally:
        fcntl.flock(lock,fcntl.LOCK_UN);lock.close()


def _rebuild_locked(root,export):
    def get(h):
        p=root/'objects/sha256'/h
        if p.is_symlink():raise RuntimeError('object symlink')
        data=p.read_bytes()
        if bytes_hash(data)!=h:raise RuntimeError('object corruption')
        return json.loads(data)
    raw_lines=export.read_bytes().split(b'\n')
    partial=raw_lines[-1]!=b''
    rows=[]
    for line in raw_lines[:-1]:
        record=json.loads(line)
        if set(record)!={'hash','event'}:raise RuntimeError('event export schema')
        body=canonical(record['event'])
        rows.append((record['event']['seq'],record['hash'],body))
    count,head,derived_state,derived_entities,derived_attempts=derive(rows,get)
    for h in derived_entities.values():get(h)
    for _,_,request,receipt in derived_attempts.values():
        get(request)
        if receipt:get(receipt)
    stamp=utcnow().replace(':','').replace('+','Z')
    quarantine=root/'quarantine'/stamp
    moved=[]
    for name in ('campaign.sqlite3','campaign.sqlite3-wal','campaign.sqlite3-shm','campaign.sqlite3-journal'):
        if (root/name).exists():
            quarantine.mkdir(parents=True,exist_ok=True)
            os.replace(root/name,quarantine/name);moved.append(name)
    db=sqlite3.connect(root/'campaign.sqlite3',isolation_level=None)
    try:
        db.execute('PRAGMA journal_mode=DELETE');db.execute('PRAGMA synchronous=FULL')
        db.executescript(SCHEMA)
        db.execute('BEGIN IMMEDIATE')
        db.executemany('INSERT INTO events VALUES (?,?,?)',rows)
        db.executemany('INSERT INTO entities VALUES (?,?,?)',[(k,i,h) for (k,i),h in derived_entities.items()])
        db.executemany('INSERT INTO attempts VALUES (?,?,?,?,?)',[(a,*v) for a,v in derived_attempts.items()])
        db.executemany('INSERT INTO state VALUES (?,?)',[(k,canonical(v)) for k,v in derived_state.items()])
        db.execute('COMMIT')
    finally:db.close()
    if partial:
        # Keep history append-only: the dropped fragment is preserved beside the quarantine.
        quarantine.mkdir(parents=True,exist_ok=True)
        (quarantine/'events.jsonl.partial-tail').write_bytes(raw_lines[-1])
        full=b''.join(line+b'\n' for line in raw_lines[:-1])
        os.replace(export,quarantine/'events.jsonl.before-rebuild')
        export.write_bytes(full)
    return {'events':count,'head':head,'quarantined':moved,'partial_tail_dropped':partial,
            'quarantine':str(quarantine) if moved or partial else None}
