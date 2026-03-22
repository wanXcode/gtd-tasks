#!/usr/bin/env python3
import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from zoneinfo import ZoneInfo

ROOT = Path('/root/.openclaw/workspace/gtd-tasks')
DATA_PATH = ROOT / 'data' / 'tasks.json'
EVENTS_PATH = ROOT / 'sync' / 'apple-reminders-completed-events.json'
APPLIED_LOG_PATH = ROOT / 'sync' / 'apple-reminders-completed-applied.json'
RENDER_SCRIPT = ROOT / 'scripts' / 'render_views.py'
TZ = ZoneInfo('Asia/Shanghai')


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec='seconds')


def load_json(path: Path, default: Any):
    if not path.exists():
        return default
    with path.open('r', encoding='utf-8') as f:
        return json.load(f)



def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')



def load_tasks() -> Dict[str, Any]:
    return load_json(DATA_PATH, {'tasks': [], 'meta': {}})



def load_events() -> Dict[str, Any]:
    return load_json(EVENTS_PATH, {'version': '0.4.0-phase1', 'events': []})



def load_applied() -> Dict[str, Any]:
    state = load_json(APPLIED_LOG_PATH, {'version': '0.4.0-phase1', 'applied_event_ids': [], 'applied_events': []})
    state.setdefault('applied_event_ids', [])
    state.setdefault('applied_events', [])
    return state



def render_views() -> None:
    subprocess.run(['python3', str(RENDER_SCRIPT)], check=True)



def find_task(tasks: List[Dict[str, Any]], gtd_id: str):
    for task in tasks:
        if task.get('id') == gtd_id:
            return task
    return None



def apply_done(task: Dict[str, Any], completed_at: str, source: str) -> bool:
    changed = False
    if task.get('status') != 'done':
        task['status'] = 'done'
        changed = True
    if task.get('bucket') != 'archive':
        task['bucket'] = 'archive'
        changed = True
    if task.get('completed_at') != completed_at:
        task['completed_at'] = completed_at
        changed = True
    sync_now = now_iso()
    if task.get('updated_at') != sync_now:
        task['updated_at'] = sync_now
        changed = True
    if task.get('last_synced_at') != sync_now:
        task['last_synced_at'] = sync_now
        changed = True
    next_sync_version = int(task.get('sync_version', 1) or 1) + 1
    if int(task.get('sync_version', 1) or 1) != next_sync_version:
        task['sync_version'] = next_sync_version
        changed = True
    return changed



def main() -> None:
    parser = argparse.ArgumentParser(description='Consume Apple Reminders completed->GTD done events')
    parser.add_argument('--events', type=Path, default=EVENTS_PATH, help='事件文件路径')
    parser.add_argument('--applied-log', type=Path, default=APPLIED_LOG_PATH, help='已消费事件日志路径')
    parser.add_argument('--dry-run', action='store_true', help='只预览，不写 tasks.json')
    parser.add_argument('--no-render', action='store_true', help='应用后不渲染视图')
    args = parser.parse_args()

    events_doc = load_json(args.events, {'events': []})
    applied = load_json(args.applied_log, {'applied_event_ids': [], 'applied_events': []})
    applied.setdefault('applied_event_ids', [])
    applied.setdefault('applied_events', [])
    applied_ids = set(applied.get('applied_event_ids', []))

    data = load_tasks()
    tasks = data.get('tasks', [])

    summary = {
        'seen': 0,
        'applied': 0,
        'skipped_no_gtd_id': 0,
        'skipped_duplicate': 0,
        'skipped_not_found': 0,
        'skipped_already_done': 0,
        'applied_event_ids': [],
        'errors': [],
    }

    for event in events_doc.get('events', []):
        summary['seen'] += 1
        event_id = str(event.get('event_id') or '').strip()
        event_type = str(event.get('event_type') or 'completed').strip()
        gtd_id = str(event.get('gtd_id') or '').strip()
        if event_type != 'completed':
            summary['errors'].append({'event_id': event_id or None, 'reason': f'unsupported_event_type:{event_type}'})
            continue
        if not gtd_id:
            summary['skipped_no_gtd_id'] += 1
            continue
        if event_id and event_id in applied_ids:
            summary['skipped_duplicate'] += 1
            continue

        task = find_task(tasks, gtd_id)
        if not task:
            summary['skipped_not_found'] += 1
            continue
        if task.get('deleted_at'):
            summary['skipped_not_found'] += 1
            continue
        if task.get('status') == 'done':
            if event_id:
                applied_ids.add(event_id)
                applied['applied_event_ids'].append(event_id)
                applied['applied_events'].append({
                    'event_id': event_id,
                    'event_type': event_type,
                    'gtd_id': gtd_id,
                    'status': 'already_done',
                    'applied_at': now_iso(),
                })
            summary['skipped_already_done'] += 1
            continue

        completed_at = str(event.get('completed_at') or now_iso())
        source = str(event.get('source') or 'apple_reminders_phase1')
        changed = apply_done(task, completed_at=completed_at, source=source)
        if changed:
            summary['applied'] += 1
        if event_id:
            applied_ids.add(event_id)
            applied['applied_event_ids'].append(event_id)
            applied['applied_events'].append({
                'event_id': event_id,
                'event_type': event_type,
                'gtd_id': gtd_id,
                'status': 'applied' if changed else 'no_change',
                'applied_at': now_iso(),
            })
            summary['applied_event_ids'].append(event_id)

    if not args.dry_run and summary['applied'] > 0:
        data.setdefault('meta', {})
        data['meta']['updated_at'] = now_iso()
        save_json(DATA_PATH, data)
        save_json(args.applied_log, applied)
        if not args.no_render:
            render_views()
    elif not args.dry_run:
        save_json(args.applied_log, applied)

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
