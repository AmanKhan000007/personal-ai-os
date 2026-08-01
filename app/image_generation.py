import os,base64,uuid
from pathlib import Path
import httpx
from .config import UPLOAD_DIR

async def generate_image(prompt:str):
    prompt=(prompt or '').strip()
    if not prompt: raise ValueError('Image prompt is empty')
    account=os.getenv('CLOUDFLARE_ACCOUNT_ID','').strip()
    token=os.getenv('CLOUDFLARE_API_TOKEN','').strip()
    model=os.getenv('IMAGE_MODEL','@cf/black-forest-labs/flux-1-schnell').strip()
    if not account or not token: raise RuntimeError('Cloudflare image generation is not configured')
    url=f'https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/{model}'
    async with httpx.AsyncClient(timeout=120) as client:
        r=await client.post(url,headers={'Authorization':f'Bearer {token}'},json={'prompt':prompt})
        r.raise_for_status()
        ctype=r.headers.get('content-type','')
        if ctype.startswith('image/'):
            data=r.content
        else:
            obj=r.json();result=obj.get('result',obj)
            encoded=result.get('image') if isinstance(result,dict) else None
            if not encoded: raise RuntimeError('Image provider returned no image')
            data=base64.b64decode(encoded)
    path=UPLOAD_DIR/f'generated-{uuid.uuid4().hex}.png';path.write_bytes(data)
    return path

def image_prompt(text:str):
    s=(text or '').strip()
    low=s.lower()
    prefixes=['/image ','generate image ','generate an image ','create image ','create an image ','make image ','make an image ','draw ']
    for p in prefixes:
        if low.startswith(p): return s[len(p):].strip()
    return None
