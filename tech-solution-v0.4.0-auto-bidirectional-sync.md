# GTD Tasks v0.4.0 技术方案文档

## 1. 目标

在现有 v0.3.0 手动单向同步基础上，扩展出：

1. `gtd-tasks` -> Apple Reminders 自动同步
2. Apple Reminders -> `gtd-tasks` 的受控回写
3. 可追踪、可重试、可修复的双向同步底座

---

## 2. 现状回顾

当前已存在：
- 主库：`data/tasks.json`
- 视图渲染：`scripts/render_views.py`
- 结构化操作：`scripts/task_cli.py`
- 自然语言录入：`scripts/nlp_capture.py`
- 单向导出：`scripts/export_apple_reminders_sync.py`
- 映射配置：`config/apple_reminders_mapping.json`
- Mac 执行桥：`sync_apple_reminders_mac.applescript`
- 手动同步说明：`mac-sync-setup.md`

当前不足：
- 同步触发仍然依赖手动
- Mac 侧更像“导入器”，不是完整的同步代理
- 没有稳定的双端映射状态库
- 缺少 Reminders -> GTD 的拉取与回写链路
- 缺少冲突处理与恢复机制

---

## 3. 总体架构

建议将同步能力拆成 5 个模块：

### 模块 A：变更产生层（GTD 写入端）
负责产生 GTD 任务变更。

来源：
- `task_cli.py`
- `nlp_capture.py --mode apply`
- 其他未来受控写入入口

### 模块 B：同步状态层（Mapping + State Store）
负责记录双端映射与同步元数据。

建议新增：
- `sync/state/apple-reminders-state.json`
  或后续升级为 sqlite

### 模块 C：GTD -> Apple 导出与推送层
负责：
- 找出需要推送的任务
- 生成增量 payload
- 调用 Mac 桥完成写入/更新

### 模块 D：Apple -> GTD 拉取层
负责：
- 从 Mac 侧导出 Apple Reminders 的增量变化
- 拉回 Linux
- 与状态层比对
- 生成回写动作

### 模块 E：协调器（Reconciler）
负责：
- 比较双端更新时间
- 判定新增 / 更新 / 完成 / 删除 / 冲突
- 执行既定同步策略

---

## 4. 目录与文件建议

建议新增/调整以下文件：

```text
gtd-tasks/
├── sync/
│   ├── apple-reminders-export.json
│   ├── apple-reminders-import.json
│   ├── logs/
│   │   └── sync-YYYY-MM-DD.log
│   └── state/
│       └── apple-reminders-state.json
├── scripts/
│   ├── export_apple_reminders_sync.py
│   ├── import_apple_reminders_changes.py
│   ├── sync_apple_reminders.py
│   ├── reconcile_apple_reminders.py
│   └── watch_and_sync.py
└── mac/
    ├── sync_apple_reminders_mac.applescript
    ├── export_apple_reminders_changes.applescript
    └── README.md
```

说明：
- `export_apple_reminders_sync.py`：保留，负责 GTD -> Apple payload 生成
- `import_apple_reminders_changes.py`：读取 Apple 端导回文件
- `sync_apple_reminders.py`：统一编排一次同步动作
- `reconcile_apple_reminders.py`：执行双向比对与冲突决策
- `watch_and_sync.py`：监听或轮询自动触发

---

## 5. 数据模型设计

## 5.1 状态库文件

建议新增：

`sync/state/apple-reminders-state.json`

结构示例：

```json
{
  "version": "0.4.0",
  "updated_at": "2026-03-19T10:00:00+08:00",
  "items": [
    {
      "gtd_id": "tsk_20260318_001",
      "apple_reminder_id": "reminder-uuid-001",
      "apple_list_id": "list-uuid-01",
      "apple_list_name": "今天",
      "last_gtd_updated_at": "2026-03-19T09:58:00+08:00",
      "last_apple_updated_at": "2026-03-19T09:57:10+08:00",
      "last_synced_at": "2026-03-19T09:58:20+08:00",
      "last_sync_direction": "gtd_to_apple",
      "sync_status": "ok",
      "content_hash": "sha1:xxxx",
      "deleted_on_gtd": false,
      "deleted_on_apple": false
    }
  ]
}
```

## 5.2 设计要点

### `gtd_id`
主库任务 ID，稳定主键。

### `apple_reminder_id`
Apple Reminders 原生唯一标识。双向同步必须使用这个字段，而不是标题匹配。

### `content_hash`
对参与同步的关键字段计算哈希，用于快速判断内容是否真的变化。

建议参与 hash 的字段：
- title
- note
- due_date
- status
- target_list

### `deleted_on_*`
避免一开始做“硬删除互删”，先记录删除意图，后续由协调器决定。

---

## 6. 自动同步方案

## 6.1 触发策略

建议使用“双机制”：

### 机制 A：写入后主动触发
在以下脚本写入成功后，追加调用：
- `task_cli.py`
- `nlp_capture.py --mode apply`

方式：
- 调用统一入口 `scripts/sync_apple_reminders.py --mode push --changed-id <task_id>`
- 或调用异步轻量队列写入待同步清单

优点：
- 及时
- 贴近业务写入点

### 机制 B：后台轮询补偿
新增：
- `scripts/watch_and_sync.py`

职责：
- 每隔固定时间检查 `tasks.json` / state / 待同步项
- 自动补偿未完成同步

优点：
- 即使主动触发失败，也能兜底

建议：
- A 用于实时性
- B 用于可靠性

## 6.2 增量同步策略

不要每次都全量导出。

建议流程：
1. 读取 `tasks.json`
2. 读取 `apple-reminders-state.json`
3. 识别 changed tasks：
   - 新任务（state 中不存在）
   - `updated_at` 晚于 `last_synced_at`
   - 状态变化
   - 目标列表变化
4. 只导出 changed tasks

这样可以避免：
- 无意义全量更新
- Apple 端过多重复操作
- 日志噪音

---

## 7. GTD -> Apple 同步细节

## 7.1 推送动作类型

协调器输出的动作建议分为：
- `create`
- `update`
- `complete`
- `move`
- `archive`（或 `soft_delete`）
- `noop`

## 7.2 列表迁移

v0.3.0 MVP 不支持跨列表迁移，v0.4.0 应补齐。

Mac 脚本需要支持：
- 通过 `apple_reminder_id` 找到 Reminder
- 将其迁移到新 list
- 更新标题 / note / due date / completed status

如果 AppleScript 难以稳定迁移，可退而求其次：
- 先创建新 Reminder
- 再删除旧 Reminder
- 但必须保持 `gtd_id` 不变，并更新 state

## 7.3 完成与归档策略

建议：
- `status=done`：同步为 Apple completed
- `status=cancelled` / `archived`：第一版先移入归档列表，或标记完成并写入 notes

不建议第一版直接删除 Apple Reminder。

---

## 8. Apple -> GTD 回写方案

## 8.1 Mac 端导出 Apple 变更

新增 Mac 侧脚本：
- `export_apple_reminders_changes.applescript`

职责：
- 读取指定 Reminders 列表
- 导出 reminder_id / title / notes / due_date / completed / modified_at / list
- 输出为 `sync/apple-reminders-import.json`

如果 AppleScript 无法稳定获取 `modified_at`，则需要改成：
- 全量导出 + Linux 侧 hash 比对

## 8.2 Linux 端导入与比对

新增脚本：
- `scripts/import_apple_reminders_changes.py`

职责：
1. 读取 `apple-reminders-import.json`
2. 通过 `apple_reminder_id` 与 state 对齐
3. 识别 Apple 端的：
   - 新增
   - 更新
   - 完成
   - 删除/缺失
4. 交给 `reconcile_apple_reminders.py` 做决策

## 8.3 Apple 新增任务如何处理

这是双向同步里最容易失控的一点。

建议第一版先限制：
- **默认不允许 Apple 端随意新增回写为 GTD 新任务**
- 或者仅允许特定列表中新建的提醒事项被回写

原因：
- iPhone 上临时随手建内容很多
- 很容易污染 GTD 主库

更稳妥的策略：
- 先只支持对“已映射任务”的修改回写
- Apple 新增任务作为 v0.4.x 后续增强

---

## 9. 冲突处理

## 9.1 冲突定义

以下情况视为冲突：
- 同一 `gtd_id` / `apple_reminder_id` 在一次同步周期内两端都发生变化
- 且变更内容涉及同一字段或关键字段集合

## 9.2 冲突策略

建议第一版使用简化规则：

### 规则 1：最后修改时间优先
若两端都能稳定获得更新时间：
- `last_modified_at` 更晚的一端胜出

### 规则 2：时间不可靠时 GTD 优先
若 Apple 侧修改时间不稳定或缺失：
- 默认以 GTD 为主

### 规则 3：删除最低优先级
删除不应轻易覆盖编辑。
若一端删除，另一端编辑：
- 先记录冲突日志
- 默认保留任务，进入人工可恢复状态

## 9.3 冲突日志

建议输出：

```json
{
  "type": "conflict",
  "gtd_id": "tsk_...",
  "apple_reminder_id": "...",
  "fields": ["title", "due_date"],
  "gtd_updated_at": "...",
  "apple_updated_at": "...",
  "winner": "gtd",
  "resolved_at": "..."
}
```

---

## 10. 日志与观测

建议统一日志文件：

`sync/logs/sync-YYYY-MM-DD.log`

日志应包含：
- 同步开始时间
- push / pull / reconcile 阶段
- 新建/更新/完成/迁移/冲突/失败数量
- 具体失败任务 ID
- 外部脚本执行结果

同时建议支持：
- `--dry-run`
- `--verbose`
- `--task-id <id>`
- `--full-resync`

---

## 11. 编排入口设计

建议统一入口：

`scripts/sync_apple_reminders.py`

支持模式：

```bash
python3 scripts/sync_apple_reminders.py --mode push
python3 scripts/sync_apple_reminders.py --mode pull
python3 scripts/sync_apple_reminders.py --mode reconcile
python3 scripts/sync_apple_reminders.py --mode all
python3 scripts/sync_apple_reminders.py --mode push --task-id tsk_20260319_001
python3 scripts/sync_apple_reminders.py --mode all --dry-run
```

推荐内部流程：

### `--mode push`
1. 读取任务主库
2. 读取 state
3. 生成增量 export
4. 调用 Mac 桥接脚本执行写入
5. 成功后更新 state

### `--mode pull`
1. 调用 Mac 导出脚本
2. 获取 import JSON
3. 导入 Apple 变更
4. 更新待协调数据

### `--mode reconcile`
1. 比较双端状态
2. 生成动作计划
3. 写回 GTD 或 Apple
4. 更新 state 与日志

### `--mode all`
按顺序执行：
- push
- pull
- reconcile

---

## 12. 代码改造建议

## 12.1 `task_cli.py`
在 add/update/done/reopen 等成功写入后：
- 增加可选钩子触发同步
- 或写入“待同步任务 ID”到队列文件

建议不要把复杂同步逻辑直接塞进 CLI 主代码。

## 12.2 `nlp_capture.py`
在 `--mode apply` 成功后，沿用同样触发机制。

## 12.3 `export_apple_reminders_sync.py`
需要增强：
- 支持增量导出
- 支持单任务导出
- 支持输出动作类型而不仅是目标列表

## 12.4 AppleScript
需要增强：
- 跨列表迁移
- 导出 reminder 原生 ID
- 导出变更集合
- 尽量输出机器可消费 JSON

---

## 13. 实施顺序建议

### Phase 1：自动单向同步底座
1. 新增 state store
2. 改造导出器支持增量
3. 新增统一同步入口 `sync_apple_reminders.py`
4. CLI/NLP 写入后自动触发 push
5. Mac 脚本支持 update + move + complete
6. 增加日志与重试

### Phase 2：Apple 变更导出
7. Mac 侧导出 reminders 变更 JSON
8. Linux 侧导入 import JSON
9. state 对齐 reminder_id / list_id / modified_at

### Phase 3：双向回写
10. 完成状态回写 GTD
11. 标题/备注/截止时间回写 GTD
12. 冲突处理与日志
13. 端到端回归测试

---

## 14. 风险点

### 风险 1：AppleScript 能力边界
Apple Reminders 可脚本化能力有限，某些字段（尤其修改时间、稳定 ID）需要实际验证。

应对：
- 先做 PoC 验证 reminder 原生 ID 与 modified date 的可获取性
- 若受限，则采用全量导出 + hash 比对

### 风险 2：双端时间精度不一致
GTD 与 Apple 时间格式/时区可能不同。

应对：
- 所有同步内部统一用 ISO 8601
- GTD 时间语义仍按 `Asia/Shanghai`
- 比较时统一规范化

### 风险 3：删除操作风险过高
互删最容易误伤。

应对：
- v0.4.0 第一版只做软删除/归档，不做硬删除互删

### 风险 4：自动触发过于频繁
每次小改都全量同步，会造成噪音和性能浪费。

应对：
- 增量导出
- debounce（短时间合并触发）
- 后台补偿轮询

---

## 15. 一句话结论

v0.4.0 的技术核心不是“再写一个 AppleScript”，而是：

**围绕主库、映射状态、增量导出、回写导入、冲突协调，搭起一套真正可长期维护的双向同步底座。**
