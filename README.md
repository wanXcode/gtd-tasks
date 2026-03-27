# GTD Tasks

一个基于 `data/tasks.json` 主库的本机 GTD 系统，给 OpenClaw / AI 助手和人一起用。

从 v0.2.1 开始，`today.md / inbox.md / matrix/*` 不再是事实源，只是渲染视图。
从 v0.2.2 开始，补齐了三层能力：

1. 更完整的 CLI 操作闭环
2. 自然语言录入入口 `scripts/nlp_capture.py`
3. 更适合复盘的 `done.md` 与 `weekly/review-latest.md`

时间语义统一按 `Asia/Shanghai`（UTC+8）解释。

## 目录结构

```text
├── data/
│   ├── tasks.json              # 主库，唯一事实源
│   └── README.md
├── scripts/
│   ├── task_cli.py             # 结构化增删改查/批量操作
│   ├── nlp_capture.py          # 自然语言录入（preview/apply）
│   ├── aigtd_executor.py       # AIGTD 写入/修改统一入口
│   ├── sync_agent_mac.py       # Mac API-first 同步代理
│   ├── pull_tasks_cache.py     # 从 API 刷新本地 cache
│   ├── render_views.py         # 渲染 today/inbox/done/weekly/matrix
│   └── migrate_legacy.py
├── today.md                    # 今日视图
├── inbox.md                    # 总览视图
├── done.md                     # 已完成/取消/归档视图
├── weekly/
│   └── review-latest.md        # 最新周回顾视图
├── matrix/
│   ├── q1-urgent-important.md
│   ├── q2-important-not-urgent.md
│   ├── q3-urgent-not-important.md
│   └── q4-not-urgent-not-important.md
└── archive/
```

## 数据原则

- GTD 的唯一事实源是当前配置的主后端（主账号现已收敛为 API-first）；本地 `data/tasks.json` 仅作为运行期 cache
- Markdown 文件全部由脚本自动生成，属于本地运行视图
- `data/tasks.json`、`today.md`、`inbox.md`、`done.md`、`weekly/review-latest.md`、`matrix/*.md` 现已视为本地运行产物，不再纳入 Git 版本管理
- “今天 / 明天 / 下周 / 未来” 等时间判断固定按北京时间
- 主分类体系统一为 5 类：`inbox / project / next_action / waiting_for / maybe`
- `bucket` 只保留时间语义（today / tomorrow / future），不再作为主分类体系
- 默认任务字段里，`category=inbox`、`bucket=future`、`quadrant=q2`
- 常规视图只展示 `status=open && deleted_at=null` 的任务
- `done / cancelled / archived` 进入完成区（`done.md` / `weekly/review-latest.md`）
- `deleted_at != null` 视为真删除，不进入主清单、完成区、矩阵等常规视图
- CLI 中 `done` 表示完成并保留历史；`delete` 表示真删除（设置 `deleted_at`），两者语义彻底分开
- Apple 回传当前只支持 `completed -> done`，不支持标题、备注、分类、删除回写

## CLI：结构化任务操作

先看帮助：

```bash
python3 scripts/task_cli.py --help
python3 scripts/task_cli.py list --help
```

### 新增任务

```bash
python3 scripts/task_cli.py add "给张闯回信"
python3 scripts/task_cli.py add "整理财务方案" --category next_action --bucket today --quadrant q1 --tags ME FIN --note "今晚过一遍"
python3 scripts/task_cli.py add "季度复盘项目" --category project
```

默认分类现在是 `category=inbox`，也就是先进入收集箱；默认 `bucket=future`，保留“先收进去，再决定今天/明天”的节奏。

### 列表查询

```bash
python3 scripts/task_cli.py list
python3 scripts/task_cli.py list --bucket today
python3 scripts/task_cli.py list --status open --tag ME
python3 scripts/task_cli.py list --text 规划 --verbose --limit 10
```

支持筛选：

- `--id`
- `--status`
- `--category`
- `--bucket`
- `--quadrant`
- `--tag`
- `--text`
- `--limit`
- `--verbose`

### 更新 / 完成 / 重开

```bash
python3 scripts/task_cli.py update tsk_20260317_008 --bucket today --note "今晚发出"
python3 scripts/task_cli.py update tsk_20260317_008 --add-tags URGENT
python3 scripts/task_cli.py done tsk_20260317_008
python3 scripts/task_cli.py reopen tsk_20260317_008 --bucket tomorrow
python3 scripts/task_cli.py add "给张闯回信" --sync-apple-reminders
```

### 批量 move / tag

```bash
python3 scripts/task_cli.py move --tag ME --bucket today --to-bucket future
python3 scripts/task_cli.py move --text 规划 --bucket tomorrow --to-bucket today

python3 scripts/task_cli.py tag add ME --text 回信
python3 scripts/task_cli.py tag remove ME --id tsk_20260317_008
python3 scripts/task_cli.py tag set ME WAIT --text 海南
```

## NLP：自然语言录入

v0.2.2 新增 `scripts/nlp_capture.py`，用于把一句自然语言先解析成结构化任务，再决定是否写入主库。

### preview：只预览，不写入

```bash
python3 scripts/nlp_capture.py "明天提醒我给张闯回信 #ME"
python3 scripts/nlp_capture.py "把海南公司主体先放未来，等确认后再推进"
```

默认模式是 `preview`，会输出：

- `title`
- `category`
- `bucket`
- `quadrant`
- `tags`
- `note`
- `timezone`
- `business_now`

### apply：解析后直接落库

```bash
python3 scripts/nlp_capture.py "明天提醒我给张闯回信 #ME" --mode apply
python3 scripts/nlp_capture.py "明天提醒我给张闯回信 #ME" --mode apply --sync-apple-reminders
```

`apply` 会：

1. 先打印解析结果
2. 调用 `task_cli.py add`
3. 自动触发 `render_views.py`
4. 如显式传 `--sync-apple-reminders` 或设置环境变量开启，则继续尝试单向 push 到 Apple Reminders

### 当前支持的轻量规则

- category：优先识别 `waiting_for / project / next_action / maybe / inbox`
- bucket：识别 `今天 / 明天 / 下周 / 以后 / 先放未来` 等时间语义
- tags：识别显式标签（如 `#ME`）和少量中文表达（如“我来处理”“等确认”）
- note：从“备注/说明/note”或少量提示短语里提取
- quadrant：识别 `#Q1~#Q4` 及少量中文表达，否则默认 `q2`

这版追求的是“够用、稳定、可预览”，不是复杂 NLP 引擎。

## 视图生成

执行：

```bash
python3 scripts/render_views.py
```

会生成：

- `today.md`
- `inbox.md`
- `done.md`
- `weekly/review-latest.md`
- `matrix/*.md`

### 视图过滤规则

- `today.md / inbox.md / matrix/*.md` 只显示 open 且未 deleted 的任务
- `done.md` 只显示 `done / cancelled / archived` 且未 deleted 的任务
- `weekly/review-latest.md` 的 open 统计只看 open 且未 deleted；完成统计只看 `done / cancelled / archived` 且未 deleted
- deleted 任务默认不进入任何常规视图

### done.md

集中查看：

- 已完成
- 已取消
- 已归档

### weekly/review-latest.md

集中看：

- 本周新增任务数
- 本周完成/取消/归档任务数
- 当前未完成任务数
- 按 bucket 分类的待办概览
- 本周新增 / 本周完成 / 当前未完成任务明细

## 推荐日常流程

1. 有新事项，先用 `nlp_capture.py` preview/apply 收进去
2. 要批量整理时，用 `task_cli.py list / move / tag / update`
3. 每次修改后自动 render，直接看 `today.md / done.md / weekly/review-latest.md`
4. 定时提醒或 AI 对话都只读视图，不直接把 Markdown 当事实源改写

## AIGTD 运行规则版本管理

AIGTD 的 live 运行规则文件位于：

- `/root/.openclaw/workspace/agents/aigtd/PROMPT.md`
- `/root/.openclaw/workspace/agents/aigtd/OPERATING-GUIDE.md`
- `/root/.openclaw/workspace/agents/aigtd/MEMORY.md`

但从当前版本开始，`gtd-tasks` 仓库内的 **版本源** 统一放在：

- `agent-runtime/aigtd/`

也就是说：

- 后续若要修改 AIGTD 运行规则，优先修改仓库内 `agent-runtime/aigtd/` 下文件
- 再执行同步脚本，把仓库版本同步到 live agent 目录：

```bash
python3 /root/.openclaw/workspace/gtd-tasks/scripts/sync_aigtd_runtime_files.py
```

仅查看会发生什么变化：

```bash
python3 /root/.openclaw/workspace/gtd-tasks/scripts/sync_aigtd_runtime_files.py --dry-run
```

这样可以避免“live 配置改了，但 GitHub 没记录”的问题。

## Apple Reminders 同步（API-first）

当前 Apple Reminders 同步主链已经收敛为：

- GTD API 是唯一事实源
- Mac 本地通过 `scripts/sync_agent_mac.py` 消费 `/api/changes`
- Apple Reminders completed 再回写 `/api/apple/completed`

核心入口：

```bash
python3 scripts/sync_agent_mac.py
python3 scripts/sync_agent_mac.py --full-sync
python3 scripts/sync_agent_mac.py --reset-cursor --full-sync
```

更完整的运行、排障、恢复说明，统一见：

- `MAC-SYNC-RUNBOOK.md`

### Mac API-first 同步方案（推荐）

当前推荐部署方式已经收敛为 **API-first**：

1. 线上 GTD API 作为唯一事实源
2. Mac 本地 launchd 定时执行 `launchd/com.wan.gtd.sync.plist`
3. 实际同步入口为 `scripts/sync_agent_mac.py`
4. Mac 通过 `/api/changes` 拉增量变化并同步到 Apple Reminders
5. Apple Reminders completed 再回写 `/api/apple/completed`

### 状态与日志

- Mac 同步状态：`sync/mac-sync-state.json`
- Mac 本地 mapping：`sync/mac-apple-mappings.json`
- Mac 日志文件：`logs/mac-sync-agent.log`
- Mac 自动执行说明：`MAC-SYNC-RUNBOOK.md`
- launchd 模板：`launchd/com.wan.gtd.sync.plist`
- 安装脚本：`launchd/install.sh`

### 旧方案说明

旧的 Git/export 驱动 Mac 同步链（例如 `mac/run_apple_reminders_sync.sh`、`mac/com.xiaohua.gtd-apple-reminders-sync.plist`）已退役，不再作为主同步入口。

## 版本

- 当前目标版本：`v0.4.0-a`
- 旧需求文档：`requirements-v0.2.2.md`
- 同步设计文档：`apple-reminders-sync-v0.3.0.md`
- 自动同步需求：`requirements-v0.4.0-auto-bidirectional-sync.md`

---

小花的看法：这一步先把“能自动、能观察、能回退”的底座立住，比急着做双向靠谱得多。 
