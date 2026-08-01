"""Personal AI OS backup/restore utility.

Usage:
  python backup.py backup
  python backup.py list
  python backup.py restore <backup.zip>

Backups contain the SQLite database and storage/uploads directory.
.env and API secrets are deliberately excluded.
"""
import argparse, shutil, sqlite3, sys, zipfile
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parent
STORAGE=ROOT/"storage"
DB=STORAGE/"personal_ai.db"
UPLOADS=STORAGE/"uploads"
BACKUPS=ROOT/"backups"

def backup():
    BACKUPS.mkdir(parents=True,exist_ok=True)
    stamp=datetime.now().strftime("%Y%m%d_%H%M%S")
    work=BACKUPS/f".tmp_{stamp}"
    work.mkdir(parents=True,exist_ok=True)
    try:
        if DB.exists():
            dst=work/"personal_ai.db"
            src=sqlite3.connect(DB)
            out=sqlite3.connect(dst)
            try: src.backup(out)
            finally: out.close();src.close()
        if UPLOADS.exists():shutil.copytree(UPLOADS,work/"uploads")
        archive=BACKUPS/f"personal-ai-os-backup-{stamp}.zip"
        with zipfile.ZipFile(archive,"w",zipfile.ZIP_DEFLATED) as z:
            for p in work.rglob("*"):
                if p.is_file():z.write(p,p.relative_to(work))
        print(f"Backup created: {archive}")
        print(f"Size: {archive.stat().st_size/1024/1024:.2f} MB")
        print("Secrets (.env/API keys) were NOT included.")
        return 0
    finally:
        shutil.rmtree(work,ignore_errors=True)

def list_backups():
    BACKUPS.mkdir(parents=True,exist_ok=True)
    files=sorted(BACKUPS.glob("personal-ai-os-backup-*.zip"),reverse=True)
    if not files:print("No backups found.");return 0
    for f in files:print(f"{f.name}  {f.stat().st_size/1024/1024:.2f} MB")
    return 0

def restore(name):
    archive=Path(name)
    if not archive.is_absolute():
        candidate=BACKUPS/archive
        archive=candidate if candidate.exists() else ROOT/archive
    if not archive.exists():print(f"Backup not found: {archive}");return 1
    with zipfile.ZipFile(archive) as z:
        names=set(z.namelist())
        if "personal_ai.db" not in names:print("Invalid backup: database missing.");return 1
        if any(Path(n).is_absolute() or ".." in Path(n).parts for n in names):print("Invalid backup paths.");return 1
    STORAGE.mkdir(parents=True,exist_ok=True)
    safety=None
    if DB.exists() or UPLOADS.exists():
        print("Creating safety backup before restore...")
        backup()
    temp=ROOT/".restore_tmp"
    shutil.rmtree(temp,ignore_errors=True);temp.mkdir()
    try:
        with zipfile.ZipFile(archive) as z:z.extractall(temp)
        if DB.exists():DB.unlink()
        shutil.copy2(temp/"personal_ai.db",DB)
        if UPLOADS.exists():shutil.rmtree(UPLOADS)
        if (temp/"uploads").exists():shutil.copytree(temp/"uploads",UPLOADS)
        else:UPLOADS.mkdir(parents=True,exist_ok=True)
        print(f"Restore complete from: {archive}")
        print("Restart Personal AI OS now.")
        return 0
    finally:shutil.rmtree(temp,ignore_errors=True)

def main():
    p=argparse.ArgumentParser(description="Personal AI OS backup utility")
    sub=p.add_subparsers(dest="cmd",required=True)
    sub.add_parser("backup");sub.add_parser("list")
    r=sub.add_parser("restore");r.add_argument("archive")
    a=p.parse_args()
    if a.cmd=="backup":return backup()
    if a.cmd=="list":return list_backups()
    return restore(a.archive)

if __name__=="__main__":sys.exit(main())
