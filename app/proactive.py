import asyncio
from .briefing import daily_brief
from .tasks import local_now

async def daily_brief_worker(send_fn,chat_id,hour=8,minute=0,interval=30):
    last_date=None
    while True:
        try:
            now=local_now()
            today=now.date().isoformat()
            if now.hour==hour and now.minute>=minute and today!=last_date:
                await send_fn(chat_id,daily_brief(chat_id))
                last_date=today
        except asyncio.CancelledError:
            raise
        except Exception:
            pass
        await asyncio.sleep(interval)
