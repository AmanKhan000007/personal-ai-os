import shutil,sqlite3,zipfile
from datetime import datetime
from pathlib import Path
from .config import DB_PATH,UPLOAD_DIR

ROOT=Path(__file__).resolve().parent.parent
BACKUP_DIR=ROOT/'backups'

def create_backup(keep=14):
 BACKUP_DIR.mkdir(parents=True,exist_ok=True);stamp=datetime.now().strftime('%Y%m%d_%H%M%S');tmp=BACKUP_DIR/f'.tmp_{stamp}';tmp.mkdir(parents=True,exist_ok=True)
 try:
  if not DB_PATH.exists():return None
  src=sqlite3.connect(DB_PATH);dst=sqlite3.connect(tmp/'personal_ai.db')
  try:src.backup(dst)
  finally:dst.close();src.close()
  if UPLOAD_DIR.exists():shutil.copytree(UPLOAD_DIR,tmp/'uploads')
  archive=BACKUP_DIR/f'personal-ai-os-backup-{stamp}.zip'
  with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
   for p in tmp.rglob('*'):
    if p.is_file():z.write(p,p.relative_to(tmp))
  prune_backups(keep);return archive
 finally:shutil.rmtree(tmp,ignore_errors=True)

def prune_backups(keep=14):
 files=sorted(BACKUP_DIR.glob('personal-ai-os-backup-*.zip'),reverse=True)
 for p in files[max(1,int(keep)):]:
  try:p.unlink()
  except OSError:pass

def latest_backup():
 BACKUP_DIR.mkdir(parents=True,exist_ok=True);files=sorted(BACKUP_DIR.glob('personal-ai-os-backup-*.zip'),reverse=True);return files[0] if files else None

def backup_status():
 p=latest_backup()
 if not p:return 'No backup found.'
 age=datetime.now()-datetime.fromtimestamp(p.stat().st_mtime)
 return f'Latest backup: {p.name} | {p.stat().st_size/1024/1024:.2f} MB | {age.days} day(s) old'
