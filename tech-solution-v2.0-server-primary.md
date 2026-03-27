> 历史方案文档：这是 v2.0 服务端主库方案设计稿，主要用于保留设计背景与演进过程。当前有效实现请优先以 `README.md`、`server/README.md`、`MAC-SYNC-RUNBOOK.md` 为准。

# GTD 服务端主库方案技术文档 v2.0

> 对应需求文档：《requirements-v2.0-server-primary.md》
> 
> 技术定位：采用 **A 方案** —— 服务端数据库为唯一事实源；AI、CLI、NLP、Mac 同步器均通过服务端接口工作；本地文件系统退化为缓存、渲染输出与兼容层。

---

## 一、技术目标

本方案要解决的核心问题不是“如何继续优化 GitHub 文件同步”，而是：

> **如何将现有 GTD 系统平滑升级为一个以服务端为核心的任务同步架构。**

具体目标：

1. 服务端承接任务主库角色
2. 复用现有 GTD 数据模型与视图能力
3. 移除 GitHub 在主链路中的职责
4. 保留 Mac -> Apple Reminders 桥接能力
5. 建立可靠的增量同步机制与状态管理机制

---

## 二、现状与重构思路

### 2.1 当前现状
当前系统已有：
- `data/tasks.json`：任务主库
- `scripts/task_cli.py`：结构化增删改查
- `scripts/nlp_capture.py`：自然语言录入
- `scripts/render_views.py`：视图渲染
- Apple Reminders 同步脚本与状态文件
- GitHub 仓库中转同步链路

### 2.2 当前问题
当前问题主要集中在同步层：
- Git push/pull/rebase 不适合高频任务操作
- 多端变更容易出现冲突
- 用户需要显式触发同步，体验差
- 任务系统缺乏服务端化的增量变更接口

### 2.3 重构策略
不建议推倒重写，而采用：

> **保留业务模型，替换同步架构。**

保留：
- 任务字段设计
- CLI/NLP 行为
- 视图渲染规则
- Apple 映射经验

替换：
- 主库存储位置
- 写入方式
- 增量同步方式
- GitHub 主链路依赖

---

## 三、目标架构

## 3.1 新架构概览

```text
用户 / AI
   ↓
GTD Write API
   ↓
服务端主库（SQLite/Postgres）
   ↓
变更日志 / 增量接口
   ↓
Mac Sync Agent（每分钟轮询）
   ↓
Apple Reminders
```

同时保留本地导出链路：

```text
服务端主库
   ↓
Local Export / Cache
   ↓
render_views.py
   ↓
today.md / inbox.md / done.md / weekly
```

---

## 3.2 核心模块

### 模块 A：服务端任务 API
负责：
- 新增任务
- 查询任务
- 更新任务
- 删除任务
- 返回增量变更

### 模块 B：服务端存储层
负责：
- 存储任务主数据
- 存储任务变更日志
- 存储客户端同步游标
- 存储 Apple 映射状态

### 模块 C：AI / CLI 接入层
负责：
- 将现有 `task_cli.py` / `nlp_capture.py` 从“本地写文件”改为“调用服务端 API”
- 保持用户输入方式尽量不变

### 模块 D：本地导出与视图层
负责：
- 从服务端拉取当前任务集
- 生成 `tasks.json` 缓存
- 复用现有 `render_views.py` 输出 Markdown 视图

### 模块 E：Mac Sync Agent
负责：
- 周期性拉取服务端增量
- 调 AppleScript 同步到 Apple Reminders
- 回传 Apple completed 变更

---

## 四、技术选型建议

## 4.1 服务端语言
建议优先：**Python**

原因：
- 现有 GTD 工具链为 Python
- CLI / NLP / 渲染逻辑可高复用
- 开发成本低，迁移快

可选框架：
- FastAPI（优先推荐）
- Flask（也可，但扩展性稍弱）

推荐：
> FastAPI + Pydantic + Uvicorn

---

## 4.2 数据库

### MVP 推荐：SQLite
适合：
- 单用户
- 轻量部署
- 快速落地

优点：
- 部署最简单
- 无额外服务依赖
- 对当前规模完全够用

### 长期推荐：PostgreSQL
适合：
- 多端扩展
- 更复杂查询
- 更强一致性要求

建议路径：
- v2.0 MVP 先用 SQLite
- 后续如有需要，再迁移 Postgres

---

## 4.3 同步协议
MVP 建议采用：
- HTTP REST API
- 基于 `updated_at` / `change_id` 的增量轮询

本轮不建议一开始就上：
- WebSocket
- SSE
- MQ

原因：
- 复杂度不划算
- 任务同步对秒级实时性要求不高
- 1 分钟轮询已足够满足当前需求

---

## 五、服务端数据模型

## 5.1 tasks 表
建议字段：

```sql
CREATE TABLE tasks (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  status TEXT NOT NULL,
  bucket TEXT NOT NULL,
  quadrant TEXT NOT NULL,
  tags_json TEXT NOT NULL,
  note TEXT NOT NULL,
  category TEXT NOT NULL,
  source TEXT,
  source_task_id TEXT,
  sync_version INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  completed_at TEXT,
  deleted_at TEXT,
  last_synced_at TEXT
);
```

说明：
- 延续现有字段结构，降低迁移成本
- `tags` 先以 JSON 数组字符串存储
- `deleted_at` 表示真删除软标记

---

## 5.2 task_changes 表
用于增量同步。

```sql
CREATE TABLE task_changes (
  change_id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id TEXT NOT NULL,
  action TEXT NOT NULL,
  changed_at TEXT NOT NULL,
  version INTEGER NOT NULL,
  payload_json TEXT,
  source TEXT
);
```

用途：
- 为 Mac 提供 `since_change_id` 拉取能力
- 避免每次全量扫描 tasks

`action` 示例：
- create
- update
- done
- reopen
- delete

---

## 5.3 sync_clients 表
记录客户端同步游标。

```sql
CREATE TABLE sync_clients (
  client_id TEXT PRIMARY KEY,
  client_type TEXT NOT NULL,
  last_change_id INTEGER NOT NULL DEFAULT 0,
  last_seen_at TEXT NOT NULL,
  meta_json TEXT
);
```

用途：
- Mac agent 保存同步进度
- 未来可扩展更多客户端

---

## 5.4 apple_mappings 表
保存服务端任务与 Apple Reminder 的稳定映射。

```sql
CREATE TABLE apple_mappings (
  task_id TEXT PRIMARY KEY,
  apple_reminder_id TEXT,
  apple_list_id TEXT,
  apple_list_name TEXT,
  last_apple_updated_at TEXT,
  last_synced_at TEXT,
  sync_status TEXT,
  content_hash TEXT,
  meta_json TEXT
);
```

说明：
- 不依赖标题模糊匹配
- 使用稳定 reminder id 做同步锚点

---

## 六、API 设计

## 6.1 写入 API

### POST /api/tasks
创建任务

请求体示例：
```json
{
  "title": "下午3点钟开2026年的员工大会",
  "status": "open",
  "bucket": "today",
  "quadrant": "q2",
  "tags": [],
  "note": "",
  "category": "inbox",
  "source": "ai"
}
```

返回：完整任务对象

---

### PATCH /api/tasks/{task_id}
更新任务

支持字段：
- title
- status
- bucket
- quadrant
- tags
- note
- category
- deleted_at

每次更新都应：
- 更新 `updated_at`
- `sync_version + 1`
- 写入 `task_changes`

---

### POST /api/tasks/{task_id}/done
标记完成

---

### POST /api/tasks/{task_id}/reopen
重开任务

---

### DELETE /api/tasks/{task_id}
真删除（建议实现为软删除）

---

## 6.2 查询 API

### GET /api/tasks
支持筛选参数：
- status
- bucket
- category
- tag
- text
- include_deleted
- limit

### GET /api/tasks/{task_id}
获取单个任务

---

## 6.3 增量同步 API

### GET /api/changes?since_change_id=123&limit=200
返回变更列表。

返回结构示例：
```json
{
  "next_change_id": 135,
  "items": [
    {
      "change_id": 124,
      "task_id": "tsk_20260324_004",
      "action": "update",
      "changed_at": "2026-03-24T04:59:35+08:00",
      "version": 3,
      "task": { }
    }
  ]
}
```

说明：
- Mac agent 用它做增量拉取
- 比按全量 task.updated_at 扫描更稳

---

### POST /api/sync/clients/{client_id}/ack
客户端确认已消费到哪个 `change_id`

请求体：
```json
{
  "last_change_id": 135,
  "meta": {
    "hostname": "mac-mini",
    "app": "apple-reminders-sync"
  }
}
```

---

## 6.4 Apple 回写 API

### POST /api/apple/completed
用于 Mac 回写 Apple completed。

请求体示例：
```json
{
  "items": [
    {
      "apple_reminder_id": "reminder-uuid-001",
      "completed_at": "2026-03-24T10:00:00+08:00"
    }
  ]
}
```

服务端行为：
- 通过 `apple_mappings` 找到对应 task
- 若 task 当前仍为 open，则标记为 done
- 写入 `task_changes`

---

## 七、AI / CLI 重构方案

## 7.1 task_cli.py 改造
当前：直接读写 `data/tasks.json`

目标：增加双模式：
- `--backend local`（兼容模式）
- `--backend api`（默认新模式）

推荐做法：
- 抽出 `TaskRepository` 接口
- 提供两个实现：
  - `LocalJsonTaskRepository`
  - `ApiTaskRepository`

这样 CLI 命令层无需大改，只替换 repository。

---

## 7.2 nlp_capture.py 改造
当前 `apply` 最终会调用本地 `task_cli.py add`

目标：
- 解析逻辑保留
- apply 阶段改为调用 API repository

这样自然语言录入能力几乎可直接复用。

---

## 7.3 render_views.py 改造
两种可行方案：

### 方案 A：服务端导出到本地缓存后复用渲染
- 新增 `scripts/pull_tasks_cache.py`
- 从 API 拉全量/增量到 `data/tasks.json`
- 继续用原 `render_views.py`

优点：最稳，改动小

### 方案 B：render_views.py 直接读 API
优点：更直接
缺点：耦合网络，调试差

推荐：
> **优先方案 A**，先保守迁移。

---

## 八、Mac Sync Agent 方案

## 8.1 运行方式
建议保留 Mac 本地 agent，使用 `launchd` 定时运行。

频率建议：
- 每 1 分钟执行一次

流程：
1. 从本地配置读取服务端地址与 token
2. 调 `/api/changes?since_change_id=...`
3. 对每条变更执行 create/update/complete/move
4. 更新本地 sync cursor
5. 导出 Apple completed changes
6. 调 `/api/apple/completed` 回写

---

## 8.2 Mac 端本地状态
建议在 Mac 本地保存：

```json
{
  "client_id": "mac-primary",
  "last_change_id": 135,
  "last_pull_at": "2026-03-24T10:01:00+08:00"
}
```

说明：
- 服务端也会记客户端 ack
- 本地也保留游标，方便断点恢复

---

## 8.3 Apple 操作动作
Mac agent 需要支持：
- create reminder
- update title/note
- move list
- mark completed
- 可选 uncomplete/reopen

注意：
- 必须使用稳定的 `apple_reminder_id`
- 不使用标题模糊匹配作为主识别手段

---

## 九、迁移方案

## 9.1 迁移原则
- 不停机大迁移
- 先建立服务端，再切写入入口
- 保留本地文件兼容
- GitHub 逐步退出主链路

---

## 9.2 分阶段迁移

### Phase 1：服务端落地
- 建 API 服务
- 建数据库表
- 从当前 `tasks.json` 导入服务端
- 验证读写一致性

### Phase 2：AI/CLI 切换到 API
- `task_cli.py` 支持 API backend
- `nlp_capture.py` apply 走 API
- 用户新任务从这一步开始直接入服务端

### Phase 3：本地渲染兼容
- 增加 `pull_tasks_cache.py`
- 从服务端导出 `tasks.json`
- 复用 `render_views.py`

### Phase 4：Mac agent 切换
- Mac 不再依赖 GitHub pull
- 改为从服务端拉增量 changes
- 验证 Apple sync 闭环

### Phase 5：GitHub 降级
- GitHub 改为低频备份快照
- 不再参与实时主链路

---

## 十、错误处理与恢复策略

### 10.1 服务端写入失败
- AI/CLI 直接报错
- 不做 silent fallback 到本地
- 避免双主库风险

### 10.2 Mac 同步失败
- 不影响主库写入
- 下个轮询周期自动重试
- 保留失败日志与最后游标

### 10.3 Apple 回写失败
- 下次重新导出 completed changes
- 服务端按幂等方式处理

### 10.4 冲突策略
本轮遵循：
- 服务端字段优先
- Apple 只允许 completed 回写
- 其他 Apple 侧变更忽略

这会大幅降低冲突复杂度。

---

## 十一、安全与配置

建议配置项：
- `GTD_API_BASE_URL`
- `GTD_API_TOKEN`
- `GTD_SYNC_CLIENT_ID`
- `GTD_TIMEZONE=Asia/Shanghai`

认证方式：
- MVP 可先用静态 Bearer Token
- 后续可升级更完整认证方式

---

## 十二、验收指标

技术验收标准：

1. API 可新增/更新/删除/完成任务
2. `task_changes` 能正确记录增量事件
3. CLI/NLP 已切到 API backend
4. 本地仍可生成 today/inbox/done/weekly 视图
5. Mac 可在 1 分钟内同步服务端变更到 Apple
6. Apple completed 能回写服务端 done
7. 日常使用不再依赖 GitHub push/pull

---

## 十三、最终结论

本方案不是在另起炉灶做一套全新 GTD，而是：

> **保留现有已验证的任务模型与使用习惯，把同步中枢从 GitHub 替换成服务端任务主库。**

一句话总结技术路线：

> **保业务、换底座；保模型、换同步；保体验、去 GitHub 主链路。**
