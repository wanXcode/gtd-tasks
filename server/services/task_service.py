from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo

from models import Task
from repository import TaskRepository
from schemas import TaskCreate, TaskListResponse, TaskUpdate

TZ = ZoneInfo('Asia/Shanghai')


class TaskNotFoundError(KeyError):
    pass


class TaskService:
    def __init__(self, repo: Optional[TaskRepository] = None):
        self.repo = repo or TaskRepository()

    @staticmethod
    def now_iso() -> str:
        return datetime.now(TZ).isoformat(timespec='seconds')

    def _next_id(self) -> str:
        today = datetime.now(TZ).strftime('%Y%m%d')
        tasks = self.repo.list_tasks(include_deleted=True, limit=100000)
        nums = []
        for task in tasks:
            parts = task.id.split('_')
            if len(parts) >= 3 and parts[1] == today:
                try:
                    nums.append(int(parts[-1]))
                except ValueError:
                    continue
        seq = max(nums) + 1 if nums else 1
        return f'tsk_{today}_{seq:03d}'

    def create_task(self, payload: TaskCreate) -> Dict[str, Any]:
        payload.validate()
        now = self.now_iso()
        task = Task(
            id=self._next_id(),
            title=payload.title.strip(),
            status=payload.status,
            bucket=payload.bucket,
            quadrant=payload.quadrant,
            tags=payload.tags,
            note=payload.note,
            category=payload.category,
            source=payload.source,
            source_task_id=payload.source_task_id,
            sync_version=1,
            created_at=now,
            updated_at=now,
            completed_at=now if payload.status != 'open' else None,
            deleted_at=None,
            last_synced_at=None,
        )
        if task.status in ('done', 'cancelled', 'archived'):
            task.bucket = 'archive'
        self.repo.upsert_task(task)
        self.repo.record_change(
            task_id=task.id,
            action='create',
            changed_at=task.updated_at,
            version=task.sync_version,
            payload=task.to_dict(),
            source=task.source,
        )
        return task.to_dict()

    def get_task(self, task_id: str) -> Dict[str, Any]:
        task = self.repo.get_task(task_id)
        if not task:
            raise TaskNotFoundError(task_id)
        return task.to_dict()

    def list_tasks(self, **filters: Any) -> Dict[str, Any]:
        items = [task.to_dict() for task in self.repo.list_tasks(**filters)]
        return TaskListResponse(items=items, total=len(items)).__dict__

    def update_task(self, task_id: str, patch: TaskUpdate, action: str = 'update') -> Dict[str, Any]:
        patch.validate()
        task = self.repo.get_task(task_id)
        if not task:
            raise TaskNotFoundError(task_id)
        changes = patch.to_patch_dict()
        for key, value in changes.items():
            if key == 'tags':
                task.tags = value
            else:
                setattr(task, key, value)
        if patch.status == 'open':
            task.completed_at = None
            if task.bucket == 'archive':
                task.bucket = 'future'
        elif patch.status in ('done', 'cancelled', 'archived'):
            task.completed_at = patch.completed_at or self.now_iso()
            task.bucket = 'archive'
        task.updated_at = self.now_iso()
        task.sync_version = int(task.sync_version or 1) + 1
        self.repo.upsert_task(task)
        self.repo.record_change(
            task_id=task.id,
            action=action,
            changed_at=task.updated_at,
            version=task.sync_version,
            payload=task.to_dict(),
            source=task.source,
        )
        return task.to_dict()

    def mark_done(self, task_id: str) -> Dict[str, Any]:
        return self.update_task(task_id, TaskUpdate(status='done'), action='done')

    def reopen(self, task_id: str, bucket: Optional[str] = None) -> Dict[str, Any]:
        patch = TaskUpdate(status='open', bucket=bucket or 'future', deleted_at=None)
        return self.update_task(task_id, patch, action='reopen')

    def delete(self, task_id: str) -> Dict[str, Any]:
        return self.update_task(task_id, TaskUpdate(deleted_at=self.now_iso()), action='delete')
