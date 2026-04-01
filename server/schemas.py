from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

VALID_BUCKETS = ['today', 'tomorrow', 'future', 'archive']
VALID_QUADRANTS = ['q1', 'q2', 'q3', 'q4']
VALID_STATUSES = ['open', 'done', 'cancelled', 'archived']
VALID_CATEGORIES = ['inbox', 'project', 'next_action', 'waiting_for', 'maybe']


def _validate_due_date(value: Optional[str]) -> Optional[str]:
    if value in (None, ''):
        return None
    try:
        datetime.strptime(value, '%Y-%m-%d')
    except ValueError as exc:
        raise SchemaError(f'invalid due_date: {value}') from exc
    return value


class SchemaError(ValueError):
    pass


@dataclass
class TaskCreate:
    title: str
    status: str = 'open'
    bucket: str = 'future'
    quadrant: str = 'q2'
    tags: List[str] = field(default_factory=list)
    note: str = ''
    due_date: Optional[str] = None
    category: Optional[str] = 'inbox'
    source: Optional[str] = 'api'
    source_task_id: Optional[str] = None

    def validate(self) -> 'TaskCreate':
        if not self.title or not self.title.strip():
            raise SchemaError('title is required')
        if self.status not in VALID_STATUSES:
            raise SchemaError(f'invalid status: {self.status}')
        if self.bucket not in VALID_BUCKETS:
            raise SchemaError(f'invalid bucket: {self.bucket}')
        if self.quadrant not in VALID_QUADRANTS:
            raise SchemaError(f'invalid quadrant: {self.quadrant}')
        if self.category is not None and self.category not in VALID_CATEGORIES:
            raise SchemaError(f'invalid category: {self.category}')
        self.tags = sorted(set(self.tags or []))
        self.note = self.note or ''
        self.due_date = _validate_due_date(self.due_date)
        return self


@dataclass
class TaskUpdate:
    title: Optional[str] = None
    status: Optional[str] = None
    bucket: Optional[str] = None
    quadrant: Optional[str] = None
    tags: Optional[List[str]] = None
    note: Optional[str] = None
    due_date: Optional[str] = None
    category: Optional[str] = None
    source: Optional[str] = None
    source_task_id: Optional[str] = None
    completed_at: Optional[str] = None
    deleted_at: Optional[str] = None
    last_synced_at: Optional[str] = None

    def validate(self) -> 'TaskUpdate':
        if self.status is not None and self.status not in VALID_STATUSES:
            raise SchemaError(f'invalid status: {self.status}')
        if self.bucket is not None and self.bucket not in VALID_BUCKETS:
            raise SchemaError(f'invalid bucket: {self.bucket}')
        if self.quadrant is not None and self.quadrant not in VALID_QUADRANTS:
            raise SchemaError(f'invalid quadrant: {self.quadrant}')
        if self.category is not None and self.category not in VALID_CATEGORIES:
            raise SchemaError(f'invalid category: {self.category}')
        if self.tags is not None:
            self.tags = sorted(set(self.tags))
        self.due_date = _validate_due_date(self.due_date)
        return self

    def to_patch_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class TaskOut:
    task: Dict[str, Any]


@dataclass
class TaskListResponse:
    items: List[Dict[str, Any]]
    total: int


@dataclass
class ChangeOut:
    change_id: int
    task_id: str
    action: str
    changed_at: str
    version: int
    source: Optional[str]
    payload: Optional[Dict[str, Any]] = None
    task: Optional[Dict[str, Any]] = None


@dataclass
class ChangeListResponse:
    items: List[Dict[str, Any]]
    next_change_id: int


@dataclass
class SyncClientAck:
    last_change_id: int
    client_type: str = 'unknown'
    meta: Optional[Dict[str, Any]] = None
