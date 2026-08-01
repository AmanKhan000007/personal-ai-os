from .db import db
from .tasks import local_now

def daily_brief(owner_id):
    now=local_now(); today=now.date().isoformat()
    with db() as c:
        tasks=c.execute("SELECT id,title,due_at,recurrence FROM tasks WHERE owner_id=? AND status='open' ORDER BY CASE WHEN due_at IS NULL THEN 1 ELSE 0 END,due_at,id LIMIT 20",(str(owner_id),)).fetchall()
        memories=c.execute("SELECT content FROM memories WHERE owner_id=? ORDER BY importance DESC,updated_at DESC LIMIT 5",(str(owner_id),)).fetchall()
        docs=c.execute("SELECT original_name FROM documents WHERE owner_id=? ORDER BY id DESC LIMIT 3",(str(owner_id),)).fetchall()
    due_today=[r for r in tasks if r['due_at'] and r['due_at'][:10]==today]
    overdue=[r for r in tasks if r['due_at'] and r['due_at'][:10]<today]
    unscheduled=[r for r in tasks if not r['due_at']]
    out=[f"☀️ Daily Brief — {now.strftime('%d %b %Y')}",""]
    if overdue:
        out.append("⚠️ Overdue")
        out.extend(f"• #{r['id']} {r['title']} — {r['due_at']}" for r in overdue[:8]);out.append("")
    if due_today:
        out.append("📅 Due today")
        out.extend(f"• #{r['id']} {r['title']} — {r['due_at'][11:16]}" for r in due_today[:10]);out.append("")
    if unscheduled:
        out.append("📝 Open tasks without a time")
        out.extend(f"• #{r['id']} {r['title']}" for r in unscheduled[:5]);out.append("")
    if memories:
        out.append("🧠 Important context")
        out.extend(f"• {r['content']}" for r in memories[:5]);out.append("")
    if docs:
        out.append("📄 Recent knowledge")
        out.extend(f"• {r['original_name']}" for r in docs)
    if len(out)==2:out.append("Nothing urgent is stored right now.")
    return "\n".join(out).strip()
