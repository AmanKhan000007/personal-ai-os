import re
from datetime import datetime
from .db import db

def add_task(owner_id,text,due_at=None,source="chat"):
 text=text.strip()
 if not text:return None
 with db() as c:
  cur=c.execute("INSERT INTO tasks(owner_id,title,due_at,source) VALUES(?,?,?,?)",(str(owner_id),text,due_at,source))
  return cur.lastrowid

def list_tasks(owner_id,include_done=False,limit=30):
 sql="SELECT * FROM tasks WHERE owner_id=?"
 params=[str(owner_id)]
 if not include_done:sql+=" AND status='open'"
 sql+=" ORDER BY CASE WHEN due_at IS NULL THEN 1 ELSE 0 END,due_at,id DESC LIMIT ?";params.append(limit)
 with db() as c:return c.execute(sql,params).fetchall()

def complete_task(owner_id,task_id):
 with db() as c:
  cur=c.execute("UPDATE tasks SET status='done',completed_at=CURRENT_TIMESTAMP WHERE owner_id=? AND id=? AND status='open'",(str(owner_id),int(task_id)))
  return cur.rowcount>0

def delete_task(owner_id,task_id):
 with db() as c:
  cur=c.execute("DELETE FROM tasks WHERE owner_id=? AND id=?",(str(owner_id),int(task_id)))
  return cur.rowcount>0

def task_command(owner_id,text):
 s=text.strip()
 m=re.match(r"^/todo(?:\s+add)?\s+(.+)$",s,re.I)
 if m:
  task=m.group(1).strip();tid=add_task(owner_id,task);return f"✅ Task #{tid} added: {task}"
 if re.match(r"^/tasks(?:\s+all)?$",s,re.I):
  rows=list_tasks(owner_id," all" in s.lower())
  if not rows:return "No open tasks."
  return "Tasks:\n"+"\n".join(f"• #{r['id']} {'✅' if r['status']=='done' else '⬜'} {r['title']}"+(f" — due {r['due_at']}" if r['due_at'] else "") for r in rows)
 m=re.match(r"^/done\s+(\d+)$",s,re.I)
 if m:return "✅ Task completed." if complete_task(owner_id,m.group(1)) else "Task not found."
 m=re.match(r"^/deltask\s+(\d+)$",s,re.I)
 if m:return "🗑 Task deleted." if delete_task(owner_id,m.group(1)) else "Task not found."
 return None
