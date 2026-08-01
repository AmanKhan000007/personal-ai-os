import os,httpx,asyncio
from .memory import search_memories,search_documents,recent_conversation
from .knowledge import search_media
SYSTEM="""You are Personal AI OS, a private personal assistant. Use supplied long-term memory, documents, media knowledge and recent conversation when relevant. Never invent a remembered fact. Clearly distinguish memory from document/media evidence. If context is insufficient, say so. Keep private data private. When using document excerpts, name the source filename. Prefer concise, useful answers."""
def build_prompt(owner_id,message):
 memories=search_memories(owner_id,message);docs=search_documents(owner_id,message);media=search_media(owner_id,message);recent=recent_conversation(owner_id)
 mem="\n".join(f"- {r['content']}" for r in memories) or "(none)";doc="\n\n".join(f"SOURCE {r['original_name']}:\n{r['content']}" for r in docs) or "(none)";med="\n\n".join(f"MEDIA {r['original_name']} ({r['media_type']}):\n{r['description']}" for r in media) or "(none)";hist="\n".join(f"{r['role'].upper()}: {r['content']}" for r in recent[-12:]) or "(none)"
 return f"{SYSTEM}\n\nLONG-TERM MEMORY:\n{mem}\n\nDOCUMENT CONTEXT:\n{doc}\n\nMEDIA KNOWLEDGE:\n{med}\n\nRECENT CHAT:\n{hist}\n\nUSER:\n{message}"
async def gemini(prompt):
 key=os.getenv("GEMINI_API_KEY","").strip()
 if not key:raise RuntimeError("GEMINI_API_KEY is not configured")
 from google import genai
 client=genai.Client(api_key=key);response=await client.aio.models.generate_content(model=os.getenv("GEMINI_MODEL","gemini-2.5-flash"),contents=prompt);return (response.text or "").strip()
async def cloudflare(prompt):
 account=os.getenv("CLOUDFLARE_ACCOUNT_ID","").strip();token=os.getenv("CLOUDFLARE_API_TOKEN","").strip();model=os.getenv("CLOUDFLARE_MODEL","@cf/meta/llama-3.1-8b-instruct")
 if not account or not token:raise RuntimeError("Cloudflare AI is not configured")
 async with httpx.AsyncClient(timeout=60) as client:r=await client.post(f"https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/{model}",headers={"Authorization":f"Bearer {token}"},json={"messages":[{"role":"system","content":SYSTEM},{"role":"user","content":prompt}]});r.raise_for_status();data=r.json()
 result=data.get("result") or {};return (result.get("response") or result.get("result") or str(result)).strip()
async def groq(prompt):
 key=os.getenv("GROQ_API_KEY","").strip()
 if not key:raise RuntimeError("GROQ_API_KEY is not configured")
 async with httpx.AsyncClient(timeout=60) as client:r=await client.post("https://api.groq.com/openai/v1/chat/completions",headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"},json={"model":os.getenv("GROQ_MODEL","llama-3.3-70b-versatile"),"messages":[{"role":"system","content":SYSTEM},{"role":"user","content":prompt}]});r.raise_for_status();data=r.json()
 return data['choices'][0]['message']['content'].strip()
async def ask(owner_id,message,use_context=True):
 prompt=build_prompt(owner_id,message) if use_context else f"{SYSTEM}\n\nUSER:\n{message}";primary=os.getenv("LLM_PROVIDER","gemini").lower().strip();configured=[p.strip().lower() for p in os.getenv("LLM_FALLBACKS","groq,cloudflare,gemini").split(',') if p.strip()];providers=[]
 for p in [primary]+configured:
  if p not in providers:providers.append(p)
 errors=[]
 for p in providers:
  try:
   if p=="gemini":return await gemini(prompt),p
   if p=="cloudflare":return await cloudflare(prompt),p
   if p=="groq":return await groq(prompt),p
  except Exception as e:errors.append(f"{p}: {type(e).__name__}: {e}");await asyncio.sleep(.25)
 raise RuntimeError("All AI providers failed. "+" | ".join(errors))
