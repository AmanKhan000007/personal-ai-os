import sqlite3
from contextlib import contextmanager
from .config import DB_PATH
SCHEMA="""
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS conversations (id INTEGER PRIMARY KEY AUTOINCREMENT,channel TEXT NOT NULL,sender_id TEXT NOT NULL,role TEXT NOT NULL,content TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_conv_sender ON conversations(sender_id,created_at);
CREATE TABLE IF NOT EXISTS memories (id INTEGER PRIMARY KEY AUTOINCREMENT,owner_id TEXT NOT NULL,content TEXT NOT NULL,category TEXT NOT NULL DEFAULT 'general',importance REAL NOT NULL DEFAULT 0.5,confidence REAL NOT NULL DEFAULT 1.0,source TEXT NOT NULL DEFAULT 'chat',access_count INTEGER NOT NULL DEFAULT 0,last_accessed TEXT,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,UNIQUE(owner_id,content));
CREATE INDEX IF NOT EXISTS idx_mem_owner ON memories(owner_id,importance DESC,updated_at DESC);
CREATE TABLE IF NOT EXISTS memory_embeddings (memory_id INTEGER PRIMARY KEY,vector TEXT NOT NULL,FOREIGN KEY(memory_id) REFERENCES memories(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS documents (id INTEGER PRIMARY KEY AUTOINCREMENT,owner_id TEXT NOT NULL,original_name TEXT NOT NULL,stored_name TEXT NOT NULL,path TEXT NOT NULL,mime_type TEXT,size_bytes INTEGER NOT NULL,extracted_text TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS document_chunks (id INTEGER PRIMARY KEY AUTOINCREMENT,document_id INTEGER NOT NULL,chunk_index INTEGER NOT NULL,content TEXT NOT NULL,FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE);
CREATE INDEX IF NOT EXISTS idx_chunks_doc ON document_chunks(document_id,chunk_index);
CREATE TABLE IF NOT EXISTS chunk_embeddings (chunk_id INTEGER PRIMARY KEY,vector TEXT NOT NULL,FOREIGN KEY(chunk_id) REFERENCES document_chunks(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS media (id INTEGER PRIMARY KEY AUTOINCREMENT,owner_id TEXT NOT NULL,media_type TEXT NOT NULL,original_name TEXT NOT NULL,stored_name TEXT NOT NULL,path TEXT NOT NULL,mime_type TEXT,size_bytes INTEGER NOT NULL,description TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT,owner_id TEXT NOT NULL,title TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'open',due_at TEXT,source TEXT NOT NULL DEFAULT 'chat',created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,completed_at TEXT,notified_at TEXT);
CREATE INDEX IF NOT EXISTS idx_tasks_owner ON tasks(owner_id,status,due_at);
CREATE TABLE IF NOT EXISTS audit_logs (id INTEGER PRIMARY KEY AUTOINCREMENT,channel TEXT NOT NULL,sender_id TEXT NOT NULL,event TEXT NOT NULL,detail TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
"""
def connect():
 c=sqlite3.connect(DB_PATH);c.row_factory=sqlite3.Row;c.execute("PRAGMA foreign_keys=ON");return c
@contextmanager
def db():
 conn=connect()
 try:yield conn;conn.commit()
 except Exception:conn.rollback();raise
 finally:conn.close()
def init_db():
 with db() as conn:
  conn.executescript(SCHEMA)
  cols={r['name'] for r in conn.execute("PRAGMA table_info(tasks)").fetchall()}
  if 'notified_at' not in cols:conn.execute("ALTER TABLE tasks ADD COLUMN notified_at TEXT")
