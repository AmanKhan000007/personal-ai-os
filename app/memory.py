import re
from .db import db
from .config import MEMORY_RESULTS, DOCUMENT_RESULTS
from .embeddings import embed, cosine, pack, unpack

STOP={"the","a","an","and","or","to","of","in","on","for","is","are","was","were","i","me","my","you","it","that","this","what","who","when","where","how"}
def terms(text):return [x for x in re.findall(r"[a-zA-Z0-9_@.-]{2,}",text.lower()) if x not in STOP]
def save_memory(owner_id,content,category="general",importance=0.65,confidence=1.0,source="chat"):
 content=" ".join(content.split()).strip()
 if len(content)<3:return None
 with db() as c:
  c.execute("""INSERT INTO memories(owner_id,content,category,importance,confidence,source) VALUES(?,?,?,?,?,?) ON CONFLICT(owner_id,content) DO UPDATE SET importance=max(importance,excluded.importance),confidence=max(confidence,excluded.confidence),updated_at=CURRENT_TIMESTAMP""",(str(owner_id),content,category,importance,confidence,source));row=c.execute("SELECT id FROM memories WHERE owner_id=? AND content=?",(str(owner_id),content)).fetchone();memory_id=row["id"];c.execute("INSERT OR REPLACE INTO memory_embeddings(memory_id,vector) VALUES(?,?)",(memory_id,pack(embed(content))))
 return memory_id
def explicit_memory(text):
 m=re.match(r"\s*(?:please\s+)?remember(?:\s+that)?\s+(.+)",text,re.I|re.S);return m.group(1).strip() if m else None
def forget_target(text):
 m=re.match(r"\s*(?:please\s+)?forget(?:\s+that)?\s+(.+)",text,re.I|re.S);return m.group(1).strip() if m else None
def forget_memories(owner_id,query):
 matches=search_memories(owner_id,query,limit=5)
 if not matches:return 0
 ids=[r["id"] for r in matches]
 with db() as c:c.executemany("DELETE FROM memories WHERE id=? AND owner_id=?",[(i,str(owner_id)) for i in ids])
 return len(ids)
def auto_memory_candidates(text):
 patterns=[r"\bmy (?:name|company|business|job|role|birthday|favorite|favourite|preference|office|address)\b.+",r"\bi (?:am|work at|work for|own|prefer|like|use|live in|live at)\b.+"];clean=" ".join(text.split())
 if 5<=len(clean)<=500 and any(re.search(p,clean,re.I) for p in patterns):return [clean]
 return []
def search_memories(owner_id,query,limit=MEMORY_RESULTS):
 qterms=terms(query);qvec=embed(query)
 with db() as c:rows=c.execute("""SELECT m.*,e.vector FROM memories m LEFT JOIN memory_embeddings e ON e.memory_id=m.id WHERE m.owner_id=? ORDER BY m.importance DESC,m.updated_at DESC LIMIT 500""",(str(owner_id),)).fetchall()
 scored=[]
 for r in rows:
  low=r["content"].lower();hits=sum(1 for t in qterms if t in low);phrase=1 if query.lower().strip() in low else 0;vec=unpack(r["vector"]);semantic=cosine(qvec,vec) if vec else cosine(qvec,embed(r["content"]));score=hits*2.5+phrase*4+semantic*6+float(r["importance"])*1.5+min(int(r["access_count"]),20)*0.02
  if score>1.15:scored.append((score,r))
 scored.sort(key=lambda x:x[0],reverse=True);chosen=[r for _,r in scored[:limit]]
 if chosen:
  with db() as c:c.executemany("UPDATE memories SET access_count=access_count+1,last_accessed=CURRENT_TIMESTAMP WHERE id=?",[(r["id"],) for r in chosen])
 return chosen
def index_chunk_embedding(chunk_id,content):
 with db() as c:c.execute("INSERT OR REPLACE INTO chunk_embeddings(chunk_id,vector) VALUES(?,?)",(chunk_id,pack(embed(content))))
def latest_document(owner_id):
 with db() as c:return c.execute("SELECT * FROM documents WHERE owner_id=? ORDER BY id DESC LIMIT 1",(str(owner_id),)).fetchone()
def latest_document_context(owner_id,limit=8):
 doc=latest_document(owner_id)
 if not doc:return []
 with db() as c:return c.execute("""SELECT dc.id,dc.content,d.original_name,d.label,d.id document_id FROM document_chunks dc JOIN documents d ON d.id=dc.document_id WHERE d.id=? ORDER BY dc.chunk_index ASC LIMIT ?""",(doc['id'],limit)).fetchall()
def contextual_document_question(text):
 s=(text or '').strip().lower()
 explicit=any(x in s for x in ['this document','this file','this pdf','that document','that file','that pdf','the document','the file','the pdf'])
 followup=bool(re.match(r'^(?:what|who|when|where|why|how|which|does|do|is|are|can|summarize|summarise|explain|tell|find|check|give)\b',s))
 short=len(s.split())<=18
 return explicit or (followup and short)
def search_documents(owner_id,query,limit=DOCUMENT_RESULTS,prefer_latest=False):
 qterms=terms(query);qvec=embed(query)
 with db() as c:
  latest=c.execute("SELECT id FROM documents WHERE owner_id=? ORDER BY id DESC LIMIT 1",(str(owner_id),)).fetchone();latest_id=latest['id'] if latest else None
  rows=c.execute("""SELECT dc.id,dc.content,d.original_name,d.label,d.id document_id,e.vector FROM document_chunks dc JOIN documents d ON d.id=dc.document_id LEFT JOIN chunk_embeddings e ON e.chunk_id=dc.id WHERE d.owner_id=? ORDER BY dc.id DESC LIMIT 2500""",(str(owner_id),)).fetchall()
 scored=[]
 for r in rows:
  low=r["content"].lower();keyword=sum(min(low.count(t),5) for t in qterms);vec=unpack(r["vector"]);semantic=cosine(qvec,vec) if vec else cosine(qvec,embed(r["content"]));latest_bonus=5.0 if prefer_latest and latest_id and r['document_id']==latest_id else 0;score=keyword*1.8+semantic*7+latest_bonus
  if score>0.8:scored.append((score,r))
 scored.sort(key=lambda x:x[0],reverse=True);return [r for _,r in scored[:limit]]
def recent_conversation(owner_id,limit=12):
 with db() as c:rows=c.execute("SELECT role,content FROM conversations WHERE sender_id=? ORDER BY id DESC LIMIT ?",(str(owner_id),limit)).fetchall()
 return list(reversed(rows))
