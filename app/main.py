import os,html,uuid,asyncio
from pathlib import Path
import httpx
from fastapi import FastAPI,Request,UploadFile,File,Form,Header,HTTPException
from fastapi.responses import HTMLResponse,FileResponse,RedirectResponse
from .config import APP_NAME,ADMIN_TOKEN,UPLOAD_DIR,MAX_UPLOAD_BYTES,TELEGRAM_OWNER_ID,TELEGRAM_BOT_TOKEN,DAILY_BRIEF_ENABLED,DAILY_BRIEF_HOUR,DAILY_BRIEF_MINUTE
from .db import init_db,db
from .storage import extract_text,chunks,ALLOWED
from .memory import save_memory,explicit_memory,auto_memory_candidates,forget_target,forget_memories,index_chunk_embedding
from .llm import ask
from .vision import describe_image,IMAGE_EXTENSIONS
from .voice import transcribe_audio,AUDIO_EXTENSIONS
from .dashboard import dashboard_html
from .commands import command_response
from .summarizer import consolidate_conversation
from .reminders import reminder_worker
from .proactive import daily_brief_worker
app=FastAPI(title=APP_NAME);init_db()
@app.on_event("startup")
async def start_background_services():
 if TELEGRAM_BOT_TOKEN and TELEGRAM_OWNER_ID:
  app.state.reminder_task=asyncio.create_task(reminder_worker(tg_send,TELEGRAM_OWNER_ID))
  if DAILY_BRIEF_ENABLED:app.state.brief_task=asyncio.create_task(daily_brief_worker(tg_send,TELEGRAM_OWNER_ID,DAILY_BRIEF_HOUR,DAILY_BRIEF_MINUTE))
@app.on_event("shutdown")
async def stop_background_services():
 for name in ("reminder_task","brief_task"):
  task=getattr(app.state,name,None)
  if task:task.cancel()
def admin_ok(token):return bool(ADMIN_TOKEN and token==ADMIN_TOKEN)
def log(channel,sender,event,detail=""):
 with db() as c:c.execute("INSERT INTO audit_logs(channel,sender_id,event,detail) VALUES(?,?,?,?)",(channel,str(sender),event,detail[:3000]))
def save_chat(channel,sender,role,content):
 with db() as c:c.execute("INSERT INTO conversations(channel,sender_id,role,content) VALUES(?,?,?,?)",(channel,str(sender),role,content))
async def tg_api(method,payload=None):
 if not TELEGRAM_BOT_TOKEN:raise RuntimeError("TELEGRAM_BOT_TOKEN missing")
 async with httpx.AsyncClient(timeout=60) as client:r=await client.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/{method}",json=payload or {});r.raise_for_status();data=r.json()
 if not data.get("ok"):raise RuntimeError(str(data))
 return data.get("result")
async def tg_send(chat_id,text):
 for start in range(0,len(text),3900):await tg_api("sendMessage",{"chat_id":chat_id,"text":text[start:start+3900]})
async def tg_download(file_id):
 info=await tg_api("getFile",{"file_id":file_id});file_path=info["file_path"]
 async with httpx.AsyncClient(timeout=90) as client:r=await client.get(f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}");r.raise_for_status();return r.content,file_path
async def index_file(owner_id,original,data,mime="application/octet-stream"):
 ext=Path(original).suffix.lower()
 if ext not in ALLOWED:raise ValueError(f"Unsupported file type {ext}. Allowed: {', '.join(sorted(ALLOWED))}")
 if len(data)>MAX_UPLOAD_BYTES:raise ValueError("File is too large")
 stored=f"{uuid.uuid4().hex}{ext}";path=UPLOAD_DIR/stored;path.write_bytes(data);text=extract_text(path)
 with db() as c:
  cur=c.execute("INSERT INTO documents(owner_id,original_name,stored_name,path,mime_type,size_bytes,extracted_text) VALUES(?,?,?,?,?,?,?)",(str(owner_id),original,stored,str(path),mime,len(data),text));doc_id=cur.lastrowid;chunk_rows=[]
  for i,ch in enumerate(chunks(text)):
   cc=c.execute("INSERT INTO document_chunks(document_id,chunk_index,content) VALUES(?,?,?)",(doc_id,i,ch));chunk_rows.append((cc.lastrowid,ch))
 for cid,ch in chunk_rows:index_chunk_embedding(cid,ch)
 return doc_id,len(text)
async def save_media(owner_id,media_type,original,data,mime,description=""):
 ext=Path(original).suffix.lower();stored=f"{uuid.uuid4().hex}{ext}";path=UPLOAD_DIR/stored;path.write_bytes(data)
 with db() as c:c.execute("INSERT INTO media(owner_id,media_type,original_name,stored_name,path,mime_type,size_bytes,description) VALUES(?,?,?,?,?,?,?,?)",(str(owner_id),media_type,original,stored,str(path),mime,len(data),description))
 return path
async def process_text(channel,owner_id,text):
 cmd=command_response(owner_id,text)
 if cmd is not None:return cmd
 save_chat(channel,owner_id,"user",text);forget=forget_target(text)
 if forget:
  n=forget_memories(owner_id,forget);answer=f"Forgot {n} matching memory item(s)." if n else "I couldn't find a matching saved memory to forget.";save_chat(channel,owner_id,"assistant",answer);return answer
 explicit=explicit_memory(text)
 if explicit:save_memory(owner_id,explicit,importance=.95,source="explicit")
 else:
  for candidate in auto_memory_candidates(text):save_memory(owner_id,candidate,importance=.7,confidence=.85,source="automatic")
 answer,provider=await ask(owner_id,text);save_chat(channel,owner_id,"assistant",answer);log(channel,owner_id,"chat",provider)
 with db() as c:count=c.execute("SELECT COUNT(*) n FROM conversations WHERE sender_id=?",(str(owner_id),)).fetchone()["n"]
 if count and count%30==0:
  try:
   result=await consolidate_conversation(owner_id,ask)
   if result:log(channel,owner_id,"memory_consolidation",str(result))
  except Exception as e:log(channel,owner_id,"memory_consolidation_error",str(e))
 return answer
CSS="body{font-family:Arial,sans-serif;background:#f5f6f8;color:#18202a;margin:0}.wrap{max-width:900px;margin:40px auto;padding:18px}.card{background:white;padding:22px;border-radius:14px;margin:16px 0;border:1px solid #ddd}textarea,input{box-sizing:border-box;width:100%;padding:12px;margin:6px 0;border:1px solid #bbb;border-radius:8px}button{padding:12px 20px;background:#18202a;color:white;border:0;border-radius:8px}pre{white-space:pre-wrap}.muted{color:#66717e}a{color:#174ea6}"
@app.get("/",response_class=HTMLResponse)
def home():return f"<html><head><meta name=viewport content='width=device-width'><style>{CSS}</style></head><body><div class=wrap><h1>{html.escape(APP_NAME)}</h1><p class=muted>Private AI with semantic memory, documents, vision and voice.</p><div class=card><h2>Chat</h2><form method=post action=/playground><textarea name=message required></textarea><input type=password name=admin_token required placeholder='Admin token'><button>Ask</button></form></div><div class=card><h2>Upload document</h2><form method=post action=/upload enctype=multipart/form-data><input type=file name=file required><input type=password name=admin_token required placeholder='Admin token'><button>Upload</button></form></div><div class=card><h2>Dashboard</h2><form method=get action=/dashboard><input type=password name=admin_token required placeholder='Admin token'><button>Open Dashboard</button></form></div></div></body></html>"
@app.get("/dashboard",response_class=HTMLResponse)
def dashboard(admin_token:str):
 if not admin_ok(admin_token):raise HTTPException(401,"Invalid admin token")
 return dashboard_html(admin_token)
@app.post("/dashboard/memory/{memory_id}/delete")
def delete_memory(memory_id:int,admin_token:str=Form(...)):
 if not admin_ok(admin_token):raise HTTPException(401,"Invalid admin token")
 with db() as c:c.execute("DELETE FROM memories WHERE id=?",(memory_id,))
 return RedirectResponse(f"/dashboard?admin_token={admin_token}",status_code=303)
@app.post("/playground",response_class=HTMLResponse)
async def playground(message:str=Form(...),admin_token:str=Form(...)):
 if not admin_ok(admin_token):raise HTTPException(401,"Invalid admin token")
 try:answer=await process_text("web","owner",message)
 except Exception as e:answer=f"AI error: {e}"
 return f"<html><head><style>{CSS}</style></head><body><div class=wrap><a href='/'>← Home</a><div class=card><h3>You</h3><pre>{html.escape(message)}</pre><h3>Assistant</h3><pre>{html.escape(answer)}</pre></div></div></body></html>"
@app.post("/upload")
async def upload(file:UploadFile=File(...),admin_token:str=Form(...)):
 if not admin_ok(admin_token):raise HTTPException(401,"Invalid admin token")
 data=await file.read()
 try:doc_id,chars=await index_file("owner",Path(file.filename or "file").name,data,file.content_type or "")
 except ValueError as e:raise HTTPException(400,str(e))
 return {"ok":True,"document_id":doc_id,"file":file.filename,"characters_indexed":chars}
@app.get("/files/{doc_id}")
def download(doc_id:int,x_admin_token:str|None=Header(default=None)):
 if not admin_ok(x_admin_token):raise HTTPException(401,"Pass ADMIN_TOKEN in X-Admin-Token")
 with db() as c:r=c.execute("SELECT * FROM documents WHERE id=?",(doc_id,)).fetchone()
 if not r:raise HTTPException(404,"Not found")
 return FileResponse(r["path"],filename=r["original_name"])
@app.post("/telegram/webhook")
async def telegram_webhook(req:Request):
 update=await req.json();msg=update.get("message") or update.get("edited_message") or {};sender=str((msg.get("from") or {}).get("id",""));chat_id=(msg.get("chat") or {}).get("id")
 if not sender:return {"ok":True}
 if not TELEGRAM_OWNER_ID or sender!=TELEGRAM_OWNER_ID:
  log("telegram",sender,"blocked","unauthorized")
  if chat_id:await tg_send(chat_id,"This is a private assistant. Access denied.")
  return {"ok":True}
 try:
  caption=(msg.get("caption") or "").strip()
  if msg.get("voice") or msg.get("audio"):
   a=msg.get("voice") or msg.get("audio");data,file_path=await tg_download(a["file_id"]);ext=Path(file_path).suffix.lower() or ".ogg";original=a.get("file_name") or f"telegram-voice{ext}";path=await save_media(sender,"audio",original,data,a.get("mime_type","audio/ogg"));transcript=await transcribe_audio(path)
   with db() as c:c.execute("UPDATE media SET description=? WHERE path=?",(transcript,str(path)))
   await tg_send(chat_id,f"🎙️ {transcript}");answer=await process_text("telegram",sender,transcript);await tg_send(chat_id,answer);return {"ok":True}
  if msg.get("photo"):
   data,_=await tg_download(msg["photo"][-1]["file_id"]);path=await save_media(sender,"image","telegram-photo.jpg",data,"image/jpeg");description=await describe_image(path,caption or "Describe this image carefully and extract useful visible text.")
   with db() as c:c.execute("UPDATE media SET description=? WHERE path=?",(description,str(path)))
   save_memory(sender,f"Image received: {description}",category="image",importance=.55,source="vision");await tg_send(chat_id,description);return {"ok":True}
  if msg.get("document"):
   d=msg["document"];original=Path(d.get("file_name") or "document").name;ext=Path(original).suffix.lower();data,_=await tg_download(d["file_id"])
   if ext in IMAGE_EXTENSIONS:
    path=await save_media(sender,"image",original,data,d.get("mime_type","image/jpeg"));description=await describe_image(path,caption or "Describe this image carefully and extract useful visible text.")
    with db() as c:c.execute("UPDATE media SET description=? WHERE path=?",(description,str(path)))
    save_memory(sender,f"Image {original}: {description}",category="image",importance=.55,source="vision");await tg_send(chat_id,description);return {"ok":True}
   if ext in AUDIO_EXTENSIONS:
    path=await save_media(sender,"audio",original,data,d.get("mime_type","audio/ogg"));transcript=await transcribe_audio(path)
    with db() as c:c.execute("UPDATE media SET description=? WHERE path=?",(transcript,str(path)))
    await tg_send(chat_id,f"🎙️ {transcript}");answer=await process_text("telegram",sender,caption or transcript);await tg_send(chat_id,answer);return {"ok":True}
   if ext not in ALLOWED:await tg_send(chat_id,f"Unsupported document type {ext}. Allowed documents: {', '.join(sorted(ALLOWED))}");return {"ok":True}
   doc_id,chars=await index_file(sender,original,data,d.get("mime_type",""));log("telegram",sender,"upload",original);await tg_send(chat_id,f"✅ Indexed {original}\nDocument ID: {doc_id}\nCharacters indexed: {chars}\n\nYou can now ask me questions about it.")
   if caption:answer=await process_text("telegram",sender,caption);await tg_send(chat_id,answer)
   return {"ok":True}
  text=(msg.get("text") or "").strip()
  if text:answer=await process_text("telegram",sender,text);await tg_send(chat_id,answer)
  return {"ok":True}
 except Exception as e:
  log("telegram",sender,"error",str(e))
  if chat_id:await tg_send(chat_id,f"I couldn't process that request. Server error: {type(e).__name__}")
  return {"ok":True}
@app.get("/health")
def health():return {"ok":True,"app":APP_NAME,"telegram_configured":bool(TELEGRAM_BOT_TOKEN and TELEGRAM_OWNER_ID),"provider":os.getenv("LLM_PROVIDER","gemini"),"semantic_memory":True,"vision":True,"voice":True,"dashboard":True,"commands":True,"cross_media_search":True,"memory_consolidation":True,"active_reminders":True,"automatic_daily_brief":DAILY_BRIEF_ENABLED}
