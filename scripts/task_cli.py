#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path('/root/.openclaw/workspace/gtd-tasks')
sys.path.insert(0, str(ROOT / 'scripts'))

from apple_reminders_sync_lib import maybe_auto_push, setup_logger  # noqa: E402

DATA = ROOT / 'data' / 'tasks.json'
RENDER = ROOT / 'scripts' / 'render_views.py'
TZ = ZoneInfo('Asia/Shanghai')
VALID_BUCKETS = ['today', 'tomorrow', 'future', 'archive']
VALID_QUADRANTS = ['q1', 'q2', 'q3', 'q4']
VALID_STATUSES = ['open', 'done', 'cancelled', 'archived']
VALID_CATEGORIES = ['index', 'project', 'next_action', 'waiting_for', 'maybe']
LOGGER = setup_logger('task_cli')


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
    task.setdefault('category', infer_category(task))
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


def infer_category(task):
    category = task.get('category')
    if category in VALID_CATEGORIES:
        return category

    tags = set(task.get('tags', []) or [])
    title = (task.get('title') or '')
    note = (task.get('note') or '')
    text = f"{title} {note}"
    bucket = task.get('bucket')

    waiting_keywords = ['等待', '确认', '回复', '回信', '跟进', '反馈', '催']
    project_keywords = ['项目', '规划', '方案', '系统', '搭建', '优化', '升级']
    action_keywords = ['给', '整理', '安排', '确认', '发送', '沟通', '推进', '处理']

    if tags & {'WAIT', 'FOLLOWUP', 'FOLLOW_UP'}:
        return 'waiting_for'
    if any(keyword in text for keyword in waiting_keywords):
        return 'waiting_for'
    if bucket == 'future':
        return 'maybe'
    if any(keyword in text for keyword in project_keywords):
        return 'project'
    if tags & {'ME'} or any(keyword in text for keyword in action_keywords):
        return 'next_action'
    return 'index'


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
    if getattr(args, 'category', None):
        items = [t for t in items if t.get('category') == args.category]
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
    base = f"{task['id']} | {task['status']} | {task.get('category', '-')} | {task['bucket']} | {task['quadrant']} | {task['title']}"
    if not verbose:
        return base
    tags = ','.join(task.get('tags', [])) or '-'
    note = task.get('note') or '-'
    return (
        f"{base}\n"
        f"  category={task.get('category', '-') }\n"
        f"  tags={tags}\n"
        f"  note={note}\n"
        f"  updated_at={task.get('updated_at')}\n"
        f"  completed_at={task.get('completed_at')}"
    )


def auto_push_after_write(task_ids, source, sync=False):
    if not sync:
        return
    try:
        result = maybe_auto_push(source=source, task_ids=task_ids, logger=LOGGER)
        LOGGER.info('auto push result: %s', result)
    except Exception as exc:
        LOGGER.warning('auto push failed: %s', exc)


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
        'category': args.category or None,
        'source': 'cli',
        'created_at': now_iso(),
        'updated_at': now_iso(),
        'completed_at': None,
    })
    data['tasks'].append(task)
    save_data(data)
    render()
    auto_push_after_write([task['id']], 'task_cli.add', sync=args.sync_apple_reminders)
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
    if args.category is not None:
        task['category'] = args.category
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
    auto_push_after_write([task['id']], 'task_cli.update', sync=args.sync_apple_reminders)
    print(f"updated: {task['id']}")


def cmd_done(args):
    data = load_data()
    task = find_task(data, args.id)
    set_status(task, 'done')
    bump_task(task)
    save_data(data)
    render()
    auto_push_after_write([task['id']], 'task_cli.done', sync=args.sync_apple_reminders)
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
    auto_push_after_write([task['id']], 'task_cli.reopen', sync=args.sync_apple_reminders)
    print(f"reopened: {task['id']}")


def cmd_list(args):
    data = load_data()
    tasks = apply_filters(data['tasks'], args)
    category_order = {name: idx for idx, name in enumerate(VALID_CATEGORIES)}
    tasks = sorted(tasks, key=lambda t: (t.get('status') != 'open', category_order.get(t.get('category', 'index'), 99), t.get('bucket', ''), t.get('id', '')))
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
    auto_push_after_write([task['id'] for task in tasks], 'task_cli.move', sync=args.sync_apple_reminders)
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
    auto_push_after_write([task['id'] for task in tasks], 'task_cli.tag', sync=args.sync_apple_reminders)
    print(f"tagged: {len(tasks)} task(s)")


def add_sync_flag(parser):
    parser.add_argument('--sync-apple-reminders', action='store_true', help='写入成功后尝试自动 push 到 Apple Reminders（默认关闭，也可用环境变量开启）')


def build_parser():
    parser = argparse.ArgumentParser(description='GTD task CLI')
    sub = parser.add_subparsers(dest='cmd', required=True)

    p = sub.add_parser('add')
    p.add_argument('title')
    p.add_argument('--bucket', default='future', choices=VALID_BUCKETS)
    p.add_argument('--quadrant', default='q2', choices=VALID_QUADRANTS)
    p.add_argument('--note')
    p.add_argument('--tags', nargs='*')
    p.add_argument('--category', choices=VALID_CATEGORIES)
    add_sync_flag(p)
    p.set_defaults(func=cmd_add)

    p = sub.add_parser('update')
    p.add_argument('id')
    p.add_argument('--title')
    p.add_argument('--bucket', choices=VALID_BUCKETS)
    p.add_argument('--quadrant', choices=VALID_QUADRANTS)
    p.add_argument('--note')
    p.add_argument('--category', choices=VALID_CATEGORIES)
    p.add_argument('--status', choices=VALID_STATUSES)
    p.add_argument('--set-tags', nargs='*')
    p.add_argument('--add-tags', nargs='*')
    p.add_argument('--remove-tags', nargs='*')
    add_sync_flag(p)
    p.set_defaults(func=cmd_update)

    p = sub.add_parser('done')
    p.add_argument('id')
    add_sync_flag(p)
    p.set_defaults(func=cmd_done)

    p = sub.add_parser('reopen')
    p.add_argument('id')
    p.add_argument('--bucket', choices=['today', 'tomorrow', 'future'])
    add_sync_flag(p)
    p.set_defaults(func=cmd_reopen)

    p = sub.add_parser('list')
    p.add_argument('--id')
    p.add_argument('--status', choices=VALID_STATUSES)
    p.add_argument('--bucket', choices=VALID_BUCKETS)
    p.add_argument('--quadrant', choices=VALID_QUADRANTS)
    p.add_argument('--category', choices=VALID_CATEGORIES)
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
    p.add_argument('--category', choices=VALID_CATEGORIES)
    p.add_argument('--tag')
    p.add_argument('--text')
    p.add_argument('--to-bucket', required=True, choices=VALID_BUCKETS)
    add_sync_flag(p)
    p.set_defaults(func=cmd_move)

    p = sub.add_parser('tag')
    p.add_argument('action', choices=['add', 'remove', 'set'])
    p.add_argument('tags', nargs='+')
    p.add_argument('--id')
    p.add_argument('--status', choices=VALID_STATUSES)
    p.add_argument('--bucket', choices=VALID_BUCKETS)
    p.add_argument('--quadrant', choices=VALID_QUADRANTS)
    p.add_argument('--category', choices=VALID_CATEGORIES)
    p.add_argument('--tag')
    p.add_argument('--text')
    add_sync_flag(p)
    p.set_defaults(func=cmd_tag)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
