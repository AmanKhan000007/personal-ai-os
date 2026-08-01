import base64, os
from pathlib import Path

IMAGE_EXTENSIONS={".jpg",".jpeg",".png",".webp"}

def _mime(path:Path):
    return {".jpg":"image/jpeg",".jpeg":"image/jpeg",".png":"image/png",".webp":"image/webp"}.get(path.suffix.lower(),"image/jpeg")

async def describe_image(path:Path,prompt:str="Describe this image carefully and extract any useful visible text."):
    key=os.getenv("GEMINI_API_KEY","").strip()
    if not key: raise RuntimeError("Image understanding currently requires GEMINI_API_KEY")
    from google import genai
    from google.genai import types
    client=genai.Client(api_key=key)
    model=os.getenv("GEMINI_VISION_MODEL",os.getenv("GEMINI_MODEL","gemini-2.5-flash"))
    image_bytes=path.read_bytes()
    response=await client.aio.models.generate_content(model=model,contents=[prompt,types.Part.from_bytes(data=image_bytes,mime_type=_mime(path))])
    return (response.text or "").strip()
