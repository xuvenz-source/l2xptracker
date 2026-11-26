"""Local session archive. Merges reference unique original sessions, never duplicate loot."""
import json, sqlite3, uuid
from collections import Counter
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from review import Review, ReviewQueue
from settings import settings_path


def now(): return datetime.now().isoformat(timespec='seconds')
def new_id(): return uuid.uuid4().hex
def duration(seconds):
    s=int(seconds); return f'{s//3600:02}:{s%3600//60:02}:{s%60:02}'
def rate(total, seconds): return f'{total*3600/seconds:,.0f}' if seconds>0 else '—'
def totals_for(events):
    totals=Counter()
    for ts,typ,who,item,q,sp,raw in events:
        if q is not None: totals[who,item]+=q
        if typ=='xp' and sp is not None: totals[who,'SP']+=sp
    return totals


def snapshot(app):
    return dict(start=app.session_date, end=app.session_end or now(), seconds=app.active_seconds,
                events=app.events, raw=app.raw, gaps=app.gaps,
                reviews=[asdict(r) for r in app.reviews.pending.values()],
                next_review=app.reviews.next_id, complete=app.session_complete if app.session_complete is not None else not(app.running or app.pending))


def review_queue(data):
    q=ReviewQueue(); q.pending={r['id']:Review(**r) for r in data['reviews']}; q.next_id=data['next_review']; return q


class Archive:
    def __init__(self,path=None):
        self.path=Path(path) if path is not None else settings_path().with_name('sessions.sqlite3')
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, name TEXT NOT NULL, kind TEXT NOT NULL, data TEXT NOT NULL)')
    @contextmanager
    def db(self):
        db=sqlite3.connect(self.path)
        try:
            with db: yield db
        finally: db.close()
    @staticmethod
    def _name(name):
        name=name.strip()
        if not name or len(name)>150: raise ValueError('Enter a name between 1 and 150 characters.')
        return name
    def save(self,id,name,data):
        # Updates never overwrite a name assigned in the history window.
        with self.db() as db:
            db.execute('INSERT INTO sessions VALUES (?,?,?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data WHERE sessions.kind=\'original\'',(id,self._name(name),'original',json.dumps(data)))
    def records(self):
        with self.db() as db: rows=db.execute('SELECT id,name,kind,data FROM sessions').fetchall()
        return {i:dict(id=i,name=n,kind=k,data=json.loads(d)) for i,n,k,d in rows}
    def rename(self,id,name):
        with self.db() as db:
            if not db.execute('UPDATE sessions SET name=? WHERE id=?',(self._name(name),id)).rowcount: raise ValueError('Session not found.')
    @staticmethod
    def sources(ids,records):
        out=[]
        for id in ids:
            r=records[id]
            for source in ([id] if r['kind']=='original' else r['data']['sources']):
                if source not in out: out.append(source)
        return out
    def merge(self,ids,name):
        records=self.records(); sources=self.sources(ids,records)
        if len(sources)<2: raise ValueError('Select at least two distinct original sessions.')
        id=new_id()
        with self.db() as db: db.execute('INSERT INTO sessions VALUES (?,?,?,?)',(id,self._name(name),'merged',json.dumps(dict(sources=sources))))
        return id
    def summary(self,id,records=None):
        if records is None: records=self.records()
        r=records[id]; sources=self.sources([id],records)
        parts=sorted((records[s]['data'] for s in sources),key=lambda p:p['start'])
        events=[tuple(e) for p in parts for e in p['events']]; raw=[tuple(e) for p in parts for e in p['raw']]
        return dict(**r,sources=sources,seconds=sum(p['seconds'] for p in parts),start=min(p['start'] for p in parts),end=max(p['end'] for p in parts),events=events,raw=raw,totals=totals_for(events),pending=sum(len(p['reviews']) for p in parts),gaps=sum(p['gaps'] for p in parts),complete=all(p['complete'] for p in parts))
