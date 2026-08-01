import asyncio
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from .config import TIMEZONE,AUTO_BACKUP_HOUR,AUTO_BACKUP_KEEP
from .backups import create_backup

async def automatic_backup_worker(log=None):
 tz=ZoneInfo(TIMEZONE)
 while True:
  now=datetime.now(tz);target=now.replace(hour=AUTO_BACKUP_HOUR,minute=0,second=0,microsecond=0)
  if target<=now:target+=timedelta(days=1)
  await asyncio.sleep(max(1,(target-now).total_seconds()))
  try:
   archive=await asyncio.to_thread(create_backup,AUTO_BACKUP_KEEP)
   if log:log('system','backup','automatic_backup',str(archive) if archive else 'backup skipped')
  except asyncio.CancelledError:raise
  except Exception as e:
   if log:log('system','backup','automatic_backup_error',str(e))
