#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data' / 'tasks.json'
TZ = ZoneInfo('Asia/Shanghai')
VALID_CATEGORIES = ['inbox', 'project', 'next_action', 'waiting_for', 'maybe']
DEFAULT_API_BASE_URL = os.getenv('GTD_API_BASE_URL', 'https://gtd.5666.net').rstrip('/')
DEFAULT_TIMEOUT = float(os.getenv('GTD_API_TIMEOUT', '10'))


class RepositoryError(RuntimeError):
    pass


class RepositoryNotSupportedError(RepositoryError):
    pass


@dataclass
class TaskMutationResult:
    task: Dict[str, Any]
    changed_ids: List[str]
    action: str


class TaskRepository(ABC):
    backend_name: str = 'unknown'

    @abstractmethod
    def add_task(
        self,
        title: str,
        *,
        bucket: str = 'future',
        quadrant: str = 'q2',
        note: str = '',
        tags: Optional[List[str]] = None,
        category: Optional[str] = None,
        source: str = 'cli',
    ) -> TaskMutationResult:
        raise NotImplementedError

    @abstractmethod
    def update_task(self, task_id: str, updates: Dict[str, Any]) -> TaskMutationResult:
        raise NotImplementedError

    @abstractmethod
    def mark_done(self, task_id: str) -> TaskMutationResult:
        raise NotImplementedError

    @abstractmethod
    def reopen_task(self, task_id: str, bucket: Optional[str] = None) -> TaskMutationResult:
        raise NotImplementedError

    @abstractmethod
    def delete_task(self, task_id: str) -> TaskMutationResult:
        raise NotImplementedError

    @abstractmethod
    def list_tasks(self) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def move_tasks(self, task_ids: List[str], to_bucket: str) -> TaskMutationResult:
        raise RepositoryNotSupportedError('move_tasks is not implemented for this backend')

    def tag_tasks(self, task_ids: List[str], action: str, tags: List[str]) -> TaskMutationResult:
        raise RepositoryNotSupportedError('tag_tasks is not implemented for this backend')


class LocalJsonTaskRepository(TaskRepository):
    backend_name = 'local'

    def __init__(self, data_path: Path = DATA):
        self.data_path = Path(data_path)

    def now_dt(self):
        return datetime.now(TZ)

    def now_iso(self):
        return self.now_dt().isoformat(timespec='seconds')

    def today_str(self):
        return self.now_dt().strftime('%Y-%m-%d')

    def load_data(self):
        with open(self.data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        data.setdefault('version', '0.2.1')
        data.setdefault('meta', {})
        data['meta'].setdefault('timezone', 'Asia/Shanghai')
        data['meta'].setdefault('business_date', self.today_str())
        data['meta'].setdefault('updated_at', self.now_iso())
        data.setdefault('tasks', [])
        for task in data['tasks']:
            self.normalize_task(task)
        return data

    def save_data(self, data):
        data['meta']['updated_at'] = self.now_iso()
        data['meta']['business_date'] = self.today_str()
        with open(self.data_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write('\n')

    def infer_category(self, task):
        category = task.get('category')
        if category == 'index':
            category = 'inbox'
        if category in VALID_CATEGORIES:
            return category

        tags = set(task.get('tags', []) or [])
        title = (task.get('title') or '')
        note = (task.get('note') or '')
        text = f"{title} {note}"
        bucket = task.get('bucket')

        waiting_keywords = ['等待', '确认', '回复', '回信', '跟进', '反馈', '催']
        project_keywords = ['项目', '规划', '方案', '系统', '搭建', '优化', '升级']
        action_keywords = ['给', '整理', '安排', '确认', '发送', '沟通', '推进', '处理']

        if tags & {'WAIT', 'FOLLOWUP', 'FOLLOW_UP'}:
            return 'waiting_for'
        if any(keyword in text for keyword in waiting_keywords):
            return 'waiting_for'
        maybe_keywords = ['以后', '先放未来', '晚点', '有空再', '再说', '也许', '可能']
        if any(keyword in text for keyword in maybe_keywords):
            return 'maybe'
        if any(keyword in text for keyword in project_keywords):
            return 'project'
        if tags & {'ME'} or any(keyword in text for keyword in action_keywords):
            return 'next_action'
        return 'inbox'

    def normalize_task(self, task):
        task.setdefault('status', 'open')
        task.setdefault('bucket', 'future')
        task.setdefault('quadrant', 'q2')
        task.setdefault('tags', [])
        task.setdefault('note', '')
        task.setdefault('category', self.infer_category(task))
        task.setdefault('source', 'manual')
        task.setdefault('source_task_id', None)
        task.setdefault('sync_version', 1)
        task.setdefault('deleted_at', None)
        task.setdefault('last_synced_at', None)
        task.setdefault('created_at', self.now_iso())
        task.setdefault('updated_at', task['created_at'])
        task.setdefault('completed_at', None)
        return task

    def next_id(self, tasks):
        nums = []
        date_prefix = self.now_dt().strftime('%Y%m%d')
        for task in tasks:
            try:
                parts = task['id'].split('_')
                if len(parts) >= 3 and parts[1] == date_prefix:
                    nums.append(int(parts[-1]))
            except Exception:
                pass
        n = max(nums) + 1 if nums else 1
        return f"tsk_{date_prefix}_{n:03d}"

    def bump_task(self, task):
        task['updated_at'] = self.now_iso()
        task['sync_version'] = int(task.get('sync_version', 1) or 1) + 1

    def set_status(self, task, status):
        task['status'] = status
        if status == 'open':
            task['completed_at'] = None
            if task.get('bucket') == 'archive':
                task['bucket'] = 'future'
        else:
            task['completed_at'] = self.now_iso()
            if status in ('done', 'cancelled', 'archived'):
                task['bucket'] = 'archive'

    def find_task(self, data, task_id):
        for task in data['tasks']:
            if task['id'] == task_id:
                return task
        raise RepositoryError(f'task not found: {task_id}')

    def add_task(self, title, *, bucket='future', quadrant='q2', note='', tags=None, category=None, source='cli'):
        data = self.load_data()
        task = self.normalize_task({
            'id': self.next_id(data['tasks']),
            'title': title,
            'status': 'open',
            'bucket': bucket,
            'quadrant': quadrant,
            'tags': sorted(set(tags or [])),
            'note': note or '',
            'category': category or None,
            'source': source,
            'created_at': self.now_iso(),
            'updated_at': self.now_iso(),
            'completed_at': None,
        })
        data['tasks'].append(task)
        self.save_data(data)
        return TaskMutationResult(task=task, changed_ids=[task['id']], action='add')

    def update_task(self, task_id, updates):
        data = self.load_data()
        task = self.find_task(data, task_id)
        for key in ['title', 'bucket', 'quadrant', 'note', 'category']:
            if key in updates and updates[key] is not None:
                task[key] = updates[key]
        if updates.get('status') is not None:
            self.set_status(task, updates['status'])
        if updates.get('set_tags') is not None:
            task['tags'] = sorted(set(updates['set_tags']))
        if updates.get('add_tags'):
            task['tags'] = sorted(set(task.get('tags', [])) | set(updates['add_tags']))
        if updates.get('remove_tags'):
            task['tags'] = [t for t in task.get('tags', []) if t not in set(updates['remove_tags'])]
        self.bump_task(task)
        self.save_data(data)
        return TaskMutationResult(task=task, changed_ids=[task['id']], action='update')

    def mark_done(self, task_id):
        data = self.load_data()
        task = self.find_task(data, task_id)
        self.set_status(task, 'done')
        self.bump_task(task)
        self.save_data(data)
        return TaskMutationResult(task=task, changed_ids=[task['id']], action='done')

    def reopen_task(self, task_id, bucket=None):
        data = self.load_data()
        task = self.find_task(data, task_id)
        task['deleted_at'] = None
        self.set_status(task, 'open')
        if bucket is not None:
            task['bucket'] = bucket
        self.bump_task(task)
        self.save_data(data)
        return TaskMutationResult(task=task, changed_ids=[task['id']], action='reopen')

    def delete_task(self, task_id):
        data = self.load_data()
        task = self.find_task(data, task_id)
        task['deleted_at'] = self.now_iso()
        self.bump_task(task)
        self.save_data(data)
        return TaskMutationResult(task=task, changed_ids=[task['id']], action='delete')

    def list_tasks(self):
        return self.load_data()['tasks']

    def move_tasks(self, task_ids, to_bucket):
        data = self.load_data()
        changed = []
        last_task = None
        for task_id in task_ids:
            task = self.find_task(data, task_id)
            task['bucket'] = to_bucket
            if task.get('status') != 'open' and to_bucket != 'archive':
                task['status'] = 'open'
                task['completed_at'] = None
            self.bump_task(task)
            changed.append(task['id'])
            last_task = task
        self.save_data(data)
        return TaskMutationResult(task=last_task or {}, changed_ids=changed, action='move')

    def tag_tasks(self, task_ids, action, tags):
        data = self.load_data()
        changed = []
        last_task = None
        for task_id in task_ids:
            task = self.find_task(data, task_id)
            current = set(task.get('tags', []))
            if action == 'add':
                current.update(tags)
            elif action == 'remove':
                current.difference_update(tags)
            elif action == 'set':
                current = set(tags)
            else:
                raise RepositoryError(f'unsupported tag action: {action}')
            task['tags'] = sorted(current)
            self.bump_task(task)
            changed.append(task['id'])
            last_task = task
        self.save_data(data)
        return TaskMutationResult(task=last_task or {}, changed_ids=changed, action='tag')


class ApiTaskRepository(TaskRepository):
    backend_name = 'api'

    def __init__(self, base_url: Optional[str] = None, timeout: float = DEFAULT_TIMEOUT):
        self.base_url = (base_url or DEFAULT_API_BASE_URL or '').rstrip('/')
        if not self.base_url:
            raise RepositoryError('GTD_API_BASE_URL is required for api backend')
        self.timeout = timeout

    def _request(self, method: str, path: str, payload: Optional[Dict[str, Any]] = None, query: Optional[Dict[str, Any]] = None):
        url = f"{self.base_url}{path}"
        if query:
            query = {k: v for k, v in query.items() if v is not None}
            if query:
                url = f"{url}?{urllib.parse.urlencode(query)}"
        data = None
        headers = {'Accept': 'application/json'}
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
            headers['Content-Type'] = 'application/json'
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode('utf-8')
                return json.loads(body) if body else None
        except urllib.error.HTTPError as exc:
            body = exc.read().decode('utf-8', errors='ignore')
            raise RepositoryError(f'API {method} {path} failed: {exc.code} {body}') from exc
        except urllib.error.URLError as exc:
            raise RepositoryError(f'API {method} {path} failed: {exc.reason}') from exc

    def _extract_task(self, response):
        if isinstance(response, dict) and isinstance(response.get('task'), dict):
            return response['task']
        if isinstance(response, dict):
            return response
        raise RepositoryError('unexpected api response, task object not found')

    def add_task(self, title, *, bucket='future', quadrant='q2', note='', tags=None, category=None, source='cli'):
        task = self._extract_task(self._request('POST', '/api/tasks', {
            'title': title,
            'status': 'open',
            'bucket': bucket,
            'quadrant': quadrant,
            'tags': sorted(set(tags or [])),
            'note': note or '',
            'category': category,
            'source': source,
        }))
        return TaskMutationResult(task=task, changed_ids=[task['id']], action='add')

    def update_task(self, task_id, updates):
        payload = {}
        for key in ['title', 'bucket', 'quadrant', 'note', 'category', 'status']:
            if updates.get(key) is not None:
                payload[key] = updates[key]
        if updates.get('set_tags') is not None:
            payload['tags'] = sorted(set(updates['set_tags']))
        elif updates.get('add_tags') is not None or updates.get('remove_tags') is not None:
            current = self.get_task(task_id)
            tags = set(current.get('tags', []) or [])
            if updates.get('add_tags'):
                tags.update(updates['add_tags'])
            if updates.get('remove_tags'):
                tags.difference_update(updates['remove_tags'])
            payload['tags'] = sorted(tags)
        task = self._extract_task(self._request('PATCH', f'/api/tasks/{task_id}', payload))
        return TaskMutationResult(task=task, changed_ids=[task['id']], action='update')

    def mark_done(self, task_id):
        task = self._extract_task(self._request('POST', f'/api/tasks/{task_id}/done', {}))
        return TaskMutationResult(task=task, changed_ids=[task['id']], action='done')

    def reopen_task(self, task_id, bucket=None):
        payload = {'bucket': bucket} if bucket else {}
        task = self._extract_task(self._request('POST', f'/api/tasks/{task_id}/reopen', payload))
        return TaskMutationResult(task=task, changed_ids=[task['id']], action='reopen')

    def delete_task(self, task_id):
        task = self._extract_task(self._request('DELETE', f'/api/tasks/{task_id}'))
        return TaskMutationResult(task=task, changed_ids=[task['id']], action='delete')

    def get_task(self, task_id):
        return self._extract_task(self._request('GET', f'/api/tasks/{task_id}'))

    def list_tasks(self):
        response = self._request('GET', '/api/tasks')
        if isinstance(response, dict) and isinstance(response.get('items'), list):
            return response['items']
        if isinstance(response, list):
            return response
        raise RepositoryError('unexpected api response, items not found')


def get_repository(backend: Optional[str] = None) -> TaskRepository:
    selected = (backend or os.getenv('GTD_TASK_BACKEND') or 'api').strip().lower()
    if selected == 'local':
        return LocalJsonTaskRepository()
    if selected == 'api':
        return ApiTaskRepository()
    raise RepositoryError(f'unsupported backend: {selected}')
