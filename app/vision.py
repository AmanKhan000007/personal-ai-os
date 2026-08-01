import base64, os
from pathlib import Path
import httpx

IMAGE_EXTENSIONS={".jpg",".jpeg",".png",".webp"}

def _mime(path:Path):
    return {".jpg":"image/jpeg",".jpeg":"image/jpeg",".png":"image/png",".webp":"image/webp"}.get(path.suffix.lower(),"image/jpeg")

async def _gemini_vision(path:Path,prompt:str):
    key=os.getenv("GEMINI_API_KEY","").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    from google import genai
    from google.genai import types
    client=genai.Client(api_key=key)
    model=os.getenv("GEMINI_VISION_MODEL",os.getenv("GEMINI_MODEL","gemini-2.5-flash"))
    response=await client.aio.models.generate_content(
        model=model,
        contents=[prompt,types.Part.from_bytes(data=path.read_bytes(),mime_type=_mime(path))]
    )
    text=(response.text or "").strip()
    if not text:
        raise RuntimeError("Gemini returned an empty image response")
    return text,"gemini"

async def _groq_vision(path:Path,prompt:str):
    key=os.getenv("GROQ_API_KEY","").strip()
    if not key:
        raise RuntimeError("GROQ_API_KEY is not configured")
    model=os.getenv("GROQ_VISION_MODEL","meta-llama/llama-4-scout-17b-16e-instruct")
    encoded=base64.b64encode(path.read_bytes()).decode("ascii")
    payload={
        "model":model,
        "messages":[{"role":"user","content":[
            {"type":"text","text":prompt},
            {"type":"image_url","image_url":{"url":f"data:{_mime(path)};base64,{encoded}"}}
        ]}],
        "temperature":0.2,
        "max_completion_tokens":1200
    }
    async with httpx.AsyncClient(timeout=90) as client:
        r=await client.post("https://api.groq.com/openai/v1/chat/completions",headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"},json=payload)
        r.raise_for_status()
        data=r.json()
    text=((data.get("choices") or [{}])[0].get("message") or {}).get("content","").strip()
    if not text:
        raise RuntimeError("Groq returned an empty image response")
    return text,"groq"

async def describe_image(path:Path,prompt:str="Describe this image carefully and extract any useful visible text."):
    """Describe an image with provider fallback.

    Vision providers are tried independently of the text LLM provider because
    not every text model supports images. Configure VISION_PROVIDERS as a
    comma-separated list. Default: gemini,groq.
    """
    providers=[p.strip().lower() for p in os.getenv("VISION_PROVIDERS","gemini,groq").split(",") if p.strip()]
    errors=[]
    for provider in providers:
        try:
            if provider=="gemini":
                text,used=await _gemini_vision(path,prompt)
            elif provider=="groq":
                text,used=await _groq_vision(path,prompt)
            else:
                errors.append(f"{provider}: unsupported vision provider")
                continue
            return text
        except Exception as e:
            errors.append(f"{provider}: {type(e).__name__}: {str(e)[:300]}")
    raise RuntimeError("All configured vision providers failed. "+" | ".join(errors))
