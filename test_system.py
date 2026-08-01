"""Personal AI OS diagnostic suite.
Run from the repository root with: python test_system.py
This test does not send Telegram messages or consume LLM quota unless --live is used.
"""
import os,sys,asyncio,argparse,tempfile
from pathlib import Path

PASS="PASS";FAIL="FAIL";WARN="WARN"
results=[]
def check(name,ok,detail="",warning=False):
 status=PASS if ok else (WARN if warning else FAIL);results.append((status,name,detail));print(f"[{status}] {name}"+(f": {detail}" if detail else ""));return ok

def main(live=False):
 try:
  from app.config import DB_PATH,UPLOAD_DIR,TELEGRAM_BOT_TOKEN,TELEGRAM_OWNER_ID,TIMEZONE
  check("Configuration import",True)
 except Exception as e:
  check("Configuration import",False,str(e));return 1
 check("Admin token",bool(os.getenv("ADMIN_TOKEN","")),"configured" if os.getenv("ADMIN_TOKEN","") else "ADMIN_TOKEN missing")
 check("Database directory",DB_PATH.parent.exists(),str(DB_PATH.parent))
 check("Upload directory",UPLOAD_DIR.exists(),str(UPLOAD_DIR))
 try:
  from zoneinfo import ZoneInfo
  ZoneInfo(TIMEZONE);check("Timezone",True,TIMEZONE)
 except Exception as e:check("Timezone",False,f"{TIMEZONE}: {e}")
 try:
  from app.db import init_db,db
  init_db()
  with db() as c:
   tables={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
  required={'conversations','memories','documents','document_chunks','media','tasks','audit_logs'}
  check("SQLite schema",required.issubset(tables),"missing: "+", ".join(sorted(required-tables)) if required-tables else "all core tables present")
 except Exception as e:check("SQLite schema",False,str(e))
 try:
  from app.tasks import parse_due,recurrence_of
  check("Reminder parser",parse_due("tomorrow at 5 pm") is not None)
  check("Recurring reminders",recurrence_of("every day at 9 am")=="daily")
 except Exception as e:check("Task/reminder engine",False,str(e))
 try:
  from app.storage import ALLOWED,chunks
  check("Document extraction config",all(x in ALLOWED for x in ['.pdf','.docx','.xlsx','.txt','.csv']))
  check("Document chunker",len(chunks("test knowledge "*500))>1)
 except Exception as e:check("Document engine",False,str(e))
 try:
  from app.memory import search_memories,search_documents
  check("Memory engine import",callable(search_memories) and callable(search_documents))
 except Exception as e:check("Memory engine import",False,str(e))
 try:
  from app.vision import IMAGE_EXTENSIONS
  check("Vision module",bool(IMAGE_EXTENSIONS),", ".join(sorted(IMAGE_EXTENSIONS)))
 except Exception as e:check("Vision module",False,str(e))
 try:
  from app.voice import AUDIO_EXTENSIONS
  check("Voice module",bool(AUDIO_EXTENSIONS),", ".join(sorted(AUDIO_EXTENSIONS)))
 except Exception as e:check("Voice module",False,str(e))
 check("Telegram credentials",bool(TELEGRAM_BOT_TOKEN and TELEGRAM_OWNER_ID),"configured" if TELEGRAM_BOT_TOKEN and TELEGRAM_OWNER_ID else "bot token or owner ID missing",warning=True)
 provider=os.getenv("LLM_PROVIDER","gemini").lower();keys={'gemini':bool(os.getenv('GEMINI_API_KEY')),'groq':bool(os.getenv('GROQ_API_KEY')),'cloudflare':bool(os.getenv('CLOUDFLARE_ACCOUNT_ID') and os.getenv('CLOUDFLARE_API_TOKEN'))}
 check("Primary LLM configuration",keys.get(provider,False),f"provider={provider}",warning=True)
 if live:
  async def live_tests():
   if TELEGRAM_BOT_TOKEN:
    try:
     import httpx
     async with httpx.AsyncClient(timeout=20) as client:r=await client.get(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe");data=r.json()
     check("LIVE Telegram API",bool(data.get('ok')),data.get('result',{}).get('username',''))
    except Exception as e:check("LIVE Telegram API",False,str(e))
   try:
    from app.llm import ask
    answer,used=await ask(str(TELEGRAM_OWNER_ID or 'diagnostic'),"Reply with exactly: PERSONAL_AI_OS_OK",use_context=False)
    check("LIVE LLM",bool(answer),f"provider={used}; response={answer[:100]}")
   except Exception as e:check("LIVE LLM",False,str(e))
  asyncio.run(live_tests())
 print("\n"+"="*58);p=sum(s==PASS for s,_,_ in results);f=sum(s==FAIL for s,_,_ in results);w=sum(s==WARN for s,_,_ in results);print(f"Personal AI OS diagnostics: {p} PASS | {w} WARN | {f} FAIL")
 if not live:print("Run `python test_system.py --live` for Telegram + LLM network tests (may consume API quota).")
 return 1 if f else 0

if __name__=="__main__":
 parser=argparse.ArgumentParser();parser.add_argument("--live",action="store_true",help="test Telegram and LLM APIs");args=parser.parse_args();sys.exit(main(args.live))
