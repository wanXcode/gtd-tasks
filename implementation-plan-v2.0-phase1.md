> 历史阶段文档：这是 v2.0 Phase 1 的实施计划记录，不代表当前线上实现全貌。当前有效口径请优先以 `README.md`、`server/README.md`、`MAC-SYNC-RUNBOOK.md` 为准。

# GTD v2.0 第一阶段开发任务拆解

> 基于 A 方案：服务端作为唯一事实源（Source of Truth）
> 目标：先完成“服务端主库 MVP”，把 GTD 从 GitHub 主链路中逐步解耦出来。

---

## 一、阶段目标

第一阶段不追求把整个系统一次性改完，而是先完成最小可运行闭环：

> **AI / CLI 可以写服务端主库，服务端可以输出当前任务集与增量变化。**

这阶段完成后，应达到：
- 服务端有真实任务主库
- 服务端支持基本增删改查
- 服务端支持 changes 增量接口
- 现有 GTD 数据可导入服务端
- 本地 JSON 主库开始从“唯一事实源”转向“兼容缓存”

---

## 二、第一阶段范围

### 本阶段要做
1. 建立服务端项目骨架
2. 建立数据库模型
3. 提供任务 API
4. 提供 changes API
5. 提供初始导入脚本
6. 给现有 CLI/NLP 抽象 repository 层
7. 先跑通 API 写入闭环

### 本阶段不做
1. 不做 Mac 端改造
2. 不做 Apple 双向同步重构
3. 不做 Web 管理后台
4. 不做多用户权限系统
5. 不做实时推送（WebSocket/SSE）

---

## 三、建议目录结构

建议在 `gtd-tasks/` 下新增：

```text
gtd-tasks/
├── server/
│   ├── app.py
│   ├── db.py
│   ├── models.py
│   ├── schemas.py
│   ├── repository.py
│   ├── routes/
│   │   ├── tasks.py
│   │   └── changes.py
│   └── services/
│       ├── task_service.py
│       └── change_service.py
├── scripts/
│   ├── import_tasks_to_server.py
│   ├── pull_tasks_cache.py
│   └── ...
└── data/
    └── gtd.db   # MVP 可直接放本地，后续再抽配置
```

---

## 四、开发任务拆解

## Task 1：建立服务端骨架

### 目标
创建可启动的 FastAPI 服务。

### 产出
- `server/app.py`
- `server/routes/tasks.py`
- `server/routes/changes.py`
- 基础 health 接口

### 验收
- 本地可运行 `uvicorn server.app:app --reload`
- `/health` 返回正常

### 优先级
P0

---

## Task 2：建立数据库层

### 目标
先用 SQLite 建任务主库。

### 产出
- `server/db.py`
- `server/models.py`
- 初始化表脚本或自动建表逻辑

### 表
1. `tasks`
2. `task_changes`
3. `sync_clients`
4. `apple_mappings`（本阶段可先建空表，后面再用）

### 验收
- 服务启动自动建表或可手动初始化
- SQLite 文件可生成

### 优先级
P0

---

## Task 3：定义数据结构（Pydantic Schema）

### 目标
把现有任务字段正式结构化。

### 产出
- `server/schemas.py`

### 至少包含
- `TaskCreate`
- `TaskUpdate`
- `TaskOut`
- `TaskListResponse`
- `ChangeOut`
- `ChangeListResponse`

### 验收
- 字段与现有 `tasks.json` 主结构兼容

### 优先级
P0

---

## Task 4：实现任务 Repository / Service 层

### 目标
把任务 CRUD 和变更日志记录抽出来。

### 产出
- `server/repository.py`
- `server/services/task_service.py`
- `server/services/change_service.py`

### 关键要求
每次 create / update / done / reopen / delete 时：
- 更新 `tasks`
- 写入 `task_changes`

### 验收
- 服务层可独立完成任务创建与更新
- `task_changes` 有记录

### 优先级
P0

---

## Task 5：实现任务 API

### 目标
提供任务增删改查接口。

### 接口
- `POST /api/tasks`
- `GET /api/tasks`
- `GET /api/tasks/{task_id}`
- `PATCH /api/tasks/{task_id}`
- `POST /api/tasks/{task_id}/done`
- `POST /api/tasks/{task_id}/reopen`
- `DELETE /api/tasks/{task_id}`

### 验收
- curl 或脚本可调用
- 新建/修改后数据库状态正确
- 响应字段完整

### 优先级
P0

---

## Task 6：实现 changes 增量接口

### 目标
为后续 Mac 增量同步做准备。

### 接口
- `GET /api/changes?since_change_id=...&limit=...`
- `POST /api/sync/clients/{client_id}/ack`

### 验收
- 创建/修改任务后，可通过 changes 接口拉到变化
- 可记录客户端 last_change_id

### 优先级
P0

---

## Task 7：实现旧 tasks.json 导入脚本

### 目标
把当前本机 GTD 主库导入服务端数据库，作为初始化数据。

### 产出
- `scripts/import_tasks_to_server.py`

### 行为
- 读取 `data/tasks.json`
- 写入 `tasks`
- 可选择是否补写历史 `task_changes`

### 验收
- 当前任务数据成功导入服务端
- 导入后 API 查询结果与原 tasks.json 基本一致

### 优先级
P0

---

## Task 8：抽象现有 CLI 的 repository 接口

### 目标
避免后续改造时直接把 CLI 逻辑写死在本地 JSON。

### 建议方式
在现有 `scripts/task_cli.py` 相关逻辑中抽出：
- `LocalJsonTaskRepository`
- `ApiTaskRepository`

### 本阶段要求
- 先完成接口抽象
- 不要求所有命令都立刻切 API

### 验收
- CLI 有清晰的 repository 抽象层
- 后续可平滑切 backend

### 优先级
P1

---

## Task 9：改造 nlp_capture.py 的 apply 路径

### 目标
让自然语言录入具备切换到 API backend 的能力。

### 本阶段要求
- 先保留 preview 逻辑
- apply 阶段支持通过 repository 写入

### 验收
- 不破坏现有 preview/apply 结构
- 后续切换服务端写入成本低

### 优先级
P1

---

## Task 10：本地缓存导出脚本（预埋）

### 目标
为第二阶段“服务端 -> 本地视图”做准备。

### 产出
- `scripts/pull_tasks_cache.py`

### 作用
- 从 API 拉全量任务
- 导出到 `data/tasks.json`
- 后续复用 `render_views.py`

### 本阶段要求
- 先建脚手架
- 不要求完全接到生产链路

### 优先级
P2

---

## 五、推荐开发顺序

按这个顺序做最稳：

1. Task 1：服务端骨架
2. Task 2：数据库层
3. Task 3：Schema
4. Task 4：Repository / Service
5. Task 5：任务 API
6. Task 6：changes API
7. Task 7：导入脚本
8. Task 8：CLI repository 抽象
9. Task 9：NLP apply 改造
10. Task 10：缓存导出脚手架

---

## 六、第一阶段验收标准

完成后必须满足：

### 验收 1
服务端可启动，健康检查正常。

### 验收 2
旧 `tasks.json` 可成功导入数据库。

### 验收 3
可通过 API 新增任务、修改任务、完成任务。

### 验收 4
每次变更都能进入 `task_changes`。

### 验收 5
`GET /api/changes` 能返回增量变化。

### 验收 6
CLI/NLP 已完成 repository 抽象准备，不再完全绑定本地 JSON。

---

## 七、我的建议

如果现在就进入开发，我建议：

> **先只做 P0，先把服务端真主库建立起来。**

原因很简单：
- P0 完成，项目方向就真正切过去了
- Mac、Apple、视图层这些都可以后续渐进改造
- 最大的架构风险在“主库是否服务端化”，不是在 UI 或同步细节

一句话：

> 第一阶段的本质，不是“做完整产品”，而是“把主库权力从 JSON/Git 转移到服务端”。
