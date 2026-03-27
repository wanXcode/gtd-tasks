# AIGTD Runtime Source of Truth

这个目录用于把 AIGTD 的运行时规则纳入 `gtd-tasks` 仓库版本管理。

当前纳入版本控制的 live 文件包括：

- `PROMPT.md`
- `OPERATING-GUIDE.md`
- `MEMORY.md`

对应 live agent 目录：

- `/root/.openclaw/workspace/agents/aigtd/`

## 同步方式

把仓库内版本同步到 live agent 目录：

```bash
python3 /root/.openclaw/workspace/gtd-tasks/scripts/sync_aigtd_runtime_files.py
```

仅查看将发生哪些变化：

```bash
python3 /root/.openclaw/workspace/gtd-tasks/scripts/sync_aigtd_runtime_files.py --dry-run
```

## 约定

- 后续若要修改 AIGTD 运行规则，优先修改本目录下文件，再执行同步脚本
- 不要把 `/root/.openclaw/workspace/agents/aigtd/` 当成唯一长期配置源
- 这样可以避免“live 配置改了但 GitHub 没记录”的情况再次发生
