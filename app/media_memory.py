import re
from pathlib import Path
from .db import db

def clean_model_text(text):
    text=re.sub(r"<think>.*?</think>","",text or "",flags=re.I|re.S)
    return text.strip()

def label_from_caption(caption):
    s=(caption or "").strip()
    patterns=[
        r"(?:save|remember|store)\s+(?:this\s+)?(?:photo|image|picture)?\s*(?:as|named|name it)\s+(.+?)(?:[.!?]|$)",
        r"(?:this is|call this)\s+(?:my\s+)?(.+?)(?:[.!?]|$)",
    ]
    for p in patterns:
        m=re.search(p,s,re.I)
        if m:
            label=m.group(1).strip(" .\"'")
            if label:return label[:120]
    return ""

def followup_label(text):
    s=(text or "").strip()
    m=re.match(r"^(?:save|remember|store)\s+(?:that|it|this|that photo|this photo|that image|this image)\s+(?:as|named|name it)\s+(.+?)[.!?]*$",s,re.I)
    return m.group(1).strip(" .\"'")[:120] if m else ""

def media_request(text):
    s=(text or "").strip()
    if re.match(r"^(?:show|send|share|give)\s+(?:me\s+)?(?:that|it|this|that photo|this photo|that image|this image)(?:\s+again)?[.!?]*$",s,re.I):return "__latest__"
    m=re.match(r"^(?:show|send|share|give)\s+(?:me\s+)?(?:the\s+)?(.+?)(?:\s+(?:photo|image|picture))?(?:\s+again)?[.!?]*$",s,re.I)
    if not m:return None
    q=m.group(1).strip(" .\"'")
    q=re.sub(r"^(?:my|the)\s+","",q,flags=re.I).strip()
    return q or None

def latest_media(owner_id,media_type="image"):
    with db() as c:return c.execute("SELECT * FROM media WHERE owner_id=? AND media_type=? ORDER BY id DESC LIMIT 1",(str(owner_id),media_type)).fetchone()

def rename_latest_media(owner_id,label):
    item=latest_media(owner_id,"image")
    if not item:return None
    with db() as c:c.execute("UPDATE media SET label=? WHERE id=?",(label,item['id']))
    return item

def find_media(owner_id,query):
    if query=="__latest__":return latest_media(owner_id,"image")
    q=(query or "").strip().lower()
    with db() as c:rows=c.execute("SELECT * FROM media WHERE owner_id=? AND media_type='image' ORDER BY id DESC LIMIT 100",(str(owner_id),)).fetchall()
    if not rows:return None
    def score(r):
        label=(r['label'] or '').lower();name=(r['original_name'] or '').lower();desc=(r['description'] or '').lower()
        if q==label:return 100
        if q and q in label:return 80
        if label and label in q:return 70
        words=[w for w in re.findall(r"[a-z0-9]+",q) if len(w)>1]
        return sum(8 for w in words if w in label)+sum(3 for w in words if w in name)+sum(1 for w in words if w in desc)
    best=max(rows,key=score)
    return best if score(best)>0 else None

def set_media_details(path,label,description):
    with db() as c:c.execute("UPDATE media SET label=?,description=? WHERE path=?",(label or "",clean_model_text(description),str(path)))
