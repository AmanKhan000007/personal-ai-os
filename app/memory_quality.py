import re
from .db import db
from .embeddings import embed,cosine,pack

FACT_PATTERNS=[
 ('name',r'\bmy name is\s+(.+?)(?:[.!?]|$)'),
 ('company',r'\bmy (?:company|business) (?:is|name is)\s+(.+?)(?:[.!?]|$)'),
 ('job',r'\bmy (?:job|role) is\s+(.+?)(?:[.!?]|$)'),
 ('address',r'\bmy (?:address|office address) is\s+(.+?)(?:[.!?]|$)'),
 ('location',r'\bi live (?:in|at)\s+(.+?)(?:[.!?]|$)'),
 ('preference',r'\bi prefer\s+(.+?)(?:[.!?]|$)'),
 ('favorite',r'\bmy (?:favorite|favourite)\s+([a-z ]{2,40})\s+is\s+(.+?)(?:[.!?]|$)'),
]

def normalize(text):return re.sub(r'\s+',' ',(text or '').strip()).lower().rstrip('.!?')
def fact_key(text):
 s=' '.join((text or '').split())
 for kind,p in FACT_PATTERNS:
  m=re.search(p,s,re.I)
  if m:
   if kind=='favorite':return f"favorite:{normalize(m.group(1))}"
   return kind
 return None

def smart_save_memory(owner_id,content,category='general',importance=.65,confidence=1.0,source='chat'):
 content=' '.join((content or '').split()).strip()
 if len(content)<3:return None
 norm=normalize(content);key=fact_key(content)
 with db() as c:
  rows=c.execute('SELECT * FROM memories WHERE owner_id=? ORDER BY updated_at DESC LIMIT 500',(str(owner_id),)).fetchall()
  for r in rows:
   if normalize(r['content'])==norm:
    c.execute('UPDATE memories SET importance=max(importance,?),confidence=max(confidence,?),updated_at=CURRENT_TIMESTAMP WHERE id=?',(importance,confidence,r['id']))
    c.execute('INSERT OR REPLACE INTO memory_embeddings(memory_id,vector) VALUES(?,?)',(r['id'],pack(embed(content))))
    return r['id']
  if key:
   for r in rows:
    if fact_key(r['content'])==key:
     c.execute('UPDATE memories SET content=?,category=?,importance=?,confidence=?,source=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',(content,category,max(float(r['importance']),importance),confidence,source,r['id']))
     c.execute('INSERT OR REPLACE INTO memory_embeddings(memory_id,vector) VALUES(?,?)',(r['id'],pack(embed(content))))
     return r['id']
  vec=embed(content);best=None;best_score=0
  for r in rows:
   if r['category']!=category:continue
   score=cosine(vec,embed(r['content']))
   if score>best_score:best_score=score;best=r
  if best is not None and best_score>=.94:
   c.execute('UPDATE memories SET importance=max(importance,?),confidence=max(confidence,?),updated_at=CURRENT_TIMESTAMP WHERE id=?',(importance,confidence,best['id']))
   return best['id']
  cur=c.execute('INSERT INTO memories(owner_id,content,category,importance,confidence,source) VALUES(?,?,?,?,?,?)',(str(owner_id),content,category,importance,confidence,source));mid=cur.lastrowid
  c.execute('INSERT OR REPLACE INTO memory_embeddings(memory_id,vector) VALUES(?,?)',(mid,pack(vec)));return mid

def cleanup_memories(owner_id):
 with db() as c:rows=c.execute('SELECT * FROM memories WHERE owner_id=? ORDER BY importance DESC,updated_at DESC',(str(owner_id),)).fetchall()
 seen={};remove=[]
 for r in rows:
  n=normalize(r['content'])
  if n in seen:remove.append(r['id'])
  else:seen[n]=r['id']
 if remove:
  with db() as c:c.executemany('DELETE FROM memories WHERE id=? AND owner_id=?',[(i,str(owner_id)) for i in remove])
 return len(remove)
