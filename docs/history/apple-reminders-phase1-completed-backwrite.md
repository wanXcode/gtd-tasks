# Apple Reminders -> GTD 双向同步 Phase 1（只回写 completed -> done）

## 结论

这一版很适合直接落最小代码，而且应该**严格收口**：

- 只处理 **Apple Reminders 已勾选完成** → `gtd-tasks` 里标记 `done`
- **只认带稳定 `[GTD_ID] <task_id>` 标记** 的 reminder
- 不做标题/备注/截止时间/删除回写
- 事件通过 **Git 驱动文件** 传递，不引入 SSH/直连
- Linux 侧的 `data/tasks.json` 更新走**单独消费脚本**，不混入现有 export 自动提交流程

---

## 最小实现设计

### 1) 推荐事件文件格式

建议新增：`sync/apple-reminders-completed-events.json`

```json
{
  "version": "0.4.0-phase1",
  "generated_at": "2026-03-19T08:30:00+08:00",
  "events": [
    {
      "event_id": "tsk_20260318_001::给张三回邮件::2026-03-19T08:29:10",
      "event_type": "completed",
      "source": "apple_reminders_phase1",
      "gtd_id": "tsk_20260318_001",
      "completed_at": "2026-03-19T08:29:10",
      "apple_list_name": "下一步行动@NextAction",
      "title": "给张三回邮件"
    }
  ]
}
```

字段约束：

- `event_type`: 固定 `completed`
- `gtd_id`: 必填；没有就直接丢弃
- `event_id`: 去重键，第一版允许用 `gtd_id + title + completed_at` 组合
- `completed_at`: 尽量带时间；拿不到就允许空，但不建议
- `source`: 固定标识来源链路

---

### 2) Mac 侧采集 completed 事件的脚本设计

建议新增一个**独立脚本**，不要改现有单向 push 主脚本：

- `mac/export_completed_reminders_phase1.applescript`

职责：

1. 遍历 Reminders 列表
2. 只取 `completed=true` 的 reminder
3. 从 body 里提取 `[GTD_ID] xxx`
4. 没有 `gtd_id` 就跳过
5. 导出成 `sync/apple-reminders-completed-events.json`

为什么独立：

- 不污染现有 `sync_apple_reminders_mac.applescript` 的单向同步路径
- 出问题时可以单独关闭/回滚
- 便于后面 Phase 2 再扩字段

当前仓库已具备 `[GTD_ID]` 查找约定，所以 Phase 1 最稳的策略就是**只吃这个稳定锚点**。

---

### 3) Linux 侧消费事件并更新 GTD 的脚本设计

建议新增独立脚本：

- `scripts/consume_apple_reminders_completed.py`

职责：

1. 读取 `sync/apple-reminders-completed-events.json`
2. 读取 `sync/apple-reminders-completed-applied.json`（已消费日志）
3. 对每条事件执行：
   - 无 `gtd_id` → 跳过
   - `event_id` 已消费 → 跳过
   - `gtd_id` 在 `tasks.json` 找不到 → 跳过
   - 任务已经 `done` → 记已消费并跳过
   - 否则把任务改成：
     - `status = done`
     - `bucket = archive`
     - `completed_at = event.completed_at`
     - `updated_at = now`
     - `sync_version += 1`
4. 保存 `data/tasks.json`
5. 渲染视图（`today.md / done.md / weekly/...`）
6. 写入已消费日志

这样 Linux 侧的改动路径是：

- **单独消费脚本写 `data/tasks.json`**
- 与现有 export / auto-push / git-sync-export 分离

这正好满足“不要污染现有 export 自动提交流程”。

---

## 幂等 / 去重策略

推荐分两层：

### 第一层：事件级去重

文件：`sync/apple-reminders-completed-applied.json`

```json
{
  "version": "0.4.0-phase1",
  "applied_event_ids": [
    "tsk_20260318_001::给张三回邮件::2026-03-19T08:29:10"
  ],
  "applied_events": [
    {
      "event_id": "tsk_20260318_001::给张三回邮件::2026-03-19T08:29:10",
      "gtd_id": "tsk_20260318_001",
      "status": "applied",
      "applied_at": "2026-03-19T08:31:00+08:00"
    }
  ]
}
```

消费时先查 `event_id`。

### 第二层：状态级幂等

即使事件重复，只要任务已是 `done`，也不重复改写业务状态。

这样即使：

- Mac 反复导出同一 completed reminder
- Git pull 重复拿到同一个事件文件
- Linux 定时重复消费

都不会把任务反复改坏。

---

## Git 提交边界建议

这是这版里最重要的边界之一。

### 建议拆成两条独立 Git 路径

#### A. Mac 侧事件提交
Mac 只负责提交：

- `sync/apple-reminders-completed-events.json`

提交信息建议：

- `chore(sync): export apple reminders completed events`

#### B. Linux 侧消费提交
Linux 消费成功后，单独提交：

- `data/tasks.json`
- `today.md`
- `done.md`
- `weekly/review-latest.md`
- `matrix/*`
- `sync/apple-reminders-completed-applied.json`

提交信息建议：

- `chore(sync): apply apple reminders completed events`

### 为什么必须拆开

因为现有自动 export git 提交流程只应该负责：

- `sync/apple-reminders-export.json`
- `sync/apple-reminders-sync-state.json`

如果把 completed 回写也混进去，会出现：

- 自动 export 提交里夹带业务数据变更
- 难审计到底是 GTD 主动改的，还是 Reminders 回写改的
- 出问题不好回滚

所以我明确建议：

- **保留现有 export 自动提交流程不动**
- **completed 回写走单独消费 + 单独提交**

---

## 现在是否适合直接落第一版代码？

适合，而且我建议就按最小版先落。

原因：

1. 当前仓库已经有稳定 `gtd_id`
2. 当前单向同步主链已经可用
3. Phase 1 只做 `completed -> done`，逻辑简单、风险可控
4. 可以完全不改现有 push/export 主流程，只新增旁路文件和脚本

---

## 已落的最小代码

我已经补了这几项：

### 新增 1：事件文件样板
- `sync/apple-reminders-completed-events.json`

### 新增 2：已消费日志样板
- `sync/apple-reminders-completed-applied.json`

### 新增 3：Linux 消费脚本
- `scripts/consume_apple_reminders_completed.py`

用法：

```bash
python3 scripts/consume_apple_reminders_completed.py --dry-run
python3 scripts/consume_apple_reminders_completed.py
```

### 新增 4：Mac 侧 completed 导出草案脚本
- `mac/export_completed_reminders_phase1.applescript`

这是一个保守版草案：

- 只导出已完成 reminder
- 只认 body 中 `[GTD_ID] xxx`
- 输出事件 JSON

注意：AppleScript 对 `completion date` / 某些属性在不同系统版本上可能有差异，这个脚本需要在真实 Mac 上跑一轮验证；但设计方向是对的，而且独立文件不影响现有单向同步。

---

## 我对第一版的建议

我建议哥哥就这样推进：

### 先上线的范围
- Mac 导出 completed 事件到 Git
- Linux 拉取后手动/定时跑 `consume_apple_reminders_completed.py`
- 成功回写 GTD done

### 暂时不要做
- 标题回写
- note 回写
- due date 回写
- reminder 删除回写
- 没有 `gtd_id` 的提醒事项入库
- 自动从 Reminders 新建 GTD 任务

因为这些一放开，复杂度和误伤风险会立刻上去。

---

## 后续最自然的下一步

等 Phase 1 稳了，再补这两个增强就够：

1. 给事件文件加 `apple_reminder_id`
2. 给 Linux 消费链路补一个专门的提交脚本 / 定时入口

但这两个都不影响当前最小版先跑起来。

---

## 一句话结论

这版最稳的实现就是：**Mac 导出“带 gtd_id 的 completed 事件”到 Git，Linux 用独立脚本幂等消费，把 GTD 任务改成 done；整条链路与现有单向 export 自动提交流程彻底分开。**
