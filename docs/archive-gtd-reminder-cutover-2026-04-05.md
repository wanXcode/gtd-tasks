# GTD 提醒链正式切换归档说明（2026-04-05）

## 一、背景

本轮改造的直接触发问题是：

- 用户已完成/线上状态已变化
- 但 GTD 提醒仍读到了旧任务
- 典型现象是提醒内容来自本地缓存/渲染视图，而不是 API 当前真相

排查后确认，旧链路存在如下结构性风险：

```text
API/主库
-> pull_tasks_cache.py
-> data/tasks.json
-> render_views.py
-> today.md / inbox.md / done.md
-> AIGTD readonly-cache
-> 提醒 / 手动待办查询
```

这条链路的问题不是某一个脚本偶发失败，而是“正式提醒正文”依赖展示层产物，导致：

1. 缓存一旦未及时刷新，就会把旧数据正式发给用户
2. 排障时必须跨越 API / cache / render / readonly-cache 多层链路
3. 手动“待办清单”和定时提醒容易出现不同源、不一致

因此本轮目标是把主账号 GTD 的正式提醒链收敛成 **API-first**。

---

## 二、改造目标

本轮改造的明确目标：

1. 正式提醒正文直接读 API open tasks，不再依赖 `today.md`
2. 保留 `render_views.py` 与 `today.md / inbox.md / done.md / matrix/*`，但仅作为展示层
3. 让早间提醒、晚间提醒、手动“待办清单 / 当前待办”查询尽量同源
4. 收口 cron 配置尾巴，避免 delivery target 与 payload target 冲突
5. 为后续排障留下清晰文档与 session 污染处理说明

---

## 三、本轮完成的改造

### 1. 新增正式提醒正文构建脚本

新增：

- `scripts/gtd_reminder_digest.py`

职责：

- 直接调用 API 获取 open tasks
- 按真实 bucket 生成：
  - 今日
  - 明日
  - 未来
  - 币价监控
  - 下一步
- 支持两种模式：
  - `--mode morning`
  - `--mode evening`
- 支持 `--json`，方便手动查询与 agent 复用

这一步使正式提醒正文不再依赖：

- `data/tasks.json`
- `today.md`
- `readonly-cache`

---

### 2. 手动待办查询入口与定时提醒同源

新增：

- `scripts/gtd_manual_query.sh`

作用：

- 作为手动“待办清单 / 发我待办清单 / 当前待办”查询的薄包装
- 底层完全复用 `gtd_reminder_digest.py`
- 避免单独再造第二套摘要逻辑

这样主账号形成：

- 定时提醒：`gtd_reminder_digest.py`
- 手动查询：`gtd_manual_query.sh -> gtd_reminder_digest.py`

---

### 3. 提示词与运行规则切到新链

本轮已更新：

- `prompts/gtd-reminder-template.md`
- `prompts/gtd-morning-brief.md`
- `prompts/gtd-daily-checkin.md`
- `agent-runtime/aigtd/PROMPT.md`
- `agent-runtime/aigtd/OPERATING-GUIDE.md`
- `agent-runtime/aigtd/MEMORY.md`
- `docs/aigtd-runtime-rules.md`

更新后的统一口径：

- 正式提醒正文优先走 `gtd_reminder_digest.py`
- 手动待办查询优先走 `gtd_manual_query.sh`
- `today.md / data/tasks.json / readonly-cache` 不再作为正式提醒输入真源

---

### 4. 保留展示层，但降级为“只展示不决策”

保留：

- `render_views.py`
- `today.md`
- `inbox.md`
- `done.md`
- `weekly/review-latest.md`
- `matrix/*`

但职责已明确收敛为：

- 人类浏览
- 复盘
- 调试交叉核验

而不是：

- 正式提醒正文输入
- 单条任务真相判断来源

---

### 5. 审计并收口 cron 引用点

本轮核对了主账号实际运行中的 cron job：

- `gtd-morning-brief`
- `gtd-daily-checkin`

确认其 payload 已经统一指向：

- `prompts/gtd-morning-brief.md`
- `prompts/gtd-daily-checkin.md`

而不再直接读 `today.md`。

同时，本轮还进一步统一了这两个 job 的：

- `delivery.to`
- payload 中要求显式发送的 `target`

避免“cron 元信息 target”和“payload target”不一致造成的后续混淆。

---

## 四、当前正式链路

主账号 GTD 当前建议视为以下正式链路：

### 1. 定时提醒

```text
gtd-morning-brief / gtd-daily-checkin
-> prompts/gtd-morning-brief.md / gtd-daily-checkin.md
-> prompts/gtd-reminder-template.md
-> scripts/gtd_reminder_digest.py
-> message 发送
```

### 2. 手动待办查询

```text
用户说“待办清单 / 发我待办清单 / 当前待办”
-> scripts/gtd_manual_query.sh
-> scripts/gtd_reminder_digest.py
-> text/json 输出
```

### 3. 展示层

```text
API / cache
-> render_views.py
-> today.md / inbox.md / done.md / weekly / matrix
```

注意：展示层仍存在，但不再承担正式提醒输入责任。

---

## 五、遗留与风险说明

### 1. 历史 cron 备份仍保留旧链

工作区中历史备份文件（如 `memory/cron-backups/*.json`）中仍可能存在旧 today.md 链。

结论：

- 这些文件只能视为历史档案
- **禁止直接 restore**
- 如需恢复，必须先人工审 `payload.message`

### 2. 旧 session 污染仍可能导致“行为像旧链”

即使仓库代码与 cron 配置都已切到新链，如果 AIGTD 会话仍表现得像旧链，优先怀疑：

- 旧 session prompt / memory 污染

处理建议：

- 路径：`/root/.openclaw/agents/aigtd/sessions/sessions.json`
- 删除对应 key：
  - `agent:aigtd:feishu:direct:<open_id>`
- 让下一条消息重建新 session

### 3. wife 子链路未纳入本轮切换

本轮收口对象仅为主账号 GTD。

`users/wife/` 下的 morning/daily 提醒链仍保留独立旧结构，后续如需统一，应单独设计与切换。

---

## 六、本轮涉及文件（摘要）

### 新增
- `scripts/gtd_reminder_digest.py`
- `scripts/gtd_manual_query.sh`
- `docs/api-first-reminder-cutover.md`
- `docs/reminder-entrypoint-audit-2026-04-05.md`
- `docs/archive-gtd-reminder-cutover-2026-04-05.md`

### 修改
- `daily-reminder.sh`
- `deploy.sh`
- `prompts/gtd-reminder-template.md`
- `prompts/gtd-morning-brief.md`
- `prompts/gtd-daily-checkin.md`
- `README.md`
- `TIMEZONE.md`
- `docs/aigtd-runtime-rules.md`
- `agent-runtime/aigtd/PROMPT.md`
- `agent-runtime/aigtd/OPERATING-GUIDE.md`
- `agent-runtime/aigtd/MEMORY.md`
- `CHANGELOG.md`
- `/root/.openclaw/workspace/TOOLS.md`（补充 session 污染处理经验）

---

## 七、当前结论

截至 2026-04-05，本轮主账号 GTD 提醒链改造已基本闭环：

- 正式提醒：已切 API-first
- 手动待办查询：已与正式提醒同源
- 展示层：继续存在，但不再作为正式提醒输入
- cron target：已收口一致

后续若出现异常，优先检查顺序应为：

1. cron payload / target 是否仍为当前版本
2. session 是否被旧 prompt / memory 污染
3. 是否误恢复了历史旧 cron 备份

本次归档说明用于后续排障、回顾与 Git 提交说明。
