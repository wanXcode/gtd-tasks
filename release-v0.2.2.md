# GTD Tasks v0.2.2 发布说明

## 一句话

v0.2.2 不再只是“有个主库”，而是把主库真正变成了一个顺手可维护的日常 GTD 系统。

这一版重点补齐三块：

1. 结构化任务操作闭环
2. 自然语言录入入口
3. 回顾/复盘视图

---

## 这版解决了什么

### 1) 任务维护终于顺手了

主账号的 `scripts/task_cli.py` 已经能覆盖日常最常见的任务维护动作：

- `list`：按 `id/status/bucket/quadrant/tag/text` 查任务
- `update`：修改 `title/bucket/quadrant/note/status/tags`
- `done`：完成任务
- `reopen`：重开任务，并可重新指定 bucket
- `move`：按条件批量移动 bucket
- `tag`：按条件批量增删/重置标签

同时会维护：

- `updated_at`
- `completed_at`
- `sync_version`

### 2) 可以直接用自然语言记任务了

新增 `scripts/nlp_capture.py`。

现在可以这样用：

```bash
python3 scripts/nlp_capture.py "明天提醒我给张闯回信 #ME"
python3 scripts/nlp_capture.py "把海南公司主体先放未来，等确认后再推进" --mode apply
```

支持两种模式：

- `preview`：只看解析结果，不写库
- `apply`：解析后直接写入主库，并自动 render

当前这版是轻量规则解析，不追求复杂 NLP，但已经够覆盖高频中文输入：

- 识别 title
- 识别 bucket（today / tomorrow / future）
- 识别 tags
- 识别 note
- 识别 quadrant（识别不到时默认 `q2`）

默认策略：

- 默认 `bucket=future`
- 默认 `quadrant=q2`
- 时间语义固定按 `Asia/Shanghai`

### 3) 视图不再只适合“看今天”

`render_views.py` 现在除了原有视图，还会生成：

- `done.md`：集中看最近完成 / 取消 / 归档事项
- `weekly/review-latest.md`：看本周新增、完成、当前未完成概览

这让系统从“有待办列表”变成“可回顾、可复盘”的工作面板。

---

## 这版的默认工作流

### 收任务

先 preview：

```bash
python3 scripts/nlp_capture.py "明天提醒我给张闯回信 #ME"
```

确认没问题再 apply：

```bash
python3 scripts/nlp_capture.py "明天提醒我给张闯回信 #ME" --mode apply
```

### 查和改

```bash
python3 scripts/task_cli.py list --status open --bucket today
python3 scripts/task_cli.py update tsk_xxx --note "今晚处理"
python3 scripts/task_cli.py move --tag ME --bucket today --to-bucket future
python3 scripts/task_cli.py tag add WAIT --text 海南
```

### 看结果

```bash
python3 scripts/render_views.py
```

然后看：

- `today.md`
- `done.md`
- `weekly/review-latest.md`

---

## 和 v0.2.1 的关键差别

### v0.2.1 解决的是：
- 有没有主库
- 视图是不是从主库渲染
- 时间口径是不是统一

### v0.2.2 解决的是：
- 主库能不能顺手维护
- 能不能直接用一句话录入
- 能不能方便回顾最近推进结果

所以这版更像“可用性层补齐版”。

---

## 已知取舍

这版 `nlp_capture.py` 采用的是可解释、低依赖、规则式实现，而不是复杂日期/NLP 引擎。

优点：
- 稳定
- 简单
- 好调
- 预览可解释

限制：
- 对复杂口语、模糊日期、长句复合意图的理解还有限
- `note` 提取目前偏启发式
- 没做高级项目/子任务解析

这是有意为之：先保证能稳定用，再考虑更聪明。

---

## 下一步建议

如果 v0.2.2 用顺了，下一阶段我更建议优先做：

1. 外部同步字段预留
2. iOS / 移动端输入链路
3. 更稳的日期语义解析
4. 项目/子任务层级

而不是继续横向堆命令。

---

## 结论

v0.2.2 的价值，不在于“多了几个脚本”，而在于 `gtd-tasks` 已经更像一个可以长期陪跑的个人任务主库了。
