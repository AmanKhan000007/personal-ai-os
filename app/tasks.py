import re
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from .db import db
from .config import TIMEZONE
def local_now():return datetime.now(ZoneInfo(TIMEZONE)).replace(tzinfo=None)
def add_task(owner_id,text,due_at=None,source="chat",recurrence=None):
 text=text.strip()
 if not text:return None
 with db() as c:return c.execute("INSERT INTO tasks(owner_id,title,due_at,source,recurrence) VALUES(?,?,?,?,?)",(str(owner_id),text,due_at,source,recurrence)).lastrowid
def list_tasks(owner_id,include_done=False,limit=30):
 sql="SELECT * FROM tasks WHERE owner_id=?";params=[str(owner_id)]
 if not include_done:sql+=" AND status='open'"
 sql+=" ORDER BY CASE WHEN due_at IS NULL THEN 1 ELSE 0 END,due_at,id DESC LIMIT ?";params.append(limit)
 with db() as c:return c.execute(sql,params).fetchall()
def complete_task(owner_id,task_id):
 with db() as c:return c.execute("UPDATE tasks SET status='done',completed_at=CURRENT_TIMESTAMP WHERE owner_id=? AND id=? AND status='open'",(str(owner_id),int(task_id))).rowcount>0
def delete_task(owner_id,task_id):
 with db() as c:return c.execute("DELETE FROM tasks WHERE owner_id=? AND id=?",(str(owner_id),int(task_id))).rowcount>0
def parse_clock(h,mi,ap):
 h=int(h);mi=int(mi or 0)
 if ap=='pm' and h<12:h+=12
 if ap=='am' and h==12:h=0
 return h,mi
def parse_due(phrase):
 now=local_now();p=phrase.lower().strip();m=re.search(r"\bin\s+(\d+)\s*(minute|minutes|min|hour|hours|day|days)\b",p)
 if m:
  n=int(m.group(1));u=m.group(2);return now+(timedelta(minutes=n) if u.startswith('min') else timedelta(hours=n) if u.startswith('hour') else timedelta(days=n))
 m=re.search(r"\b(today|tomorrow)\s+(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b",p)
 if m:
  day,h,mi,ap=m.groups();h,mi=parse_clock(h,mi,ap);d=now+(timedelta(days=1) if day=='tomorrow' else timedelta());return d.replace(hour=h,minute=mi,second=0,microsecond=0)
 m=re.search(r"\b(?:every day|daily)\s+(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b",p)
 if m:
  h,mi,ap=m.groups();h,mi=parse_clock(h,mi,ap);d=now.replace(hour=h,minute=mi,second=0,microsecond=0);return d if d>now else d+timedelta(days=1)
 if 'tomorrow' in p:return (now+timedelta(days=1)).replace(hour=9,minute=0,second=0,microsecond=0)
 return None
def recurrence_of(text):
 p=text.lower()
 if 'every day' in p or 'daily' in p:return 'daily'
 if 'every week' in p or 'weekly' in p:return 'weekly'
 return None
def natural_task(owner_id,text):
 s=text.strip();low=s.lower();prefix=next((p for p in ("remind me to ","remind me ","add a task to ","add task to ","todo ") if low.startswith(p)),None)
 if not prefix:return None
 body=s[len(prefix):].strip();due=parse_due(body);rec=recurrence_of(body);clean=re.sub(r"\s+in\s+\d+\s*(?:minutes?|min|hours?|days?)\s*$","",body,flags=re.I);clean=re.sub(r"\s+(?:today|tomorrow)(?:\s+at)?\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?\s*$","",clean,flags=re.I);clean=re.sub(r"\s+(?:every day|daily)(?:\s+at)?\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?\s*$","",clean,flags=re.I);clean=re.sub(r"\s+tomorrow\s*$","",clean,flags=re.I).strip();tid=add_task(owner_id,clean,due.isoformat(timespec='minutes') if due else None,"natural_language",rec)
 return f"✅ Task #{tid} added: {clean}"+(f"\n🔁 Repeats: {rec}" if rec else "")+(f"\n⏰ Next: {due.strftime('%d %b %Y, %I:%M %p')} ({TIMEZONE})" if due else "")
def task_command(owner_id,text):
 natural=natural_task(owner_id,text)
 if natural:return natural
 s=text.strip();m=re.match(r"^/todo(?:\s+add)?\s+(.+)$",s,re.I)
 if m:
  task=m.group(1).strip();tid=add_task(owner_id,task);return f"✅ Task #{tid} added: {task}"
 if re.match(r"^/tasks(?:\s+all)?$",s,re.I):
  rows=list_tasks(owner_id," all" in s.lower())
  if not rows:return "No open tasks."
  return "Tasks:\n"+"\n".join(f"• #{r['id']} {'✅' if r['status']=='done' else '⬜'} {r['title']}"+(f" — {r['recurrence']}" if r['recurrence'] else "")+(f" — due {r['due_at']}" if r['due_at'] else "") for r in rows)
 m=re.match(r"^/done\s+(\d+)$",s,re.I)
 if m:return "✅ Task completed." if complete_task(owner_id,m.group(1)) else "Task not found."
 m=re.match(r"^/deltask\s+(\d+)$",s,re.I)
 if m:return "🗑 Task deleted." if delete_task(owner_id,m.group(1)) else "Task not found."
 return None
