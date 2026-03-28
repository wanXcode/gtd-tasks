#!/usr/bin/env python3
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))

# 设置默认使用服务端 API
os.environ.setdefault('GTD_TASK_BACKEND', 'api')
os.environ.setdefault('GTD_API_BASE_URL', 'https://gtd.5666.net')

from apple_reminders_sync_lib import maybe_auto_push, setup_logger  # noqa: E402

DATA = ROOT / 'data' / 'tasks.json'
TASK_CLI = ROOT / 'scripts' / 'task_cli.py'
TZ = ZoneInfo('Asia/Shanghai')
DEFAULT_BUCKET = 'future'
DEFAULT_QUADRANT = 'q2'
DEFAULT_CATEGORY = 'inbox'
LOGGER = setup_logger('nlp_capture')
BUCKET_KEYWORDS = [
    ('today', ['今天', '今日', '今晚', '今晚上', '今天内', '今天处理', '今天做']),
    ('tomorrow', ['明天', '明日', '明早', '明晚', '明天下午', '明天上午']),
]
TAG_PATTERNS = [
    ('ME', [r'#ME\b', r'我来处理', r'我自己做', r'我自己处理', r'我来做', r'我跟进', r'亲自处理', r'由我处理']),
    ('WAIT', [r'#WAIT\b', r'等确认', r'等回复', r'等待', r'待确认', r'待回复']),
    ('DELEGATE', [r'#DELEGATE\b', r'委托', r'让.+处理', r'安排.+处理', r'交给.+处理']),
]
QUADRANT_PATTERNS = [
    ('q1', [r'#Q1\b', r'紧急重要', r'马上处理', r'立即处理', r'尽快处理']),
    ('q2', [r'#Q2\b', r'重要不紧急', r'计划处理', r'后续推进', r'先放未来']),
    ('q3', [r'#Q3\b', r'紧急不重要']),
    ('q4', [r'#Q4\b', r'不紧急不重要']),
]
NOTE_HINTS = [
    '下周', '下下周', '月底', '月末', '周末', '等确认', '等回复', '后续推进',
    '已出初步方案', '需要确认', '等老板', '等对方'
]
STOP_PREFIXES = [
    '提醒我', '帮我', '记得', '记一下', '记录一下', '新增任务', '加个任务', '待办', 'todo', 'todo:', 'todo：'
]
TRIM_TAILS = ['先放未来', '放未来', '记一下', '提醒我', '帮我', '这件事', '这个事情']
CATEGORY_HINTS = {
    'waiting_for': ['等确认', '等回复', '等待', '待确认', '待回复', '跟进', '催一下', '等对方'],
    'project': ['项目', '规划', '方案', '系统', '版本', '升级', '搭建', '建设'],
    'next_action': ['给', '整理', '发送', '沟通', '安排', '处理', '推进', '确认一下', '回信'],
    'maybe': ['以后', '先放未来', '晚点', '有空再', '再说', '也许', '可能'],
}


def now_dt():
    return datetime.now(TZ)


def load_data():
    with open(DATA, 'r', encoding='utf-8') as f:
        data = json.load(f)
    data.setdefault('tasks', [])
    return data


def clean_spaces(text: str) -> str:
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def detect_bucket(text: str, default_bucket: str = DEFAULT_BUCKET):
    for bucket, kws in BUCKET_KEYWORDS:
        if any(kw in text for kw in kws):
            return bucket
    if re.search(r'下周|以后|晚点|过几天|之后|有空', text):
        return 'future'
    return default_bucket


def detect_tags(text: str):
    tags = set(re.findall(r'#([A-Za-z][A-Za-z0-9_-]*)', text))
    for tag, patterns in TAG_PATTERNS:
        if any(re.search(p, text, flags=re.I) for p in patterns):
            tags.add(tag)
    return sorted(tags)


def detect_quadrant(text: str, bucket: str, default_quadrant: str = DEFAULT_QUADRANT):
    for quadrant, patterns in QUADRANT_PATTERNS:
        if any(re.search(p, text, flags=re.I) for p in patterns):
            return quadrant
    if bucket == 'today' and re.search(r'尽快|马上|立即|urgent|紧急', text, flags=re.I):
        return 'q1'
    return default_quadrant


def extract_note(text: str):
    notes = []

    explicit = re.search(r'(?:备注|note)\s*[:：]\s*(.+)$', text, flags=re.I)
    if explicit:
        value = re.sub(r'#[A-Za-z][A-Za-z0-9_-]*', ' ', explicit.group(1))
        value = clean_spaces(value).strip(' ，,。；;:：')
        if value:
            notes.append(value)

    for hint in NOTE_HINTS:
        if hint in text:
            seg = re.search(rf'([^。；;，,]*{re.escape(hint)}[^。；;]*)', text)
            if seg:
                value = seg.group(1)
                value = re.sub(r'^(把|将)\s*', '', value)
                value = re.sub(r'#[A-Za-z][A-Za-z0-9_-]*', ' ', value)
                value = re.sub(r'(?:提醒我|帮我|记得|记一下|记录一下)\s*', ' ', value)
                value = re.sub(r'(?:今天|今日|今晚|明天|明日|下周|以后)\s*', ' ', value)
                value = clean_spaces(value).strip(' ，,。；;:：')
                if value and len(value) <= 30 and value not in notes:
                    notes.append(value)

    deduped = []
    for note in notes:
        if note not in deduped:
            deduped.append(note)
    return '；'.join(deduped)


def strip_tags_and_meta(text: str):
    text = re.sub(r'#[A-Za-z][A-Za-z0-9_-]*', ' ', text)
    meta_patterns = [
        r'今天', r'今日', r'今晚', r'明天', r'明日', r'下周', r'以后',
        r'提醒我', r'帮我', r'记得', r'记一下', r'记录一下', r'新增任务',
        r'我来处理', r'我自己做', r'我自己处理', r'我来做', r'我跟进', r'亲自处理',
        r'先放未来', r'放未来', r'等确认', r'等回复', r'待确认', r'待回复',
        r'紧急重要', r'重要不紧急', r'紧急不重要', r'不紧急不重要',
        r'备注[:：]?.*$', r'说明[:：]?.*$', r'note[:：]?.*$'
    ]
    for p in meta_patterns:
        text = re.sub(p, ' ', text, flags=re.I)
    return clean_spaces(text)


def derive_title(text: str):
    title = strip_tags_and_meta(text)
    for prefix in STOP_PREFIXES:
        if title.startswith(prefix):
            title = title[len(prefix):].strip()
    title = re.sub(r'^(把|将|给|替|去|要|先|再)\s*', '', title)
    title = re.sub(r'\b(后再推进|再推进|推进)\b$', '', title)
    title = re.sub(r'\s*[，,]\s*', ' ', title)
    for tail in TRIM_TAILS:
        if title.endswith(tail):
            title = title[:-len(tail)].strip()
    title = title.strip(' ，,。；;:：')
    title = re.sub(r'^(一下|一个|这件事|这个事情)\s*', '', title)
    return title or clean_spaces(text)


def detect_category(text: str, bucket: str, tags):
    if any(tag in tags for tag in ['WAIT', 'FOLLOWUP', 'FOLLOW_UP']):
        return 'waiting_for'
    if any(hint in text for hint in CATEGORY_HINTS['waiting_for']):
        return 'waiting_for'
    if any(hint in text for hint in CATEGORY_HINTS['maybe']):
        return 'maybe'
    if any(hint in text for hint in CATEGORY_HINTS['project']):
        return 'project'
    # ME 只代表“明确由我来处理”的标签，不应反向驱动所有任务都变成 next_action
    if any(hint in text for hint in CATEGORY_HINTS['next_action']):
        return 'next_action'
    return DEFAULT_CATEGORY


def build_preview(text: str, default_bucket: str, default_quadrant: str):
    raw = clean_spaces(text)
    bucket = detect_bucket(raw, default_bucket)
    tags = detect_tags(raw)
    quadrant = detect_quadrant(raw, bucket, default_quadrant)
    note = extract_note(raw)
    title = derive_title(raw)
    category = detect_category(raw, bucket, tags)
    return {
        'input': raw,
        'title': title,
        'bucket': bucket,
        'quadrant': quadrant,
        'category': category,
        'tags': tags,
        'note': note,
        'timezone': 'Asia/Shanghai',
        'business_now': now_dt().isoformat(timespec='seconds'),
        'mode': 'preview',
    }


def print_preview(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def apply_capture(preview, sync_apple_reminders=False):
    # 使用 task_repository 直接调用，而不是通过子进程调用 task_cli.py
    from task_repository import get_repository
    
    backend = os.getenv('GTD_TASK_BACKEND', 'local')
    repo = get_repository(backend)
    
    result = repo.add_task(
        title=preview['title'],
        bucket=preview['bucket'],
        quadrant=preview['quadrant'],
        note=preview.get('note', ''),
        tags=preview.get('tags', []),
        category=preview.get('category'),
        source='nlp',
    )
    
    # 如果需要同步 Apple Reminders 且是 local backend
    if sync_apple_reminders and backend == 'local':
        from apple_reminders_sync_lib import maybe_auto_push
        try:
            maybe_auto_push(source='nlp_capture.apply_capture', changed_only=True, logger=LOGGER)
        except Exception as exc:
            LOGGER.warning('auto push failed: %s', exc)
    
    return f"added: {result.task['id']} {result.task['title']}"


def build_parser():
    parser = argparse.ArgumentParser(description='Natural language task capture')
    parser.add_argument('text', help='自然语言任务描述')
    parser.add_argument('--mode', choices=['preview', 'apply'], default='preview')
    parser.add_argument('--default-bucket', choices=['today', 'tomorrow', 'future'], default=DEFAULT_BUCKET)
    parser.add_argument('--default-quadrant', choices=['q1', 'q2', 'q3', 'q4'], default=DEFAULT_QUADRANT)
    parser.add_argument('--sync-apple-reminders', action='store_true', help='apply 成功后尝试自动 push 到 Apple Reminders（默认关闭，也可用环境变量开启）')
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    preview = build_preview(args.text, args.default_bucket, args.default_quadrant)
    preview['mode'] = args.mode
    print_preview(preview)
    if args.mode == 'apply':
        result = apply_capture(preview, sync_apple_reminders=args.sync_apple_reminders)
        LOGGER.info('nlp apply result: %s', result)
        print(result)


if __name__ == '__main__':
    main()
