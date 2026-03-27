# GTD API Server

## 当前定位

这是 `gtd-tasks` 的 API-first 服务端实现。

当前真实主链已经收敛为：

- GTD API 是唯一事实源
- CLI / AIGTD 通过 API 读写任务
- Mac 端通过 `/api/changes` 拉增量变化
- Apple Reminders completed 通过 `/api/apple/completed` 回写
- 服务端在回写后会直接刷新本地 `data/tasks.json` 与视图文件

## 本地运行

```bash
cd /root/.openclaw/workspace/gtd-tasks
python3 -m venv .venv-server
source .venv-server/bin/activate
pip install -r server/requirements.txt
uvicorn server.app:app --reload
```

## 线上运行事实

当前线上部署（x2）不是直接用 `uvicorn server.app:app --reload`，而是：

- nginx 反代 `gtd.5666.net`
- 转发到 `127.0.0.1:8083`
- 由 `python /root/gtd-tasks/run_8083.py` 启动服务

## 当前 API 端点

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
- `POST /api/apple/completed`

## 当前实现说明

- 服务端主路由由 `server/app.py` 直接处理
- 任务核心逻辑位于：
  - `server/services/task_service.py`
  - `server/services/change_service.py`
- 数据访问位于：
  - `server/repository.py`
- 数据库存储：
  - `data/gtd.db`

## 重要说明

- `DELETE /api/tasks/{task_id}` 当前实现为软删除：写入 `deleted_at`，并记录 change action=`delete`
- `GET /api/changes` 返回 change + task/payload 快照，供 Mac sync agent 直接消费
- `/api/apple/completed` 在成功回写后，会直接刷新本地 cache 与视图，不再依赖 HTTP loopback
