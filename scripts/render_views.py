#!/usr/bin/env python3
import json
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path('/root/.openclaw/workspace/gtd-tasks')
DATA = ROOT / 'data' / 'tasks.json'

WEEKDAYS = ['周一','周二','周三','周四','周五','周六','周日']


def load_data():
    with open(DATA, 'r', encoding='utf-8') as f:
        return json.load(f)


def fmt_cn_date(date_str):
    d = datetime.strptime(date_str, '%Y-%m-%d')
    return f"{date_str}（{WEEKDAYS[d.weekday()]}，北京时间）"


def task_line(task, bullet='•'):
    title = task['title']
    note = task.get('note') or ''
    prefix = '#ME ' if 'ME' in task.get('tags', []) else ''
    suffix = ' 👤' if 'ME' in task.get('tags', []) else ''
    text = f"{prefix}{title}"
    if note:
        text += f" — {note}"
    text += suffix
    return f"{bullet} {text}"


def by_bucket(tasks, bucket):
    return [t for t in tasks if t.get('status') == 'open' and t.get('bucket') == bucket]


def done_tasks(tasks):
    items = [t for t in tasks if t.get('status') in ('done', 'cancelled', 'archived')]
    return sorted(items, key=lambda x: x.get('completed_at') or x.get('updated_at') or '', reverse=True)


def render_today(data):
    tasks = data['tasks']
    meta = data['meta']
    business_date = meta['business_date']
    today = by_bucket(tasks, 'today')
    tomorrow = by_bucket(tasks, 'tomorrow')
    future = by_bucket(tasks, 'future')
    lines = [
        '# 今日待办 Today',
        '',
        f"日期：{fmt_cn_date(business_date)}",
        '模板：统一提醒模板（与早上 10 点 / 晚上 8:30 推送一致）',
        '时间口径：Asia/Shanghai（UTC+8）',
        '',
        '---',
        '',
        '哥哥，GTD 提醒来了：',
        '',
        '【今日】',
    ]
    lines += [task_line(t, '•') for t in today] or ['（暂无）']
    lines += ['', '【明日】']
    lines += [task_line(t, '•') for t in tomorrow] or ['（暂无）']
    lines += ['', '【未来】']
    lines += [task_line(t, '•') for t in future] or ['（暂无）']
    lines += [
        '',
        '【提醒】',
        '优先处理今日事项；明日项提前预判，未来项按节奏推进。',
        '',
        '---',
        '',
        '*说明：本文件中的“今日 / 明日 / 未来”一律按北京时间（UTC+8）解释；手动查看与定时推送使用同一模板骨架。*',
    ]
    return '\n'.join(lines) + '\n'


def render_inbox(data):
    tasks = data['tasks']
    today = by_bucket(tasks, 'today')
    tomorrow = by_bucket(tasks, 'tomorrow')
    future = by_bucket(tasks, 'future')
    done = done_tasks(tasks)
    lines = [
        '# 收集箱 Inbox',
        '',
        '新事项先放在这里，后续按“今日 / 明日 / 未来”维护，不再单独保留“待处理”。',
        '',
        '## 今日',
        '',
    ]
    lines += [task_line(t, '·') for t in today] or ['（暂无）']
    lines += ['', '## 明日', '']
    lines += [task_line(t, '·') for t in tomorrow] or ['（暂无）']
    lines += ['', '## 未来', '']
    lines += [task_line(t, '·') for t in future] or ['（暂无）']
    lines += ['', '<!-- 新事项自动添加在这里 -->', '', '## 已处理', '']
    lines += [task_line(t, '·') for t in done] or ['（暂无）']
    return '\n'.join(lines) + '\n'


def render_matrix(data):
    tasks = data['tasks']
    mapping = {
        'q1': ('Q1 紧急重要（立即做）', ROOT / 'matrix' / 'q1-urgent-important.md'),
        'q2': ('Q2 重要不紧急（计划做）', ROOT / 'matrix' / 'q2-important-not-urgent.md'),
        'q3': ('Q3 紧急不重要（委托做）', ROOT / 'matrix' / 'q3-urgent-not-important.md'),
        'q4': ('Q4 不紧急不重要（少做）', ROOT / 'matrix' / 'q4-not-urgent-not-important.md'),
    }
    for quadrant, (title, path) in mapping.items():
        open_tasks = [t for t in tasks if t.get('status') == 'open' and t.get('quadrant') == quadrant]
        done = [t for t in tasks if t.get('status') in ('done', 'cancelled', 'archived') and t.get('quadrant') == quadrant]
        lines = [f'# {title}', '', '由 v0.2.1 主库自动生成。', '', '## 待办', '']
        lines += [f"- [ ] {task_line(t, '').strip()}" for t in open_tasks] or ['（暂无）']
        lines += ['', '## 已完成', '']
        lines += [f"- [x] {task_line(t, '').strip()}" for t in done] or ['（暂无）']
        path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main():
    data = load_data()
    (ROOT / 'today.md').write_text(render_today(data), encoding='utf-8')
    (ROOT / 'inbox.md').write_text(render_inbox(data), encoding='utf-8')
    render_matrix(data)


if __name__ == '__main__':
    main()
