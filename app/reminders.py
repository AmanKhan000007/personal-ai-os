import asyncio
from datetime import datetime
from .db import db

async def reminder_worker(send_fn,chat_id,interval=20):
    """Continuously deliver due task reminders while the app is running."""
    while True:
        try:
            now=datetime.now().isoformat(timespec="minutes")
            with db() as c:
                rows=c.execute("""SELECT id,title,due_at FROM tasks
                    WHERE owner_id=? AND status='open' AND due_at IS NOT NULL
                    AND due_at<=? AND notified_at IS NULL ORDER BY due_at,id""",
                    (str(chat_id),now)).fetchall()
            for r in rows:
                await send_fn(chat_id,f"⏰ Reminder\n\n{r['title']}\n\nTask #{r['id']}")
                with db() as c:
                    c.execute("UPDATE tasks SET notified_at=CURRENT_TIMESTAMP WHERE id=?",(r['id'],))
        except asyncio.CancelledError:
            raise
        except Exception:
            pass
        await asyncio.sleep(interval)
