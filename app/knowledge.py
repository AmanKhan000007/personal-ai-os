from .db import db
from .embeddings import embed,cosine

def search_media(owner_id,query,limit=5):
    q=embed(query)
    with db() as c:rows=c.execute("SELECT * FROM media WHERE owner_id=? AND description<>'' ORDER BY id DESC LIMIT 500",(str(owner_id),)).fetchall()
    scored=[]
    for r in rows:
        score=cosine(q,embed(r['description']))
        if score>.08:scored.append((score,r))
    scored.sort(key=lambda x:x[0],reverse=True)
    return [r for _,r in scored[:limit]]

def knowledge_stats(owner_id):
    with db() as c:
        return {
            'memories':c.execute("SELECT COUNT(*) n FROM memories WHERE owner_id=?",(str(owner_id),)).fetchone()['n'],
            'documents':c.execute("SELECT COUNT(*) n FROM documents WHERE owner_id=?",(str(owner_id),)).fetchone()['n'],
            'media':c.execute("SELECT COUNT(*) n FROM media WHERE owner_id=?",(str(owner_id),)).fetchone()['n'],
        }
