#!/usr/bin/env python3
import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path('/root/.openclaw/workspace/gtd-tasks')
DATA = ROOT / 'data' / 'tasks.json'
RENDER = ROOT / 'scripts' / 'render_views.py'
TZ = ZoneInfo('Asia/Shanghai')
VALID_BUCKETS = ['today', 'tomorrow', 'future', 'archive']
VALID_QUADRANTS = ['q1', 'q2', 'q3', 'q4']
VALID_STATUSES = ['open', 'done', 'cancelled', 'archived']


def now_dt():
    return datetime.now(TZ)


def now_iso():
    return now_dt().isoformat(timespec='seconds')


def today_str():
    return now_dt().strftime('%Y-%m-%d')


def load_data():
    with open(DATA, 'r', encoding='utf-8') as f:
        data = json.load(f)
    data.setdefault('version', '0.2.1')
    data.setdefault('meta', {})
    data['meta'].setdefault('timezone', 'Asia/Shanghai')
    data['meta'].setdefault('business_date', today_str())
    data['meta'].setdefault('updated_at', now_iso())
    data.setdefault('tasks', [])
    for task in data['tasks']:
        normalize_task(task)
    return data


def normalize_task(task):
    task.setdefault('status', 'open')
    task.setdefault('bucket', 'future')
    task.setdefault('quadrant', 'q2')
    task.setdefault('tags', [])
    task.setdefault('note', '')
    task.setdefault('source', 'manual')
    task.setdefault('source_task_id', None)
    task.setdefault('sync_version', 1)
    task.setdefault('deleted_at', None)
    task.setdefault('last_synced_at', None)
    task.setdefault('created_at', now_iso())
    task.setdefault('updated_at', task['created_at'])
    task.setdefault('completed_at', None)
    return task


def save_data(data):
    data['meta']['updated_at'] = now_iso()
    data['meta']['business_date'] = today_str()
    with open(DATA, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')


def next_id(tasks):
    nums = []
    date_prefix = now_dt().strftime('%Y%m%d')
    for t in tasks:
        try:
            parts = t['id'].split('_')
            if len(parts) >= 3 and parts[1] == date_prefix:
                nums.append(int(parts[-1]))
        except Exception:
            pass
    n = max(nums) + 1 if nums else 1
    return f"tsk_{date_prefix}_{n:03d}"


def render():
    subprocess.run(['python3', str(RENDER)], check=True)


def bump_task(task):
    task['updated_at'] = now_iso()
    task['sync_version'] = int(task.get('sync_version', 1) or 1) + 1


def set_status(task, status):
    task['status'] = status
    if status == 'open':
        task['completed_at'] = None
        if task.get('bucket') == 'archive':
            task['bucket'] = 'future'
    else:
        task['completed_at'] = now_iso()
        if status in ('done', 'cancelled', 'archived'):
            task['bucket'] = 'archive'


def find_task(data, task_id):
    for task in data['tasks']:
        if task['id'] == task_id:
            return task
    raise SystemExit(f'task not found: {task_id}')


def apply_filters(tasks, args):
    items = tasks
    if getattr(args, 'id', None):
        items = [t for t in items if t['id'] == args.id]
    if getattr(args, 'status', None):
        items = [t for t in items if t.get('status') == args.status]
    if getattr(args, 'bucket', None):
        items = [t for t in items if t.get('bucket') == args.bucket]
    if getattr(args, 'quadrant', None):
        items = [t for t in items if t.get('quadrant') == args.quadrant]
    if getattr(args, 'tag', None):
        items = [t for t in items if args.tag in t.get('tags', [])]
    if getattr(args, 'text', None):
        needle = args.text.casefold()
        items = [
            t for t in items
            if needle in t.get('title', '').casefold() or needle in (t.get('note') or '').casefold()
        ]
    return items


def format_task(task, verbose=False):
    base = f"{task['id']} | {task['status']} | {task['bucket']} | {task['quadrant']} | {task['title']}"
    if not verbose:
        return base
    tags = ','.join(task.get('tags', [])) or '-'
    note = task.get('note') or '-'
    return (
        f"{base}\n"
        f"  tags={tags}\n"
        f"  note={note}\n"
        f"  updated_at={task.get('updated_at')}\n"
        f"  completed_at={task.get('completed_at')}"
    )


def cmd_add(args):
    data = load_data()
    task = normalize_task({
        'id': next_id(data['tasks']),
        'title': args.title,
        'status': 'open',
        'bucket': args.bucket,
        'quadrant': args.quadrant,
        'tags': sorted(set(args.tags or [])),
        'note': args.note or '',
        'source': 'cli',
        'created_at': now_iso(),
        'updated_at': now_iso(),
        'completed_at': None,
    })
    data['tasks'].append(task)
    save_data(data)
    render()
    print(f"added: {task['id']} {task['title']}")


def cmd_update(args):
    data = load_data()
    task = find_task(data, args.id)
    if args.title is not None:
        task['title'] = args.title
    if args.bucket is not None:
        task['bucket'] = args.bucket
    if args.quadrant is not None:
        task['quadrant'] = args.quadrant
    if args.note is not None:
        task['note'] = args.note
    if args.status is not None:
        set_status(task, args.status)
    if args.set_tags is not None:
        task['tags'] = sorted(set(args.set_tags))
    if args.add_tags:
        task['tags'] = sorted(set(task.get('tags', [])) | set(args.add_tags))
    if args.remove_tags:
        task['tags'] = [t for t in task.get('tags', []) if t not in set(args.remove_tags)]
    bump_task(task)
    save_data(data)
    render()
    print(f"updated: {task['id']}")


def cmd_done(args):
    data = load_data()
    task = find_task(data, args.id)
    set_status(task, 'done')
    bump_task(task)
    save_data(data)
    render()
    print(f"done: {task['id']}")


def cmd_reopen(args):
    data = load_data()
    task = find_task(data, args.id)
    set_status(task, 'open')
    if args.bucket is not None:
        task['bucket'] = args.bucket
    bump_task(task)
    save_data(data)
    render()
    print(f"reopened: {task['id']}")


def cmd_list(args):
    data = load_data()
    tasks = apply_filters(data['tasks'], args)
    tasks = sorted(tasks, key=lambda t: (t.get('status') != 'open', t.get('bucket', ''), t.get('id', '')))
    if args.limit:
        tasks = tasks[:args.limit]
    for t in tasks:
        print(format_task(t, verbose=args.verbose))


def cmd_move(args):
    data = load_data()
    tasks = apply_filters(data['tasks'], args)
    if not tasks:
        raise SystemExit('no tasks matched')
    for task in tasks:
        task['bucket'] = args.to_bucket
        if task.get('status') != 'open' and args.to_bucket != 'archive':
            task['status'] = 'open'
            task['completed_at'] = None
        bump_task(task)
    save_data(data)
    render()
    print(f"moved: {len(tasks)} task(s) -> {args.to_bucket}")


def cmd_tag(args):
    data = load_data()
    tasks = apply_filters(data['tasks'], args)
    if not tasks:
        raise SystemExit('no tasks matched')
    for task in tasks:
        tags = set(task.get('tags', []))
        if args.action == 'add':
            tags.update(args.tags)
        elif args.action == 'remove':
            tags.difference_update(args.tags)
        elif args.action == 'set':
            tags = set(args.tags)
        task['tags'] = sorted(tags)
        bump_task(task)
    save_data(data)
    render()
    print(f"tagged: {len(tasks)} task(s)")


def build_parser():
    parser = argparse.ArgumentParser(description='GTD task CLI')
    sub = parser.add_subparsers(dest='cmd', required=True)

    p = sub.add_parser('add')
    p.add_argument('title')
    p.add_argument('--bucket', default='future', choices=VALID_BUCKETS)
    p.add_argument('--quadrant', default='q2', choices=VALID_QUADRANTS)
    p.add_argument('--note')
    p.add_argument('--tags', nargs='*')
    p.set_defaults(func=cmd_add)

    p = sub.add_parser('update')
    p.add_argument('id')
    p.add_argument('--title')
    p.add_argument('--bucket', choices=VALID_BUCKETS)
    p.add_argument('--quadrant', choices=VALID_QUADRANTS)
    p.add_argument('--note')
    p.add_argument('--status', choices=VALID_STATUSES)
    p.add_argument('--set-tags', nargs='*')
    p.add_argument('--add-tags', nargs='*')
    p.add_argument('--remove-tags', nargs='*')
    p.set_defaults(func=cmd_update)

    p = sub.add_parser('done')
    p.add_argument('id')
    p.set_defaults(func=cmd_done)

    p = sub.add_parser('reopen')
    p.add_argument('id')
    p.add_argument('--bucket', choices=['today', 'tomorrow', 'future'])
    p.set_defaults(func=cmd_reopen)

    p = sub.add_parser('list')
    p.add_argument('--id')
    p.add_argument('--status', choices=VALID_STATUSES)
    p.add_argument('--bucket', choices=VALID_BUCKETS)
    p.add_argument('--quadrant', choices=VALID_QUADRANTS)
    p.add_argument('--tag')
    p.add_argument('--text')
    p.add_argument('--limit', type=int)
    p.add_argument('--verbose', action='store_true')
    p.set_defaults(func=cmd_list)

    p = sub.add_parser('move')
    p.add_argument('--id')
    p.add_argument('--status', choices=VALID_STATUSES)
    p.add_argument('--bucket', choices=VALID_BUCKETS)
    p.add_argument('--quadrant', choices=VALID_QUADRANTS)
    p.add_argument('--tag')
    p.add_argument('--text')
    p.add_argument('--to-bucket', required=True, choices=VALID_BUCKETS)
    p.set_defaults(func=cmd_move)

    p = sub.add_parser('tag')
    p.add_argument('action', choices=['add', 'remove', 'set'])
    p.add_argument('tags', nargs='+')
    p.add_argument('--id')
    p.add_argument('--status', choices=VALID_STATUSES)
    p.add_argument('--bucket', choices=VALID_BUCKETS)
    p.add_argument('--quadrant', choices=VALID_QUADRANTS)
    p.add_argument('--tag')
    p.add_argument('--text')
    p.set_defaults(func=cmd_tag)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
