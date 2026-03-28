# AIGTD Runtime Source of Truth

这个目录用于把 AIGTD 的运行时规则纳入 `gtd-tasks` 仓库版本管理。

当前纳入版本控制的 live 文件包括：

- `PROMPT.md`
- `OPERATING-GUIDE.md`
- `MEMORY.md`

对应 live agent 目录：

- `/root/.openclaw/workspace/agents/aigtd/`

## 当前生效方式

当前 live agent 目录中的以下文件已直接链接到本目录：

- `PROMPT.md`
- `OPERATING-GUIDE.md`
- `MEMORY.md`

也就是说，修改本目录下这 3 个文件，会直接反映到：

- `/root/.openclaw/workspace/agents/aigtd/`

通常**不再需要**额外执行同步脚本。

## 同步脚本说明

历史上曾通过以下脚本把仓库版本复制到 live agent 目录：

```bash
python3 /root/.openclaw/workspace/gtd-tasks/scripts/sync_aigtd_runtime_files.py
```

现在它主要作为：
- 兼容旧结构的辅助工具
- 检查/修复 live 目录被误覆盖时的兜底工具

而不是日常主流程。

## 约定

- 后续若要修改 AIGTD 运行规则，优先修改本目录下文件
- 不要把 `/root/.openclaw/workspace/agents/aigtd/` 当成另一套长期真源手工维护
- 如果发现 live 目录再次出现独立副本而非链接，优先修回“单一真源”结构
