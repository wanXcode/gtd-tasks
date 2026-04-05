#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
ALCH_STATE_PATH = Path('/root/.openclaw/workspace/scripts/.alchusdt_state.json')
TZ = ZoneInfo('Asia/Shanghai')
DEFAULT_API_BASE_URL = os.getenv('GTD_API_BASE_URL', 'https://gtd.5666.net').rstrip('/')
DEFAULT_API_TIMEOUT = float(os.getenv('GTD_API_TIMEOUT', '10'))
CATEGORY_ORDER = ['project', 'next_action', 'waiting_for', 'inbox', 'maybe']
CATEGORY_RANK = {name: idx for idx, name in enumerate(CATEGORY_ORDER)}
BUCKETS = ['today', 'tomorrow', 'future']
ME_TAGS = {'ME', '#ME'}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Generate GTD reminder digest directly from API open tasks')
    parser.add_argument('--mode', choices=['morning', 'evening'], default='morning')
    parser.add_argument('--base-url', default=DEFAULT_API_BASE_URL)
    parser.add_argument('--timeout', type=float, default=DEFAULT_API_TIMEOUT)
    parser.add_argument('--json', action='store_true', help='output structured JSON instead of plain text')
    parser.add_argument('--pretty', action='store_true', help='pretty print JSON output')
    return parser.parse_args()


def api_get_json(url: str, timeout: float) -> Any:
    req = urllib.request.Request(url, headers={'Accept': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode('utf-8')
            return json.loads(body)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode('utf-8', errors='ignore')
        raise RuntimeError(f'API request failed: {exc.code} {body}') from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f'API request failed: {exc.reason}') from exc


def fetch_open_tasks(base_url: str, timeout: float) -> list[dict[str, Any]]:
    payload = api_get_json(f'{base_url}/api/tasks?status=open&limit=500', timeout)
    if isinstance(payload, dict) and isinstance(payload.get('items'), list):
        return payload['items']
    if isinstance(payload, list):
        return payload
    raise RuntimeError('Unexpected API response: items not found')


def normalize_tag(tag: Any) -> str:
    text = str(tag or '').strip()
    if not text:
        return ''
    return '#' + text.lstrip('#').upper()


def task_display(task: dict[str, Any]) -> str:
    title = (task.get('title') or '').strip() or '未命名任务'
    tags = []
    seen = set()
    for raw in (task.get('tags') or []):
        pretty = normalize_tag(raw)
        if pretty and pretty not in seen:
            seen.add(pretty)
            tags.append(pretty)
    suffix = f" {' '.join(tags)}" if tags else ''
    return f'{title}{suffix}'


def is_me_task(task: dict[str, Any]) -> bool:
    normalized = {normalize_tag(tag) for tag in (task.get('tags') or [])}
    return bool(normalized & {'#ME'})


def sort_tasks(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def key(task: dict[str, Any]):
        category = (task.get('category') or 'inbox').replace('index', 'inbox')
        return (
            1 if is_me_task(task) else 0,
            CATEGORY_RANK.get(category, 99),
            task.get('due_date') or '9999-99-99',
            task.get('updated_at') or '',
            task.get('id') or '',
        )

    return sorted(tasks, key=key)


def bucketize(tasks: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    buckets = {name: [] for name in BUCKETS}
    seen_ids = set()
    seen_titles = set()
    for bucket in BUCKETS:
        current = []
        for task in tasks:
            if task.get('bucket') != bucket:
                continue
            task_id = task.get('id')
            title = (task.get('title') or '').strip()
            dedupe_key = task_id or title
            if not dedupe_key:
                continue
            if task_id and task_id in seen_ids:
                continue
            if title and title in seen_titles:
                continue
            current.append(task)
            if task_id:
                seen_ids.add(task_id)
            if title:
                seen_titles.add(title)
        buckets[bucket] = sort_tasks(current)
    return buckets


def load_alch_state() -> dict[str, Any]:
    if not ALCH_STATE_PATH.exists():
        return {}
    try:
        return json.loads(ALCH_STATE_PATH.read_text(encoding='utf-8'))
    except Exception:
        return {}


def fetch_alch_price(timeout: float) -> float | None:
    payload = api_get_json('https://fapi.binance.com/fapi/v1/ticker/price?symbol=ALCHUSDT', timeout)
    try:
        return float(payload['price'])
    except Exception:
        return None


def format_price_block(timeout: float) -> dict[str, str]:
    state = load_alch_state()
    current_price = fetch_alch_price(timeout)
    base_price_raw = state.get('base_price')
    try:
        base_price = float(base_price_raw) if base_price_raw is not None else None
    except Exception:
        base_price = None

    current_text = f'{current_price:.6f}' if current_price is not None else '暂无数据'
    base_text = f'{base_price:.6f}' if base_price is not None else '暂无数据'
    if current_price is not None and base_price not in (None, 0):
        pct = (current_price - base_price) / base_price * 100
        pct_text = f'{pct:+.2f}%'
    else:
        pct_text = '暂无数据'
    return {
        'current_price': current_text,
        'base_price': base_text,
        'change_pct': pct_text,
    }


def next_step(mode: str, buckets: dict[str, list[dict[str, Any]]]) -> str:
    today = buckets['today']
    tomorrow = buckets['tomorrow']
    future = buckets['future']
    if mode == 'evening':
        return '你直接回我今天完成了哪些、卡在哪、明天最先做什么，我再帮你顺手收一下明天安排。'
    if today:
        lead = task_display(today[0])
        return f'今天先从“{lead}”开推；今日项清完后，再看明日和未来。'
    if tomorrow:
        lead = task_display(tomorrow[0])
        return f'今天没有排进 today 的未完项，建议先把“{lead}”提前预热一下。'
    if future:
        lead = task_display(future[0])
        return f'当前没有 today / tomorrow 项，建议先从未来清单里挑“{lead}”定成下一步。'
    return '当前 open tasks 已清空，今天可以顺手做一次收集和排程。'


def render_lines(mode: str, buckets: dict[str, list[dict[str, Any]]], price_block: dict[str, str]) -> list[str]:
    mapping = [('today', '今日'), ('tomorrow', '明日'), ('future', '未来')]
    lines = ['哥哥，GTD 提醒来了：', '']
    for bucket_key, title in mapping:
        lines.append(f'【{title}】')
        items = buckets[bucket_key]
        if items:
            lines.extend([f'· {task_display(task)}' for task in items])
        else:
            lines.append('· 暂无未完成事项')
        lines.append('')
    lines.extend([
        '【币价监控】',
        f"· 当前价：{price_block['current_price']}",
        f"· 基准价：{price_block['base_price']}",
        f"· 涨跌幅：{price_block['change_pct']}",
        '',
        '【下一步】',
        f'· {next_step(mode, buckets)}',
    ])
    return lines


def build_payload(mode: str, tasks: list[dict[str, Any]], timeout: float) -> dict[str, Any]:
    open_tasks = [task for task in tasks if task.get('status') == 'open' and not task.get('deleted_at')]
    buckets = bucketize(open_tasks)
    price_block = format_price_block(timeout)
    rendered = '\n'.join(render_lines(mode, buckets, price_block))
    return {
        'generated_at': datetime.now(TZ).isoformat(timespec='seconds'),
        'timezone': 'Asia/Shanghai',
        'mode': mode,
        'source': 'api-open-tasks',
        'counts': {key: len(value) for key, value in buckets.items()},
        'tasks': {key: [{'id': t.get('id'), 'title': t.get('title'), 'display': task_display(t), 'bucket': t.get('bucket'), 'category': t.get('category'), 'tags': t.get('tags') or [], 'due_date': t.get('due_date')} for t in value] for key, value in buckets.items()},
        'price': price_block,
        'text': rendered,
    }


def main() -> None:
    args = parse_args()
    tasks = fetch_open_tasks(args.base_url, args.timeout)
    payload = build_payload(args.mode, tasks, args.timeout)
    if args.json:
        text = json.dumps(payload, ensure_ascii=False, indent=2 if args.pretty else None)
        print(text)
    else:
        print(payload['text'])


if __name__ == '__main__':
    main()
