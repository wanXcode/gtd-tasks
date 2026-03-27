#!/usr/bin/env python3
"""Mac Sync Agent - 从服务端同步任务到 Apple Reminders

Phase 2 核心组件：
- 从服务端 /api/changes 拉增量
- 同步到 Apple Reminders（创建/更新/完成）
- 回写 Apple completed 到服务端
- 维护本地同步游标

Usage:
    # 手动运行一次
    python3 scripts/sync_agent_mac.py

    # 指定服务端地址
    GTD_API_BASE_URL=http://server:8000 python3 scripts/sync_agent_mac.py

    # launchd 定时运行（建议每分钟）
    # 配置参考 minimal-deployment.md
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))

# 配置
TZ = ZoneInfo('Asia/Shanghai')
DEFAULT_API_URL = os.getenv('GTD_API_BASE_URL', 'https://gtd.5666.net')
DEFAULT_CLIENT_ID = os.getenv('GTD_SYNC_CLIENT_ID', 'mac-primary')
SYNC_STATE_PATH = ROOT / 'sync' / 'mac-sync-state.json'
MAPPING_PATH = ROOT / 'sync' / 'mac-apple-mappings.json'
APPLE_SCRIPT_PATH = ROOT / 'sync_apple_reminders_mac.applescript'
LOG_PATH = ROOT / 'logs' / 'mac-sync-agent.log'
PULL_CACHE_SCRIPT = ROOT / 'scripts' / 'pull_tasks_cache.py'
RENDER_VIEWS_SCRIPT = ROOT / 'scripts' / 'render_views.py'

# Apple List 映射（按用户 Apple Reminders 实际分类）
BUCKET_TO_LIST = {
    'today': '下一步行动@NextAction',
    'tomorrow': '下一步行动@NextAction',
    'future': '可能的事@Maybe',
    'archive': '可能的事@Maybe',
}

# Category 到 Apple List 的映射
CATEGORY_TO_LIST = {
    'inbox': '收集箱@Inbox',
    'next_action': '下一步行动@NextAction',
    'project': '项目@Project',
    'waiting_for': '等待@Waiting For',
    'maybe': '可能的事@Maybe',
}


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec='seconds')


def log(msg: str) -> None:
    timestamp = now_iso()
    line = f"[{timestamp}] {msg}"
    print(line)
    # 追加到日志文件
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(line + '\n')


def default_sync_state() -> Dict[str, Any]:
    return {
        'client_id': DEFAULT_CLIENT_ID,
        'last_change_id': 0,
        'last_sync_at': None,
    }


def load_sync_state() -> Dict[str, Any]:
    """加载本地同步游标"""
    if SYNC_STATE_PATH.exists():
        try:
            with open(SYNC_STATE_PATH, 'r', encoding='utf-8') as f:
                state = json.load(f)
            if not isinstance(state, dict):
                raise ValueError('state is not a dict')
            if 'client_id' not in state:
                state['client_id'] = DEFAULT_CLIENT_ID
            if not isinstance(state.get('last_change_id', 0), int):
                state['last_change_id'] = int(state.get('last_change_id') or 0)
            state.setdefault('last_sync_at', None)
            return state
        except Exception as exc:
            log(f'Invalid sync state file, fallback to default: {exc}')
            return default_sync_state()
    return default_sync_state()


def save_sync_state(state: Dict[str, Any]) -> None:
    """保存本地同步游标"""
    SYNC_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SYNC_STATE_PATH, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.write('\n')


def load_mappings() -> Dict[str, str]:
    """加载 task_id -> apple_reminder_id 映射"""
    if MAPPING_PATH.exists():
        with open(MAPPING_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_mappings(mappings: Dict[str, str]) -> None:
    """保存 task_id -> apple_reminder_id 映射"""
    MAPPING_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MAPPING_PATH, 'w', encoding='utf-8') as f:
        json.dump(mappings, f, ensure_ascii=False, indent=2)
        f.write('\n')


def sync_mappings_from_server(base_url: str = DEFAULT_API_URL) -> Dict[str, str]:
    """从服务端拉取 apple mappings，并与本地合并"""
    local = load_mappings()
    try:
        resp = api_request('GET', '/api/apple/mappings', base_url=base_url)
        items = resp.get('items', []) if isinstance(resp, dict) else []
        merged = dict(local)
        for item in items:
            task_id = item.get('task_id')
            apple_id = item.get('apple_reminder_id')
            if task_id and apple_id and task_id not in merged:
                merged[task_id] = apple_id
        if merged != local:
            save_mappings(merged)
            log(f'Synced mappings from server: local={len(local)} merged={len(merged)}')
        return merged
    except Exception as exc:
        log(f'Failed to sync mappings from server: {exc}')
        return local


def api_request(method: str, path: str, payload: Optional[Dict] = None, base_url: str = DEFAULT_API_URL) -> Any:
    """调用服务端 API"""
    import ssl
    url = f"{base_url.rstrip('/')}{path}"
    data = None
    headers = {'Accept': 'application/json'}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    
    # 创建 SSL 上下文，禁用证书验证（解决 macOS 证书问题）
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
    # 允许不安全的重新协商，解决某些服务器的 SSL 握手问题（Python 3.12+）
    if hasattr(ssl, 'OP_LEGACY_SERVER_CONNECT'):
        ssl_context.options |= ssl.OP_LEGACY_SERVER_CONNECT
    
    try:
        with urllib.request.urlopen(req, timeout=60, context=ssl_context) as resp:
            body = resp.read().decode('utf-8')
            return json.loads(body) if body else None
    except urllib.error.HTTPError as exc:
        body = exc.read().decode('utf-8', errors='ignore')
        raise RuntimeError(f'API {method} {path} failed: {exc.code} {body}') from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f'API {method} {path} failed: {exc.reason}') from exc


def get_changes(since_change_id: int, limit: int = 100, base_url: str = DEFAULT_API_URL) -> Dict[str, Any]:
    """从服务端获取增量变更"""
    return api_request('GET', f'/api/changes?since_change_id={since_change_id}&limit={limit}', base_url=base_url)


def ack_changes(client_id: str, last_change_id: int, base_url: str = DEFAULT_API_URL) -> Dict[str, Any]:
    """确认已消费的变更"""
    return api_request(
        'POST',
        f'/api/sync/clients/{client_id}/ack',
        {'last_change_id': last_change_id, 'client_type': 'mac', 'meta': {'hostname': 'mac-local'}},
        base_url=base_url,
    )


def apple_script_exists() -> bool:
    """检查 AppleScript 是否存在"""
    return APPLE_SCRIPT_PATH.exists()


def refresh_local_cache_from_api(base_url: str = DEFAULT_API_URL) -> Dict[str, str]:
    """刷新本地 API cache 与渲染视图，供 AIGTD 查询使用"""
    env = os.environ.copy()
    env['GTD_API_BASE_URL'] = base_url
    pull = subprocess.run(
        ['python3', str(PULL_CACHE_SCRIPT), '--base-url', base_url],
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
    )
    if pull.returncode != 0:
        raise RuntimeError(f'pull_tasks_cache failed: {pull.stderr.strip() or pull.stdout.strip()}')

    render = subprocess.run(
        ['python3', str(RENDER_VIEWS_SCRIPT)],
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
    )
    if render.returncode != 0:
        raise RuntimeError(f'render_views failed: {render.stderr.strip() or render.stdout.strip()}')

    return {
        'pull_tasks_cache': pull.stdout.strip(),
        'render_views': render.stdout.strip(),
    }


def run_apple_script(action: str, **params) -> Dict[str, Any]:
    """运行 AppleScript 操作 Apple Reminders"""
    if not apple_script_exists():
        raise RuntimeError(f'AppleScript not found: {APPLE_SCRIPT_PATH}')
    
    # 构建 AppleScript 调用
    # 简化版：直接调用 osascript
    script_lines = []
    
    if action == 'create':
        # 创建 reminder
        title = params.get('title', '')
        list_name = params.get('list_name', 'GTD Today')
        note = params.get('note', '')
        script = f'''
tell application "Reminders"
    set targetList to list "{list_name}"
    tell targetList
        set newReminder to make new reminder with properties {{name:"{title}", body:"{note}"}}
        return id of newReminder
    end tell
end tell
'''
    elif action == 'complete':
        # 完成 reminder
        reminder_id = params.get('reminder_id', '')
        script = f'''
tell application "Reminders"
    set r to first reminder whose id is "{reminder_id}"
    set completed of r to true
    return "ok"
end tell
'''
    elif action == 'update':
        # 更新 reminder
        reminder_id = params.get('reminder_id', '')
        title = params.get('title', '')
        note = params.get('note', '')
        script = f'''
tell application "Reminders"
    set r to first reminder whose id is "{reminder_id}"
    set name of r to "{title}"
    set body of r to "{note}"
    return "ok"
end tell
'''
    elif action == 'move':
        # 移动 reminder 到另一个 list
        reminder_id = params.get('reminder_id', '')
        new_list = params.get('list_name', 'GTD Today')
        script = f'''
tell application "Reminders"
    set r to first reminder whose id is "{reminder_id}"
    set targetList to list "{new_list}"
    move r to targetList
    return "ok"
end tell
'''
    elif action == 'delete':
        reminder_id = params.get('reminder_id', '')
        script = f'''
tell application "Reminders"
    try
        set r to first reminder whose id is "{reminder_id}"
        delete r
        return "ok"
    on error
        return "not_found"
    end try
end tell
'''
    elif action == 'get_completed':
        # 获取已完成的 reminders（用于回写）
        # 只查询 GTD 相关的列表，避免遍历全部 reminders 导致超时
        script = '''
tell application "Reminders"
    set completedReminders to {}
    set gtdLists to {"收集箱@Inbox", "下一步行动@NextAction", "项目@Project", "等待@Waiting For", "可能的事@Maybe"}
    repeat with listName in gtdLists
        try
            set targetList to list listName
            repeat with r in reminders of targetList
                if completed of r is true and modification date of r > (current date) - 24 * hours then
                    set end of completedReminders to {id:(id of r), name:(name of r), completed_date:(completion date of r)}
                end if
            end repeat
        on error
            -- 列表不存在则跳过
        end try
    end repeat
    return completedReminders
end tell
'''
    else:
        raise ValueError(f'Unknown action: {action}')
    
    # 执行 AppleScript
    result = subprocess.run(
        ['osascript', '-e', script],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f'AppleScript failed: {result.stderr}')
    return {'stdout': result.stdout.strip(), 'stderr': result.stderr}


def sync_task_to_apple(change: Dict[str, Any]) -> Dict[str, Any]:
    """将单个任务变更同步到 Apple Reminders"""
    task = change.get('task', {})
    if not task:
        return {'status': 'skipped', 'reason': 'no_task_data'}
    
    action = change.get('action')
    task_id = task.get('id')
    title = task.get('title', '')
    bucket = task.get('bucket', 'today')
    category = task.get('category', 'next_action')
    note = task.get('note', '')
    # 优先使用 category 映射，否则用 bucket 映射
    list_name = CATEGORY_TO_LIST.get(category, BUCKET_TO_LIST.get(bucket, '下一步行动@NextAction'))
    
    # 获取现有的 Apple mapping（如果有）
    # 这里简化处理，实际应该查询本地缓存或服务端
    
    # 加载本地 mapping
    mappings = load_mappings()
    
    try:
        if action == 'create':
            # 如果已有 mapping，说明已同步过，避免重复创建
            if task_id and task_id in mappings:
                existing_apple_id = mappings[task_id]
                return {
                    'status': 'skipped',
                    'reason': 'already_mapped',
                    'task_id': task_id,
                    'apple_reminder_id': existing_apple_id,
                }
            
            # 创建新 reminder
            result = run_apple_script('create', title=title, list_name=list_name, note=note)
            apple_id = result.get('stdout', '').strip()
            # 保存到本地 mapping
            if apple_id and task_id:
                mappings[task_id] = apple_id
                save_mappings(mappings)
                log(f'Saved local mapping: {task_id} -> {apple_id}')
                # 同时回写到服务端
                try:
                    api_request('POST', '/api/apple/mappings', {
                        'mappings': [{'task_id': task_id, 'apple_reminder_id': apple_id}]
                    }, base_url=DEFAULT_API_URL)
                except Exception as e:
                    log(f'Failed to save mapping to server: {e}')
            return {'status': 'created', 'task_id': task_id, 'apple_reminder_id': apple_id}
        
        elif action == 'update':
            if not task_id or task_id not in mappings:
                return {'status': 'skipped', 'reason': 'update_missing_mapping', 'task_id': task_id}

            apple_id = mappings[task_id]
            update_result = run_apple_script('update', reminder_id=apple_id, title=title, note=note)
            move_result = None
            try:
                move_result = run_apple_script('move', reminder_id=apple_id, list_name=list_name)
            except Exception as move_exc:
                return {
                    'status': 'error',
                    'reason': f'update_move_failed: {move_exc}',
                    'task_id': task_id,
                    'apple_reminder_id': apple_id,
                }
            return {
                'status': 'updated',
                'task_id': task_id,
                'apple_reminder_id': apple_id,
                'update_stdout': update_result.get('stdout', ''),
                'move_stdout': (move_result or {}).get('stdout', ''),
            }
        
        elif action == 'done':
            if not task_id or task_id not in mappings:
                return {'status': 'skipped', 'reason': 'done_missing_mapping', 'task_id': task_id}

            apple_id = mappings[task_id]
            result = run_apple_script('complete', reminder_id=apple_id)
            return {
                'status': 'done',
                'task_id': task_id,
                'apple_reminder_id': apple_id,
                'stdout': result.get('stdout', ''),
            }
        
        elif action == 'delete':
            if not task_id or task_id not in mappings:
                return {'status': 'skipped', 'reason': 'delete_missing_mapping', 'task_id': task_id}

            apple_id = mappings[task_id]
            result = run_apple_script('delete', reminder_id=apple_id)
            mappings.pop(task_id, None)
            save_mappings(mappings)
            return {
                'status': 'deleted',
                'task_id': task_id,
                'apple_reminder_id': apple_id,
                'stdout': result.get('stdout', ''),
            }
        
        else:
            return {'status': 'skipped', 'reason': f'unknown_action_{action}'}
    
    except Exception as exc:
        return {'status': 'error', 'reason': str(exc)}


def check_reminder_completed(apple_reminder_id: str) -> bool:
    """检查单个 reminder 是否已完成"""
    try:
        script = f'''
tell application "Reminders"
    try
        set r to first reminder whose id is "{apple_reminder_id}"
        return completed of r
    on error
        return "not_found"
    end try
end tell
'''
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            stdout = result.stdout.strip()
            if stdout == 'true':
                return True
            elif stdout == 'false':
                return False
        return None
    except Exception:
        return None


def push_apple_completed_to_server(base_url: str = DEFAULT_API_URL) -> Dict[str, Any]:
    """将 Apple Reminders 的 completed 状态回写到服务端
    
    优化版：只查询本地 mapping 中的 reminder，避免遍历全部列表
    """
    try:
        # 加载本地 mapping
        mappings = load_mappings()
        if not mappings:
            log('No local mappings, skipping completed check')
            return {'status': 'ok', 'processed': 0, 'reason': 'no_mappings'}
        
        log(f'Checking {len(mappings)} reminders for completed status')
        
        # 只查询 mapping 中的 reminder
        completed_items = []
        for task_id, apple_id in list(mappings.items()):
            is_completed = check_reminder_completed(apple_id)
            if is_completed is True:
                completed_items.append({
                    'apple_reminder_id': apple_id,
                    'completed_at': datetime.now(TZ).isoformat(),
                })
                log(f'Reminder {apple_id} is completed')
            elif is_completed is None:
                log(f'Reminder {apple_id} not found or error, removing from mapping')
                del mappings[task_id]
        
        # 保存更新后的 mapping（移除已删除的）
        save_mappings(mappings)
        
        log(f'Found {len(completed_items)} completed reminders')
        
        if completed_items:
            response = api_request('POST', '/api/apple/completed', {'items': completed_items}, base_url=base_url)
            result = {'status': 'ok', 'processed': response.get('processed', 0)}
            if result['processed'] > 0:
                try:
                    refresh_result = refresh_local_cache_from_api(base_url=base_url)
                    result['cache_refresh'] = refresh_result
                    log(f"Refreshed local cache after completed push: {refresh_result}")
                except Exception as refresh_exc:
                    result['cache_refresh_error'] = str(refresh_exc)
                    log(f'Refresh local cache after completed push failed: {refresh_exc}')
            return result
        return {'status': 'ok', 'processed': 0, 'reason': 'no_completed_items'}
    
    except Exception as exc:
        log(f'Push completed error: {exc}')
        return {'status': 'error', 'reason': str(exc)}


def run_sync(base_url: str = DEFAULT_API_URL, dry_run: bool = False, full_sync: bool = False, reset_cursor: bool = False) -> Dict[str, Any]:
    """运行一次完整同步"""
    log(f'Starting sync (dry_run={dry_run}, full_sync={full_sync}, reset_cursor={reset_cursor})')
    
    state_file_exists = SYNC_STATE_PATH.exists()
    # 1. 加载本地状态
    state = load_sync_state()
    client_id = state.get('client_id', DEFAULT_CLIENT_ID)
    last_change_id = state.get('last_change_id', 0)

    auto_initial_full_sync = False
    if not state_file_exists:
        auto_initial_full_sync = True
        full_sync = True
        last_change_id = 0
        state['last_change_id'] = 0
        log('No sync state found; switching to initial full sync mode')

    if reset_cursor:
        last_change_id = 0
        state['last_change_id'] = 0
        log('Cursor reset requested; forcing last_change_id=0 for this run')

    log(f'Client: {client_id}, Last change_id: {last_change_id}')
    
    # 1.5 同步服务端 mappings 到本地，避免 full-sync 重复创建
    synced_mappings = sync_mappings_from_server(base_url=base_url)
    log(f'Available mappings: {len(synced_mappings)}')
    
    # 2. 获取任务（全量或增量）
    items = []
    try:
        if full_sync:
            # 全量同步：获取所有 open 任务
            tasks = get_all_open_tasks(base_url=base_url)
            items = [{'action': 'create', 'task': task} for task in tasks]
            next_change_id = last_change_id  # 全量同步不更新 change_id
            log(f'Got {len(items)} open tasks (full sync)')
        else:
            # 增量同步
            changes_resp = get_changes(last_change_id, base_url=base_url)
            items = changes_resp.get('items', [])
            next_change_id = changes_resp.get('next_change_id', last_change_id)
            log(f'Got {len(items)} changes')
    except Exception as exc:
        log(f'Failed to get changes: {exc}')
        return {'status': 'error', 'phase': 'get_changes', 'error': str(exc)}
    
    # 3. 同步到 Apple（如果不是 dry_run）
    sync_results = []
    if not dry_run and apple_script_exists():
        for change in items:
            result = sync_task_to_apple(change)
            sync_results.append(result)
            log(f"Sync task {change.get('task', {}).get('id')}: {result['status']}")
    elif not apple_script_exists():
        log('AppleScript not found, skipping Apple sync')
    else:
        log('Dry run mode, skipping Apple sync')
    
    # 4. 回写 Apple completed 到服务端（优化版：只查询本地 mapping）
    if not dry_run:
        push_result = push_apple_completed_to_server(base_url=base_url)
        log(f'Push completed result: {push_result}')
    
    # 5. Ack 已消费的变更
    if not dry_run and next_change_id > last_change_id:
        try:
            ack_result = ack_changes(client_id, next_change_id, base_url=base_url)
            log(f'Acked changes: {ack_result}')
            # 更新本地状态
            state['last_change_id'] = next_change_id
            state['last_sync_at'] = now_iso()
            save_sync_state(state)
        except Exception as exc:
            log(f'Failed to ack changes: {exc}')
            return {'status': 'error', 'phase': 'ack', 'error': str(exc)}
    elif not dry_run and full_sync and (auto_initial_full_sync or reset_cursor):
        state['last_change_id'] = next_change_id
        state['last_sync_at'] = now_iso()
        save_sync_state(state)
        log(f'Persisted sync state after recovery/full-sync run: last_change_id={next_change_id}')
    
    log('Sync completed')
    return {
        'status': 'ok',
        'changes_processed': len(items),
        'next_change_id': next_change_id,
        'sync_results': sync_results,
    }


def get_all_open_tasks(base_url: str = DEFAULT_API_URL) -> List[Dict[str, Any]]:
    """获取所有待办任务（用于全量同步）"""
    response = api_request('GET', '/api/tasks?status=open&limit=1000', base_url=base_url)
    return response.get('items', [])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Mac Sync Agent for GTD')
    parser.add_argument('--base-url', default=DEFAULT_API_URL, help='服务端 API 地址')
    parser.add_argument('--dry-run', action='store_true', help='只检查不执行')
    parser.add_argument('--init', action='store_true', help='初始化同步状态')
    parser.add_argument('--full-sync', action='store_true', help='全量同步所有待办任务到 Apple Reminders')
    parser.add_argument('--reset-cursor', action='store_true', help='将本地 last_change_id 临时重置为 0，用于恢复/补同步')
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    
    if args.init:
        # 初始化状态
        state = default_sync_state()
        save_sync_state(state)
        log(f'Initialized sync state: {SYNC_STATE_PATH}')
        return
    
    result = run_sync(
        base_url=args.base_url,
        dry_run=args.dry_run,
        full_sync=args.full_sync,
        reset_cursor=args.reset_cursor,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    # 返回非零退出码如果出错
    if result.get('status') != 'ok':
        sys.exit(1)


if __name__ == '__main__':
    main()
