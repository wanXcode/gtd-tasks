#!/usr/bin/env python3
import json
from datetime import datetime
from pathlib import Path

ROOT = Path('/root/.openclaw/workspace/gtd-tasks/users/wife')
DATA = ROOT / 'data' / 'tasks.json'
WEEKDAYS = ['周一','周二','周三','周四','周五','周六','周日']


def load_data():
    with open(DATA, 'r', encoding='utf-8') as f:
        return json.load(f)


def fmt_cn_date(date_str):
    d = datetime.strptime(date_str, '%Y-%m-%d')
    return f"{date_str}（{WEEKDAYS[d.weekday()]}，北京时间）"


def task_line(task, bullet='•'):
    text = task['title']
    if task.get('note'):
        text += f" — {task['note']}"
    return f"{bullet} {text}"


def main():
    data = load_data()
    tasks = data['tasks']
    bd = data['meta']['business_date']
    today = [t for t in tasks if t.get('status') == 'open' and t.get('bucket') == 'today']
    tomorrow = [t for t in tasks if t.get('status') == 'open' and t.get('bucket') == 'tomorrow']
    future = [t for t in tasks if t.get('status') == 'open' and t.get('bucket') == 'future']
    done = [t for t in tasks if t.get('status') in ('done','cancelled','archived')]

    today_md = [
        '# 今日待办 - Today', '',
        '**用户**: wife',
        f"**日期**: {fmt_cn_date(bd)}", '', '---', '', '## 今日重点', ''
    ]
    today_md += [task_line(t, '•') for t in today] or ['_暂无 - 等待生成_']
    today_md += ['', '## 明日', '']
    today_md += [task_line(t, '•') for t in tomorrow] or ['_暂无_']
    today_md += ['', '## 未来', '']
    today_md += [task_line(t, '•') for t in future] or ['_暂无_']
    today_md += ['', '---', '', '*每日早 10 点自动生成，晚 8:30 回顾*']
    (ROOT / 'today.md').write_text('\n'.join(today_md) + '\n', encoding='utf-8')

    inbox_md = ['# 收集箱 - Inbox', '', '**用户**: wife', f"**最后更新**: {bd}", '', '---', '', '## 今日', '']
    inbox_md += [task_line(t, '·') for t in today] or ['_暂无 - 等待添加_']
    inbox_md += ['', '## 明日', '']
    inbox_md += [task_line(t, '·') for t in tomorrow] or ['_暂无_']
    inbox_md += ['', '## 未来', '']
    inbox_md += [task_line(t, '·') for t in future] or ['_暂无_']
    inbox_md += ['', '## 已处理', '']
    inbox_md += [task_line(t, '·') for t in done] or ['_暂无_']
    (ROOT / 'inbox.md').write_text('\n'.join(inbox_md) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
