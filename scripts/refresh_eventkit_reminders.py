#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAPPING_PATH = ROOT / 'sync' / 'mac-apple-mappings.json'
TASKS_PATH = ROOT / 'data' / 'tasks.json'

import sys
sys.path.insert(0, str(ROOT / 'scripts'))

from sync_agent_mac import CATEGORY_TO_LIST, BUCKET_TO_LIST, render_reminder_note, render_reminder_title, bucket_to_due_date, run_reminders_backend  # noqa: E402


def load_json(path: Path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def main() -> int:
    mappings = load_json(MAPPING_PATH) if MAPPING_PATH.exists() else {}
    tasks_doc = load_json(TASKS_PATH)
    tasks = {str(t.get('id')): t for t in tasks_doc.get('tasks', []) if t.get('id')}

    refreshed = []
    skipped = []
    errors = []

    for task_id, reminder_id in mappings.items():
        task = tasks.get(task_id)
        if not task or task.get('deleted_at') or task.get('status') != 'open':
            skipped.append({'task_id': task_id, 'reason': 'task_missing_or_not_open'})
            continue

        raw_title = task.get('title', '')
        tags = list(task.get('tags') or [])
        title = render_reminder_title(raw_title, tags)
        note = render_reminder_note(task.get('note', '') or '', tags)
        bucket = task.get('bucket', 'today')
        due_date = bucket_to_due_date(bucket)
        category = task.get('category', 'next_action')
        list_name = CATEGORY_TO_LIST.get(category, BUCKET_TO_LIST.get(bucket, '下一步行动@NextAction'))

        try:
            run_reminders_backend('update', reminder_id=reminder_id, title=title, note=note, due_date=due_date)
            run_reminders_backend('move', reminder_id=reminder_id, list_name=list_name)
            refreshed.append({
                'task_id': task_id,
                'reminder_id': reminder_id,
                'title': title,
                'list_name': list_name,
            })
        except Exception as exc:
            errors.append({'task_id': task_id, 'reminder_id': reminder_id, 'error': str(exc)})

    print(json.dumps({
        'status': 'ok' if not errors else 'partial',
        'refreshed_count': len(refreshed),
        'skipped_count': len(skipped),
        'error_count': len(errors),
        'refreshed': refreshed,
        'skipped': skipped,
        'errors': errors,
    }, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == '__main__':
    raise SystemExit(main())
