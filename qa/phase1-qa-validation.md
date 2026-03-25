# GTD v2.0 Phase 1 QA / Validation

> 范围基于：
> - `implementation-plan-v2.0-phase1.md`
> - `requirements-v2.0-server-primary.md`
> - `tech-solution-v2.0-server-primary.md`
>
> 目标：为 Phase 1（服务端主库 MVP）建立可执行的验收清单、核心测试场景、回归检查框架与已知风险清单。

---

## 1. 结论先说

当前仓库状态更接近：
- **方案和边界已定义清楚**
- **本地 JSON GTD 链路仍可用**
- **服务端骨架目录已创建，但 Phase 1 服务端核心代码尚未落地**

因此本次 QA 结论是：
- 现在还**不能做完整 Phase 1 功能验收**
- 但已经可以先把 **验收标准 / 测试点 / 风险清单** 固化，作为开发与联调的直接准绳
- 现有 CLI / NLP 可作为兼容基线，用于后续对照验证

---

## 2. 当前仓库初步验收结果

### 2.1 文档侧
已存在并可作为 Phase 1 依据：
- `implementation-plan-v2.0-phase1.md`
- `requirements-v2.0-server-primary.md`
- `tech-solution-v2.0-server-primary.md`

### 2.2 代码侧
现状：
- `server/` 目录已存在
- 但目前仅有：
  - `server/__init__.py`
  - `server/routes/__init__.py`
  - `server/services/__init__.py`
- **缺少 Phase 1 关键文件**：
  - `server/app.py`
  - `server/db.py`
  - `server/models.py`
  - `server/schemas.py`
  - `server/repository.py`
  - `server/routes/tasks.py`
  - `server/routes/changes.py`
  - `server/services/task_service.py`
  - `server/services/change_service.py`
  - `scripts/import_tasks_to_server.py`
  - `scripts/pull_tasks_cache.py`

### 2.3 现有本地链路快速检查
已完成的轻量验证：
- `scripts/task_cli.py` 可运行
- `scripts/nlp_capture.py` preview 可运行
- 核心 Python 脚本可通过 `py_compile`
- `data/tasks.json` 存在且可正常读取

### 2.4 数据基线观察
对当前 `data/tasks.json` 的快速观察：
- 总任务数：28
- 状态分布：`open=11`, `done=17`
- bucket 分布：`archive=15`, `today=5`, `tomorrow=4`, `future=4`
- category 分布中存在 **`None` 值 4 条**

这说明：
- 现有 JSON 数据整体可用
- 但如果服务端 schema 将 `category` 设为必填且严格校验，**导入脚本/兼容层会立刻踩坑**

---

## 3. Phase 1 验收清单（Checklist）

> 下面是正式验收时应逐项勾选的清单。

## 3.1 P0 必过项

### A. 服务端骨架
- [ ] `uvicorn server.app:app --reload` 可启动
- [ ] `GET /health` 返回 200
- [ ] 启动失败时日志可读，不是静默崩溃

### B. 数据库层
- [ ] 服务启动能自动建表，或提供明确 init 方式
- [ ] SQLite 数据库文件可成功生成
- [ ] 至少存在以下表：
  - [ ] `tasks`
  - [ ] `task_changes`
  - [ ] `sync_clients`
  - [ ] `apple_mappings`
- [ ] 表结构与方案文档字段定义一致或有明确偏差说明

### C. Schema 与兼容性
- [ ] 存在 `TaskCreate`
- [ ] 存在 `TaskUpdate`
- [ ] 存在 `TaskOut`
- [ ] 存在 `TaskListResponse`
- [ ] 存在 `ChangeOut`
- [ ] 存在 `ChangeListResponse`
- [ ] 字段能兼容现有 `data/tasks.json` 主结构
- [ ] 对可空字段（如 `completed_at` / `deleted_at` / `source_task_id` / `last_synced_at`）处理正确
- [ ] 对旧数据中的 `category=None` 有兼容策略

### D. 任务 API
- [ ] `POST /api/tasks` 可创建任务
- [ ] `GET /api/tasks` 可查询任务列表
- [ ] `GET /api/tasks/{task_id}` 可获取单任务
- [ ] `PATCH /api/tasks/{task_id}` 可修改任务
- [ ] `POST /api/tasks/{task_id}/done` 可完成任务
- [ ] `POST /api/tasks/{task_id}/reopen` 可重开任务
- [ ] `DELETE /api/tasks/{task_id}` 可删除任务（建议软删除）
- [ ] 响应字段完整、时间字段格式一致

### E. changes 增量接口
- [ ] `GET /api/changes?since_change_id=...&limit=...` 可工作
- [ ] 创建任务会产生 change
- [ ] 修改任务会产生 change
- [ ] done / reopen / delete 都会产生 change
- [ ] `POST /api/sync/clients/{client_id}/ack` 可记录游标
- [ ] `next_change_id` 语义清晰且连续

### F. 导入脚本
- [ ] 存在 `scripts/import_tasks_to_server.py`
- [ ] 能读取 `data/tasks.json`
- [ ] 导入后任务总数与源数据一致
- [ ] 导入后关键字段一致
- [ ] 导入逻辑支持重复执行时的幂等策略（至少不应无限重复插入）

## 3.2 P1 建议过项

### G. CLI repository 抽象
- [ ] 现有 CLI 已抽象 repository interface
- [ ] 至少有 `LocalJsonTaskRepository`
- [ ] 至少有 `ApiTaskRepository`
- [ ] 命令层不直接写死 `tasks.json`

### H. NLP apply 改造
- [ ] `nlp_capture.py --mode preview` 保持不变
- [ ] `apply` 能通过 repository 落到 API backend
- [ ] apply 失败时不会 silent fallback 到本地 JSON

## 3.3 P2 预埋项

### I. 本地缓存导出脚手架
- [ ] 存在 `scripts/pull_tasks_cache.py`
- [ ] 能从 API 拉全量任务
- [ ] 能导出成兼容 `data/tasks.json` 的结构
- [ ] 预留后续接 `render_views.py` 的清晰入口

---

## 4. 核心测试场景

## 4.1 数据一致性测试

### Case D1：JSON 导入后一致性
**目标**：验证旧库导入服务端后不失真。

检查点：
- 任务数量一致
- `id/title/status/bucket/quadrant/category/tags/note` 一致
- `completed_at/deleted_at/created_at/updated_at` 不丢失
- `sync_version` 保留或按规则迁移

通过标准：
- 全量数量一致
- 核心字段无异常丢失
- 差异项必须可解释

### Case D2：状态语义一致性
**目标**：确认 `open / done / deleted` 语义没有混掉。

检查点：
- done 不应等价为 deleted
- deleted 默认不出现在主列表
- reopen 后 `completed_at` 被清空
- done 后 bucket 是否自动归 `archive`，需与当前策略一致

### Case D3：时间字段一致性
**目标**：确保更新时间和业务时间口径正确。

检查点：
- 所有 API 读写使用统一时区口径
- GTD 业务判断仍以 `Asia/Shanghai` 为准
- `updated_at` 在修改时必变
- `completed_at` 仅在 done 时设置

### Case D4：可空字段兼容
**目标**：确保旧数据不会因为严格 schema 导入失败。

重点字段：
- `category`
- `completed_at`
- `deleted_at`
- `source_task_id`
- `last_synced_at`
- `note`

---

## 4.2 API 功能测试

### Case A1：创建任务
输入：
- 最小合法字段集
- 完整字段集
- 包含 tags / note / category / source 的任务

断言：
- 返回 200/201
- 数据库成功落库
- `task_changes` 出现 `create`
- `sync_version` 初始值符合设计

### Case A2：更新任务
输入：
- 改标题
- 改 bucket
- 改 category
- 改 note
- 改 tags

断言：
- 仅修改指定字段
- `updated_at` 更新
- `sync_version + 1`
- `task_changes` 出现 `update`

### Case A3：完成 / 重开任务
断言：
- done 后 `status=done`
- done 后 `completed_at` 非空
- reopen 后 `status=open`
- reopen 后 `completed_at=None`
- 对应 change action 正确

### Case A4：删除任务
断言：
- 若采用软删除，则 `deleted_at` 非空
- 普通列表默认不返回 deleted
- `include_deleted=true` 时可见
- `task_changes` 记录 delete

### Case A5：列表查询过滤
过滤条件：
- `status`
- `bucket`
- `category`
- `tag`
- `text`
- `include_deleted`
- `limit`

断言：
- 各过滤条件独立可用
- 多条件组合时结果正确
- limit 生效

---

## 4.3 changes / 增量同步测试

### Case C1：按 change_id 增量拉取
步骤：
1. 记录当前 `last_change_id`
2. 创建 1 条任务
3. 修改 1 条任务
4. done 1 条任务
5. 调 `GET /api/changes?since_change_id=旧值`

断言：
- 返回包含新增的 3 条 change
- 顺序稳定（通常按 `change_id ASC`）
- 每条 change 含正确 action/version/task

### Case C2：ack 游标
步骤：
1. client 拉取 changes
2. 调 `/api/sync/clients/{client_id}/ack`
3. 查询 `sync_clients`

断言：
- `last_change_id` 正确更新
- `last_seen_at` 更新
- 重复 ack 同值应幂等

### Case C3：大于 limit 的分页
断言：
- 超出 limit 时返回截断集
- `next_change_id` 逻辑可用于继续拉取
- 不漏、不重、不断档

### Case C4：删除/重开边界
断言：
- delete 后 change 可被下游识别
- reopen 后 change 不会被误解为 create
- 同一 task 多次变更可按版本推进

---

## 4.4 兼容性测试

### Case K1：兼容现有 tasks.json
断言：
- 导入脚本可处理现有字段
- 没有 `completed_at` 的 open 任务不报错
- `category=None` 可被兜底或保留为兼容值

### Case K2：兼容 render / views 链路
断言：
- 从服务端导出的缓存结构仍能被 `render_views.py` 接受
- `today.md / inbox.md / done.md / weekly/review-latest.md` 可继续生成

### Case K3：兼容 Apple 同步边界
Phase 1 虽不要求完整 Mac 改造，但应预验：
- `done` 事件能被 change 流表达
- 删除不会被 Apple 端误当作硬删除立即执行
- `apple_mappings` 表结构已能容纳后续接入

### Case K4：CLI / NLP 兼容迁移
断言：
- repository 接口切换后，用户命令层基本不变
- preview 不受 API backend 引入影响
- API backend 失败时返回可诊断错误

---

## 5. 回归检查框架

> 每次 Phase 1 开发提交后，建议至少跑下面这组回归。

## 5.1 Smoke 回归（每次提交必跑）
- [ ] 服务可启动
- [ ] `/health` 正常
- [ ] 新建任务成功
- [ ] 修改任务成功
- [ ] done 成功
- [ ] changes 可拉到对应变更
- [ ] 导入脚本可跑

## 5.2 数据回归
- [ ] 从 `data/tasks.json` 导入后数量不变
- [ ] 随机抽样 5 条任务做字段对比
- [ ] `done/deleted/open` 任务都各抽样验证
- [ ] 中文标题、note、tags 不乱码

## 5.3 兼容回归
- [ ] CLI local backend 不被破坏
- [ ] NLP preview 不被破坏
- [ ] render_views 仍可基于缓存输出
- [ ] Apple 相关旧脚本至少不因公共模块变更而语法报错

## 5.4 增量回归
- [ ] create -> change
- [ ] update -> change
- [ ] done -> change
- [ ] reopen -> change
- [ ] delete -> change
- [ ] ack 游标更新

---

## 6. 推荐测试数据集

建议准备至少三组数据：

### 数据集 T1：最小集
- 1 条 open today
- 1 条 open future
- 1 条 done archive

用途：快速冒烟

### 数据集 T2：真实导入集
- 直接使用当前 `data/tasks.json`

用途：兼容性与迁移验证

### 数据集 T3：边界集
包含：
- `category=None`
- `tags=[]`
- `note=''`
- `deleted_at!=None`
- 中文标题
- 重复更新多次的任务

用途：schema 与 changes 边界验证

---

## 7. Bug / 风险点列表

## 7.1 当前已观察到的风险

### R1. 服务端代码尚未实现，Phase 1 现在不可验收
风险等级：高

说明：
- 当前只有空 `server/` 包结构
- 文档有了，但 P0 功能尚未落代码

影响：
- 无法执行真正的 API / DB / changes 验收

### R2. 现有 JSON 数据存在 `category=None`
风险等级：高

说明：
- 当前真实数据中有 4 条任务 `category=None`
- 若 schema 把 `category` 写成严格非空枚举，导入会失败或 API 序列化失败

建议：
- 导入层做兼容兜底：`None -> infer_category(...)` 或默认 `inbox`
- 同时保留导入修复日志

### R3. `deleted` 语义与现有本地实现有偏差风险
风险等级：中高

说明：
- 需求文档里把 `deleted` 视为语义状态
- 当前本地 JSON 实现是 `status` 仍可能为 open/done，但用 `deleted_at` 标记删除

风险：
- 服务端若把 delete 设计成单独 status，可能与现有渲染/过滤逻辑不一致

建议：
- Phase 1 明确：删除采用 `deleted_at` 软删除为准
- API 输出中不要再引入第二套删除语义

### R4. `sync_version` 递增规则需钉死
风险等级：中

说明：
- 当前本地 CLI 是写操作统一 bump
- 服务端若有不同规则，Mac 增量和调试判断会混乱

建议：
- create 初值、update/done/reopen/delete 的递增规则写成测试

### R5. 时间口径容易被服务端 UTC 污染
风险等级：高

说明：
- 项目规则明确 GTD 业务时间按 `Asia/Shanghai`
- 若服务端直接按系统 UTC 推断 “today/tomorrow” 或写业务日期，容易错桶

建议：
- 测试用例里强制覆盖北京时间边界（如 00:30 / 23:30）
- 文档和代码同时标注业务时区

### R6. CLI / NLP 切 API 时容易出现 silent fallback
风险等级：高

说明：
- 技术文档明确“不做 silent fallback 到本地”
- 如果 API 失败又偷偷写本地 JSON，会立刻形成双主库

建议：
- 作为 hard rule 写进测试：API backend 失败必须显式报错

### R7. import 脚本幂等性不清晰
风险等级：中高

说明：
- 如果重复导入直接再插一遍，会污染主库

建议：
- 最低要求：按 task id upsert 或 skip existing
- 需要单独测试二次导入

### R8. changes 分页/续拉逻辑容易漏数
风险等级：中高

说明：
- `since_change_id` / `next_change_id` 语义如果没定义清楚，下游 Mac 很容易丢变更

建议：
- 明确采用 change_id 单调递增
- 测试覆盖 limit 截断和连续续拉

### R9. Apple 回写虽不在 Phase 1 主范围，但表结构若设计错，后续返工大
风险等级：中

建议：
- `apple_mappings` 先按技术方案字段建齐
- 不要先做“能跑就行”的临时表

---

## 8. 建议的开发完成定义（DoD）

当以下条件同时满足时，Phase 1 才建议进入“可联调 / 可试用”状态：

1. 服务端 API + DB + changes 全部可跑通
2. 旧 `tasks.json` 可稳定导入
3. 任意一次写操作都会落 `task_changes`
4. CLI / NLP 至少完成 repository 抽象，且可切 API backend
5. 没有 silent fallback 到本地 JSON
6. 可导出兼容缓存供视图层继续使用
7. 关键兼容问题（特别是 `category=None` / 删除语义 / 时间口径）已被测试覆盖

---

## 9. 建议下一步执行顺序

建议开发/联调按这个顺序推进：

1. 先落 `server/app.py + db.py + models.py + schemas.py`
2. 再落 `repository/service/tasks routes`
3. 接着实现 `changes` 与 `sync_clients ack`
4. 再做 `import_tasks_to_server.py`
5. 最后再做 CLI/NLP repository 抽象与 API 接入

原因：
- Phase 1 的最大风险不是 CLI，而是 **主库与 changes 语义是否先站稳**

---

## 10. 附：本次初步验证记录

本次已完成的仓库内快速检查：
- `python3 -m py_compile` 检查通过：
  - `scripts/task_cli.py`
  - `scripts/nlp_capture.py`
  - `scripts/render_views.py`
  - `scripts/apple_reminders_sync_lib.py`
  - `scripts/sync_apple_reminders.py`
  - `scripts/consume_apple_reminders_completed.py`
  - `scripts/export_apple_reminders_sync.py`
- `python3 scripts/task_cli.py list --limit 3` 可运行
- `python3 scripts/nlp_capture.py '明天下午 3 点开员工大会' --mode preview` 可运行
- `server/` 核心实现文件目前缺失，无法进行 API 级验收

---

如果后续服务端代码补上，这份文档可以直接作为第一版 QA 执行单。