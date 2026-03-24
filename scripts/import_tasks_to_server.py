#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from server.db import init_db  # noqa: E402
from server.models import Task  # noqa: E402
from server.repository import TaskRepository  # noqa: E402

DATA_FILE = ROOT / 'data' / 'tasks.json'


def normalize_task(task: Dict[str, Any]) -> Dict[str, Any]:
    payload = dict(task)
    payload.setdefault('status', 'open')
    payload.setdefault('bucket', 'future')
    payload.setdefault('quadrant', 'q2')
    payload.setdefault('tags', [])
    payload.setdefault('note', '')
    payload.setdefault('category', 'inbox')
    payload.setdefault('source', 'legacy_json')
    payload.setdefault('source_task_id', None)
    payload.setdefault('sync_version', 1)
    payload.setdefault('deleted_at', None)
    payload.setdefault('last_synced_at', None)
    payload.setdefault('completed_at', None)
    created_at = payload.get('created_at') or payload.get('updated_at')
    updated_at = payload.get('updated_at') or created_at
    payload['created_at'] = created_at
    payload['updated_at'] = updated_at
    if payload['status'] in ('done', 'cancelled', 'archived') and not payload.get('completed_at'):
        payload['completed_at'] = updated_at
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description='Import legacy data/tasks.json into SQLite server db')
    parser.add_argument('--input', default=str(DATA_FILE), help='tasks.json path')
    parser.add_argument('--db-path', default=None, help='sqlite file path, default data/gtd.db')
    parser.add_argument('--append', action='store_true', help='append to existing db without clearing old rows')
    parser.add_argument('--write-changes', action='store_true', help='also write synthetic create/done/delete changes')
    args = parser.parse_args()

    db_path = init_db(args.db_path)
    repo = TaskRepository(str(db_path))

    with open(args.input, 'r', encoding='utf-8') as f:
        data = json.load(f)
    tasks = data.get('tasks', [])

    if not args.append:
        from server.db import get_conn
        with get_conn(str(db_path)) as conn:
            conn.execute('DELETE FROM task_changes')
            conn.execute('DELETE FROM apple_mappings')
            conn.execute('DELETE FROM sync_clients')
            conn.execute('DELETE FROM tasks')

    imported = 0
    change_count = 0
    for raw in tasks:
        payload = normalize_task(raw)
        task = Task.from_dict(payload)
        repo.upsert_task(task)
        imported += 1
        if args.write_changes:
            change_count += 1
            repo.record_change(
                task_id=task.id,
                action='create',
                changed_at=task.created_at,
                version=1,
                payload=task.to_dict(),
                source=task.source,
            )
            if task.status in ('done', 'cancelled', 'archived'):
                change_count += 1
                repo.record_change(
                    task_id=task.id,
                    action='done',
                    changed_at=task.completed_at or task.updated_at,
                    version=task.sync_version,
                    payload=task.to_dict(),
                    source=task.source,
                )
            if task.deleted_at:
                change_count += 1
                repo.record_change(
                    task_id=task.id,
                    action='delete',
                    changed_at=task.deleted_at,
                    version=task.sync_version,
                    payload=task.to_dict(),
                    source=task.source,
                )

    print(json.dumps({
        'db_path': str(db_path),
        'imported_tasks': imported,
        'written_changes': change_count,
        'input': str(Path(args.input).resolve()),
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
