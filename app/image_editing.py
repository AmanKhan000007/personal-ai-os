import os,base64,uuid
from pathlib import Path
import httpx
from .db import db
from .config import UPLOAD_DIR,TELEGRAM_BOT_TOKEN

EDIT_WORDS=('edit','change','replace','remove','add','make this','make it','turn this','transform','background','color','colour','enhance','upscale','retouch','clean up','erase','restore')

def edit_instruction(text:str):
 s=(text or '').strip()
 if not s:return None
 low=s.lower()
 if low.startswith('/edit '):return s[6:].strip()
 if low=='/edit':return ''
 if any(low.startswith(x+' ') for x in ('edit','change','replace','remove','add','enhance','upscale','retouch','transform')):return s
 if any(x in low for x in ('remove the background','change the background','make this image','make this photo','make it look','turn this into')):return s
 return None

def latest_user_image(owner_id):
 with db() as c:return c.execute("SELECT * FROM media WHERE owner_id=? AND media_type='image' ORDER BY id DESC LIMIT 1",(str(owner_id),)).fetchone()
def pending_edit_from_caption(caption:str):return edit_instruction(caption)
def edit_request_summary(instruction:str):return f"Image edit requested: {instruction.strip()}"
def source_exists(row):return bool(row and Path(row['path']).exists())

def _provider():
 account=os.getenv('CLOUDFLARE_ACCOUNT_ID','').strip();token=os.getenv('CLOUDFLARE_API_TOKEN','').strip();model=os.getenv('IMAGE_EDIT_MODEL','@cf/black-forest-labs/flux-2-klein-4b').strip()
 if not account or not token:raise RuntimeError('Cloudflare image editing is not configured')
 return account,token,model

def _decode_response(r):
 ctype=r.headers.get('content-type','')
 if ctype.startswith('image/'):return r.content
 obj=r.json();result=obj.get('result',obj);encoded=result.get('image') if isinstance(result,dict) else None
 if not encoded:raise RuntimeError('Image editing provider returned no image')
 return base64.b64decode(encoded)

def _payload(source,instruction,key='input_image'):
 return {'prompt':instruction,key:base64.b64encode(Path(source).read_bytes()).decode('ascii')}

async def edit_image(source_path,instruction:str):
 source=Path(source_path);instruction=(instruction or '').strip()
 if not source.exists():raise FileNotFoundError(str(source))
 if not instruction:raise ValueError('Image editing instruction is empty')
 account,token,model=_provider();url=f'https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/{model}';headers={'Authorization':f'Bearer {token}','Content-Type':'application/json'}
 async with httpx.AsyncClient(timeout=180) as client:
  r=await client.post(url,headers=headers,json=_payload(source,instruction))
  if r.status_code>=400:r=await client.post(url,headers=headers,json=_payload(source,instruction,'image'))
  r.raise_for_status();data=_decode_response(r)
 out=UPLOAD_DIR/f'edited-{uuid.uuid4().hex}.png';out.write_bytes(data);return out

def edit_image_sync(source_path,instruction:str):
 source=Path(source_path);instruction=(instruction or '').strip()
 if not source.exists():raise FileNotFoundError(str(source))
 if not instruction:raise ValueError('Image editing instruction is empty')
 account,token,model=_provider();url=f'https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/{model}';headers={'Authorization':f'Bearer {token}','Content-Type':'application/json'}
 with httpx.Client(timeout=180) as client:
  r=client.post(url,headers=headers,json=_payload(source,instruction))
  if r.status_code>=400:r=client.post(url,headers=headers,json=_payload(source,instruction,'image'))
  r.raise_for_status();data=_decode_response(r)
 out=UPLOAD_DIR/f'edited-{uuid.uuid4().hex}.png';out.write_bytes(data);return out

def store_edited_image(owner_id,path,instruction,source_path):
 path=Path(path);description=f'AI-edited image. Instruction: {instruction}. Source: {Path(source_path).name}'
 with db() as c:
  cur=c.execute('INSERT INTO media(owner_id,media_type,original_name,stored_name,path,mime_type,size_bytes,description,label) VALUES(?,?,?,?,?,?,?,?,?)',(str(owner_id),'image',path.name,path.name,str(path),'image/png',path.stat().st_size,description,'Edited image'));return cur.lastrowid

def edit_latest_store_send(owner_id,instruction):
 item=latest_user_image(owner_id)
 if not source_exists(item):raise FileNotFoundError('No saved image is available to edit. Send a photo first.')
 out=edit_image_sync(item['path'],instruction);store_edited_image(owner_id,out,instruction,item['path'])
 if TELEGRAM_BOT_TOKEN and str(owner_id).isdigit():
  url=f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto'
  with httpx.Client(timeout=120) as client:
   with out.open('rb') as f:r=client.post(url,data={'chat_id':str(owner_id),'caption':f'✏️ Edited image\n\n{instruction[:850]}'},files={'photo':(out.name,f,'image/png')})
   r.raise_for_status();result=r.json()
   if not result.get('ok'):raise RuntimeError(str(result))
 return out
