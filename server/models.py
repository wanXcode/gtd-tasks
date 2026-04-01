from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Task:
    id: str
    title: str
    status: str = 'open'
    bucket: str = 'future'
    quadrant: str = 'q2'
    tags: List[str] = field(default_factory=list)
    note: str = ''
    due_date: Optional[str] = None
    category: Optional[str] = 'inbox'
    source: Optional[str] = 'manual'
    source_task_id: Optional[str] = None
    sync_version: int = 1
    created_at: str = ''
    updated_at: str = ''
    completed_at: Optional[str] = None
    deleted_at: Optional[str] = None
    last_synced_at: Optional[str] = None

    @classmethod
    def from_row(cls, row: Any) -> 'Task':
        payload = dict(row)
        payload['tags'] = json.loads(payload.pop('tags_json', '[]') or '[]')
        return cls(**payload)

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> 'Task':
        data = dict(payload)
        data.setdefault('tags', [])
        data.setdefault('note', '')
        data.setdefault('due_date', None)
        data.setdefault('status', 'open')
        data.setdefault('bucket', 'future')
        data.setdefault('quadrant', 'q2')
        data.setdefault('sync_version', 1)
        return cls(**data)

    def to_record(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload['tags_json'] = json.dumps(payload.pop('tags', []), ensure_ascii=False)
        return payload

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TaskChange:
    change_id: Optional[int]
    task_id: str
    action: str
    changed_at: str
    version: int
    payload_json: Optional[str] = None
    source: Optional[str] = None

    @classmethod
    def from_row(cls, row: Any) -> 'TaskChange':
        return cls(**dict(row))

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if self.payload_json:
            try:
                data['payload'] = json.loads(self.payload_json)
            except Exception:
                data['payload'] = self.payload_json
        else:
            data['payload'] = None
        return data


@dataclass
class SyncClient:
    client_id: str
    client_type: str
    last_change_id: int = 0
    last_seen_at: str = ''
    meta_json: Optional[str] = None

    @classmethod
    def from_row(cls, row: Any) -> 'SyncClient':
        return cls(**dict(row))


@dataclass
class AppleMapping:
    task_id: str
    apple_reminder_id: Optional[str] = None
    apple_list_id: Optional[str] = None
    apple_list_name: Optional[str] = None
    last_apple_updated_at: Optional[str] = None
    last_synced_at: Optional[str] = None
    sync_status: Optional[str] = None
    content_hash: Optional[str] = None
    meta_json: Optional[str] = None

    @classmethod
    def from_row(cls, row: Any) -> 'AppleMapping':
        return cls(**dict(row))
