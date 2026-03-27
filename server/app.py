from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

LOCAL_API_BASE_URL = 'http://127.0.0.1:8083'

from server.db import init_db
from server.schemas import SyncClientAck, TaskCreate, TaskUpdate
from server.services.change_service import ChangeService
from server.services.task_service import TaskNotFoundError, TaskService

ROOT = Path(__file__).resolve().parent.parent
PULL_CACHE_SCRIPT = ROOT / 'scripts' / 'pull_tasks_cache.py'
RENDER_VIEWS_SCRIPT = ROOT / 'scripts' / 'render_views.py'
DEFAULT_API_BASE_URL = os.getenv('GTD_API_BASE_URL', 'https://gtd.5666.net')


def json_response(handler: BaseHTTPRequestHandler, payload, status: int = 200):
    body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    handler.send_response(status)
    handler.send_header('Content-Type', 'application/json; charset=utf-8')
    handler.send_header('Content-Length', str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def refresh_server_local_cache() -> dict:
    env = os.environ.copy()
    env['GTD_API_BASE_URL'] = LOCAL_API_BASE_URL
    pull = subprocess.run(
        ['python3', str(PULL_CACHE_SCRIPT), '--base-url', LOCAL_API_BASE_URL],
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
        'base_url': LOCAL_API_BASE_URL,
        'pull_tasks_cache': pull.stdout.strip(),
        'pull_tasks_cache_stderr': pull.stderr.strip(),
        'render_views': render.stdout.strip(),
        'render_views_stderr': render.stderr.strip(),
    }


class AppHandler(BaseHTTPRequestHandler):
    task_service = TaskService()
    change_service = ChangeService()

    def _read_json(self):
        length = int(self.headers.get('Content-Length', '0') or 0)
        raw = self.rfile.read(length) if length > 0 else b'{}'
        return json.loads(raw.decode('utf-8') or '{}')

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/health':
            return json_response(self, {'ok': True})
        if parsed.path == '/api/tasks':
            q = parse_qs(parsed.query)
            data = self.task_service.list_tasks(
                status=(q.get('status') or [None])[0],
                bucket=(q.get('bucket') or [None])[0],
                category=(q.get('category') or [None])[0],
                tag=(q.get('tag') or [None])[0],
                text=(q.get('text') or [None])[0],
                include_deleted=((q.get('include_deleted') or ['false'])[0].lower() == 'true'),
                limit=int((q.get('limit') or [0])[0] or 0) or None,
            )
            return json_response(self, data)
        if parsed.path.startswith('/api/tasks/'):
            task_id = parsed.path.rsplit('/', 1)[-1]
            try:
                return json_response(self, self.task_service.get_task(task_id))
            except TaskNotFoundError:
                return json_response(self, {'error': 'task not found'}, status=404)
        if parsed.path == '/api/changes':
            q = parse_qs(parsed.query)
            return json_response(
                self,
                self.change_service.list_changes(
                    since_change_id=int((q.get('since_change_id') or [0])[0] or 0),
                    limit=int((q.get('limit') or [200])[0] or 200),
                ),
            )
        if parsed.path == '/api/apple/mappings':
            return json_response(self, self.task_service.list_apple_mappings())
        return json_response(self, {'error': 'not found'}, status=404)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == '/api/tasks':
            payload = TaskCreate(**self._read_json()).validate()
            return json_response(self, self.task_service.create_task(payload), status=201)
        if parsed.path.endswith('/done') and parsed.path.startswith('/api/tasks/'):
            task_id = parsed.path.split('/')[-2]
            try:
                return json_response(self, self.task_service.mark_done(task_id))
            except TaskNotFoundError:
                return json_response(self, {'error': 'task not found'}, status=404)
        if parsed.path.endswith('/reopen') and parsed.path.startswith('/api/tasks/'):
            task_id = parsed.path.split('/')[-2]
            body = self._read_json()
            try:
                return json_response(self, self.task_service.reopen(task_id, body.get('bucket')))
            except TaskNotFoundError:
                return json_response(self, {'error': 'task not found'}, status=404)
        if parsed.path.startswith('/api/sync/clients/') and parsed.path.endswith('/ack'):
            client_id = parsed.path.split('/')[-2]
            body = self._read_json()
            ack = SyncClientAck(
                last_change_id=int(body['last_change_id']),
                client_type=body.get('client_type', 'unknown'),
                meta=body.get('meta'),
            )
            return json_response(self, self.change_service.ack_client(client_id, ack, TaskService.now_iso()))
        if parsed.path == '/api/apple/completed':
            # Apple Reminders completed 回写
            body = self._read_json()
            results = []
            for item in body.get('items', []):
                apple_reminder_id = item.get('apple_reminder_id')
                completed_at = item.get('completed_at')
                if apple_reminder_id:
                    result = self.task_service.mark_done_by_apple_id(apple_reminder_id, completed_at)
                    results.append(result)
            response = {'processed': len(results), 'results': results}
            if results:
                try:
                    response['cache_refresh'] = refresh_server_local_cache()
                    print(f"[apple.completed] cache refresh ok: {response['cache_refresh']}", flush=True)
                except Exception as exc:
                    response['cache_refresh_error'] = str(exc)
                    print(f"[apple.completed] cache refresh failed: {exc}", flush=True)
            return json_response(self, response)
        if parsed.path == '/api/apple/mappings':
            # 保存 Apple Reminder ID 到 Task ID 的映射
            body = self._read_json()
            mappings = body.get('mappings', [])
            results = []
            for mapping in mappings:
                task_id = mapping.get('task_id')
                apple_reminder_id = mapping.get('apple_reminder_id')
                if task_id and apple_reminder_id:
                    result = self.task_service.save_apple_mapping(task_id, apple_reminder_id)
                    results.append(result)
            return json_response(self, {'saved': len(results), 'results': results})
        return json_response(self, {'error': 'not found'}, status=404)

    def do_PATCH(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith('/api/tasks/'):
            task_id = parsed.path.rsplit('/', 1)[-1]
            try:
                return json_response(self, self.task_service.update_task(task_id, TaskUpdate(**self._read_json())))
            except TaskNotFoundError:
                return json_response(self, {'error': 'task not found'}, status=404)
        return json_response(self, {'error': 'not found'}, status=404)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith('/api/tasks/'):
            task_id = parsed.path.rsplit('/', 1)[-1]
            try:
                return json_response(self, self.task_service.delete(task_id))
            except TaskNotFoundError:
                return json_response(self, {'error': 'task not found'}, status=404)
        return json_response(self, {'error': 'not found'}, status=404)


def run(host: str = '127.0.0.1', port: int = 8000):
    init_db()
    server = HTTPServer((host, port), AppHandler)
    print(f'Listening on http://{host}:{port}')
    server.serve_forever()


if __name__ == '__main__':
    run()
