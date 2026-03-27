#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))

from apple_reminders_sync_lib import maybe_auto_push, setup_logger  # noqa: E402
from task_repository import get_repository, TaskRepository, TaskMutationResult  # noqa: E402

DATA = ROOT / 'data' / 'tasks.json'
RENDER = ROOT / 'scripts' / 'render_views.py'
PULL_CACHE = ROOT / 'scripts' / 'pull_tasks_cache.py'
TZ = ZoneInfo('Asia/Shanghai')
VALID_BUCKETS = ['today', 'tomorrow', 'future', 'archive']
VALID_QUADRANTS = ['q1', 'q2', 'q3', 'q4']
VALID_STATUSES = ['open', 'done', 'cancelled', 'archived']
VALID_CATEGORIES = ['inbox', 'project', 'next_action', 'waiting_for', 'maybe']
LOGGER = setup_logger('task_cli')


def now_dt():
    return datetime.now(TZ)


def now_iso():
    return now_dt().isoformat(timespec='seconds')


def today_str():
    return now_dt().strftime('%Y-%m-%d')


def render():
    subprocess.run(['python3', str(RENDER)], check=True)


def refresh_api_cache():
    subprocess.run(['python3', str(PULL_CACHE)], check=True)
    render()


def refresh_after_write(backend: str):
    if backend == 'api':
        refresh_api_cache()
    elif backend == 'local':
        render()


def auto_push_after_write(task_ids, source, sync=False, backend='local'):
    if not sync:
        return
    if backend != 'local':
        LOGGER.info('auto push skipped: backend is %s', backend)
        return
    try:
        result = maybe_auto_push(source=source, changed_only=True, logger=LOGGER)
        LOGGER.info('auto push result: %s', result)
    except Exception as exc:
        LOGGER.warning('auto push failed: %s', exc)


def apply_filters(tasks, args):
    include_deleted = getattr(args, 'include_deleted', False)
    items = tasks if include_deleted else [t for t in tasks if not t.get('deleted_at')]
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


def cmd_add(args):
    repo = get_repository(args.backend)
    result = repo.add_task(
        title=args.title,
        bucket=args.bucket,
        quadrant=args.quadrant,
        note=args.note or '',
        tags=args.tags or [],
        category=args.category,
        source='cli',
    )
    refresh_after_write(args.backend)
    auto_push_after_write([result.task['id']], 'task_cli.add', sync=args.sync_apple_reminders, backend=args.backend)
    print(f"added: {result.task['id']} {result.task['title']}")


def cmd_update(args):
    repo = get_repository(args.backend)
    updates = {}
    if args.title is not None:
        updates['title'] = args.title
    if args.bucket is not None:
        updates['bucket'] = args.bucket
    if args.quadrant is not None:
        updates['quadrant'] = args.quadrant
    if args.note is not None:
        updates['note'] = args.note
    if args.category is not None:
        updates['category'] = args.category
    if args.status is not None:
        updates['status'] = args.status
    if args.set_tags is not None:
        updates['set_tags'] = args.set_tags
    if args.add_tags:
        updates['add_tags'] = args.add_tags
    if args.remove_tags:
        updates['remove_tags'] = args.remove_tags
    result = repo.update_task(args.id, updates)
    refresh_after_write(args.backend)
    auto_push_after_write([result.task['id']], 'task_cli.update', sync=args.sync_apple_reminders, backend=args.backend)
    print(f"updated: {result.task['id']}")


def cmd_done(args):
    repo = get_repository(args.backend)
    result = repo.mark_done(args.id)
    refresh_after_write(args.backend)
    auto_push_after_write([result.task['id']], 'task_cli.done', sync=args.sync_apple_reminders, backend=args.backend)
    print(f"done: {result.task['id']}")


def cmd_reopen(args):
    repo = get_repository(args.backend)
    bucket = args.bucket if hasattr(args, 'bucket') else None
    result = repo.reopen_task(args.id, bucket=bucket)
    refresh_after_write(args.backend)
    auto_push_after_write([result.task['id']], 'task_cli.reopen', sync=args.sync_apple_reminders, backend=args.backend)
    print(f"reopened: {result.task['id']}")


def cmd_delete(args):
    repo = get_repository(args.backend)
    result = repo.delete_task(args.id)
    refresh_after_write(args.backend)
    auto_push_after_write([result.task['id']], 'task_cli.delete', sync=args.sync_apple_reminders, backend=args.backend)
    print(f"deleted: {result.task['id']}")


def cmd_list(args):
    repo = get_repository(args.backend)
    tasks = repo.list_tasks()
    tasks = apply_filters(tasks, args)
    category_order = {name: idx for idx, name in enumerate(VALID_CATEGORIES)}
    tasks = sorted(tasks, key=lambda t: (t.get('status') != 'open', category_order.get((t.get('category') or 'inbox').replace('index', 'inbox'), 99), t.get('bucket', ''), t.get('id', '')))
    if args.limit:
        tasks = tasks[:args.limit]
    for t in tasks:
        print(format_task(t, verbose=args.verbose))


def cmd_move(args):
    repo = get_repository(args.backend)
    tasks = repo.list_tasks()
    tasks = apply_filters(tasks, args)
    if not tasks:
        raise SystemExit('no tasks matched')
    task_ids = [t['id'] for t in tasks]
    if hasattr(repo, 'move_tasks'):
        result = repo.move_tasks(task_ids, args.to_bucket)
    else:
        for task_id in task_ids:
            repo.update_task(task_id, {'bucket': args.to_bucket})
        result = type('Result', (), {'changed_ids': task_ids})()
    if args.backend == 'local':
        render()
    auto_push_after_write(result.changed_ids, 'task_cli.move', sync=args.sync_apple_reminders, backend=args.backend)
    print(f"moved: {len(result.changed_ids)} task(s) -> {args.to_bucket}")


def cmd_tag(args):
    repo = get_repository(args.backend)
    tasks = repo.list_tasks()
    tasks = apply_filters(tasks, args)
    if not tasks:
        raise SystemExit('no tasks matched')
    task_ids = [t['id'] for t in tasks]
    if hasattr(repo, 'tag_tasks'):
        result = repo.tag_tasks(task_ids, args.action, args.tags)
    else:
        for task_id in task_ids:
            current = repo.get_task(task_id) if hasattr(repo, 'get_task') else {}
            tags = set(current.get('tags', []))
            if args.action == 'add':
                tags.update(args.tags)
            elif args.action == 'remove':
                tags.difference_update(args.tags)
            elif args.action == 'set':
                tags = set(args.tags)
            repo.update_task(task_id, {'tags': sorted(tags)})
        result = type('Result', (), {'changed_ids': task_ids})()
    if args.backend == 'local':
        render()
    auto_push_after_write(result.changed_ids, 'task_cli.tag', sync=args.sync_apple_reminders, backend=args.backend)
    print(f"tagged: {len(result.changed_ids)} task(s)")


def add_sync_flag(parser):
    parser.add_argument('--sync-apple-reminders', action='store_true', help='写入成功后尝试自动 push 到 Apple Reminders（默认关闭，也可用环境变量开启）')


def build_parser():
    parser = argparse.ArgumentParser(description='GTD task CLI')
    parser.add_argument('--backend', choices=['local', 'api'], 
                        default=os.getenv('GTD_TASK_BACKEND', 'local'),
                        help='选择 backend：local（本地JSON）或 api（服务端API），默认从环境变量 GTD_TASK_BACKEND 读取')
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
    p.add_argument('--include-deleted', action='store_true', help='包含已删除任务')
    p.set_defaults(func=cmd_list)

    p = sub.add_parser('delete')
    p.add_argument('id')
    add_sync_flag(p)
    p.set_defaults(func=cmd_delete)

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
