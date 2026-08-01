from .db import db
from .memory import save_memory

async def consolidate_conversation(owner_id, ask_fn, min_messages=24):
    with db() as c:
        rows=c.execute("SELECT id,role,content FROM conversations WHERE sender_id=? ORDER BY id DESC LIMIT 60",(str(owner_id),)).fetchall()
    if len(rows)<min_messages:return None
    rows=list(reversed(rows)); transcript="\n".join(f"{r['role'].upper()}: {r['content']}" for r in rows)
    prompt="""Summarize this conversation into durable long-term memory. Keep only stable facts, preferences, decisions, projects, constraints and commitments that would be useful in future conversations. Do not store temporary chatter. Return concise bullet points only.\n\n"""+transcript
    summary,provider=await ask_fn(owner_id,prompt,use_context=False)
    saved=0
    for line in summary.splitlines():
        item=line.strip().lstrip("-*• ").strip()
        if len(item)>=8:
            save_memory(owner_id,item,category="conversation_summary",importance=.72,confidence=.8,source="summary");saved+=1
    return {"saved":saved,"provider":provider}
