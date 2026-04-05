# AIGTD Runtime Rules Snapshot

> 目的：把当前线上已验证有效的 AIGTD 查询/写入规则纳入 `gtd-tasks` 仓库版本管理，避免只存在于 `/root/.openclaw/workspace/agents/aigtd/` 本机目录中而无法追踪。
>
> 说明：这是 **runtime 规则快照**，不是自动双向同步机制。当前 live agent 文件仍位于：
> - `/root/.openclaw/workspace/agents/aigtd/PROMPT.md`
> - `/root/.openclaw/workspace/agents/aigtd/OPERATING-GUIDE.md`
> - `/root/.openclaw/workspace/agents/aigtd/MEMORY.md`

## 1. 总原则

- AIGTD 采用 **API-first + local-cache**
- `https://gtd.5666.net` 是唯一事实源
- `data/tasks.json` / `today.md` / `inbox.md` / `done.md` 只是缓存与展示层
- 正式提醒正文与手动“待办清单 / 发我待办清单 / 当前待办”摘要，优先走 `scripts/gtd_manual_query.sh` / `scripts/gtd_reminder_digest.py` 这条 digest 链，直接从 API open tasks 生成
- 约定：手动查询默认调用 `scripts/gtd_manual_query.sh morning --json`；定时提醒继续按场景调用 `scripts/gtd_reminder_digest.py --mode morning|evening`
- `gtd_manual_query.sh` 只是 digest 的薄包装，目的是让“定时提醒 + 手动待办查询”共用同一份 text/json 输出能力
- 主账号 GTD 写操作禁止直接改这些缓存/视图文件，必须先走 API / executor

## 2. 主账号 GTD 写入规则

- 主账号 GTD 新增 / 修改 / 完成 / 删除，优先统一走：
  - `python3 /root/.openclaw/workspace/gtd-tasks/scripts/aigtd_executor.py <action> ...`
- 唯一主入口：
  - `python3 /root/.openclaw/workspace/gtd-tasks/scripts/aigtd_executor.py <action> ...`
- 兼容旧入口（仅 wrapper，不推荐作为主入口）：
  - `python3 /root/.openclaw/workspace/gtd-tasks/scripts/aigtd_api_sync.py add <title> ...`
- API 成功后再刷新缓存与视图
- 如果 API 失败，必须明确告诉用户失败，不能伪造“已添加 / 已改好 / 已完成”

## 3. AIGTD 只读缓存规则

AIGTD 为避免直接读写主文件，存在只读镜像层：

- `/root/.openclaw/workspace/agents/aigtd/readonly-cache/`

但这个只读镜像 **不是持续自动同步目录**，而是通过：

- `bash /root/.openclaw/workspace/agents/aigtd/bin/aigtd-shell <command> ...`

在执行时触发同步。

因此：

- **禁止**为了省事直接 `read /root/.openclaw/workspace/agents/aigtd/readonly-cache/...` 后就回答单条任务状态
- 若需读取缓存/视图，优先通过以下方式触发同步后再读：
  - `bash /root/.openclaw/workspace/agents/aigtd/bin/aigtd-shell cat /root/.openclaw/workspace/gtd-tasks/data/tasks.json`
  - `bash /root/.openclaw/workspace/agents/aigtd/bin/aigtd-shell cat /root/.openclaw/workspace/gtd-tasks/data/inbox.json`
  - `bash /root/.openclaw/workspace/agents/aigtd/bin/aigtd-shell cat /root/.openclaw/workspace/gtd-tasks/today.md`
  - `bash /root/.openclaw/workspace/agents/aigtd/bin/aigtd-shell cat /root/.openclaw/workspace/gtd-tasks/inbox.md`
  - `bash /root/.openclaw/workspace/agents/aigtd/bin/aigtd-shell cat /root/.openclaw/workspace/gtd-tasks/done.md`

## 4. 单条任务状态查询规则（关键修复）

以下场景：

- `tsk_xxx` 现在什么状态
- 这条任务完成了吗
- 刚在 Reminders 点完成有没有生效
- 刚改名 / 刚删除 / 刚 reopen 后现在是什么状态

必须遵守：

- **禁止**只凭 readonly-cache 快照或旧会话记忆直接回答
- 已知 `task_id` 时，优先查最新真相（API / executor 结果）
- 需要看缓存时，也必须先通过 `aigtd-shell cat <真实路径>` 触发 readonly-cache 同步

## 5. 已验证过的真实根因

此前 AIGTD 查询状态错误，不是因为：

- Reminders -> API 回写失败
- 服务端主环境 cache 未刷新
- `data/tasks.json` / `done.md` 未更新

真实根因是：

1. AIGTD 旧 session 污染
2. AIGTD 直接读取 `agents/aigtd/readonly-cache/...` 旧快照
3. 该 readonly-cache 只有在 `aigtd-shell` 执行时才会同步刷新

## 6. 线上验证结论

在完成以下修复后，链路已真实验证通过：

- 服务端 `/api/apple/completed` 成功后，直接本地写 `data/tasks.json` + `render_views.py`
- AIGTD 查询规则改为：单条任务状态不得直接凭 readonly-cache 回答
- 清理旧 AIGTD session

真实验收任务：

- `tsk_20260328_005`
- 标题：`无回环 cache 刷新验收`

结果：

- API：`done / archive`
- `/root/gtd-tasks/data/tasks.json`：`done / archive`
- `done.md`：已更新
- AIGTD 新 session 已正确答出：已完成

## 7. 当前已知限制

- `agents/aigtd/` 目录当前不在 Git 仓库中
- 本文档只是把当时的 runtime 规则快照纳入 `gtd-tasks` 版本管理
- 现已收口为单一真源：`gtd-tasks/agent-runtime/aigtd/`
- live 目录中的核心三件套（`PROMPT.md / OPERATING-GUIDE.md / MEMORY.md`）已改为链接到真源，不再依赖日常手工同步
