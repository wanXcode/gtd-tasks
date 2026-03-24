from __future__ import annotations

from typing import Any, Dict, Optional

from repository import TaskRepository
from schemas import ChangeListResponse, SyncClientAck


class ChangeService:
    def __init__(self, repo: Optional[TaskRepository] = None):
        self.repo = repo or TaskRepository()

    def list_changes(self, since_change_id: int = 0, limit: int = 200) -> Dict[str, Any]:
        changes = self.repo.list_changes(since_change_id=since_change_id, limit=limit)
        items = []
        next_change_id = since_change_id
        for change in changes:
            task = self.repo.get_task(change.task_id)
            items.append({
                'change_id': change.change_id,
                'task_id': change.task_id,
                'action': change.action,
                'changed_at': change.changed_at,
                'version': change.version,
                'source': change.source,
                'payload': change.to_dict().get('payload'),
                'task': task.to_dict() if task else None,
            })
            next_change_id = max(next_change_id, int(change.change_id or 0))
        return ChangeListResponse(items=items, next_change_id=next_change_id).__dict__

    def ack_client(self, client_id: str, ack: SyncClientAck, seen_at: str) -> Dict[str, Any]:
        client = self.repo.ack_sync_client(
            client_id=client_id,
            client_type=ack.client_type,
            last_change_id=ack.last_change_id,
            last_seen_at=seen_at,
            meta=ack.meta,
        )
        return {
            'client_id': client.client_id,
            'client_type': client.client_type,
            'last_change_id': client.last_change_id,
            'last_seen_at': client.last_seen_at,
            'meta_json': client.meta_json,
        }
