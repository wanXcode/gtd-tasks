#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import re

ROOT = Path(__file__).resolve().parent.parent
TASK_CLI = ROOT / 'scripts' / 'task_cli.py'
PULL_CACHE = ROOT / 'scripts' / 'pull_tasks_cache.py'
RENDER = ROOT / 'scripts' / 'render_views.py'
LOG_DIR = ROOT / 'logs'
LOG_PATH = LOG_DIR / 'aigtd-executor.log'
TOUCHPOINT = ROOT / 'scripts' / 'aigtd_touchpoint.py'
DEFAULT_API_BASE_URL = os.getenv('GTD_API_BASE_URL', 'https://gtd.5666.net')
TASK_ID_RE = re.compile(r'^tsk_\d{8}_\d+$')


class ExecutorError(RuntimeError):
    pass


def ensure_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault('GTD_API_BASE_URL', DEFAULT_API_BASE_URL)
    env.setdefault('GTD_TASK_BACKEND', 'api')
    return env


def run(cmd: list[str], *, env: dict[str, str], capture: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        check=True,
        text=True,
        capture_output=capture,
        env=env,
    )


def append_log(entry: dict[str, Any]) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')


def refresh(env: dict[str, str]) -> dict[str, str]:
    pull = run(['python3', str(PULL_CACHE)], env=env)
    render = run(['python3', str(RENDER)], env=env)
    return {
        'pull_tasks_cache': pull.stdout.strip(),
        'render_views': render.stdout.strip(),
    }


def emit_touchpoint(event: str, action: str, *, env: dict[str, str], title: str | None = None,
                    task_id: str | None = None, note: str | None = None) -> None:
    if not TOUCHPOINT.exists():
        return
    cmd = ['python3', str(TOUCHPOINT), event, '--action', action, '--source', 'aigtd_executor']
    session_key = env.get('AIGTD_SESSION_KEY')
    if title:
        cmd += ['--title', title]
    if task_id:
        cmd += ['--task-id', task_id]
    if session_key:
        cmd += ['--session-key', session_key]
    if note:
        cmd += ['--note', note]
    subprocess.run(cmd, check=False, text=True, capture_output=True, env=env)


def parse_task_list_output(text: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if ' | ' not in line:
            continue
        parts = line.split(' | ', 5)
        if len(parts) < 6:
            continue
        items.append({
            'id': parts[0],
            'status': parts[1],
            'category': parts[2],
            'bucket': parts[3],
            'quadrant': parts[4],
            'title': parts[5],
        })
    return items


def list_tasks_by_text(text: str, *, env: dict[str, str], limit: int = 20) -> list[dict[str, Any]]:
    proc = run([
        'python3', str(TASK_CLI), '--backend', 'api', 'list', '--text', text, '--limit', str(limit), '--verbose'
    ], env=env)
    return parse_task_list_output(proc.stdout)


def find_task_by_title(title: str, *, env: dict[str, str]) -> dict[str, Any] | None:
    needle = title.strip()
    if not needle:
        return None
    candidates = list_tasks_by_text(needle, env=env)
    exact = [item for item in candidates if (item.get('title') or '').strip() == needle]
    if exact:
        return exact[0]
    for item in candidates:
        if needle in (item.get('title') or ''):
            return item
    return None


def resolve_task_reference(ref: str, *, env: dict[str, str]) -> dict[str, Any]:
    ref = (ref or '').strip()
    if not ref:
        raise ExecutorError('task reference is required')
    if TASK_ID_RE.match(ref):
        return {'id': ref, 'matched_by': 'task_id'}

    candidates = list_tasks_by_text(ref, env=env)
    visible = [item for item in candidates if item.get('status') != 'deleted']
    exact = [item for item in visible if (item.get('title') or '').strip() == ref]
    if len(exact) == 1:
        return {'id': exact[0]['id'], 'matched_by': 'exact_title', 'task': exact[0]}
    if len(exact) > 1:
        sample = ', '.join(f"{item['id']}:{item['title']}" for item in exact[:5])
        raise ExecutorError(f'task reference is ambiguous: {ref} -> {sample}')

    contains = [item for item in visible if ref in (item.get('title') or '')]
    if len(contains) == 1:
        return {'id': contains[0]['id'], 'matched_by': 'title_contains', 'task': contains[0]}
    if len(contains) > 1:
        sample = ', '.join(f"{item['id']}:{item['title']}" for item in contains[:5])
        raise ExecutorError(f'task reference is ambiguous: {ref} -> {sample}')

    raise ExecutorError(f'task not found by reference: {ref}')


def execute_action(action: str, args: argparse.Namespace, *, env: dict[str, str]) -> dict[str, Any]:
    cmd = ['python3', str(TASK_CLI), '--backend', 'api']
    verify: dict[str, Any] = {'lookup': None}
    intent_title = getattr(args, 'title', None)
    intent_id = getattr(args, 'id', None)
    resolved_ref: dict[str, Any] | None = None
    resolved_id = intent_id

    if action == 'list':
        cmd += ['list']
        if args.status:
            cmd += ['--status', args.status]
        if args.bucket:
            cmd += ['--bucket', args.bucket]
        if args.category:
            cmd += ['--category', args.category]
        if args.quadrant:
            cmd += ['--quadrant', args.quadrant]
        if args.tag:
            for tag in args.tag:
                cmd += ['--tag', tag]
        if args.text:
            cmd += ['--text', args.text]
        if args.limit is not None:
            cmd += ['--limit', str(args.limit)]
        if args.verbose:
            cmd += ['--verbose']
        listed = run(cmd, env=env)
        return {
            'command': cmd,
            'stdout': listed.stdout.strip(),
            'stderr': listed.stderr.strip(),
            'refresh': {},
            'verify': {'count': len(parse_task_list_output(listed.stdout))},
        }

    if action in {'update', 'done', 'reopen', 'delete'}:
        resolved_ref = resolve_task_reference(intent_id, env=env)
        resolved_id = resolved_ref['id']
        args.id = resolved_id

    emit_touchpoint('intent', action, env=env, title=intent_title, task_id=resolved_id)

    if action == 'add':
        cmd += ['add', args.title, '--bucket', args.bucket, '--quadrant', args.quadrant]
        if args.note:
            cmd += ['--note', args.note]
        if args.category:
            cmd += ['--category', args.category]
        if args.tags:
            cmd += ['--tags', *args.tags]
    elif action == 'update':
        cmd += ['update', args.id]
        if args.title is not None:
            cmd += ['--title', args.title]
        if args.bucket is not None:
            cmd += ['--bucket', args.bucket]
        if args.quadrant is not None:
            cmd += ['--quadrant', args.quadrant]
        if args.note is not None:
            cmd += ['--note', args.note]
        if args.category is not None:
            cmd += ['--category', args.category]
        if args.status is not None:
            cmd += ['--status', args.status]
        if args.set_tags is not None:
            cmd += ['--set-tags', *args.set_tags]
        if args.add_tags:
            cmd += ['--add-tags', *args.add_tags]
        if args.remove_tags:
            cmd += ['--remove-tags', *args.remove_tags]
    elif action == 'done':
        cmd += ['done', args.id]
    elif action == 'reopen':
        cmd += ['reopen', args.id]
        if args.bucket:
            cmd += ['--bucket', args.bucket]
    elif action == 'delete':
        cmd += ['delete', args.id]
    else:
        raise ExecutorError(f'unsupported action: {action}')

    mutate = run(cmd, env=env)
    refresh_result = refresh(env)

    if action == 'add':
        verify['lookup'] = find_task_by_title(args.title, env=env)
    elif resolved_ref is not None:
        verify['resolved_reference'] = resolved_ref
        verify['lookup'] = resolved_ref.get('task') or {'id': resolved_ref['id']}
    elif getattr(args, 'id', None):
        verify['lookup'] = find_task_by_title(args.id, env=env)

    result = {
        'command': cmd,
        'stdout': mutate.stdout.strip(),
        'stderr': mutate.stderr.strip(),
        'refresh': refresh_result,
        'verify': verify,
    }
    verified_id = (verify.get('lookup') or {}).get('id') if isinstance(verify, dict) else None
    emit_touchpoint('success', action, env=env, title=intent_title, task_id=verified_id or intent_id)
    return result


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description='AIGTD controlled GTD executor (API-only)')
    sub = p.add_subparsers(dest='cmd', required=True)

    list_cmd = sub.add_parser('list', help='List tasks via API (read-only)')
    list_cmd.add_argument('--status', choices=['open', 'done', 'cancelled', 'archived'])
    list_cmd.add_argument('--bucket', choices=['today', 'tomorrow', 'future', 'archive'])
    list_cmd.add_argument('--category', choices=['inbox', 'project', 'next_action', 'waiting_for', 'maybe'])
    list_cmd.add_argument('--quadrant', choices=['q1', 'q2', 'q3', 'q4'])
    list_cmd.add_argument('--tag', action='append', default=[])
    list_cmd.add_argument('--text')
    list_cmd.add_argument('--limit', type=int, default=100)
    list_cmd.add_argument('--verbose', action='store_true')

    add = sub.add_parser('add', help='Add a task via API, then refresh cache/views')
    add.add_argument('title')
    add.add_argument('--bucket', default='future', choices=['today', 'tomorrow', 'future', 'archive'])
    add.add_argument('--quadrant', default='q2', choices=['q1', 'q2', 'q3', 'q4'])
    add.add_argument('--note')
    add.add_argument('--category', choices=['inbox', 'project', 'next_action', 'waiting_for', 'maybe'])
    add.add_argument('--tags', nargs='*')

    update = sub.add_parser('update', help='Update a task via API, then refresh cache/views')
    update.add_argument('id')
    update.add_argument('--title')
    update.add_argument('--bucket', choices=['today', 'tomorrow', 'future', 'archive'])
    update.add_argument('--quadrant', choices=['q1', 'q2', 'q3', 'q4'])
    update.add_argument('--note')
    update.add_argument('--category', choices=['inbox', 'project', 'next_action', 'waiting_for', 'maybe'])
    update.add_argument('--status', choices=['open', 'done', 'cancelled', 'archived'])
    update.add_argument('--set-tags', nargs='*')
    update.add_argument('--add-tags', nargs='*')
    update.add_argument('--remove-tags', nargs='*')

    done = sub.add_parser('done', help='Mark a task done via API, then refresh cache/views')
    done.add_argument('id')

    reopen = sub.add_parser('reopen', help='Reopen a task via API, then refresh cache/views')
    reopen.add_argument('id')
    reopen.add_argument('--bucket', choices=['today', 'tomorrow', 'future'])

    delete = sub.add_parser('delete', help='Delete a task via API, then refresh cache/views')
    delete.add_argument('id')

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    env = ensure_env()
    started_at = datetime.now(timezone.utc).isoformat()
    try:
        result = execute_action(args.cmd, args, env=env)
        payload = {
            'ok': True,
            'cmd': args.cmd,
            'started_at': started_at,
            'api_base_url': env.get('GTD_API_BASE_URL'),
            **result,
        }
        append_log(payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    except subprocess.CalledProcessError as exc:
        payload = {
            'ok': False,
            'cmd': args.cmd,
            'started_at': started_at,
            'api_base_url': env.get('GTD_API_BASE_URL'),
            'returncode': exc.returncode,
            'command': exc.cmd,
            'stdout': (exc.stdout or '').strip(),
            'stderr': (exc.stderr or '').strip(),
        }
        emit_touchpoint('failure', args.cmd, env=env, title=getattr(args, 'title', None), task_id=getattr(args, 'id', None), note=(exc.stderr or '').strip() or (exc.stdout or '').strip())
        append_log(payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2), file=sys.stderr)
        raise SystemExit(exc.returncode)
    except Exception as exc:
        payload = {
            'ok': False,
            'cmd': args.cmd,
            'started_at': started_at,
            'api_base_url': env.get('GTD_API_BASE_URL'),
            'error': str(exc),
        }
        emit_touchpoint('failure', args.cmd, env=env, title=getattr(args, 'title', None), task_id=getattr(args, 'id', None), note=str(exc))
        append_log(payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2), file=sys.stderr)
        raise SystemExit(1)


if __name__ == '__main__':
    main()
