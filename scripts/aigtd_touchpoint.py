#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / 'logs'
LOG_PATH = LOG_DIR / 'aigtd-touchpoints.log'


def append_log(entry: dict[str, Any]) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')


def main() -> None:
    parser = argparse.ArgumentParser(description='Emit AIGTD executor touchpoint logs for observability')
    parser.add_argument('event', choices=['intent', 'success', 'failure'])
    parser.add_argument('--action', required=True)
    parser.add_argument('--title')
    parser.add_argument('--task-id')
    parser.add_argument('--session-key')
    parser.add_argument('--source', default='aigtd_executor')
    parser.add_argument('--note')
    args = parser.parse_args()

    payload = {
        'ts': datetime.now(timezone.utc).isoformat(),
        'event': args.event,
        'action': args.action,
        'title': args.title,
        'task_id': args.task_id,
        'session_key': args.session_key,
        'source': args.source,
        'note': args.note,
    }
    append_log(payload)
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == '__main__':
    main()
