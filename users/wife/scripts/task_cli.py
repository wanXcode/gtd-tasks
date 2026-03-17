#!/usr/bin/env python3
import argparse, json
from datetime import datetime
from pathlib import Path
import subprocess

ROOT = Path('/root/.openclaw/workspace/gtd-tasks/users/wife')
DATA = ROOT / 'data' / 'tasks.json'
RENDER = ROOT / 'scripts' / 'render_views.py'


def now_iso():
    return datetime.now().astimezone().isoformat(timespec='seconds')


def load_data():
    with open(DATA,'r',encoding='utf-8') as f:
        return json.load(f)


def save_data(data):
    data['meta']['updated_at'] = now_iso()
    with open(DATA,'w',encoding='utf-8') as f:
        json.dump(data,f,ensure_ascii=False,indent=2)
        f.write('\n')


def next_id(tasks):
    return f"wife_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def render():
    subprocess.run(['python3', str(RENDER)], check=True)


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('list')
    p.set_defaults(cmd='list')
    p = sub.add_parser('add')
    p.add_argument('title')
    p.add_argument('--bucket', default='today')
    p.set_defaults(cmd='add')
    args = parser.parse_args()
    data = load_data()
    if args.cmd == 'list':
        for t in data['tasks']:
            print(f"{t['id']} | {t['status']} | {t['bucket']} | {t['title']}")
    elif args.cmd == 'add':
        data['tasks'].append({
            'id': next_id(data['tasks']),
            'title': args.title,
            'status': 'open',
            'bucket': args.bucket,
            'quadrant': 'q2',
            'tags': [],
            'note': '',
            'source': 'cli',
            'source_task_id': None,
            'sync_version': 1,
            'deleted_at': None,
            'last_synced_at': None,
            'created_at': now_iso(),
            'updated_at': now_iso(),
            'completed_at': None
        })
        save_data(data)
        render()
        print('added')


if __name__ == '__main__':
    main()
