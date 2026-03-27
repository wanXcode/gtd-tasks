#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SESSIONS_ROOT = Path('/root/.openclaw/agents/aigtd/sessions')
EXECUTOR_LOG = Path('/root/.openclaw/workspace/gtd-tasks/logs/aigtd-executor.log')
TOUCHPOINT_LOG = Path('/root/.openclaw/workspace/gtd-tasks/logs/aigtd-touchpoints.log')


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if not path.exists():
        return items
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return items


def scan_sessions(limit: int) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    session_files = sorted(SESSIONS_ROOT.glob('*.jsonl'), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]
    direct_file_ops = 0
    executor_mentions = 0
    no_reply_hits = 0
    for path in session_files:
        for idx, line in enumerate(path.read_text(encoding='utf-8', errors='ignore').splitlines(), start=1):
            if 'gtd-tasks/data/tasks.json' in line and ('"name":"write"' in line or '"name":"edit"' in line or '"name":"read"' in line):
                direct_file_ops += 1
                findings.append({'file': str(path), 'line': idx, 'kind': 'direct_tasks_json_op'})
            if 'aigtd_executor.py' in line:
                executor_mentions += 1
                findings.append({'file': str(path), 'line': idx, 'kind': 'executor_call'})
            if 'NO_REPLY' in line:
                no_reply_hits += 1
                findings.append({'file': str(path), 'line': idx, 'kind': 'no_reply'})
    return {
        'session_files_checked': len(session_files),
        'direct_tasks_json_ops': direct_file_ops,
        'executor_mentions': executor_mentions,
        'no_reply_hits': no_reply_hits,
        'sample_findings': findings[:20],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description='Verify whether AIGTD natural dialogue is adopting executor path')
    parser.add_argument('--session-limit', type=int, default=8)
    args = parser.parse_args()

    executor_entries = load_jsonl(EXECUTOR_LOG)
    touchpoint_entries = load_jsonl(TOUCHPOINT_LOG)
    session_scan = scan_sessions(args.session_limit)

    payload = {
        'executor_log_exists': EXECUTOR_LOG.exists(),
        'executor_entries': len(executor_entries),
        'last_executor_entry': executor_entries[-1] if executor_entries else None,
        'touchpoint_log_exists': TOUCHPOINT_LOG.exists(),
        'touchpoint_entries': len(touchpoint_entries),
        'last_touchpoint_entry': touchpoint_entries[-1] if touchpoint_entries else None,
        'session_scan': session_scan,
        'verdict': {
            'executor_path_observed': len(executor_entries) > 0,
            'natural_dialogue_still_has_direct_file_ops': session_scan['direct_tasks_json_ops'] > 0,
            'session_reset_likely_required': session_scan['direct_tasks_json_ops'] > 0,
        },
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
