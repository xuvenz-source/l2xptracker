"""Local session archive. Merges reference unique original sessions, never duplicate loot."""
import json, sqlite3, uuid
from collections import Counter
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from review import Review, ReviewQueue
from settings import settings_path
from party import report as party_report
from consumable_costs import cost_report, clean_prices
from loot_values import loot_report


def now(): return datetime.now().isoformat(timespec='seconds')
def new_id(): return uuid.uuid4().hex
def duration(seconds):
    s=int(seconds); return f'{s//3600:02}:{s%3600//60:02}:{s%60:02}'
def rate(total, seconds): return f'{total*3600/seconds:,.0f}' if seconds>0 else '—'
def totals_for(events):
    totals=Counter()
    for ts,typ,who,item,q,sp,raw in events:
        if q is not None and typ!='consumable': totals[who,item]+=q
        if typ=='xp' and sp is not None: totals[who,'SP']+=sp
    return totals


def consumables_for(events):
    totals=Counter()
    for _,typ,_,item,q,_,_ in events:
        if typ=='consumable' and q is not None:totals[item]+=q
    return totals


def count_kills(events):
    """One recorded personal XP event equals one estimated kill, even if partial."""
    return sum(1 for _,typ,who,_,xp,sp,_ in events
               if typ=='xp' and who.casefold()=='you' and (xp is not None or sp is not None))


def snapshot(app):
    return dict(start=app.session_date, end=app.session_end or now(), seconds=app.active_seconds,
                events=app.events, raw=app.raw, gaps=app.gaps, party_members=list(getattr(app,'party_members',[])),
                consumable_prices=clean_prices(getattr(app,'session_prices',{})),
                loot_prices=clean_prices(getattr(app,'session_loot_prices',{})),
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
            db.execute("CREATE TABLE IF NOT EXISTS folders (id TEXT PRIMARY KEY, name TEXT NOT NULL, parent TEXT NOT NULL DEFAULT '')")
            db.execute("CREATE TABLE IF NOT EXISTS folder_placements (id TEXT PRIMARY KEY, folder TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS history_preferences (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
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
            db.execute('BEGIN IMMEDIATE')
            exists=db.execute('SELECT 1 FROM sessions WHERE id=?',(id,)).fetchone()
            db.execute('INSERT INTO sessions VALUES (?,?,?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data WHERE sessions.kind=\'original\'',(id,self._name(name),'original',json.dumps(data)))
            if not exists:
                folder=self._default_folder(db)
                if folder:db.execute('INSERT INTO folder_placements VALUES (?,?)',(id,folder))
    def records(self):
        with self.db() as db: rows=db.execute('SELECT id,name,kind,data FROM sessions').fetchall()
        return {i:dict(id=i,name=n,kind=k,data=json.loads(d)) for i,n,k,d in rows}
    @staticmethod
    def _organised(db):
        records={i:dict(id=i,name=n,kind=k,data=json.loads(d)) for i,n,k,d in db.execute('SELECT id,name,kind,data FROM sessions')}
        for i,n,p in db.execute('SELECT id,name,parent FROM folders'):
            records[i]=dict(id=i,name=n,kind='folder',data={},folder=p)
        for i,p in db.execute('SELECT id,folder FROM folder_placements'):
            if i in records and records[i]['kind']!='folder':records[i]['folder']=p
        return records
    def organised_records(self):
        with self.db() as db:return self._organised(db)
    @staticmethod
    def _default_folder(db):
        row=db.execute("SELECT value FROM history_preferences WHERE key='destination'").fetchone()
        return row[0] if row and db.execute('SELECT 1 FROM folders WHERE id=?',(row[0],)).fetchone() else ''
    def default_folder(self):
        with self.db() as db:return self._default_folder(db)
    def set_default_folder(self,folder):
        with self.db() as db:
            if folder and not db.execute('SELECT 1 FROM folders WHERE id=?',(folder,)).fetchone():raise ValueError('Folder no longer exists.')
            db.execute("INSERT INTO history_preferences VALUES ('destination',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(folder,))
    def create_folder(self,name,parent=''):
        i=new_id()
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            if parent and not db.execute('SELECT 1 FROM folders WHERE id=?',(parent,)).fetchone():raise ValueError('Parent folder no longer exists.')
            db.execute('INSERT INTO folders VALUES (?,?,?)',(i,self._name(name),parent))
        return i
    def move_entries(self,ids,folder=''):
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            records=self._organised(db)
            for i in folder_move_plan(records,ids,folder):
                if records[i]['kind']=='folder':db.execute('UPDATE folders SET parent=? WHERE id=?',(folder,i))
                else:db.execute('INSERT INTO folder_placements VALUES (?,?) ON CONFLICT(id) DO UPDATE SET folder=excluded.folder',(i,folder))
    def delete_entries(self,ids,protected=()):
        """Remove selected records atomically. Folder deletion promotes contents."""
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            records=self._organised(db)
            removed,updates,moves=deletion_plan(records,ids,protected)
            destination=self._default_folder(db)
            if destination in removed:
                parent=records[destination].get('folder','')
                while parent in removed:parent=records[parent].get('folder','')
                db.execute("UPDATE history_preferences SET value=? WHERE key='destination'",(parent,))
            for i,folder in moves.items():
                if records[i]['kind']=='folder':db.execute('UPDATE folders SET parent=? WHERE id=?',(folder,i))
                else:db.execute('INSERT INTO folder_placements VALUES (?,?) ON CONFLICT(id) DO UPDATE SET folder=excluded.folder',(i,folder))
            for i,data in updates.items():db.execute('UPDATE sessions SET data=? WHERE id=?',(json.dumps(data),i))
            for i in removed:
                db.execute('DELETE FROM folders WHERE id=?',(i,))
                db.execute('DELETE FROM sessions WHERE id=?',(i,))
                db.execute('DELETE FROM folder_placements WHERE id=?',(i,))
        return removed
    def rename(self,id,name):
        name=self._name(name)
        with self.db() as db:
            if not db.execute('UPDATE sessions SET name=? WHERE id=?',(name,id)).rowcount and not db.execute('UPDATE folders SET name=? WHERE id=?',(name,id)).rowcount:raise ValueError('Entry not found.')
    @staticmethod
    def sources(ids,records):
        out=[]
        for id in ids:
            if id not in records:raise ValueError('Entry no longer exists.')
            r=records[id]
            if r['kind']=='folder':raise ValueError('Folders organise sessions; select sessions or merged reports to merge.')
            for source in ([id] if r['kind']=='original' else r['data']['sources']):
                if source not in out: out.append(source)
        return out
    def merge(self,ids,name):
        records=self.organised_records(); ids=list(dict.fromkeys(ids)); sources=self.sources(ids,records)
        if len(sources)<2: raise ValueError('Select at least two distinct original sessions.')
        # Keep the selected report hierarchy separately from the immutable,
        # deduplicated original source list used for all calculations.
        covered={s for i in ids if records[i]['kind']=='merged' for s in self.sources([i],records)}
        children=[i for i in ids if records[i]['kind']=='merged' or i not in covered]
        id=new_id()
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('INSERT INTO sessions VALUES (?,?,?,?)',(id,self._name(name),'merged',json.dumps(dict(sources=sources,children=children))))
            # Place a merged report beside its selected inputs when they share
            # a folder, without changing their actual folder assignments.
            organised=self._organised(db)
            locations={organised[i].get('folder','') for i in ids}
            if len(locations)==1:
                folder=next(iter(locations))
                if folder:db.execute('INSERT INTO folder_placements VALUES (?,?)',(id,folder))
        return id
    def add_to_group(self,target,ids):
        """Add references to a group, atomically updating all ancestor totals."""
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            records={i:dict(id=i,name=n,kind=k,data=json.loads(d)) for i,n,k,d in db.execute('SELECT id,name,kind,data FROM sessions')}
            plan=group_drop_plan(records,target,ids)
            for i,data in plan.items():
                db.execute("UPDATE sessions SET data=? WHERE id=? AND kind='merged'",(json.dumps(data),i))
        return bool(plan)
    def summary(self,id,records=None):
        if records is None: records=self.records()
        r=records[id]; sources=self.sources([id],records)
        parts=sorted((records[s]['data'] for s in sources),key=lambda p:p['start'])
        events=[tuple(e) for p in parts for e in p['events']]; raw=[tuple(e) for p in parts for e in p['raw']]
        return dict(**r,sources=sources,seconds=sum(p['seconds'] for p in parts),start=min(p['start'] for p in parts),end=max(p['end'] for p in parts),events=events,raw=raw,totals=totals_for(events),kills=count_kills(events),consumable_report=cost_report(parts),loot_report=loot_report(parts),party=party_report(parts),pending=sum(len(p['reviews']) for p in parts),gaps=sum(p['gaps'] for p in parts),complete=all(p['complete'] for p in parts))


def history_children(records):
    """Display-only hierarchy. Legacy reports have original sessions as children.

    Shared originals or reports may appear in more than one parent; the archive
    retains a single record and all calculations still use unique sources.
    """
    children={}
    for i,r in records.items():
        if r['kind']!='merged':continue
        sources=set(r['data']['sources'])
        valid=[]
        # Only accept children actually represented in this report's totals.
        for child in r['data'].get('children',r['data']['sources']):
            if child==i or child not in records or child in valid or records[child]['kind']=='folder':continue
            child_sources=set(Archive.sources([child],records))
            if child_sources and child_sources<=sources:valid.append(child)
        represented={s for child in valid for s in Archive.sources([child],records)}
        valid.extend(s for s in r['data']['sources'] if s not in represented and s in records)
        children[i]=valid
    return children

def history_forest(records,summaries):
    """Return stable paths in display order, with cycles guarded defensively."""
    children=history_children(records)
    attached={i for group in children.values() for i in group}
    for i,r in records.items():
        parent=r.get('folder','')
        if parent in records and records[parent]['kind']=='folder' and parent!=i:
            children.setdefault(parent,[]).append(i);attached.add(i)
    def ordered(ids):
        folders=sorted((i for i in ids if records[i]['kind']=='folder'),key=lambda i:(records[i]['name'].casefold(),i))
        sessions=sorted((i for i in ids if records[i]['kind']!='folder'),key=lambda i:(summaries[i]['start'],i),reverse=True)
        return folders+sessions
    reached=set()
    def walk(i,path):
        if i in path:return
        current=(*path,i);reached.add(i)
        yield current
        for child in ordered(children.get(i,[])):
            yield from walk(child,current)
    roots=(set(records)-attached)|{i for i,r in records.items() if r.get('folder',None)==''}
    for i in ordered(roots):
        yield from walk(i,())
    # Corrupt/cyclic legacy metadata must not make records disappear.
    for i in ordered(records):
        if i not in reached:yield from walk(i,())


def group_drop_plan(records,target,ids):
    """Pure planning step; no modifications to the supplied records."""
    if target not in records or records[target]['kind']!='merged':
        raise ValueError('Drop onto an existing group.')
    ids=list(dict.fromkeys(ids))
    if any(i not in records for i in ids):raise ValueError('Session no longer exists.')
    children=history_children(records)
    def descendants(i):
        seen=set();pending=[i]
        while pending:
            j=pending.pop()
            if j in seen:continue
            seen.add(j);pending.extend(children.get(j,[]))
        return seen
    if any(target in descendants(i) for i in ids):
        raise ValueError('Cannot drop a group onto itself or one of its descendants.')
    before=set(Archive.sources([target],records))
    added=[i for i in ids if not set(Archive.sources([i],records))<=before]
    if not added:return {}
    # Avoid redundant direct original links when a dragged group covers them.
    covered={s for i in added if records[i]['kind']=='merged' for s in Archive.sources([i],records)}
    added=[i for i in added if records[i]['kind']=='merged' or i not in covered]
    links=list(dict.fromkeys(children[target]+added))
    updated=dict(records[target]['data'],children=links,sources=Archive.sources([target,*added],records))
    plan={target:updated}
    # Propagate new unique sources to every ancestor, including shared groups.
    # Iterate to a fixed point, keeping each ancestor's old sources intact.
    while True:
        changed=False
        for i,links in children.items():
            if i==target:continue
            if not any(c in plan for c in links):continue
            current=plan.get(i,records[i]['data'])
            sources=list(current['sources'])
            for c in links:
                for source in (plan[c]['sources'] if c in plan else Archive.sources([c],records)):
                    if source not in sources:sources.append(source)
            if sources!=current['sources']:
                plan[i]=dict(current,children=links,sources=sources);changed=True
        if not changed:break
    return plan


def folder_move_plan(records,ids,folder):
    ids=list(dict.fromkeys(ids))
    if folder and (folder not in records or records[folder]['kind']!='folder'):raise ValueError('Choose a folder or the history root.')
    if any(i not in records for i in ids):raise ValueError('Entry no longer exists.')
    ancestors=set();p=folder
    while p:
        if p in ancestors:raise ValueError('Invalid folder hierarchy.')
        ancestors.add(p);p=records.get(p,{}).get('folder','')
    if any(i in ancestors for i in ids):raise ValueError('Cannot move a folder into itself or a descendant.')
    # When both a folder and its child are selected, move the folder only.
    selected=set(ids)
    def nested(i):
        seen=set();p=records[i].get('folder','')
        while p and p not in seen:
            if p in selected:return True
            seen.add(p);p=records.get(p,{}).get('folder','')
        return False
    return [i for i in ids if not nested(i)]

def deletion_plan(records,ids,protected=()):
    removed=set(ids)
    if not removed<=records.keys():raise ValueError('Entry no longer exists.')
    if removed.intersection(protected):raise ValueError('Stop the active session before deleting it.')
    # Remove deleted original references in every report. A group with
    # surviving sources remains useful, even if reduced to a single source.
    originals={i for i in removed if records[i]['kind']=='original'}
    for i,r in records.items():
        if r['kind']=='merged' and not any(s not in originals and s in records for s in r['data']['sources']):removed.add(i)
    updates={};moves={}
    for i,r in records.items():
        if i in removed:continue
        if r['kind']=='merged':
            data=r['data'];sources=[s for s in data['sources'] if s not in removed and s in records]
            children=[c for c in data.get('children',data['sources']) if c not in removed and c in records]
            if sources!=data['sources'] or children!=data.get('children',data['sources']):
                updates[i]=dict(data,sources=sources,children=children)
        parent=r.get('folder','')
        if parent in removed:
            seen=set()
            while parent in removed and parent not in seen:
                seen.add(parent);parent=records[parent].get('folder','')
            moves[i]=parent if parent not in seen else ''
    return removed,updates,moves

def folder_options(records):
    """Stable, readable paths for the destination picker, including root."""
    out=[('','History root')]
    def walk(parent,path,seen):
        ids=sorted((i for i,r in records.items() if r['kind']=='folder' and r.get('folder','')==parent and i not in seen),key=lambda i:(records[i]['name'].casefold(),i))
        for i in ids:
            label=path+records[i]['name'];out.append((i,label))
            walk(i,label+' / ',seen|{i})
    walk('','',set())
    return out
