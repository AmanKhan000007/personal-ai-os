import os, asyncio, httpx
from dotenv import load_dotenv

load_dotenv()
TOKEN=os.getenv("TELEGRAM_BOT_TOKEN","").strip()
BASE=os.getenv("PUBLIC_BASE_URL","").strip().rstrip("/")

async def call(method, payload=None):
    async with httpx.AsyncClient(timeout=30) as client:
        r=await client.post(f"https://api.telegram.org/bot{TOKEN}/{method}",json=payload or {})
        return r.json()

async def main():
    if not TOKEN: raise SystemExit("TELEGRAM_BOT_TOKEN is missing in .env")
    if not BASE.startswith("https://"): raise SystemExit("PUBLIC_BASE_URL must be your HTTPS public URL")
    print("Bot:",await call("getMe"))
    print("Webhook:",await call("setWebhook",{"url":f"{BASE}/telegram/webhook","drop_pending_updates":True}))
    print("Info:",await call("getWebhookInfo"))

if __name__=="__main__": asyncio.run(main())
