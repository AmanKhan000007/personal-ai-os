import os, httpx
from .memory import search_memories, search_documents, recent_conversation

SYSTEM = """You are Personal AI OS, a private personal assistant. Use supplied memory and document context when relevant. Never invent a remembered fact. If context is insufficient, say so. Keep private data private. When document excerpts are supplied, cite the source filename naturally in your answer."""

def build_prompt(owner_id, message):
    memories=search_memories(owner_id,message)
    docs=search_documents(owner_id,message)
    recent=recent_conversation(owner_id)
    mem="\n".join(f"- {r['content']}" for r in memories) or "(none)"
    doc="\n\n".join(f"SOURCE {r['original_name']}:\n{r['content']}" for r in docs) or "(none)"
    hist="\n".join(f"{r['role'].upper()}: {r['content']}" for r in recent[-10:]) or "(none)"
    return f"{SYSTEM}\n\nLONG-TERM MEMORY:\n{mem}\n\nDOCUMENT CONTEXT:\n{doc}\n\nRECENT CHAT:\n{hist}\n\nUSER:\n{message}"

async def gemini(prompt):
    key=os.getenv("GEMINI_API_KEY","").strip()
    if not key: raise RuntimeError("GEMINI_API_KEY is not configured")
    model=os.getenv("GEMINI_MODEL","gemini-2.5-flash")
    from google import genai
    client=genai.Client(api_key=key)
    response=await client.aio.models.generate_content(model=model, contents=prompt)
    return (response.text or "").strip()

async def cloudflare(prompt):
    account=os.getenv("CLOUDFLARE_ACCOUNT_ID","").strip()
    token=os.getenv("CLOUDFLARE_API_TOKEN","").strip()
    model=os.getenv("CLOUDFLARE_MODEL","@cf/meta/llama-3.1-8b-instruct")
    if not account or not token: raise RuntimeError("Cloudflare AI is not configured")
    url=f"https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/{model}"
    async with httpx.AsyncClient(timeout=60) as client:
        r=await client.post(url,headers={"Authorization":f"Bearer {token}"},json={"messages":[{"role":"system","content":SYSTEM},{"role":"user","content":prompt}]})
        r.raise_for_status(); data=r.json()
    result=data.get("result") or {}
    return (result.get("response") or result.get("result") or str(result)).strip()

async def ask(owner_id, message):
    prompt=build_prompt(owner_id,message)
    primary=os.getenv("LLM_PROVIDER","gemini").lower().strip()
    providers=[primary] + [p for p in ("gemini","cloudflare") if p != primary]
    errors=[]
    for p in providers:
        try:
            if p=="gemini": return await gemini(prompt), p
            if p=="cloudflare": return await cloudflare(prompt), p
        except Exception as e:
            errors.append(f"{p}: {type(e).__name__}: {e}")
    raise RuntimeError("All AI providers failed. " + " | ".join(errors))
