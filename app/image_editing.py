import re
from pathlib import Path
from .db import db

EDIT_WORDS=(
 'edit','change','replace','remove','add','make this','make it','turn this','transform',
 'background','color','colour','enhance','upscale','retouch','clean up','erase','restore'
)

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
 with db() as c:
  return c.execute("SELECT * FROM media WHERE owner_id=? AND media_type='image' ORDER BY id DESC LIMIT 1",(str(owner_id),)).fetchone()

def pending_edit_from_caption(caption:str):
 return edit_instruction(caption)

def edit_request_summary(instruction:str):
 return f"Image edit requested: {instruction.strip()}"

def source_exists(row):
 return bool(row and Path(row['path']).exists())
