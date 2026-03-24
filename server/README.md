# GTD v2 Server Skeleton

## Run

```bash
cd /root/.openclaw/workspace/gtd-tasks
python3 -m venv .venv
source .venv/bin/activate
pip install -r server/requirements.txt
uvicorn server.app:app --reload
```

## Available endpoints

- `GET /health`
- `POST /api/tasks`
- `GET /api/tasks`
- `GET /api/tasks/{task_id}`
- `PATCH /api/tasks/{task_id}`
- `POST /api/tasks/{task_id}/done`
- `POST /api/tasks/{task_id}/reopen`
- `DELETE /api/tasks/{task_id}`
- `GET /api/changes?since_change_id=0&limit=200`
- `POST /api/sync/clients/{client_id}/ack`

## Notes

- 当前是 Phase 1 可合并骨架，使用 SQLite 本地文件 `data/gtd.db`。
- `DELETE /api/tasks/{task_id}` 目前实现为软删除标记：写入 `deleted_at`，并记录 change action=`delete`。
- changes 接口返回 `task` 快照和 `payload` 快照，便于后续 Mac sync agent 直接消费。
- Apple completed 回写 API、旧 `tasks.json` 导入脚本、CLI/NLP repository 抽象尚未在这次子任务里实现。
