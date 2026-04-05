# API-first Reminder Cutover

## 目标

把主账号 GTD 的正式提醒链，从“读本地视图/缓存”切到“直接读 API open tasks 生成正文”。

本次只完成：
- 代码改造
- 提示词改造
- 文档改造

本次**不做**：
- 真发消息
- 改线上 cron
- 改线上 openclaw job

## 新入口

统一入口：

```bash
python3 /root/.openclaw/workspace/gtd-tasks/scripts/gtd_reminder_digest.py --mode morning
python3 /root/.openclaw/workspace/gtd-tasks/scripts/gtd_reminder_digest.py --mode evening
```

可选结构化输出：

```bash
python3 /root/.openclaw/workspace/gtd-tasks/scripts/gtd_reminder_digest.py --mode morning --json --pretty
```

## 设计原则

1. **提醒输入只认 API open tasks**
   - 使用 `GET /api/tasks?status=open&limit=500`
   - 不再用 `today.md`、`data/tasks.json`、readonly-cache 作为提醒输入真源

2. **保留旧模板骨架**
   - 今日
   - 明日
   - 未来
   - 币价监控
   - 下一步

3. **区分早晚两种模式**
   - morning：晨间总览
   - evening：晚间复盘

4. **保留 render_views.py**
   - 继续负责渲染 `today.md / inbox.md / done.md / weekly / matrix`
   - 但不再承担正式提醒正文生成

## 新旧链路职责划分

### 新链路（正式提醒 / 手动待办查询）
- `scripts/gtd_reminder_digest.py`
- 直接查 API
- 直接生成正文 / JSON 摘要

### 旧链路（展示 / cache）
- `scripts/pull_tasks_cache.py`
- `scripts/render_views.py`
- `today.md / inbox.md / done.md / weekly / matrix`

## 手动查询建议

当用户说：
- 发我待办清单
- 当前待办
- 看看我的待办
- 今天 / 明天 / 未来有哪些

优先走：

```bash
/root/.openclaw/workspace/gtd-tasks/scripts/gtd_manual_query.sh morning --json
```

如需纯文本：

```bash
/root/.openclaw/workspace/gtd-tasks/scripts/gtd_manual_query.sh morning --text
```

底层等价于：

```bash
python3 /root/.openclaw/workspace/gtd-tasks/scripts/gtd_reminder_digest.py --mode morning --json
```

理由：
- 直接取 API 最新 open tasks
- 结构稳定
- 可以复用统一提醒骨架
- 不会依赖 readonly-cache 是否刚同步
- 手动查询与定时提醒同源，后续切换成本更低

## 定时提醒切换建议（后续人工切）

### 早上提醒
旧：读本地 markdown / prompt 拼正文  
新：

```bash
python3 /root/.openclaw/workspace/gtd-tasks/scripts/gtd_reminder_digest.py --mode morning
```

### 晚上提醒
旧：`daily-reminder.sh` 读 `today.md`  
新：

```bash
python3 /root/.openclaw/workspace/gtd-tasks/scripts/gtd_reminder_digest.py --mode evening
```

说明：当前 `daily-reminder.sh` 已改成兼容包装层，默认转发到 evening 模式。

## 后续建议

1. 先在测试环境人工跑 morning / evening 各一次，确认正文风格
2. 再把 cron / job 切到新脚本
3. 再把线上 AIGTD 话术/会话行为实际切到 `scripts/gtd_manual_query.sh morning --json`
4. 等验证稳定后，再考虑：
   - 增加更细筛选（只看 category / tag）
   - 增加 account/user 维度
   - 给 digest 增加更明确的 schema version
