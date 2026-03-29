#!/usr/bin/env python3
from __future__ import annotations

import json
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


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')


def main() -> int:
    mappings: Dict[str, str] = load_json(MAPPING_PATH, {})
    tasks_doc: Dict[str, Any] = load_json(TASKS_PATH, {'tasks': []})
    task_ids = {str(task.get('id')) for task in tasks_doc.get('tasks', []) if task.get('id')}

    removed: List[Dict[str, str]] = []
    kept: Dict[str, str] = {}

    for task_id, reminder_id in mappings.items():
        if task_id in task_ids:
            kept[task_id] = reminder_id
        else:
            removed.append({'task_id': task_id, 'reminder_id': reminder_id})

    save_json(MAPPING_PATH, kept)

    print(json.dumps({
        'status': 'ok',
        'removed_count': len(removed),
        'kept_count': len(kept),
        'removed': removed,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
