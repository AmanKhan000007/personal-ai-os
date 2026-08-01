# Personal AI OS

A private, owner-only AI assistant with persistent memory, Telegram integration, document indexing, and provider fallback.

## MVP features
- FastAPI backend
- Telegram webhook: text + document uploads
- Owner-only Telegram access
- Persistent SQLite conversations and memories
- Automatic memory extraction + explicit `remember ...`
- Hybrid memory retrieval (FTS-style keyword scoring + recency/importance)
- PDF, DOCX, XLSX, CSV, TXT, JSON and Markdown extraction
- Document chunking and retrieval for Q&A
- Gemini primary provider
- Cloudflare Workers AI fallback
- Local web playground
- Audit logging

## Quick start

1. Clone the repository.
2. Create a virtual environment: `python -m venv .venv`
3. Activate it on Windows: `.\.venv\Scripts\Activate.ps1`
4. Install dependencies: `pip install -r requirements.txt`
5. Copy `.env.example` to `.env` and fill in your secrets.
6. Start: `python run.py`
7. For Telegram on localhost, expose port 8000 with Cloudflare Tunnel and set `PUBLIC_BASE_URL` to the HTTPS tunnel URL.
8. Run `python telegram_setup.py` whenever the public URL or bot token changes.

Never commit `.env` or real API/bot tokens.
