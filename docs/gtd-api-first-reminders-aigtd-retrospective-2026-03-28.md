# GTD API-first × Mac Reminders × AIGTD 查询链复盘（2026-03-28）

## 一、背景与目标

这轮工作的目标，是把新的 GTD 主链真正打通并验证稳定性：

- 飞书 AIGTD 写入必须走 API-first
- Mac 端只保留新的 Reminders 同步链
- Apple Reminders completed 要能可靠回写 API
- 服务端主环境 cache 要跟着刷新
- AIGTD 查询状态时要能读到最新真相

最终需要闭环的是：

```text
飞书 AIGTD → GTD API → Mac Reminders → completed 回写 API → 服务端主环境 cache 刷新 → AIGTD 正确查询
```

---

## 二、最终结论

### 1. 主问题已闭环

本轮最终已经真实验收通过：

- AIGTD 能通过 API 正确写入任务
- Mac 端能消费 changes 并同步到 Apple Reminders
- Reminders completed 能回写到 API
- 服务端主环境 `data/tasks.json` 与 `done.md` 能跟着刷新
- AIGTD 在新 session 中已能正确查询最新状态

### 2. 最终根因不是 API，也不是 Mac completed 回写失败

真正根因是两层叠加：

1. **AIGTD 旧 session 污染**
2. **AIGTD 直接读取 `agents/aigtd/readonly-cache/...` 旧快照**

而这份 readonly-cache 并不是持续自动同步目录，只会在经过：

```bash
bash /root/.openclaw/workspace/agents/aigtd/bin/aigtd-shell <command> ...
```

时被刷新。

因此此前即使：

- API 已经是 `done`
- 服务端主环境 `/root/gtd-tasks/data/tasks.json` 已经是 `done`
- `done.md` 也已经刷新

AIGTD 仍可能因为旧 session + 旧 readonly-cache 快照而答成 `open / future / Q2`。

---

## 三、关键修复与排障过程

### A. Mac sync 主链确认与清理

确认新的 Mac 主链路为：

- `com.wan.gtd.sync` → `scripts/sync_agent_mac.py`

停用并归档旧链路：

- `com.xiaohua.gtd-apple-reminders-sync`
- `com.iosgtd.syncbridge`

同时确认：

- 新链路基于 API `/api/changes`
- 使用本地 state / mapping 文件
- 使用 ack API
- 通过 AppleScript 操作 Apple Reminders

### B. `sync_agent_mac.py` 能力补齐

为 `scripts/sync_agent_mac.py` 增加：

- cursor recovery
- `--reset-cursor`
- state 丢失时自动 initial full sync
- `update`
- `done`
- `delete`

此前 update 只是被消费并 ack，但返回 `update_not_implemented`；这轮完成了最小可用实现。

### C. AIGTD executor 安全护栏

在 `scripts/aigtd_executor.py` 增加任务引用防呆与解析：

- `TASK_ID_RE`
- `parse_task_list_output()`
- `list_tasks_by_text()`
- `find_task_by_title()`
- `resolve_task_reference()`

使得：

- 非 `tsk_...` 引用不再直接拼进 `/api/tasks/{task_id}`
- 改为先定位任务，再执行 `update / done / reopen / delete`
- 歧义时报错，找不到时报错，不再发生危险失败

### D. 服务端 completed 后 cache 刷新

起初尝试过两版：

1. `/api/apple/completed` 后回打 `https://gtd.5666.net`
2. 再回打 `http://127.0.0.1:8083`

这两版都只是排障过渡，不适合长期保留。

最终正确收口方案是：

- `/api/apple/completed` 成功后
- **不再 HTTP loopback 调自己**
- 直接在服务端本地：
  - `task_service.list_tasks()`
  - `dump_cache(...)` 写 `data/tasks.json`
  - 执行 `render_views.py`

这样彻底去除了对：

- 域名
- 端口
- nginx
- 反代
- 自身 HTTP 回环

的依赖。

### E. AIGTD 查询链根因定位

一度怀疑“服务器主环境 cache 没刷新到位”，但最终通过现场验证确认：

- API 正确
- `/root/gtd-tasks/data/tasks.json` 正确
- `done.md` 正确
- AIGTD 仍答错

这说明问题已经收敛到 **AIGTD 查询链本身**，而不是同步链或服务端 cache 链。

进一步阅读 AIGTD 配置后确认：

- `PROMPT.md`
- `OPERATING-GUIDE.md`
- `MEMORY.md`

都明确鼓励它优先读：

- `/root/.openclaw/workspace/agents/aigtd/readonly-cache/...`

这就是最终根因之一。

### F. AIGTD 规则修复 + session 重建

对 AIGTD 规则进行本机修复：

- 单条任务状态确认不得只凭 readonly-cache 回答
- 若要看缓存，必须通过 `aigtd-shell cat <真实路径>` 触发同步
- 已知 `task_id` 时，优先查最新真相

随后清理旧 session：

- 删除 key：`agent:aigtd:feishu:direct:ou_6ab7ba428602cd1b577b677e255c5d5f`
- 备份：`/root/.openclaw/agents/aigtd/sessions/sessions.json.bak.query-fix`

清理后，新 session 已能正确回答最新状态。

---

## 四、关键验收结果

### 1. 任务 `tsk_20260328_004`

- 标题：`服务器主环境 cache 刷新最终验收`
- 结果：用于证明“仅补服务端 cache 刷新还不够”

在这一步里，即使：

- Mac completed 已回写
- 服务端 cache 刷新补丁已上线

AIGTD 仍答 `open / future / Q2`。

这一步的价值是：

> 明确证明“问题不止在服务端 cache 层”。

### 2. 任务 `tsk_20260328_005`

- 标题：`无回环 cache 刷新验收`

这一步是最终关键验收：

- API：`done / archive`
- `/root/gtd-tasks/data/tasks.json`：`done / archive`
- `done.md`：已更新
- 服务端日志：明确出现 `cache refresh ok`
- AIGTD 旧 session：仍答错
- AIGTD 新 session：已正确答出“已完成”

这一步最终把根因钉死。

---

## 五、部署事实存档

### `gtd.5666.net` 的真实部署链路（x2）

- 主机：`43.134.109.206`
- nginx 配置：`/etc/nginx/conf.d/gtd.5666.net.conf`
- 域名：`gtd.5666.net`
- 反代目标：`http://127.0.0.1:8083`
- GTD 服务入口：`python /root/gtd-tasks/run_8083.py`
- 仓库目录：`/root/gtd-tasks`

额外确认：

- x2 上对外 `8000` 的 `finpad-api` 容器 **不是** GTD 服务

这点在中途一度查偏，后已更正并存档。

---

## 六、AIGTD 运行规则已纳入仓库版本管理（路线 B）

这轮额外完成了一个长期有价值的动作：

把 AIGTD live 运行规则正式纳入 `gtd-tasks` GitHub 仓库。

### 1. 新增版本源目录

```text
agent-runtime/aigtd/
```

包含：

- `PROMPT.md`
- `OPERATING-GUIDE.md`
- `MEMORY.md`
- `README.md`

### 2. 同步脚本（历史保留）

```bash
python3 /root/.openclaw/workspace/gtd-tasks/scripts/sync_aigtd_runtime_files.py
```

该脚本最初用于把仓库内版本复制到 live agent 目录：

- `/root/.openclaw/workspace/agents/aigtd/`

支持 dry-run：

```bash
python3 /root/.openclaw/workspace/gtd-tasks/scripts/sync_aigtd_runtime_files.py --dry-run
```

**当前口径已更新：** live 目录中的核心三件套已改为直接链接到 `gtd-tasks/agent-runtime/aigtd/`，因此该脚本现在主要作为兼容旧结构 / 修复误覆盖时的兜底工具。

### 3. README 已补充说明

`gtd-tasks/README.md` 已明确：

- 后续若要修改 AIGTD 运行规则，优先改仓库内 `agent-runtime/aigtd/`
- live 核心文件采用 link 到真源的方式，通常不再需要手工同步
- 不再把 live 目录当唯一长期真相源

这一步解决了此前“规则改了但没进入 GitHub”的长期隐患，也减少了“改了但忘同步”的风险。

---

## 七、本轮关键提交

### GTD 主链 / 服务端 / 同步相关

- `7ed5c17` — `feat(gtd): stabilize API-first AIGTD and Mac reminders sync`
- `7b41bb4` — `feat(gtd): refresh local cache after API writes`
- `d7b1475` — `fix(gtd): guard task reference resolution in AIGTD executor`
- `3cd5208` — `fix(gtd): refresh local cache after Apple completed push`
- `d1add02` — `fix(server): refresh main cache after Apple completed backwrite`
- `819a95b` — `fix(server): use local API for cache refresh after apple completed`
- `b4cd224` — `fix(server): refresh local cache without HTTP loopback`

### AIGTD 规则版本化 / 文档化

- `2a2194c` — `docs(aigtd): snapshot runtime rules into gtd-tasks repo`
- `d9927db` — `feat(aigtd): version runtime config and sync script`
- `6f7eecf` — `docs(aigtd): document repo-backed runtime config source`

---

## 八、最终结论（一句话）

这轮不是“勉强能用”，而是关键主链已经真实打通：

> **AIGTD 写得进去，Reminders 回得来，服务端刷得动，AIGTD 也终于查得准。**

---

## 九、剩余优化项（非主故障）

### 1. 可继续把 AIGTD 单条状态查询收紧为更硬的 API-first

当前已经可用，但后续还可以进一步减少对缓存层的依赖。

### 2. 若未来要支持 Reminders 双向编辑

例如：

- 改标题
- 改 note
- 删除
- 移 list

需要单独设计同步协议与冲突策略，不建议顺手硬上。
