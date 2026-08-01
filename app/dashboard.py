import html
from .db import db

def esc(v): return html.escape(str(v or ""))

def dashboard_html(token):
    with db() as c:
        stats={
            "memories":c.execute("SELECT COUNT(*) n FROM memories").fetchone()["n"],
            "documents":c.execute("SELECT COUNT(*) n FROM documents").fetchone()["n"],
            "messages":c.execute("SELECT COUNT(*) n FROM conversations").fetchone()["n"],
            "media":c.execute("SELECT COUNT(*) n FROM media").fetchone()["n"],
        }
        memories=c.execute("SELECT id,content,category,importance,source,updated_at FROM memories ORDER BY updated_at DESC LIMIT 100").fetchall()
        docs=c.execute("SELECT id,original_name,size_bytes,created_at FROM documents ORDER BY id DESC LIMIT 100").fetchall()
        media=c.execute("SELECT id,original_name,media_type,description,created_at FROM media ORDER BY id DESC LIMIT 50").fetchall()
    cards="".join(f"<div class=stat><b>{v}</b><span>{esc(k.title())}</span></div>" for k,v in stats.items())
    memrows="".join(f"<tr><td>{r['id']}</td><td>{esc(r['content'])}</td><td>{esc(r['category'])}</td><td>{r['importance']:.2f}</td><td>{esc(r['source'])}</td><td><form method=post action='/dashboard/memory/{r['id']}/delete'><input type=hidden name=admin_token value='{esc(token)}'><button class=danger>Delete</button></form></td></tr>" for r in memories)
    docrows="".join(f"<tr><td>{r['id']}</td><td>{esc(r['original_name'])}</td><td>{r['size_bytes']}</td><td>{esc(r['created_at'])}</td></tr>" for r in docs)
    mediarows="".join(f"<tr><td>{r['id']}</td><td>{esc(r['original_name'])}</td><td>{esc(r['media_type'])}</td><td>{esc(r['description'][:300])}</td></tr>" for r in media)
    return f"""<!doctype html><html><head><meta name=viewport content='width=device-width,initial-scale=1'><title>PAIOS Dashboard</title><style>
    *{{box-sizing:border-box}}body{{margin:0;background:#0c1017;color:#edf2f7;font-family:Inter,Arial,sans-serif}}.wrap{{max-width:1250px;margin:auto;padding:28px}}h1{{margin-bottom:4px}}.muted{{color:#8f9bad}}.stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:25px 0}}.stat,.panel{{background:#151b25;border:1px solid #273142;border-radius:15px;padding:20px}}.stat b{{font-size:30px;display:block}}.stat span{{color:#8f9bad}}.panel{{margin:16px 0;overflow:auto}}table{{width:100%;border-collapse:collapse;min-width:750px}}th,td{{text-align:left;padding:11px;border-bottom:1px solid #273142;vertical-align:top}}th{{color:#8f9bad}}button{{background:#2b6cb0;color:white;border:0;border-radius:7px;padding:8px 12px;cursor:pointer}}.danger{{background:#9b2c2c}}a{{color:#63b3ed}}@media(max-width:700px){{.stats{{grid-template-columns:repeat(2,1fr)}}.wrap{{padding:15px}}}}
    </style></head><body><div class=wrap><h1>Personal AI OS</h1><div class=muted>Memory & knowledge dashboard</div><div class=stats>{cards}</div>
    <div class=panel><h2>Memories</h2><table><tr><th>ID</th><th>Memory</th><th>Category</th><th>Importance</th><th>Source</th><th></th></tr>{memrows}</table></div>
    <div class=panel><h2>Documents</h2><table><tr><th>ID</th><th>File</th><th>Bytes</th><th>Created</th></tr>{docrows}</table></div>
    <div class=panel><h2>Image / Media Knowledge</h2><table><tr><th>ID</th><th>File</th><th>Type</th><th>Description</th></tr>{mediarows}</table></div>
    <p><a href='/'>← Chat</a></p></div></body></html>"""
