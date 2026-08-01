# Personal AI OS

A private, owner-only AI assistant with persistent semantic memory, Telegram, document/image/audio understanding, tasks, reminders and proactive briefings.

## Current features
- FastAPI backend and private web dashboard
- Owner-only Telegram access
- Telegram text, documents, images and voice/audio
- Persistent SQLite conversations and long-term memories
- Explicit and automatic memory capture
- Semantic memory/document retrieval
- Conversation memory consolidation
- PDF, DOCX, XLSX, CSV, TXT, JSON and Markdown extraction
- Document chunking and Q&A
- Image understanding and visible-text extraction
- Voice/audio transcription
- Persistent task management
- Natural-language reminders
- Daily and weekly recurring reminders
- Active Telegram reminder delivery
- `/brief` personal daily briefing
- Automatic proactive morning briefing
- Gemini with Groq and Cloudflare fallback support
- Audit logging

## Quick start
1. Clone the repository.
2. Create a virtual environment: `python -m venv .venv`
3. Activate on Windows: `.\.venv\Scripts\Activate.ps1`
4. Install dependencies: `pip install -r requirements.txt`
5. Copy `.env.example` to `.env` and fill in your secrets.
6. Start: `python run.py`
7. Expose port 8000 using Cloudflare Tunnel if running Telegram from localhost.
8. Put the current HTTPS tunnel address in `PUBLIC_BASE_URL`.
9. Run `python telegram_setup.py` whenever the tunnel URL or bot token changes.

## Telegram commands
- `/help` commands
- `/status` knowledge/task counts
- `/brief` daily personal briefing
- `/memory` recent memories
- `/files` indexed documents
- `/media` recent images/audio
- `/todo <task>` create task
- `/tasks` open tasks
- `/tasks all` all tasks
- `/done <id>` complete task
- `/deltask <id>` delete/stop task
- `/clearhistory` clear chat history while keeping long-term knowledge

## Natural language
Examples:
- `Remember that my preferred supplier is ...`
- `Forget my old supplier`
- `Remind me to call the customer tomorrow at 5 pm`
- `Remind me to check orders every day at 9 am`

## Scheduling
The default timezone is `Asia/Kolkata`. Configure it with `TIMEZONE`.

Automatic morning briefings are enabled by default at 08:00. Configure:
- `DAILY_BRIEF_ENABLED=true`
- `DAILY_BRIEF_HOUR=8`
- `DAILY_BRIEF_MINUTE=0`

Background reminders and automatic briefings require `python run.py` to remain running.

## Security
Never commit `.env`, API keys, Telegram bot tokens, admin tokens, or other secrets. If a secret has ever been exposed publicly, rotate it rather than only deleting it from the latest file.
