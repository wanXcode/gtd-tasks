#!/usr/bin/env python3
import hashlib
import json
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
SYNC_DIR = ROOT / 'sync'
LOG_DIR = ROOT / 'logs'
TASKS_PATH = ROOT / 'data' / 'tasks.json'
MAPPING_PATH = ROOT / 'config' / 'apple_reminders_mapping.json'
EXPORT_PATH = SYNC_DIR / 'apple-reminders-export.json'
TMP_EXPORT_DIR = SYNC_DIR / 'tmp'
STATE_PATH = SYNC_DIR / 'apple-reminders-sync-state.json'
LOCAL_MAP_PATH = SYNC_DIR / 'apple-reminders-local-map.json'
DEFAULT_LOG_PATH = LOG_DIR / 'apple-reminders-sync.log'
EXPORT_SCRIPT = ROOT / 'scripts' / 'export_apple_reminders_sync.py'
MAC_SCRIPT = ROOT / 'sync_apple_reminders_mac.applescript'
TZ = ZoneInfo('Asia/Shanghai')
GIT_SYNC_ALLOWED_PATHS = [
    Path('sync/apple-reminders-export.json'),
    Path('sync/apple-reminders-sync-state.json'),
    Path('sync/apple-reminders-local-map.json'),
]

SYNC_ENV_FLAG = 'GTD_APPLE_REMINDERS_AUTO_PUSH'
SYNC_ENV_MODE = 'GTD_APPLE_REMINDERS_SYNC_MODE'
SYNC_ENV_SKIP = 'GTD_APPLE_REMINDERS_SKIP_PUSH'
SYNC_ENV_DRY_RUN = 'GTD_APPLE_REMINDERS_DRY_RUN'
SYNC_ENV_LOG_LEVEL = 'GTD_APPLE_REMINDERS_LOG_LEVEL'
GIT_SYNC_ENABLED_ENV = 'GTD_APPLE_REMINDERS_GIT_SYNC_ENABLED'
GIT_SYNC_COMMIT_ENV = 'GTD_APPLE_REMINDERS_GIT_COMMIT_ENABLED'
GIT_SYNC_PUSH_ENV = 'GTD_APPLE_REMINDERS_GIT_PUSH_ENABLED'
GIT_SYNC_DRY_RUN_ENV = 'GTD_APPLE_REMINDERS_GIT_DRY_RUN'
GIT_SYNC_REMOTE_ENV = 'GTD_APPLE_REMINDERS_GIT_REMOTE'
GIT_SYNC_BRANCH_ENV = 'GTD_APPLE_REMINDERS_GIT_BRANCH'


class SyncError(RuntimeError):
    pass


class PushSkipped(SyncError):
    pass


class PushNotConfigured(SyncError):
    pass


def now_dt() -> datetime:
    return datetime.now(TZ)


def now_iso() -> str:
    return now_dt().isoformat(timespec='seconds')


def ensure_dirs() -> None:
    SYNC_DIR.mkdir(parents=True, exist_ok=True)
    TMP_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def setup_logger(name: str = 'apple_reminders_sync', log_path: Path = DEFAULT_LOG_PATH) -> logging.Logger:
    ensure_dirs()
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    level_name = os.getenv(SYNC_ENV_LOG_LEVEL, 'INFO').upper()
    level = getattr(logging, level_name, logging.INFO)
    logger.setLevel(level)

    formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s | %(message)s')

    file_handler = logging.FileHandler(log_path, encoding='utf-8')
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(level)
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    logger.propagate = False
    return logger


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open('r', encoding='utf-8') as f:
        return json.load(f)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')


def file_sha256(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def bool_from_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {'1', 'true', 'yes', 'on'}


def should_auto_push(explicit: Optional[bool] = None) -> bool:
    if explicit is not None:
        return explicit
    if bool_from_env(SYNC_ENV_SKIP, False):
        return False
    mode = (os.getenv(SYNC_ENV_MODE) or '').strip().lower()
    if mode:
        return mode in {'auto', 'push', 'on'}
    return bool_from_env(SYNC_ENV_FLAG, False)


def load_state() -> Dict[str, Any]:
    state = load_json(STATE_PATH, {
        'version': '0.4.0-a',
        'updated_at': None,
        'last_export': {},
        'last_push': {},
        'tasks': {},
    })
    state.setdefault('version', '0.4.0-a')
    state.setdefault('updated_at', None)
    state.setdefault('last_export', {})
    state.setdefault('last_push', {})
    state.setdefault('tasks', {})
    return state


def save_state(state: Dict[str, Any]) -> None:
    state['updated_at'] = now_iso()
    save_json(STATE_PATH, state)


def load_tasks_doc() -> Dict[str, Any]:
    return load_json(TASKS_PATH, {'tasks': [], 'meta': {}})


def index_tasks_by_id(tasks: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {str(task.get('id')): task for task in tasks if task.get('id')}


def build_task_snapshot(task: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'title': task.get('title'),
        'status': task.get('status'),
        'bucket': task.get('bucket'),
        'quadrant': task.get('quadrant'),
        'category': task.get('category'),
        'tags': list(task.get('tags') or []),
        'note': task.get('note') or '',
        'updated_at': task.get('updated_at'),
        'sync_version': task.get('sync_version'),
    }


def calc_task_signature(task: Dict[str, Any]) -> str:
    payload = json.dumps(build_task_snapshot(task), ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def update_state_from_tasks(state: Dict[str, Any], tasks_doc: Dict[str, Any]) -> List[str]:
    task_index = index_tasks_by_id(tasks_doc.get('tasks', []))
    known = state.setdefault('tasks', {})
    changed_ids: List[str] = []

    for task_id, task in task_index.items():
        sig = calc_task_signature(task)
        record = known.get(task_id, {})
        if record.get('signature') != sig:
            changed_ids.append(task_id)
        record.update({
            'gtd_id': task_id,
            'status': task.get('status'),
            'updated_at': task.get('updated_at'),
            'sync_version': task.get('sync_version'),
            'signature': sig,
            'last_seen_at': now_iso(),
            'last_exported_at': record.get('last_exported_at'),
            'last_pushed_at': record.get('last_pushed_at'),
            'last_push_status': record.get('last_push_status'),
            'last_target_list': record.get('last_target_list'),
            'last_error': record.get('last_error'),
        })
        known[task_id] = record

    for task_id, record in list(known.items()):
        if task_id not in task_index:
            if record.get('status') != 'deleted':
                changed_ids.append(task_id)
            record['status'] = 'deleted'
            record['deleted_at'] = now_iso()
            record['last_seen_at'] = now_iso()
            known[task_id] = record

    return sorted(set(changed_ids))


def mark_exported_tasks(state: Dict[str, Any], exported_tasks: Iterable[Dict[str, Any]], exported_at: Optional[str] = None) -> None:
    stamp = exported_at or now_iso()
    for item in exported_tasks:
        task_id = str(item.get('gtd_id') or '')
        if not task_id:
            continue
        record = state.setdefault('tasks', {}).setdefault(task_id, {'gtd_id': task_id})
        record['last_exported_at'] = stamp
        record['last_target_list'] = item.get('target_list')
        record['exported_signature'] = record.get('signature')
        record['last_error'] = None


def mark_pushed_tasks(state: Dict[str, Any], exported_tasks: Iterable[Dict[str, Any]], pushed_at: Optional[str] = None, status: str = 'success', error: Optional[str] = None) -> None:
    stamp = pushed_at or now_iso()
    for item in exported_tasks:
        task_id = str(item.get('gtd_id') or '')
        if not task_id:
            continue
        record = state.setdefault('tasks', {}).setdefault(task_id, {'gtd_id': task_id})
        record['last_pushed_at'] = stamp
        record['last_push_status'] = status
        record['last_target_list'] = item.get('target_list')
        record['last_error'] = error


def build_incremental_tasks(tasks_doc: Dict[str, Any], task_ids: Optional[Iterable[str]] = None, changed_only: bool = False, state: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    tasks = list(tasks_doc.get('tasks', []))
    if task_ids:
        task_set = {str(item) for item in task_ids if item}
        return [task for task in tasks if str(task.get('id')) in task_set]
    if changed_only:
        local_state = state or load_state()
        selected = []
        for task in tasks:
            task_id = str(task.get('id') or '')
            if not task_id:
                continue
            record = local_state.get('tasks', {}).get(task_id, {})
            if record.get('exported_signature') != record.get('signature'):
                selected.append(task)
        return selected
    return tasks


def run_subprocess(cmd: List[str], logger: logging.Logger, check: bool = True) -> subprocess.CompletedProcess:
    logger.info('run command: %s', ' '.join(str(x) for x in cmd))
    completed = subprocess.run(cmd, capture_output=True, text=True)
    if completed.stdout.strip():
        logger.info('stdout: %s', completed.stdout.strip())
    if completed.stderr.strip():
        logger.warning('stderr: %s', completed.stderr.strip())
    if check and completed.returncode != 0:
        raise SyncError(completed.stderr.strip() or completed.stdout.strip() or f'command failed: {cmd}')
    return completed


def derive_export_output_path(task_ids: Optional[Iterable[str]] = None, changed_only: bool = False, output_path: Optional[Path] = None) -> Path:
    if output_path:
        return output_path
    if task_ids:
        ensure_dirs()
        task_part = '-'.join(sorted({str(task_id) for task_id in task_ids if task_id})) or 'task'
        safe_task_part = ''.join(ch if ch.isalnum() or ch in {'-', '_'} else '_' for ch in task_part)[:120]
        timestamp = now_dt().strftime('%Y%m%d-%H%M%S')
        return TMP_EXPORT_DIR / f'apple-reminders-task-export-{timestamp}-{safe_task_part}.json'
    return EXPORT_PATH


def export_sync_payload(task_ids: Optional[Iterable[str]] = None, changed_only: bool = False, output_path: Optional[Path] = None, logger: Optional[logging.Logger] = None) -> Dict[str, Any]:
    logger = logger or setup_logger()
    state = load_state()
    tasks_doc = load_tasks_doc()
    changed_ids = update_state_from_tasks(state, tasks_doc)
    payload_path = derive_export_output_path(task_ids=task_ids, changed_only=changed_only, output_path=output_path)

    cmd = ['python3', str(EXPORT_SCRIPT)]
    if task_ids:
        for task_id in task_ids:
            cmd += ['--task-id', str(task_id)]
    elif changed_only:
        cmd.append('--changed-only')
    cmd += ['--output', str(payload_path)]

    completed = run_subprocess(cmd, logger)
    payload = load_json(payload_path, {'tasks': []})
    exported_at = payload.get('generated_at') or now_iso()
    state['last_export'] = {
        'at': exported_at,
        'output_path': str(payload_path),
        'task_count': len(payload.get('tasks', [])),
        'stdout': completed.stdout.strip(),
        'changed_ids': changed_ids,
        'requested_task_ids': list(task_ids or []),
        'changed_only': bool(changed_only),
        'tasks_sha256': file_sha256(TASKS_PATH),
        'mapping_sha256': file_sha256(MAPPING_PATH),
        'export_sha256': file_sha256(payload_path),
    }
    mark_exported_tasks(state, payload.get('tasks', []), exported_at)
    save_state(state)
    return payload


def push_sync_payload(export_path: Optional[Path] = None, logger: Optional[logging.Logger] = None, dry_run: Optional[bool] = None) -> Dict[str, Any]:
    logger = logger or setup_logger()
    payload_path = export_path or EXPORT_PATH
    if not payload_path.exists():
        raise SyncError(f'export payload not found: {payload_path}')

    payload = load_json(payload_path, {'tasks': []})
    state = load_state()
    now = now_iso()
    dry_run = bool_from_env(SYNC_ENV_DRY_RUN, False) if dry_run is None else dry_run

    if dry_run:
        logger.info('dry-run push enabled, skip AppleScript push')
        state['last_push'] = {
            'at': now,
            'status': 'dry_run',
            'export_path': str(payload_path),
            'task_count': len(payload.get('tasks', [])),
            'apple_script': str(MAC_SCRIPT),
        }
        mark_pushed_tasks(state, payload.get('tasks', []), now, status='dry_run')
        save_state(state)
        return {'status': 'dry_run', 'task_count': len(payload.get('tasks', [])), 'export_path': str(payload_path)}

    if not MAC_SCRIPT.exists():
        raise PushNotConfigured(f'mac script not found: {MAC_SCRIPT}')

    if os.uname().sysname != 'Darwin':
        raise PushNotConfigured('push requires macOS/osascript; export succeeded, push skipped')

    cmd = ['osascript', str(MAC_SCRIPT), str(payload_path)]
    try:
        completed = run_subprocess(cmd, logger)
        state['last_push'] = {
            'at': now,
            'status': 'success',
            'export_path': str(payload_path),
            'task_count': len(payload.get('tasks', [])),
            'stdout': completed.stdout.strip(),
            'apple_script': str(MAC_SCRIPT),
        }
        mark_pushed_tasks(state, payload.get('tasks', []), now, status='success')
        save_state(state)
        return {'status': 'success', 'task_count': len(payload.get('tasks', [])), 'export_path': str(payload_path)}
    except Exception as exc:
        error = str(exc)
        state['last_push'] = {
            'at': now,
            'status': 'failed',
            'export_path': str(payload_path),
            'task_count': len(payload.get('tasks', [])),
            'apple_script': str(MAC_SCRIPT),
            'error': error,
        }
        mark_pushed_tasks(state, payload.get('tasks', []), now, status='failed', error=error)
        save_state(state)
        raise


def maybe_auto_push(source: str, task_ids: Optional[Iterable[str]] = None, changed_only: bool = False, logger: Optional[logging.Logger] = None, explicit: Optional[bool] = None) -> Dict[str, Any]:
    logger = logger or setup_logger()
    if not should_auto_push(explicit=explicit):
        logger.info('auto push disabled for source=%s', source)
        return {'status': 'disabled', 'source': source}

    effective_task_ids = list(task_ids or [])
    effective_changed_only = bool(changed_only)

    # 自动链路稳定性优先：如果调用方只给了 task_ids，但没有显式要求 changed_only，
    # 那么优先切到 changed-only 导出，避免把共享 export 文件写成“单任务快照”。
    # 仍保留显式 task_ids 能力给手动脚本/调试入口使用。
    if effective_task_ids and not effective_changed_only:
        logger.info(
            'auto push source=%s received task_ids=%s without changed_only; fallback to changed-only export for shared payload stability',
            source,
            effective_task_ids,
        )
        effective_task_ids = []
        effective_changed_only = True

    payload = export_sync_payload(task_ids=effective_task_ids or None, changed_only=effective_changed_only, logger=logger)
    git_result = git_sync_export(logger=logger)
    try:
        push_result = push_sync_payload(logger=logger)
        return {
            'status': push_result.get('status', 'success'),
            'source': source,
            'exported': len(payload.get('tasks', [])),
            'changed_only': effective_changed_only,
            'requested_task_ids': effective_task_ids,
            'git_sync': git_result,
        }
    except PushNotConfigured as exc:
        logger.warning('push skipped: %s', exc)
        return {
            'status': 'push_skipped',
            'source': source,
            'reason': str(exc),
            'exported': len(payload.get('tasks', [])),
            'changed_only': effective_changed_only,
            'requested_task_ids': effective_task_ids,
            'git_sync': git_result,
        }


def append_sync_log(message: str, logger: Optional[logging.Logger] = None, level: str = 'info') -> None:
    logger = logger or setup_logger()
    log_fn = getattr(logger, level, logger.info)
    log_fn(message)


def run_git_command(args: List[str], logger: logging.Logger, check: bool = True) -> subprocess.CompletedProcess:
    return run_subprocess(['git', '-C', str(ROOT), *args], logger=logger, check=check)


def path_has_changes(path: Path, logger: logging.Logger) -> bool:
    completed = run_git_command(['status', '--short', '--', str(path)], logger=logger, check=False)
    return bool((completed.stdout or '').strip())


def collect_changed_git_sync_paths(logger: logging.Logger) -> List[str]:
    changed: List[str] = []
    for rel_path in GIT_SYNC_ALLOWED_PATHS:
        if path_has_changes(rel_path, logger):
            changed.append(str(rel_path))
    return changed


def get_git_sync_branch(logger: logging.Logger) -> str:
    branch = (os.getenv(GIT_SYNC_BRANCH_ENV) or '').strip()
    if branch:
        return branch
    completed = run_git_command(['rev-parse', '--abbrev-ref', 'HEAD'], logger=logger, check=False)
    current = (completed.stdout or '').strip()
    if completed.returncode != 0 or not current or current == 'HEAD':
        raise SyncError('git sync requires a checked-out branch or GTD_APPLE_REMINDERS_GIT_BRANCH')
    return current


def git_sync_export(logger: Optional[logging.Logger] = None, enable_commit: Optional[bool] = None, enable_push: Optional[bool] = None, dry_run: Optional[bool] = None) -> Dict[str, Any]:
    logger = logger or setup_logger()
    enabled = bool_from_env(GIT_SYNC_ENABLED_ENV, False)
    enable_commit = enabled if enable_commit is None else enable_commit
    enable_push = bool_from_env(GIT_SYNC_PUSH_ENV, False) if enable_push is None else enable_push
    dry_run = bool_from_env(GIT_SYNC_DRY_RUN_ENV, False) if dry_run is None else dry_run

    result: Dict[str, Any] = {
        'status': 'disabled',
        'enabled': bool(enable_commit),
        'push_enabled': bool(enable_push),
        'dry_run': bool(dry_run),
        'allowed_paths': [str(p) for p in GIT_SYNC_ALLOWED_PATHS],
        'staged_paths': [],
    }

    if enable_push:
        enable_commit = True
        result['enabled'] = True

    if not enable_commit:
        logger.info('git sync disabled')
        return result

    try:
        changed_paths = collect_changed_git_sync_paths(logger)
        result['changed_paths'] = changed_paths
        if not changed_paths:
            result['status'] = 'no_changes'
            logger.info('git sync: no allowed path changes detected')
            return result

        branch = get_git_sync_branch(logger)
        remote = (os.getenv(GIT_SYNC_REMOTE_ENV) or 'origin').strip() or 'origin'
        result['branch'] = branch
        result['remote'] = remote

        commit_message = f'chore(sync): update apple reminders export {now_dt().strftime("%Y-%m-%d %H:%M:%S %z")}'
        result['commit_message'] = commit_message

        if dry_run:
            result['status'] = 'dry_run'
            result['staged_paths'] = changed_paths
            logger.info('git sync dry-run: would stage paths=%s push=%s', changed_paths, enable_push)
            return result

        run_git_command(['add', '--', *changed_paths], logger=logger)
        result['staged_paths'] = changed_paths

        diff_cached = run_git_command(['diff', '--cached', '--quiet', '--', *changed_paths], logger=logger, check=False)
        if diff_cached.returncode == 0:
            result['status'] = 'no_staged_diff'
            logger.info('git sync: no staged diff after add')
            return result

        run_git_command(['commit', '-m', commit_message], logger=logger)
        result['status'] = 'committed'

        if enable_push:
            run_git_command(['push', remote, branch], logger=logger)
            result['status'] = 'pushed'

        return result
    except Exception as exc:
        logger.warning('git sync failed: %s', exc)
        result['status'] = 'failed'
        result['error'] = str(exc)
        return result
