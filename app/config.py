import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

APP_NAME = os.getenv("APP_NAME", "Personal AI OS")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "").strip()
DB_PATH = Path(os.getenv("DB_PATH", "storage/personal_ai.db"))
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "storage/uploads"))
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_MB", "20")) * 1024 * 1024
MEMORY_RESULTS = int(os.getenv("MEMORY_RESULTS", "12"))
DOCUMENT_RESULTS = int(os.getenv("DOCUMENT_RESULTS", "8"))
TELEGRAM_OWNER_ID = os.getenv("TELEGRAM_OWNER_ID", "").strip()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")

DB_PATH.parent.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
