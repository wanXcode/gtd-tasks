from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from server.db import get_conn
from server.models import AppleMapping, SyncClient, Task, TaskChange

TZ = ZoneInfo('Asia/Shanghai')


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec='seconds')


class TaskRepository:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    def upsert_task(self, task: Task) -> Task:
        record = task.to_record()
        with get_conn(self.db_path) as conn:
            conn.execute(
                '''
                INSERT INTO tasks (
                    id, title, status, bucket, quadrant, tags_json, note, category,
                    source, source_task_id, sync_version, created_at, updated_at,
                    completed_at, deleted_at, last_synced_at
                ) VALUES (
                    :id, :title, :status, :bucket, :quadrant, :tags_json, :note, :category,
                    :source, :source_task_id, :sync_version, :created_at, :updated_at,
                    :completed_at, :deleted_at, :last_synced_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title,
                    status=excluded.status,
                    bucket=excluded.bucket,
                    quadrant=excluded.quadrant,
                    tags_json=excluded.tags_json,
                    note=excluded.note,
                    category=excluded.category,
                    source=excluded.source,
                    source_task_id=excluded.source_task_id,
                    sync_version=excluded.sync_version,
                    created_at=excluded.created_at,
                    updated_at=excluded.updated_at,
                    completed_at=excluded.completed_at,
                    deleted_at=excluded.deleted_at,
                    last_synced_at=excluded.last_synced_at
                ''',
                record,
            )
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        with get_conn(self.db_path) as conn:
            row = conn.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)).fetchone()
        return Task.from_row(row) if row else None

    def list_tasks(
        self,
        *,
        status: Optional[str] = None,
        bucket: Optional[str] = None,
        category: Optional[str] = None,
        tag: Optional[str] = None,
        text: Optional[str] = None,
        include_deleted: bool = False,
        limit: Optional[int] = None,
    ) -> List[Task]:
        sql = 'SELECT * FROM tasks WHERE 1=1'
        params: List[Any] = []
        if not include_deleted:
            sql += ' AND deleted_at IS NULL'
        if status:
            sql += ' AND status = ?'
            params.append(status)
        if bucket:
            sql += ' AND bucket = ?'
            params.append(bucket)
        if category:
            sql += ' AND category = ?'
            params.append(category)
        if tag:
            sql += ' AND tags_json LIKE ?'
            params.append(f'%"{tag}"%')
        if text:
            sql += ' AND (title LIKE ? OR note LIKE ?)'
            needle = f'%{text}%'
            params.extend([needle, needle])
        sql += ' ORDER BY updated_at DESC, id DESC'
        if limit:
            sql += ' LIMIT ?'
            params.append(limit)
        with get_conn(self.db_path) as conn:
            rows = conn.execute(sql, params).fetchall()
        return [Task.from_row(row) for row in rows]

    def record_change(
        self,
        *,
        task_id: str,
        action: str,
        changed_at: str,
        version: int,
        payload: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None,
    ) -> int:
        payload_json = json.dumps(payload, ensure_ascii=False) if payload is not None else None
        with get_conn(self.db_path) as conn:
            cur = conn.execute(
                '''
                INSERT INTO task_changes (task_id, action, changed_at, version, payload_json, source)
                VALUES (?, ?, ?, ?, ?, ?)
                ''',
                (task_id, action, changed_at, version, payload_json, source),
            )
            return int(cur.lastrowid)

    def list_changes(self, since_change_id: int = 0, limit: int = 200) -> List[TaskChange]:
        with get_conn(self.db_path) as conn:
            rows = conn.execute(
                'SELECT * FROM task_changes WHERE change_id > ? ORDER BY change_id ASC LIMIT ?',
                (since_change_id, limit),
            ).fetchall()
        return [TaskChange.from_row(row) for row in rows]

    def ack_sync_client(
        self,
        *,
        client_id: str,
        client_type: str,
        last_change_id: int,
        last_seen_at: str,
        meta: Optional[Dict[str, Any]] = None,
    ) -> SyncClient:
        meta_json = json.dumps(meta, ensure_ascii=False) if meta is not None else None
        with get_conn(self.db_path) as conn:
            conn.execute(
                '''
                INSERT INTO sync_clients (client_id, client_type, last_change_id, last_seen_at, meta_json)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(client_id) DO UPDATE SET
                    client_type=excluded.client_type,
                    last_change_id=excluded.last_change_id,
                    last_seen_at=excluded.last_seen_at,
                    meta_json=excluded.meta_json
                ''',
                (client_id, client_type, last_change_id, last_seen_at, meta_json),
            )
            row = conn.execute('SELECT * FROM sync_clients WHERE client_id = ?', (client_id,)).fetchone()
        return SyncClient.from_row(row)

    def get_sync_client(self, client_id: str) -> Optional[SyncClient]:
        with get_conn(self.db_path) as conn:
            row = conn.execute('SELECT * FROM sync_clients WHERE client_id = ?', (client_id,)).fetchone()
        return SyncClient.from_row(row) if row else None

    def upsert_apple_mapping(self, mapping: AppleMapping) -> AppleMapping:
        with get_conn(self.db_path) as conn:
            conn.execute(
                '''
                INSERT INTO apple_mappings (
                    task_id, apple_reminder_id, apple_list_id, apple_list_name,
                    last_apple_updated_at, last_synced_at, sync_status, content_hash, meta_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    apple_reminder_id=excluded.apple_reminder_id,
                    apple_list_id=excluded.apple_list_id,
                    apple_list_name=excluded.apple_list_name,
                    last_apple_updated_at=excluded.last_apple_updated_at,
                    last_synced_at=excluded.last_synced_at,
                    sync_status=excluded.sync_status,
                    content_hash=excluded.content_hash,
                    meta_json=excluded.meta_json
                ''',
                (
                    mapping.task_id,
                    mapping.apple_reminder_id,
                    mapping.apple_list_id,
                    mapping.apple_list_name,
                    mapping.last_apple_updated_at,
                    mapping.last_synced_at,
                    mapping.sync_status,
                    mapping.content_hash,
                    mapping.meta_json,
                ),
            )
        return mapping

    def get_apple_mapping(self, task_id: str) -> Optional[AppleMapping]:
        with get_conn(self.db_path) as conn:
            row = conn.execute('SELECT * FROM apple_mappings WHERE task_id = ?', (task_id,)).fetchone()
        return AppleMapping.from_row(row) if row else None

    def get_apple_mapping_by_reminder_id(self, apple_reminder_id: str) -> Optional[AppleMapping]:
        with get_conn(self.db_path) as conn:
            row = conn.execute(
                'SELECT * FROM apple_mappings WHERE apple_reminder_id = ?', (apple_reminder_id,)
            ).fetchone()
        return AppleMapping.from_row(row) if row else None

    def list_apple_mappings(self) -> list[AppleMapping]:
        with get_conn(self.db_path) as conn:
            rows = conn.execute('SELECT * FROM apple_mappings').fetchall()
        return [AppleMapping.from_row(row) for row in rows]

    def save_apple_mapping(self, task_id: str, apple_reminder_id: str) -> None:
        """保存或更新 Apple Reminder ID 映射"""
        with get_conn(self.db_path) as conn:
            conn.execute(
                '''INSERT INTO apple_mappings (task_id, apple_reminder_id)
                   VALUES (?, ?)
                   ON CONFLICT(task_id) DO UPDATE SET
                   apple_reminder_id = excluded.apple_reminder_id''',
                (task_id, apple_reminder_id)
            )
            conn.commit()
