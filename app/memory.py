import re
from .db import db
from .config import MEMORY_RESULTS, DOCUMENT_RESULTS

STOP = {"the","a","an","and","or","to","of","in","on","for","is","are","was","were","i","me","my","you","it","that","this","what","who","when","where","how"}

def terms(text):
    return [x for x in re.findall(r"[a-zA-Z0-9_@.-]{2,}", text.lower()) if x not in STOP]

def save_memory(owner_id, content, category="general", importance=0.65, confidence=1.0, source="chat"):
    content = " ".join(content.split()).strip()
    if len(content) < 3: return
    with db() as c:
        c.execute("""INSERT INTO memories(owner_id,content,category,importance,confidence,source)
        VALUES(?,?,?,?,?,?) ON CONFLICT(owner_id,content) DO UPDATE SET
        importance=max(importance,excluded.importance), confidence=max(confidence,excluded.confidence),
        updated_at=CURRENT_TIMESTAMP""", (str(owner_id),content,category,importance,confidence,source))

def explicit_memory(text):
    m = re.match(r"\s*(?:please\s+)?remember(?:\s+that)?\s+(.+)", text, re.I|re.S)
    return m.group(1).strip() if m else None

def auto_memory_candidates(text):
    # Conservative automatic memory: personal declarations/preferences only.
    patterns = [
        r"\bmy (?:name|company|business|job|role|birthday|favorite|favourite|preference|office|address)\b.+",
        r"\bi (?:am|work at|work for|own|prefer|like|use|live in|live at)\b.+",
    ]
    clean = " ".join(text.split())
    if 5 <= len(clean) <= 500 and any(re.search(p, clean, re.I) for p in patterns):
        return [clean]
    return []

def search_memories(owner_id, query, limit=MEMORY_RESULTS):
    qterms = terms(query)
    with db() as c:
        rows = c.execute("SELECT * FROM memories WHERE owner_id=? ORDER BY importance DESC, updated_at DESC LIMIT 300", (str(owner_id),)).fetchall()
    scored=[]
    for r in rows:
        low=r["content"].lower()
        hits=sum(1 for t in qterms if t in low)
        phrase=1 if query.lower().strip() in low else 0
        score=hits*3 + phrase*5 + float(r["importance"])*2
        if score > 1.0 or not qterms: scored.append((score,r))
    scored.sort(key=lambda x:x[0], reverse=True)
    chosen=[r for _,r in scored[:limit]]
    if chosen:
        with db() as c:
            c.executemany("UPDATE memories SET access_count=access_count+1,last_accessed=CURRENT_TIMESTAMP WHERE id=?", [(r["id"],) for r in chosen])
    return chosen

def search_documents(owner_id, query, limit=DOCUMENT_RESULTS):
    qterms=terms(query)
    if not qterms: return []
    with db() as c:
        rows=c.execute("""SELECT dc.id,dc.content,d.original_name,d.id document_id
        FROM document_chunks dc JOIN documents d ON d.id=dc.document_id
        WHERE d.owner_id=? ORDER BY dc.id DESC LIMIT 1500""",(str(owner_id),)).fetchall()
    scored=[]
    for r in rows:
        low=r["content"].lower()
        hits=sum(low.count(t) for t in qterms)
        if hits: scored.append((hits,r))
    scored.sort(key=lambda x:x[0], reverse=True)
    return [r for _,r in scored[:limit]]

def recent_conversation(owner_id, limit=12):
    with db() as c:
        rows=c.execute("SELECT role,content FROM conversations WHERE sender_id=? ORDER BY id DESC LIMIT ?",(str(owner_id),limit)).fetchall()
    return list(reversed(rows))
