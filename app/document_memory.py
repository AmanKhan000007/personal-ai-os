import re
from .db import db

def document_label(text):
    s=(text or '').strip()
    patterns=[
        r'(?:save|remember|store)\s+(?:this\s+)?(?:document|file|pdf|sheet|spreadsheet)?\s*(?:as|named|name it)\s+(.+?)(?:[.!?]|$)',
        r'(?:call this)\s+(.+?)(?:[.!?]|$)',
    ]
    for p in patterns:
        m=re.search(p,s,re.I)
        if m:return m.group(1).strip(' .\"\'')[:120]
    return ''

def followup_document_label(text):
    s=(text or '').strip()
    m=re.match(r'^(?:save|remember|store)\s+(?:that|it|this|that document|this document|that file|this file|that pdf|this pdf)\s+(?:as|named|name it)\s+(.+?)[.!?]*$',s,re.I)
    return m.group(1).strip(' .\"\'')[:120] if m else ''

def document_request(text):
    s=(text or '').strip()
    if re.match(r'^(?:show|send|share|give)\s+(?:me\s+)?(?:that|it|this|that document|this document|that file|this file|that pdf|this pdf)(?:\s+again)?[.!?]*$',s,re.I):return '__latest__'
    m=re.match(r'^(?:show|send|share|give)\s+(?:me\s+)?(?:the\s+)?(.+?)(?:\s+(?:document|file|pdf|sheet|spreadsheet))?(?:\s+again)?[.!?]*$',s,re.I)
    if not m:return None
    q=m.group(1).strip(' .\"\'');q=re.sub(r'^(?:my|the)\s+','',q,flags=re.I).strip()
    return q or None

def latest_document(owner_id):
    with db() as c:return c.execute('SELECT * FROM documents WHERE owner_id=? ORDER BY id DESC LIMIT 1',(str(owner_id),)).fetchone()

def rename_latest_document(owner_id,label):
    item=latest_document(owner_id)
    if not item:return None
    with db() as c:c.execute('UPDATE documents SET label=? WHERE id=?',(label,item['id']))
    return item

def set_document_label(doc_id,label):
    with db() as c:c.execute('UPDATE documents SET label=? WHERE id=?',(label or '',doc_id))

def find_document(owner_id,query):
    if query=='__latest__':return latest_document(owner_id)
    q=(query or '').strip().lower()
    with db() as c:rows=c.execute('SELECT * FROM documents WHERE owner_id=? ORDER BY id DESC LIMIT 100',(str(owner_id),)).fetchall()
    if not rows:return None
    def score(r):
        label=(r['label'] or '').lower();name=(r['original_name'] or '').lower();text=(r['extracted_text'] or '').lower()[:10000]
        if q==label:return 100
        if q==name:return 95
        if q and q in label:return 80
        if q and q in name:return 70
        words=[w for w in re.findall(r'[a-z0-9]+',q) if len(w)>1]
        return sum(8 for w in words if w in label)+sum(5 for w in words if w in name)+sum(1 for w in words if w in text)
    best=max(rows,key=score)
    return best if score(best)>0 else None
