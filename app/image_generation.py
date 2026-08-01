import os,base64,uuid
from pathlib import Path
import httpx
from .config import UPLOAD_DIR,TELEGRAM_BOT_TOKEN
from .db import db

def _provider():
 account=os.getenv('CLOUDFLARE_ACCOUNT_ID','').strip();token=os.getenv('CLOUDFLARE_API_TOKEN','').strip();model=os.getenv('IMAGE_MODEL','@cf/black-forest-labs/flux-1-schnell').strip()
 if not account or not token:raise RuntimeError('Cloudflare image generation is not configured')
 return account,token,model

def _decode(r):
 ctype=r.headers.get('content-type','')
 if ctype.startswith('image/'):return r.content
 obj=r.json();result=obj.get('result',obj);encoded=result.get('image') if isinstance(result,dict) else None
 if not encoded:raise RuntimeError('Image provider returned no image')
 return base64.b64decode(encoded)

async def generate_image(prompt:str):
 prompt=(prompt or '').strip()
 if not prompt:raise ValueError('Image prompt is empty')
 account,token,model=_provider();url=f'https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/{model}'
 async with httpx.AsyncClient(timeout=120) as client:r=await client.post(url,headers={'Authorization':f'Bearer {token}'},json={'prompt':prompt});r.raise_for_status();data=_decode(r)
 path=UPLOAD_DIR/f'generated-{uuid.uuid4().hex}.png';path.write_bytes(data);return path

def generate_image_sync(prompt:str):
 prompt=(prompt or '').strip()
 if not prompt:raise ValueError('Image prompt is empty')
 account,token,model=_provider();url=f'https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/{model}'
 with httpx.Client(timeout=120) as client:r=client.post(url,headers={'Authorization':f'Bearer {token}'},json={'prompt':prompt});r.raise_for_status();data=_decode(r)
 path=UPLOAD_DIR/f'generated-{uuid.uuid4().hex}.png';path.write_bytes(data);return path

def image_prompt(text:str):
 s=(text or '').strip();low=s.lower();prefixes=['/image ','generate image ','generate an image ','create image ','create an image ','make image ','make an image ','draw ']
 for p in prefixes:
  if low.startswith(p):return s[len(p):].strip()
 return None

def generate_store_send(owner_id,prompt):
 path=generate_image_sync(prompt);label='Generated image';description=f'AI-generated image. Prompt: {prompt}'
 with db() as c:c.execute('INSERT INTO media(owner_id,media_type,original_name,stored_name,path,mime_type,size_bytes,description,label) VALUES(?,?,?,?,?,?,?,?,?)',(str(owner_id),'image',path.name,path.name,str(path),'image/png',path.stat().st_size,description,label))
 if TELEGRAM_BOT_TOKEN and str(owner_id).isdigit():
  url=f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto'
  with httpx.Client(timeout=120) as client:
   with path.open('rb') as f:r=client.post(url,data={'chat_id':str(owner_id),'caption':f'🎨 Generated\n\nPrompt: {prompt[:850]}'},files={'photo':(path.name,f,'image/png')})
   r.raise_for_status();result=r.json()
   if not result.get('ok'):raise RuntimeError(str(result))
 return path
