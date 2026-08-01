from .db import db
from .tasks import task_command
from .briefing import daily_brief
from .system_health import health_text
from .backups import create_backup,backup_status,BACKUP_DIR
from .image_generation import image_prompt,generate_store_send
from .image_editing import edit_instruction,edit_latest_store_send
HELP="""Personal AI OS commands:
/help - show commands
/status - system knowledge counts
/system - storage/database integrity check
/backup - create a backup now
/backups - show backup status and recent backups
/brief - today's personal briefing
/memory - show recent saved memories
/files - show indexed documents
/media - show recent images/audio
/image <prompt> - generate an AI image and send it here
/edit <instruction> - edit your most recent image and send the new version
/todo <task> - add a task
/tasks - list open tasks
/tasks all - include completed tasks
/done <id> - complete a task
/deltask <id> - delete a task
/clearhistory - clear conversation history (keeps memory/files/tasks)

Image examples:
/image premium white sneaker in a luxury studio
/edit remove the background
/edit change the shoes to white
/edit make it look like a premium advertisement

Natural-language controls:
Remember that ...
Forget ...
Remind me to ... tomorrow at 5 pm
Remind me to ... every day at 9 am"""
def command_response(owner_id,text):
 edit=edit_instruction(text)
 if edit is not None:
  if not edit:return "Usage: /edit <describe the change you want>. Send a photo first, then use /edit."
  try:
   path=edit_latest_store_send(owner_id,edit);return f"IMAGE_EDIT_SENT:{path.name}"
  except Exception as e:return f"Image editing failed: {type(e).__name__}: {e}"
 prompt=image_prompt(text)
 if prompt is not None:
  if not prompt:return "Usage: /image <describe the image you want>"
  try:
   path=generate_store_send(owner_id,prompt);return f"IMAGE_SENT:{path.name}"
  except Exception as e:return f"Image generation failed: {type(e).__name__}: {e}"
 task=task_command(owner_id,text)
 if task is not None:return task
 cmd=text.strip().split()[0].lower() if text.strip() else ""
 if cmd=="/help":return HELP
 if cmd=="/system":return health_text()
 if cmd=="/backup":
  try:
   p=create_backup();return f"Backup created successfully.\n{p.name}\n{p.stat().st_size/1024/1024:.2f} MB" if p else "Backup could not be created because the database does not exist."
  except Exception as e:return f"Backup failed: {type(e).__name__}: {e}"
 if cmd=="/backups":
  files=sorted(BACKUP_DIR.glob('personal-ai-os-backup-*.zip'),reverse=True)[:10];listing='\n'.join(f"• {p.name} — {p.stat().st_size/1024/1024:.2f} MB" for p in files) if files else 'No backups found.';return backup_status()+"\n\nRecent backups:\n"+listing
 if cmd=="/brief":return daily_brief(owner_id)
 if cmd=="/status":
  with db() as c:m=c.execute("SELECT COUNT(*) n FROM memories WHERE owner_id=?",(str(owner_id),)).fetchone()["n"];d=c.execute("SELECT COUNT(*) n FROM documents WHERE owner_id=?",(str(owner_id),)).fetchone()["n"];media=c.execute("SELECT COUNT(*) n FROM media WHERE owner_id=?",(str(owner_id),)).fetchone()["n"];conv=c.execute("SELECT COUNT(*) n FROM conversations WHERE sender_id=?",(str(owner_id),)).fetchone()["n"];tasks=c.execute("SELECT COUNT(*) n FROM tasks WHERE owner_id=? AND status='open'",(str(owner_id),)).fetchone()["n"]
  return f"🧠 Memories: {m}\n📄 Documents: {d}\n🖼 Media: {media}\n💬 Stored messages: {conv}\n✅ Open tasks: {tasks}"
 if cmd=="/memory":
  with db() as c:rows=c.execute("SELECT content FROM memories WHERE owner_id=? ORDER BY updated_at DESC LIMIT 15",(str(owner_id),)).fetchall()
  return "Recent memories:\n"+"\n".join(f"• {r['content']}" for r in rows) if rows else "No long-term memories saved yet."
 if cmd=="/files":
  with db() as c:rows=c.execute("SELECT id,original_name FROM documents WHERE owner_id=? ORDER BY id DESC LIMIT 25",(str(owner_id),)).fetchall()
  return "Indexed documents:\n"+"\n".join(f"• #{r['id']} {r['original_name']}" for r in rows) if rows else "No documents indexed yet."
 if cmd=="/media":
  with db() as c:rows=c.execute("SELECT media_type,original_name,description FROM media WHERE owner_id=? ORDER BY id DESC LIMIT 15",(str(owner_id),)).fetchall()
  return "Recent media:\n"+"\n".join(f"• {r['media_type']}: {r['original_name']} — {r['description'][:120]}" for r in rows) if rows else "No media stored yet."
 if cmd=="/clearhistory":
  with db() as c:c.execute("DELETE FROM conversations WHERE sender_id=?",(str(owner_id),))
  return "Conversation history cleared. Long-term memories, documents, media and tasks were kept."
 return None
