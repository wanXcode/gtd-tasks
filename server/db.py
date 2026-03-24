from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / 'data' / 'gtd.db'


def get_db_path(db_path: Optional[str] = None) -> Path:
    raw = db_path or os.getenv('GTD_DB_PATH')
    path = Path(raw).expanduser() if raw else DEFAULT_DB_PATH
    if not path.is_absolute():
        path = ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def connect(db_path: Optional[str] = None) -> sqlite3.Connection:
    path = get_db_path(db_path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON;')
    conn.execute('PRAGMA journal_mode = WAL;')
    return conn


@contextmanager
def get_conn(db_path: Optional[str] = None) -> Iterator[sqlite3.Connection]:
    conn = connect(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS tasks (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  status TEXT NOT NULL,
  bucket TEXT NOT NULL,
  quadrant TEXT NOT NULL,
  tags_json TEXT NOT NULL DEFAULT '[]',
  note TEXT NOT NULL DEFAULT '',
  category TEXT,
  source TEXT,
  source_task_id TEXT,
  sync_version INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  completed_at TEXT,
  deleted_at TEXT,
  last_synced_at TEXT
);

CREATE TABLE IF NOT EXISTS task_changes (
  change_id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id TEXT NOT NULL,
  action TEXT NOT NULL,
  changed_at TEXT NOT NULL,
  version INTEGER NOT NULL,
  payload_json TEXT,
  source TEXT,
  FOREIGN KEY(task_id) REFERENCES tasks(id)
);

CREATE TABLE IF NOT EXISTS sync_clients (
  client_id TEXT PRIMARY KEY,
  client_type TEXT NOT NULL,
  last_change_id INTEGER NOT NULL DEFAULT 0,
  last_seen_at TEXT NOT NULL,
  meta_json TEXT
);

CREATE TABLE IF NOT EXISTS apple_mappings (
  task_id TEXT PRIMARY KEY,
  apple_reminder_id TEXT,
  apple_list_id TEXT,
  apple_list_name TEXT,
  last_apple_updated_at TEXT,
  last_synced_at TEXT,
  sync_status TEXT,
  content_hash TEXT,
  meta_json TEXT,
  FOREIGN KEY(task_id) REFERENCES tasks(id)
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_bucket ON tasks(bucket);
CREATE INDEX IF NOT EXISTS idx_tasks_category ON tasks(category);
CREATE INDEX IF NOT EXISTS idx_tasks_updated_at ON tasks(updated_at);
CREATE INDEX IF NOT EXISTS idx_tasks_deleted_at ON tasks(deleted_at);
CREATE INDEX IF NOT EXISTS idx_task_changes_task_id ON task_changes(task_id);
CREATE INDEX IF NOT EXISTS idx_task_changes_changed_at ON task_changes(changed_at);
CREATE INDEX IF NOT EXISTS idx_task_changes_change_id ON task_changes(change_id);
CREATE INDEX IF NOT EXISTS idx_apple_mappings_reminder_id ON apple_mappings(apple_reminder_id);
"""


def init_db(db_path: Optional[str] = None) -> Path:
    path = get_db_path(db_path)
    with get_conn(str(path)) as conn:
        conn.executescript(SCHEMA_SQL)
    return path
