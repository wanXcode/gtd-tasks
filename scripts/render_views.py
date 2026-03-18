#!/usr/bin/env python3
import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path('/root/.openclaw/workspace/gtd-tasks')
DATA = ROOT / 'data' / 'tasks.json'
TZ = ZoneInfo('Asia/Shanghai')
WEEKDAYS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']


def load_data():
    with open(DATA, 'r', encoding='utf-8') as f:
        data = json.load(f)
    data.setdefault('meta', {})
    data.setdefault('tasks', [])
    return data


def parse_dt(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).astimezone(TZ)
    except Exception:
        return None


def business_date(data):
    raw = data.get('meta', {}).get('business_date')
    if raw:
        return datetime.strptime(raw, '%Y-%m-%d').date()
    return datetime.now(TZ).date()


def fmt_cn_date(date_str):
    d = datetime.strptime(date_str, '%Y-%m-%d')
    return f"{date_str}（{WEEKDAYS[d.weekday()]}，北京时间）"


def fmt_cn_date_obj(d):
    return f"{d.strftime('%Y-%m-%d')}（{WEEKDAYS[d.weekday()]}，北京时间）"


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


def verbose_task_line(task, bullet='-'):
    tags = ', '.join(task.get('tags', [])) or '-'
    note = task.get('note') or '-'
    return f"{bullet} {task['title']} | {task.get('status')} | {task.get('bucket')} | {task.get('quadrant')} | tags={tags} | note={note}"


def by_bucket(tasks, bucket):
    return [t for t in tasks if t.get('status') == 'open' and t.get('bucket') == bucket]


def done_tasks(tasks):
    items = [t for t in tasks if t.get('status') in ('done', 'cancelled', 'archived')]
    return sorted(items, key=lambda x: x.get('completed_at') or x.get('updated_at') or '', reverse=True)


def render_today(data):
    tasks = data['tasks']
    meta = data['meta']
    bd = meta.get('business_date') or datetime.now(TZ).strftime('%Y-%m-%d')
    today = by_bucket(tasks, 'today')
    tomorrow = by_bucket(tasks, 'tomorrow')
    future = by_bucket(tasks, 'future')
    lines = [
        '# 今日待办 Today',
        '',
        f"日期：{fmt_cn_date(bd)}",
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


def render_done(data):
    tasks = data['tasks']
    done = [t for t in done_tasks(tasks) if t.get('status') == 'done']
    cancelled = [t for t in done_tasks(tasks) if t.get('status') == 'cancelled']
    archived = [t for t in done_tasks(tasks) if t.get('status') == 'archived']
    lines = [
        '# 已完成 Done',
        '',
        '由主库自动生成，方便集中查看最近完成 / 取消 / 归档事项。',
        '',
        f"生成时间：{datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S %Z')}",
        '',
        f"已完成：{len(done)} 项",
        f"已取消：{len(cancelled)} 项",
        f"已归档：{len(archived)} 项",
        '',
        '## 最近完成',
        '',
    ]
    lines += [verbose_task_line(t) for t in done[:50]] or ['（暂无）']
    lines += ['', '## 已取消', '']
    lines += [verbose_task_line(t) for t in cancelled[:50]] or ['（暂无）']
    lines += ['', '## 已归档', '']
    lines += [verbose_task_line(t) for t in archived[:50]] or ['（暂无）']
    return '\n'.join(lines) + '\n'


def render_weekly_review(data):
    tasks = data['tasks']
    bd = business_date(data)
    start = bd - timedelta(days=bd.weekday())
    end = start + timedelta(days=6)
    open_tasks = [t for t in tasks if t.get('status') == 'open']
    created_this_week = [
        t for t in tasks
        if (dt := parse_dt(t.get('created_at'))) and start <= dt.date() <= end
    ]
    completed_this_week = [
        t for t in tasks
        if t.get('status') in ('done', 'cancelled', 'archived') and (dt := parse_dt(t.get('completed_at') or t.get('updated_at'))) and start <= dt.date() <= end
    ]
    by_bucket_counts = {
        bucket: len([t for t in open_tasks if t.get('bucket') == bucket])
        for bucket in ['today', 'tomorrow', 'future', 'archive']
    }
    lines = [
        '# Weekly Review',
        '',
        f"统计周期：{fmt_cn_date_obj(start)} ～ {fmt_cn_date_obj(end)}",
        f"业务日期：{fmt_cn_date_obj(bd)}",
        '时间口径：Asia/Shanghai（UTC+8）',
        '',
        '## 本周概览',
        '',
        f"- 本周新增任务数：{len(created_this_week)}",
        f"- 本周完成/取消/归档任务数：{len(completed_this_week)}",
        f"- 当前未完成任务数：{len(open_tasks)}",
        '',
        '## 当前待办分桶',
        '',
        f"- today: {by_bucket_counts['today']}",
        f"- tomorrow: {by_bucket_counts['tomorrow']}",
        f"- future: {by_bucket_counts['future']}",
        '',
        '## 本周新增',
        '',
    ]
    lines += [verbose_task_line(t) for t in sorted(created_this_week, key=lambda x: x.get('created_at') or '', reverse=True)] or ['（暂无）']
    lines += ['', '## 本周完成', '']
    lines += [verbose_task_line(t) for t in sorted(completed_this_week, key=lambda x: x.get('completed_at') or x.get('updated_at') or '', reverse=True)] or ['（暂无）']
    lines += ['', '## 当前未完成任务概览', '']
    lines += [verbose_task_line(t) for t in sorted(open_tasks, key=lambda x: (x.get('bucket', ''), x.get('quadrant', ''), x.get('id', '')))] or ['（暂无）']
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
        lines = [f'# {title}', '', '由 v0.2.x 主库自动生成。', '', '## 待办', '']
        lines += [f"- [ ] {task_line(t, '').strip()}" for t in open_tasks] or ['（暂无）']
        lines += ['', '## 已完成', '']
        lines += [f"- [x] {task_line(t, '').strip()}" for t in done] or ['（暂无）']
        path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main():
    data = load_data()
    (ROOT / 'weekly').mkdir(exist_ok=True)
    (ROOT / 'today.md').write_text(render_today(data), encoding='utf-8')
    (ROOT / 'inbox.md').write_text(render_inbox(data), encoding='utf-8')
    (ROOT / 'done.md').write_text(render_done(data), encoding='utf-8')
    (ROOT / 'weekly' / 'review-latest.md').write_text(render_weekly_review(data), encoding='utf-8')
    render_matrix(data)


if __name__ == '__main__':
    main()
