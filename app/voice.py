import os
from pathlib import Path

AUDIO_EXTENSIONS={".ogg",".oga",".mp3",".wav",".m4a",".aac",".flac",".webm"}

def _mime(path:Path):
    return {".ogg":"audio/ogg",".oga":"audio/ogg",".mp3":"audio/mpeg",".wav":"audio/wav",".m4a":"audio/mp4",".aac":"audio/aac",".flac":"audio/flac",".webm":"audio/webm"}.get(path.suffix.lower(),"audio/ogg")

async def transcribe_audio(path:Path):
    key=os.getenv("GEMINI_API_KEY","").strip()
    if not key: raise RuntimeError("Voice transcription requires GEMINI_API_KEY")
    from google import genai
    from google.genai import types
    client=genai.Client(api_key=key)
    model=os.getenv("GEMINI_AUDIO_MODEL",os.getenv("GEMINI_MODEL","gemini-2.5-flash"))
    response=await client.aio.models.generate_content(
        model=model,
        contents=["Transcribe this audio accurately. Return only the spoken words, preserving the language used by the speaker.",types.Part.from_bytes(data=path.read_bytes(),mime_type=_mime(path))]
    )
    return (response.text or "").strip()
