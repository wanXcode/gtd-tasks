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
│   ├── export_apple_reminders_sync.py  # 导出 Apple Reminders 同步 payload
│   ├── sync_apple_reminders.py         # 统一同步入口（export/push/status）
│   ├── apple_reminders_sync_lib.py     # 同步状态/日志/自动 push 公共层
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

- `data/tasks.json` 是唯一事实源
- Markdown 文件全部由脚本自动生成
- “今天 / 明天 / 下周 / 未来” 等时间判断固定按北京时间
- 主分类体系统一为 5 类：`index / project / next_action / waiting_for / maybe`
- `bucket` 只保留时间语义（today / tomorrow / future），不再作为主分类体系
- 默认任务字段里，`category=index`、`bucket=future`、`quadrant=q2`

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

默认分类现在是 `category=index`，也就是先进入收集箱；默认 `bucket=future`，保留“先收进去，再决定今天/明天”的节奏。

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

- category：优先识别 `waiting_for / project / next_action / maybe / index`
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

## Apple Reminders 同步（v0.4.0-a MVP）

这版新增了一个低风险同步底座，但仍然坚持：

- `data/tasks.json` 是唯一事实源
- 当前只做 **GTD -> Apple Reminders 单向 push**
- 不碰双向回写
- 原有手动链路继续可用
- **推荐架构改为：Linux 更新仓库，Mac 本地 `git pull` 后再执行 AppleScript**
- **不再推荐 Linux 主动 SSH / rsync / scp 推送到 Mac**

### 统一入口

```bash
python3 scripts/sync_apple_reminders.py --mode export
python3 scripts/sync_apple_reminders.py --mode sync --dry-run
python3 scripts/sync_apple_reminders.py --mode status
```

### 增量导出 / 单任务导出

```bash
python3 scripts/export_apple_reminders_sync.py --changed-only
python3 scripts/export_apple_reminders_sync.py --task-id tsk_20260317_008
python3 scripts/sync_apple_reminders.py --mode export --task-id tsk_20260317_008
```

### 自动 push（默认关闭）

默认不会自动 push。可以两种方式开启：

```bash
python3 scripts/task_cli.py add "给张闯回信" --sync-apple-reminders
python3 scripts/nlp_capture.py "明天提醒我给张闯回信 #ME" --mode apply --sync-apple-reminders
```

或者设置环境变量：

```bash
export GTD_APPLE_REMINDERS_AUTO_PUSH=1
```

如果当前机器不是 macOS，或没有 `osascript` / Apple Reminders 环境，系统会：

- 正常完成 export
- 记录状态和日志
- 把 push 标记为 skipped / failed
- 不影响主库写入

### Linux 侧 Git 自动提交（默认关闭）

现在可以把 Apple Reminders 导出链路接到 Git，但仍然保持很保守：

- 只允许提交这两个同步文件：
  - `sync/apple-reminders-export.json`
  - `sync/apple-reminders-sync-state.json`
- **不会** 自动提交 `data/tasks.json`、`today.md`、`done.md`、`weekly/*` 等业务文件
- commit / push 失败只记日志，不影响主流程

推荐环境变量：

```bash
export GTD_APPLE_REMINDERS_GIT_SYNC_ENABLED=1
export GTD_APPLE_REMINDERS_GIT_PUSH_ENABLED=1
# 可选
export GTD_APPLE_REMINDERS_GIT_REMOTE=origin
export GTD_APPLE_REMINDERS_GIT_BRANCH=main
```

手动测试：

```bash
python3 scripts/sync_apple_reminders.py --mode export --git-sync --dry-run --pretty
python3 scripts/git_sync_export.py --commit --dry-run --pretty
python3 scripts/git_sync_export.py --commit --push --pretty
```

说明：

- `--git-sync` / `--commit` 只做安全范围内的 `git add + commit`
- `--git-push` / `--push` 才会继续 `git push`
- dry-run 只报告将要提交哪些文件，不会改 Git 状态

### Mac 主动拉取方案（推荐）

推荐部署方式：

1. Linux 端更新任务并生成 `sync/apple-reminders-export.json`
2. Linux 端只把同步产物提交/推送到远端 Git
3. Mac 本地 launchd 定时执行 `mac/run_apple_reminders_sync.sh`
4. 包装脚本先尝试 `git fetch + git pull --ff-only`
5. 成功后再消费本地最新 export，同步到 Apple Reminders

当前 Mac 包装脚本带了几个保守保护：

- `logs/` 已忽略，不再因为日志导致工作区脏
- pull 前会尝试 `git restore sync/apple-reminders-export.json`，把它当作可重建运行产物处理
- 如果还有其他 tracked 脏文件，仍然跳过 pull，但继续用当前本地 export
- `git fetch` / `git pull` 失败时只记日志，不破坏本地仓库
- 可通过 `GTD_APPLE_REMINDERS_ENABLE_GIT_PULL=0` 关闭自动 pull
- 可通过 `GTD_APPLE_REMINDERS_GIT_RESTORE_EXPORT_BEFORE_PULL=0` 关闭 pull 前自动 restore export
- 保持原手动执行方式兼容

### 状态与日志

- 同步状态：`sync/apple-reminders-sync-state.json`
- 导出文件：`sync/apple-reminders-export.json`
- 导出语义：open 任务输出 `sync_action=upsert`；显式完成类状态（`done/cancelled/archived/deleted`）输出 `sync_action=complete`，Mac 端仅在收到该显式事件时把 Reminder 标记为 completed，不会因本轮 export 缺席而推断完成
- 日志文件：`logs/apple-reminders-sync.log`
- Mac 自动执行说明：`mac/README.md`
- Mac 包装脚本：`mac/run_apple_reminders_sync.sh`
- launchd 模板：`mac/com.xiaohua.gtd-apple-reminders-sync.plist`

## 版本

- 当前目标版本：`v0.4.0-a`
- 旧需求文档：`requirements-v0.2.2.md`
- 同步设计文档：`apple-reminders-sync-v0.3.0.md`
- 自动同步需求：`requirements-v0.4.0-auto-bidirectional-sync.md`

---

小花的看法：这一步先把“能自动、能观察、能回退”的底座立住，比急着做双向靠谱得多。 
