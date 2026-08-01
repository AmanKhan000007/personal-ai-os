from .db import db
HELP="""Personal AI OS commands:
/help - show commands
/status - system knowledge counts
/memory - show recent saved memories
/files - show indexed documents
/media - show recent images/audio
/clearhistory - clear conversation history (keeps long-term memory)

Natural-language controls:
Remember that ...
Forget ..."""
def command_response(owner_id,text):
 cmd=text.strip().split()[0].lower() if text.strip() else ""
 if cmd=="/help":return HELP
 if cmd=="/status":
  with db() as c:
   m=c.execute("SELECT COUNT(*) n FROM memories WHERE owner_id=?",(str(owner_id),)).fetchone()["n"];d=c.execute("SELECT COUNT(*) n FROM documents WHERE owner_id=?",(str(owner_id),)).fetchone()["n"];media=c.execute("SELECT COUNT(*) n FROM media WHERE owner_id=?",(str(owner_id),)).fetchone()["n"];conv=c.execute("SELECT COUNT(*) n FROM conversations WHERE sender_id=?",(str(owner_id),)).fetchone()["n"]
  return f"🧠 Memories: {m}\n📄 Documents: {d}\n🖼 Media: {media}\n💬 Stored messages: {conv}"
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
  return "Conversation history cleared. Long-term memories and documents were kept."
 return None
