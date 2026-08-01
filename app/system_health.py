import shutil,sqlite3
from pathlib import Path
from .config import DB_PATH,UPLOAD_DIR
from .db import db

def _size(path):
 try:return Path(path).stat().st_size
 except OSError:return 0

def system_health():
 checks=[]
 def add(name,ok,detail):checks.append({'name':name,'ok':bool(ok),'detail':str(detail)})
 try:
  with sqlite3.connect(DB_PATH) as c:result=c.execute('PRAGMA integrity_check').fetchone()[0]
  add('SQLite integrity',result=='ok',result)
 except Exception as e:add('SQLite integrity',False,e)
 try:
  with db() as c:
   docs=c.execute('SELECT id,path FROM documents').fetchall();media=c.execute('SELECT id,path FROM media').fetchall()
   orphan_mem=c.execute('SELECT COUNT(*) FROM memory_embeddings e LEFT JOIN memories m ON m.id=e.memory_id WHERE m.id IS NULL').fetchone()[0]
   missing_mem=c.execute('SELECT COUNT(*) FROM memories m LEFT JOIN memory_embeddings e ON e.memory_id=m.id WHERE e.memory_id IS NULL').fetchone()[0]
   orphan_chunks=c.execute('SELECT COUNT(*) FROM chunk_embeddings e LEFT JOIN document_chunks d ON d.id=e.chunk_id WHERE d.id IS NULL').fetchone()[0]
   missing_chunks=c.execute('SELECT COUNT(*) FROM document_chunks d LEFT JOIN chunk_embeddings e ON e.chunk_id=d.id WHERE e.chunk_id IS NULL').fetchone()[0]
  missing_docs=[r['id'] for r in docs if not Path(r['path']).exists()];missing_media=[r['id'] for r in media if not Path(r['path']).exists()]
  add('Document files',not missing_docs,f'{len(docs)} records; {len(missing_docs)} missing')
  add('Media files',not missing_media,f'{len(media)} records; {len(missing_media)} missing')
  add('Memory embeddings',orphan_mem==0 and missing_mem==0,f'{missing_mem} missing; {orphan_mem} orphaned')
  add('Document embeddings',orphan_chunks==0 and missing_chunks==0,f'{missing_chunks} missing; {orphan_chunks} orphaned')
 except Exception as e:add('Database references',False,e)
 try:
  known={str(Path(r['path']).resolve()) for r in docs+media};files=[p for p in UPLOAD_DIR.rglob('*') if p.is_file()];orphans=[p for p in files if str(p.resolve()) not in known]
  add('Upload storage',True,f'{len(files)} files; {len(orphans)} unreferenced; {sum(_size(p) for p in files)/1024/1024:.1f} MB')
 except Exception as e:add('Upload storage',False,e)
 try:
  usage=shutil.disk_usage(DB_PATH.parent);free_gb=usage.free/1024**3
  add('Disk space',free_gb>=1,f'{free_gb:.2f} GB free')
 except Exception as e:add('Disk space',False,e)
 ok=all(x['ok'] for x in checks)
 return {'ok':ok,'status':'HEALTHY' if ok else 'ATTENTION NEEDED','checks':checks}

def health_text():
 r=system_health();lines=[f"SYSTEM: {r['status']}"]
 for x in r['checks']:lines.append(f"{'PASS' if x['ok'] else 'FAIL'} | {x['name']} | {x['detail']}")
 return '\n'.join(lines)
