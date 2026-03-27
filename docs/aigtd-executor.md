# AIGTD GTD-Executor（最小可用版）

## 目标

给飞书小三（AIGTD）一个**固定、受控、API-only** 的 GTD 写入口。

目的不是重构整个 GTD 系统，而是先把主账号 GTD 的关键写路径收口：

- 不再直接 `edit/write gtd-tasks/data/tasks.json`
- 必须先写 `https://gtd.5666.net`
- 写成功后自动刷新本地缓存与 Markdown 视图
- 给会话一个明确、稳定、可审计的调用入口

## 当前约束

主账号 GTD 现在采用：

- 线上事实源：`https://gtd.5666.net`
- 本地缓存：`gtd-tasks/data/tasks.json`
- 本地视图：`today.md` / `inbox.md` / `done.md`

所以 AIGTD 的正确写法必须是：

1. 调 API
2. pull 最新缓存
3. render 本地视图
4. 再回复用户“记好了 / 改好了 / 完成了”

## 固定入口

### 新主入口

```bash
python3 /root/.openclaw/workspace/gtd-tasks/scripts/aigtd_executor.py add "给哥哥订周五机票"
```

### 兼容旧入口

```bash
python3 /root/.openclaw/workspace/gtd-tasks/scripts/aigtd_api_sync.py add "给哥哥订周五机票"
```

旧入口仍可用，但现在只是 wrapper，会转发到 `aigtd_executor.py`。

## 支持动作

### 1) 新增任务

```bash
python3 /root/.openclaw/workspace/gtd-tasks/scripts/aigtd_executor.py add "给哥哥订周五机票" \
  --bucket today \
  --quadrant q1 \
  --category next_action \
  --note "优先看南航和国航" \
  --tags 出行 机票
```

### 2) 修改任务

```bash
python3 /root/.openclaw/workspace/gtd-tasks/scripts/aigtd_executor.py update tsk_20260326_001 \
  --bucket tomorrow \
  --category waiting_for
```

### 3) 完成任务

```bash
python3 /root/.openclaw/workspace/gtd-tasks/scripts/aigtd_executor.py done tsk_20260326_001
```

### 4) 重新打开任务

```bash
python3 /root/.openclaw/workspace/gtd-tasks/scripts/aigtd_executor.py reopen tsk_20260326_001 --bucket today
```

### 5) 删除任务

```bash
python3 /root/.openclaw/workspace/gtd-tasks/scripts/aigtd_executor.py delete tsk_20260326_001
```

## 受控行为

这个执行层会强制做几件事：

- 默认设置 `GTD_TASK_BACKEND=api`
- 默认设置 `GTD_API_BASE_URL=https://gtd.5666.net`
- 通过 `task_cli.py --backend api` 写线上 GTD
- 写完后自动执行：
  - `pull_tasks_cache.py`
  - `render_views.py`
- 把执行结果记录到：
  - `gtd-tasks/logs/aigtd-executor.log`

也就是说，AIGTD 后续只要走这个入口，就不会再需要直接写 `data/tasks.json`。

## 给会话/agent 的调用约定

建议 AIGTD 后续统一使用：

```bash
python3 /root/.openclaw/workspace/gtd-tasks/scripts/aigtd_executor.py <action> ...
```

不要再把以下路径当成写入口：

- `/root/.openclaw/workspace/gtd-tasks/data/tasks.json`
- `/root/.openclaw/workspace/gtd-tasks/data/inbox.json`
- `/root/.openclaw/workspace/gtd-tasks/today.md`
- `/root/.openclaw/workspace/gtd-tasks/inbox.md`
- `/root/.openclaw/workspace/gtd-tasks/done.md`

这些现在只是缓存 / 展示层。

## 如何验证“真的写进 gtd.5666.net，而不是本地 tasks.json”

建议按下面顺序验：

### 验证 1：执行结果里看 API-only 命令

执行后会输出 JSON，其中 `command` 字段应包含：

```text
python3 .../task_cli.py --backend api ...
```

只要这里是 `--backend api`，说明写入动作走的是 API，不是 local backend。

### 验证 2：看执行日志

```bash
tail -n 20 /root/.openclaw/workspace/gtd-tasks/logs/aigtd-executor.log
```

日志中应出现：

- `api_base_url: https://gtd.5666.net`
- `command: ["python3", "...task_cli.py", "--backend", "api", ...]`

### 验证 3：直接从 API backend 查询

新增后立刻执行：

```bash
python3 /root/.openclaw/workspace/gtd-tasks/scripts/task_cli.py --backend api list --text "给哥哥订周五机票" --limit 20
```

如果能查到，说明线上库已有该任务。

### 验证 4：再看本地缓存只是被刷新

然后执行：

```bash
grep -n "给哥哥订周五机票" /root/.openclaw/workspace/gtd-tasks/data/tasks.json
```

如果这里也能看到，表示**缓存刷新成功**，不是本地直写成功。

## 最小方案边界

这一版故意保守：

- 不改现有 `task_cli.py` 主逻辑
- 不改现有 render / Apple Reminders 链路
- 不改其他 agent
- 不强行重置现有会话

只做三件事：

1. 提供明确固定入口
2. 保证默认 API-only 可直接运行
3. 留下日志与验证手段

后续如果要继续升级，可以再加：

- 面向会话的更稳定 JSON 输入协议
- 根据标题/文本自动解析 task id
- 增量刷新而不是全量 pull
- 专门的 `verify` / `status` 子命令

## 当前新增的会话侧可观测性

为了确认“自然对话到底有没有接到 executor”，现在额外提供：

### 1) touchpoint 日志

每次 executor 触发时，会额外写：

```text
/root/.openclaw/workspace/gtd-tasks/logs/aigtd-touchpoints.log
```

记录三类事件：

- `intent`：executor 已被调用
- `success`：executor 执行成功
- `failure`：executor 执行失败

如果上层会话愿意传入环境变量 `AIGTD_SESSION_KEY`，日志里还会带上 session key，方便把飞书会话和执行链路对上。

### 2) adoption 验证脚本

```bash
python3 /root/.openclaw/workspace/gtd-tasks/scripts/verify_aigtd_executor_adoption.py
```

它会同时检查：

- `aigtd-executor.log` 里是否已有 executor 调用
- `aigtd-touchpoints.log` 里是否有触点事件
- 最近若干 AIGTD session 里，是否还存在 `read/edit/write gtd-tasks/data/tasks.json`
- 最近 session 里是否还残留 `NO_REPLY`

### 3) 一个现实结论

如果验证脚本仍报告最近 session 存在大量直接 `tasks.json` 操作，这通常不代表 prompt 没改，而是：

- 旧 session 还在沿用旧行为
- 新规则尚未通过 session 重建真正生效

也就是说，**仅靠提示层无法保证已存在会话立刻切换默认行为**。

## 还缺的关键一环

想真正做到“飞书自然对话新增主账号 GTD 任务时默认切到 executor”，还缺至少一项机制级接入：

1. **会话重建 / 清旧 session**  
   让 AIGTD 下一轮对话从新 prompt / memory / tools 快照重新开始。

2. **更硬的运行时护栏**（后续可选）  
   例如在 AIGTD runtime 增加路径写保护：一旦它试图直接写 `gtd-tasks/data/tasks.json`，就拒绝并提示改走 executor。

3. **显式桥接层**（后续可选）  
   给自然语言新增一个稳定桥接命令或工具，让会话不再自己拼命令和猜文件结构。

当前这版已经把“默认入口、日志、验证、会话污染判断”补齐，但**还没有在 runtime 层强制拦截 `write/edit tasks.json`**。
