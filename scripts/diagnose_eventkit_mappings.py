#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
MAPPING_PATH = ROOT / 'sync' / 'mac-apple-mappings.json'
TASKS_PATH = ROOT / 'data' / 'tasks.json'


def load_json(path: Path, default: Any):
    if not path.exists():
        return default
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def main() -> int:
    mappings: Dict[str, str] = load_json(MAPPING_PATH, {})
    tasks_doc: Dict[str, Any] = load_json(TASKS_PATH, {'tasks': []})
    tasks = {str(task.get('id')): task for task in tasks_doc.get('tasks', []) if task.get('id')}

    old_style: List[Dict[str, Any]] = []
    new_style: List[Dict[str, Any]] = []
    missing_tasks: List[str] = []

    for task_id, reminder_id in mappings.items():
        task = tasks.get(task_id)
        if not task:
            missing_tasks.append(task_id)
            continue
        row = {
            'task_id': task_id,
            'title': task.get('title', ''),
            'category': task.get('category', ''),
            'bucket': task.get('bucket', ''),
            'reminder_id': reminder_id,
        }
        if str(reminder_id).startswith('x-apple-reminder://'):
            old_style.append(row)
        else:
            new_style.append(row)

    result = {
        'status': 'ok',
        'summary': {
            'total_mappings': len(mappings),
            'old_style_count': len(old_style),
            'new_style_count': len(new_style),
            'missing_tasks_count': len(missing_tasks),
        },
        'old_style': old_style,
        'missing_tasks': missing_tasks,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
