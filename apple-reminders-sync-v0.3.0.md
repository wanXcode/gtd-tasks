# GTD Tasks v0.3.0 - Apple Reminders 同步设计文档

## 1. 目标

本阶段目标不是做完整双向同步，而是尽快实现：

**将 `gtd-tasks` 主库中的任务，按既定分类规则单向同步到 Apple Reminders，并在 iPhone 上原生可用。**

原则：
- `gtd-tasks` 仍然是唯一事实源
- Apple Reminders 是移动端消费层
- 先做单向同步（GTD -> Apple Reminders）
- 先保证能用，再追求双向和冲突处理

---

## 2. 当前前提

已知条件：
- GTD 主库位于 Linux：`/root/.openclaw/workspace/gtd-tasks/data/tasks.json`
- 用户有可用 Mac，可作为 Apple Reminders 同步桥
- 用户明确要求：**Apple Reminders 分类按用户提供的截图分类规则执行**
- 因此，本设计不再直接采用此前默认的 `today / tomorrow / future -> 三个 Reminder 列表` 的粗映射方式

---

## 3. 架构

整体架构如下：

`gtd-tasks (Linux 主库)`
→ 导出同步 payload
→ `Mac Sync Agent`
→ Apple Reminders
→ iPhone（通过 iCloud 自动同步）

职责划分：

### Linux 端
负责：
- 读取 GTD 主库
- 根据分类规则生成同步 payload
- 输出结构化 JSON 给 Mac 消费

不负责：
- 直接调用 Apple Reminders
- 直接处理 iCloud / Apple API

### Mac 端
负责：
- 读取 Linux 导出的同步 JSON
- 在 Apple Reminders 中创建 / 更新提醒事项
- 按分类规则将任务放入正确的 Reminder List

### iPhone 端
负责：
- 展示 Apple Reminders 结果
- 提供原生使用体验

---

## 4. 同步方向

v0.3.0 MVP 仅支持：

**GTD -> Apple Reminders**

不支持：
- Apple Reminders -> GTD
- 双向冲突合并
- 删除回写
- 完成状态回写

原因：
1. 先降低复杂度
2. 先验证分类和映射是否符合真实使用习惯
3. 后续如确认 Apple Reminders 体验合适，再做回写与双向同步

---

## 5. 分类策略

## 5.1 分类原则

Apple Reminders 中的分类，**以用户提供的截图分类体系为准**。

也就是说：
- GTD 内部现有的 `bucket` / `quadrant` 并不是最终的 Apple Reminders 分类结果
- 同步层需要新增一层“Reminders 分类映射规则”
- 这层规则优先服从用户定义的移动端使用习惯

## 5.2 设计要求

本阶段需要将“用户截图中的分类结构”抽象成一份配置，而不是写死在脚本中。

建议新增配置文件：

`config/apple_reminders_mapping.json`

配置内容包括：
- Apple Reminders 的目标列表名称
- GTD 任务进入哪个列表的规则
- 必要时支持按 tag / status / bucket / note 进行映射

例如（示意，不代表最终分类）：

```json
{
  "lists": [
    {
      "name": "今天",
      "rules": [{"bucket": "today"}]
    },
    {
      "name": "跟进",
      "rules": [{"tags_contains": "WAIT"}]
    },
    {
      "name": "我来做",
      "rules": [{"tags_contains": "ME"}]
    }
  ]
}
```

实际规则以用户截图为准。

## 5.3 分类优先级

当一个任务同时命中多个规则时，必须定义优先级。

建议优先级：
1. 明确人工标签规则（如 `ME` / `WAIT` / 特定项目标签）
2. 明确业务分类规则
3. bucket 规则（today/tomorrow/future）
4. 默认兜底列表

这样做是为了保证：
- 用户显式表达的分类优先
- 时间分桶只是次级维度，不强行覆盖人工分类

---

## 6. 数据映射

## 6.1 主库仍是唯一事实源

`data/tasks.json` 仍然是唯一事实源。

Apple Reminders 不是事实源，只是投影层。

## 6.2 同步对象范围

v0.3.0 默认只同步：
- `status = open` 的任务

默认不同步：
- `done`
- `cancelled`
- `archived`

后续可以扩展“自动从 Reminders 移除/标记完成”，但 MVP 不做。

## 6.3 字段映射

建议第一版映射如下：

### GTD -> Reminder title
- `title` → Reminder 标题

### GTD -> Reminder notes
以下信息写入 notes：
- GTD 任务备注 `note`
- 机器标识字段
- tags
- 更新时间

示例：

```text
[GTD_ID] tsk_20260318_001
[GTD_BUCKET] future
[GTD_QUADRANT] q2
[GTD_TAGS] ME
[GTD_UPDATED_AT] 2026-03-18T00:09:26+08:00

补 release 文档
```

### GTD -> Reminder list
由映射配置决定，而非简单固定映射。

---

## 7. 同步数据格式

建议 Linux 端导出：

`sync/apple-reminders-export.json`

结构示例：

```json
{
  "version": "0.3.0-mvp",
  "timezone": "Asia/Shanghai",
  "generated_at": "2026-03-18T00:30:00+08:00",
  "tasks": [
    {
      "gtd_id": "tsk_20260318_001",
      "title": "整理发布 v0.2.2",
      "note": "补 release 文档",
      "status": "open",
      "bucket": "future",
      "quadrant": "q2",
      "tags": ["ME"],
      "updated_at": "2026-03-18T00:09:26+08:00",
      "target_list": "这里由映射规则计算后填入"
    }
  ]
}
```

---

## 8. Linux 端实现

建议新增脚本：

`scripts/export_apple_reminders_sync.py`

职责：
1. 读取 `data/tasks.json`
2. 加载 `config/apple_reminders_mapping.json`
3. 对 open 任务执行分类计算
4. 输出 `sync/apple-reminders-export.json`

输出要求：
- 仅输出 Apple Reminders 需要的字段
- 记录生成时间
- 显式给出每个任务的 `target_list`
- 未匹配到规则的任务进入默认列表

---

## 9. Mac 端实现

建议 Mac 端提供一个本地同步脚本，形式可选：
- AppleScript
- Shortcuts
- Python + osascript

MVP 优先建议：
**AppleScript / Shortcuts**

职责：
1. 读取 `apple-reminders-export.json`
2. 检查目标 Reminder List 是否存在，不存在则提示/创建
3. 根据 `GTD_ID` 查找是否已有对应提醒事项
4. 若不存在则创建
5. 若已存在则更新标题、备注、列表归属

查找现有任务时，优先通过 note 中的：
- `[GTD_ID] xxx`
来识别，而不是仅靠标题匹配。

---

## 10. 最小落地步骤

### Phase 1：分类配置定稿
- 根据用户截图，整理出 Apple Reminders 分类清单
- 将规则写入 `config/apple_reminders_mapping.json`

### Phase 2：导出器
- 实现 `export_apple_reminders_sync.py`
- 生成标准同步 JSON

### Phase 3：Mac 桥
- 实现 Reminder 写入脚本
- 确保可创建 / 更新 Reminder

### Phase 4：联调
- Linux 生成导出文件
- Mac 消费导出文件
- iPhone 上检查分类与显示效果

---

## 11. 风险与注意事项

### 11.1 分类规则未结构化前，容易反复返工
所以第一优先级不是写同步代码，而是先把“截图分类”整理成机器可执行规则。

### 11.2 Apple Reminders 不适合第一版就做复杂双向
如果一开始就做回写，会很快引入：
- 删除冲突
- 状态不一致
- 列表迁移问题
- 标题被手改后识别失败

所以 MVP 先不碰。

### 11.3 机器标记必须稳定
`[GTD_ID]` 一类标记必须保留在 note 中，否则后续无法稳定识别已有任务。

---

## 12. 下一步建议

接下来建议立即产出两个交付物：

1. `config/apple_reminders_mapping.json`
   - 把用户截图中的分类规则正式结构化

2. `scripts/export_apple_reminders_sync.py`
   - 完成 Linux 侧的标准导出

等这两个完成后，再写 Mac 侧桥接脚本。

---

## 13. 一句话总结

v0.3.0 的核心不是“把任务简单塞进 Reminders”，而是：

**在保持 `gtd-tasks` 为唯一事实源的前提下，按用户自己的分类体系，把任务稳定投影到 Apple Reminders / iPhone。**
