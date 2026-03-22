#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAIN_DATA = ROOT / 'data' / 'tasks.json'
WIFE_DATA = ROOT / 'users' / 'wife' / 'data' / 'tasks.json'


def load_json(path: Path):
    if not path.exists():
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def summarize(label: str, path: Path):
    data = load_json(path)
    if data is None:
        print(f'[{label}] 未找到主库: {path}')
        return

    tasks = data.get('tasks', [])
    open_tasks = [t for t in tasks if t.get('status') == 'open']
    done_tasks = [t for t in tasks if t.get('status') in ('done', 'cancelled', 'archived')]
    meta = data.get('meta', {})

    print(f'[{label}] 主库: {path}')
    print(f"- version: {data.get('version', 'unknown')}")
    print(f"- business_date: {meta.get('business_date', 'unknown')}")
    print(f"- timezone: {meta.get('timezone', 'unknown')}")
    print(f'- 任务总数: {len(tasks)}')
    print(f'- 未完成: {len(open_tasks)}')
    print(f'- 已处理: {len(done_tasks)}')


def main():
    print('GTD v0.2.1 迁移状态检查')
    print('说明：当前脚本为“迁移状态检查器”，不直接改写旧 markdown，也不覆盖现有 JSON 主库。')
    print('建议：如需从 legacy markdown 再迁一次，请先备份，再编写专项迁移逻辑。')
    print()
    summarize('main', MAIN_DATA)
    print()
    summarize('wife', WIFE_DATA)


if __name__ == '__main__':
    main()
