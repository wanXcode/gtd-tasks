#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))

from apple_reminders_sync_lib import (  # noqa: E402
    EXPORT_PATH,
    PushNotConfigured,
    derive_export_output_path,
    export_sync_payload,
    git_sync_export,
    load_state,
    push_sync_payload,
    setup_logger,
)


def build_parser():
    parser = argparse.ArgumentParser(description='Unified Apple Reminders sync entrypoint')
    parser.add_argument('--mode', choices=['export', 'push', 'sync', 'status'], default='sync')
    parser.add_argument('--task-id', action='append', dest='task_ids', help='只导出/同步指定 task id，可重复传入；未显式传 --output 时默认写入 sync/tmp/ 临时文件')
    parser.add_argument('--changed-only', action='store_true', help='仅导出/同步自上次状态变化的任务；未显式传 --output 时默认写入共享 sync/apple-reminders-export.json')
    parser.add_argument('--output', type=Path, help='导出 JSON 输出路径；不传时：full/changed-only 写共享 export，单任务导出写临时文件')
    parser.add_argument('--dry-run', action='store_true', help='仅导出，不真正执行 AppleScript push')
    parser.add_argument('--git-sync', action='store_true', help='导出后尝试安全 git add/commit/push 仅限 sync 文件')
    parser.add_argument('--git-push', action='store_true', help='与 --git-sync 一起使用时，额外执行 git push')
    parser.add_argument('--pretty', action='store_true', help='输出 JSON 时格式化')
    return parser


def dump(obj, pretty=False):
    if pretty:
        print(json.dumps(obj, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(obj, ensure_ascii=False))


def main():
    parser = build_parser()
    args = parser.parse_args()
    logger = setup_logger('sync_apple_reminders')
    resolved_output = derive_export_output_path(task_ids=args.task_ids, changed_only=args.changed_only, output_path=args.output)

    if args.mode == 'status':
        dump(load_state(), pretty=True or args.pretty)
        return

    if args.mode == 'export':
        payload = export_sync_payload(task_ids=args.task_ids, changed_only=args.changed_only, output_path=args.output, logger=logger)
        result = {
            'status': 'exported',
            'task_count': len(payload.get('tasks', [])),
            'summary': payload.get('summary', {}),
            'output': str(resolved_output),
        }
        if args.git_sync or args.git_push:
            result['git_sync'] = git_sync_export(logger=logger, enable_commit=True, enable_push=args.git_push, dry_run=args.dry_run)
        dump(result, pretty=args.pretty)
        return

    if args.mode == 'push':
        try:
            result = push_sync_payload(export_path=args.output, logger=logger, dry_run=args.dry_run)
        except PushNotConfigured as exc:
            dump({'status': 'push_skipped', 'reason': str(exc)}, pretty=args.pretty)
            return
        dump(result, pretty=args.pretty)
        return

    payload = export_sync_payload(task_ids=args.task_ids, changed_only=args.changed_only, output_path=args.output, logger=logger)
    try:
        result = push_sync_payload(export_path=args.output, logger=logger, dry_run=args.dry_run)
        dump({
            'status': result.get('status', 'success'),
            'task_count': len(payload.get('tasks', [])),
            'summary': payload.get('summary', {}),
            'output': str(resolved_output),
        }, pretty=args.pretty)
    except PushNotConfigured as exc:
        dump({
            'status': 'push_skipped',
            'reason': str(exc),
            'task_count': len(payload.get('tasks', [])),
            'summary': payload.get('summary', {}),
            'output': str(resolved_output),
        }, pretty=args.pretty)


if __name__ == '__main__':
    main()
