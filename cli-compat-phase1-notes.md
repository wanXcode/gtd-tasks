# CLI / Compatibility 改造说明（Phase 1）

## 这次先做了什么

目标是先把 `task_cli.py` / `nlp_capture.py` 从“直接绑死本地 JSON”改成“命令层 -> repository”，尽量不破坏现有行为。

本次新增：

- `scripts/task_repository.py`
  - `TaskRepository` 抽象接口
  - `LocalJsonTaskRepository`
  - `ApiTaskRepository`
  - `get_repository()` 工厂
- `scripts/pull_tasks_cache.py`
  - 从 API 拉全量任务并落本地 `data/tasks.json` 缓存的脚手架

本次改造：

- `scripts/task_cli.py`
  - 写操作改为走 repository
  - `list / move / tag` 先用 `repo.list_tasks()` + 本地过滤，减少 API 改造面
  - 新增 `--backend local|api`
  - 不传时读取 `GTD_TASK_BACKEND`，默认 `local`
- `scripts/nlp_capture.py`
  - preview 逻辑保持不动
  - apply 阶段支持直接走 repository
  - 兼容 `--backend local|api`

---

## 当前兼容策略

### local 模式
完全兼容现有行为：
- 仍写 `data/tasks.json`
- 仍调用 `render_views.py`
- 仍支持 Apple Reminders 的自动 push 链路

### api 模式
目前是“最小可接入”而不是“全功能完成”：

已接：
- `add`
- `update`
- `done`
- `reopen`
- `delete`
- `list`
- NLP apply -> add

未完全做完：
- `move`
- `tag`

这两个命令在 `api` 模式下目前依赖 repository 的批量能力；本次只在 `LocalJsonTaskRepository` 实现，`ApiTaskRepository` 暂未实现，后续应由服务端补批量接口，或 CLI 层退化成逐条 PATCH。

---

## 推荐的服务端接口对齐方式

为了让 `ApiTaskRepository` 真正替换本地 JSON，建议后续服务端至少满足：

- `POST /api/tasks`
- `GET /api/tasks`
- `GET /api/tasks/{task_id}`
- `PATCH /api/tasks/{task_id}`
- `POST /api/tasks/{task_id}/done`
- `POST /api/tasks/{task_id}/reopen`
- `DELETE /api/tasks/{task_id}`

返回最好统一：

```json
{
  "task": { ... }
}
```

如果直接返回任务对象，本次 `ApiTaskRepository` 也兼容。

---

## 为什么这样改

这样做的好处：

1. **先把命令层和存储层拆开**
   - 后续服务端接入时，不用继续改命令解析逻辑
2. **保住现有 CLI/NLP 行为**
   - local 仍是稳定回退路径
3. **render_views 暂时不用动**
   - 可以先通过 `pull_tasks_cache.py` 维持视图链路
4. **后续可以渐进切换默认 backend**
   - 先 local 默认，服务端稳定后再改成 api 默认

---

## 建议下一步

### P0
1. 落地 FastAPI 服务端最小任务 API
2. 让接口字段与现有 `tasks.json` 兼容
3. 跑通 `task_cli.py --backend api add/list/update/done`

### P1
4. 完成 `pull_tasks_cache.py`
   - 支持 `GET /api/changes`
   - 支持增量刷新本地缓存
   - 支持同步状态文件（如 `sync/tasks-cache-state.json`）
5. 决定 `move/tag` 的 api 方案
   - 服务端提供批量接口，或
   - CLI 中逐条 PATCH 包装

### P1/P2
6. `render_views.py` 增加 cache/source 标识输出
7. 服务端 ready 后，把 `GTD_TASK_BACKEND` 默认值从 `local` 切到 `api`
8. 再评估 Apple 同步链路是继续基于缓存文件，还是直接基于服务端 changes

---

## 当前风险 / 注意点

1. `ApiTaskRepository` 现在是假设式接入，接口还没真正存在
2. `move/tag` 在 api backend 还不能用
3. `task_cli.py` 只有 local backend 才会 render 视图，这个是刻意保守策略
4. `sync-apple-reminders` 目前仍偏向本地导出链路，真正服务端主库化后还需要再梳理一次
