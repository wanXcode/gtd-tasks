#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))

from apple_reminders_bridge import ReminderBridge  # noqa: E402
from sync_agent_mac import api_request, load_mappings, save_mappings, DEFAULT_API_URL  # noqa: E402

TASKS_PATH = ROOT / 'data' / 'tasks.json'


def load_tasks() -> List[Dict[str, Any]]:
    if not TASKS_PATH.exists():
        return []
    with open(TASKS_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return list(data.get('tasks', []))


def target_list_for_task(task: Dict[str, Any]) -> str:
    category = task.get('category', 'next_action')
    bucket = task.get('bucket', 'today')
    category_to_list = {
        'inbox': '收集箱@Inbox',
        'next_action': '下一步行动@NextAction',
        'project': '项目@Project',
        'waiting_for': '等待@Waiting For',
        'maybe': '可能的事@Maybe',
    }
    bucket_to_list = {
        'today': '下一步行动@NextAction',
        'tomorrow': '下一步行动@NextAction',
        'future': '可能的事@Maybe',
        'archive': '可能的事@Maybe',
    }
    return category_to_list.get(category, bucket_to_list.get(bucket, '下一步行动@NextAction'))


def main() -> int:
    if (os.getenv('GTD_REMINDERS_BACKEND') or 'eventkit').strip().lower() != 'eventkit':
        print('This migration is only for GTD_REMINDERS_BACKEND=eventkit')
        return 1

    bridge = ReminderBridge(backend='eventkit')
    mappings = load_mappings()
    tasks = load_tasks()
    task_index = {str(task.get('id')): task for task in tasks if task.get('id')}

    migrated = 0
    skipped = 0

    for task_id, reminder_id in list(mappings.items()):
        if not str(reminder_id).startswith('x-apple-reminder://'):
            skipped += 1
            continue

        task = task_index.get(task_id)
        if not task:
            skipped += 1
            continue

        title = task.get('title', '')
        note = task.get('note', '') or ''
        list_name = target_list_for_task(task)
        if not title:
            skipped += 1
            continue

        try:
            result = bridge.run_eventkit('create', {
                'title': title,
                'list_name': list_name,
                'note': note,
            }, timeout=20)
            new_id = str(result.get('reminder_id') or '').strip()
            if not new_id:
                skipped += 1
                continue
            mappings[task_id] = new_id
            api_request('POST', '/api/apple/mappings', {
                'mappings': [{'task_id': task_id, 'apple_reminder_id': new_id}]
            }, base_url=DEFAULT_API_URL)
            migrated += 1
            print(f'migrated {task_id}: {reminder_id} -> {new_id}')
        except Exception as exc:
            skipped += 1
            print(f'skip {task_id}: {exc}')

    save_mappings(mappings)
    print(json.dumps({'status': 'ok', 'migrated': migrated, 'skipped': skipped}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
