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
```

`apply` 会：

1. 先打印解析结果
2. 调用 `task_cli.py add`
3. 自动触发 `render_views.py`

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

## 版本

- 当前目标版本：`v0.2.2`
- 需求文档：`requirements-v0.2.2.md`
- 版本说明：`release-v0.2.2.md`

---

小花的看法：这套系统现在已经不是“记几条待办”了，而是一个轻量、稳定、适合长期维护的个人任务主库。下一步如果再进化，应该优先做同步能力，不是再堆命令。 
