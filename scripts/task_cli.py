#!/usr/bin/env python3
import argparse
import json
from datetime import datetime
from pathlib import Path

ROOT = Path('/root/.openclaw/workspace/gtd-tasks')
DATA = ROOT / 'data' / 'tasks.json'
RENDER = ROOT / 'scripts' / 'render_views.py'


def now_iso():
    return datetime.now().astimezone().isoformat(timespec='seconds')


def load_data():
    with open(DATA, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_data(data):
    data['meta']['updated_at'] = now_iso()
    with open(DATA, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')


def next_id(tasks):
    nums = []
    for t in tasks:
        try:
            nums.append(int(t['id'].split('_')[-1]))
        except Exception:
            pass
    n = max(nums) + 1 if nums else 1
    return f"tsk_{datetime.now().strftime('%Y%m%d')}_{n:03d}"


def render():
    import subprocess
    subprocess.run(['python3', str(RENDER)], check=True)


def cmd_add(args):
    data = load_data()
    task = {
        'id': next_id(data['tasks']),
        'title': args.title,
        'status': 'open',
        'bucket': args.bucket,
        'quadrant': args.quadrant,
        'tags': args.tags or [],
        'note': args.note or '',
        'source': 'cli',
        'created_at': now_iso(),
        'updated_at': now_iso(),
        'completed_at': None
    }
    data['tasks'].append(task)
    save_data(data)
    render()
    print(f"added: {task['id']} {task['title']}")


def find_task(data, task_id):
    for task in data['tasks']:
        if task['id'] == task_id:
            return task
    raise SystemExit(f'task not found: {task_id}')


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
        task['status'] = args.status
        if args.status in ('done', 'cancelled', 'archived'):
            task['completed_at'] = now_iso()
    task['updated_at'] = now_iso()
    save_data(data)
    render()
    print(f"updated: {task['id']}")


def cmd_done(args):
    data = load_data()
    task = find_task(data, args.id)
    task['status'] = 'done'
    task['bucket'] = 'archive'
    task['completed_at'] = now_iso()
    task['updated_at'] = now_iso()
    save_data(data)
    render()
    print(f"done: {task['id']}")


def cmd_list(args):
    data = load_data()
    tasks = data['tasks']
    if args.status:
        tasks = [t for t in tasks if t['status'] == args.status]
    if args.bucket:
        tasks = [t for t in tasks if t['bucket'] == args.bucket]
    for t in tasks:
        print(f"{t['id']} | {t['status']} | {t['bucket']} | {t['title']}")


def main():
    parser = argparse.ArgumentParser(description='GTD task CLI')
    sub = parser.add_subparsers(dest='cmd', required=True)

    p = sub.add_parser('add')
    p.add_argument('title')
    p.add_argument('--bucket', default='today', choices=['today', 'tomorrow', 'future', 'archive'])
    p.add_argument('--quadrant', default='q2', choices=['q1', 'q2', 'q3', 'q4'])
    p.add_argument('--note')
    p.add_argument('--tags', nargs='*')
    p.set_defaults(func=cmd_add)

    p = sub.add_parser('update')
    p.add_argument('id')
    p.add_argument('--title')
    p.add_argument('--bucket', choices=['today', 'tomorrow', 'future', 'archive'])
    p.add_argument('--quadrant', choices=['q1', 'q2', 'q3', 'q4'])
    p.add_argument('--note')
    p.add_argument('--status', choices=['open', 'done', 'cancelled', 'archived'])
    p.set_defaults(func=cmd_update)

    p = sub.add_parser('done')
    p.add_argument('id')
    p.set_defaults(func=cmd_done)

    p = sub.add_parser('list')
    p.add_argument('--status')
    p.add_argument('--bucket')
    p.set_defaults(func=cmd_list)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
