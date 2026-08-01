import asyncio
from datetime import datetime,timedelta
from .db import db
from .tasks import local_now

def next_due(value,recurrence):
 d=datetime.fromisoformat(value)
 if recurrence=='daily':return d+timedelta(days=1)
 if recurrence=='weekly':return d+timedelta(days=7)
 return None
async def reminder_worker(send_fn,chat_id,interval=20):
 while True:
  try:
   now=local_now().isoformat(timespec="minutes")
   with db() as c:rows=c.execute("SELECT id,title,due_at,recurrence FROM tasks WHERE owner_id=? AND status='open' AND due_at IS NOT NULL AND due_at<=? AND notified_at IS NULL ORDER BY due_at,id",(str(chat_id),now)).fetchall()
   for r in rows:
    repeat=f"\n🔁 Repeats {r['recurrence']}" if r['recurrence'] else ""
    await send_fn(chat_id,f"⏰ Reminder\n\n{r['title']}\n\nTask #{r['id']}{repeat}"+(f"\nUse /deltask {r['id']} to stop it." if r['recurrence'] else f"\nReply /done {r['id']} when finished."))
    with db() as c:
     nxt=next_due(r['due_at'],r['recurrence'])
     if nxt:c.execute("UPDATE tasks SET due_at=?,notified_at=NULL WHERE id=?",(nxt.isoformat(timespec='minutes'),r['id']))
     else:c.execute("UPDATE tasks SET notified_at=CURRENT_TIMESTAMP WHERE id=?",(r['id'],))
  except asyncio.CancelledError:raise
  except Exception:pass
  await asyncio.sleep(interval)
