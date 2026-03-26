# GTD Mac Sync 运行手册

## 当前状态

已完成并验证：
- 服务端任务 → Apple Reminders 同步
- Apple Reminders 勾选完成 → 服务端自动回写
- launchd 每分钟自动同步
- full-sync 防重复创建（基于 task_id -> apple_reminder_id mapping）
- 本地 mapping 持久化
- 启动时合并服务端 mappings 到本地，减少重复创建风险

## 核心文件

### Mac 本地运行时文件
- `sync/mac-sync-state.json`：Mac 增量同步游标（last_change_id）
- `sync/mac-apple-mappings.json`：task_id -> apple_reminder_id 本地映射

### launchd
- `launchd/com.wan.gtd.sync.plist`
- 安装命令：`./launchd/install.sh`

### 日志
- `logs/sync.log`
- 查看：`tail -f ~/workspace/gtd-tasks/logs/sync.log`

## 常用命令

### 1. 手动跑一次增量同步
```bash
python3 scripts/sync_agent_mac.py
```

### 2. 全量同步 open 任务到 Apple Reminders
```bash
python3 scripts/sync_agent_mac.py --full-sync
```

说明：
- 已有 mapping 的任务会 `skipped`，不会重复创建
- 没有 mapping 的任务会 `created`

### 3. 查看日志
```bash
tail -f ~/workspace/gtd-tasks/logs/sync.log
```

### 4. 重载 launchd
```bash
launchctl unload ~/Library/LaunchAgents/com.wan.gtd.sync.plist
launchctl load ~/Library/LaunchAgents/com.wan.gtd.sync.plist
```

### 5. 查看 launchd 状态
```bash
launchctl list | grep com.wan.gtd.sync
```

## 验证方法

### A. 验证服务端 → Apple Reminders
1. 在服务端创建任务
2. 等待定时任务或手动执行：
```bash
python3 scripts/sync_agent_mac.py
```
3. 在 Apple Reminders 中确认任务出现

### B. 验证 Apple Reminders → 服务端 completed 回写
1. 在 Apple Reminders 勾选一个已同步任务
2. 等待 1 分钟，或手动执行：
```bash
python3 scripts/sync_agent_mac.py
```
3. 日志应出现：
```text
Checking N reminders for completed status
Found 1 completed reminders
Push completed result: {'status': 'ok', 'processed': 1}
```

## 已知现状

### 已完成
- create 同步
- completed 回写
- full-sync 幂等化（避免重复创建）
- 本地/服务端 mapping 合并

### 仍可继续优化
- update / move / delete 同步尚未完整实现
- completed 回写后可进一步优化“已完成项不再重复检查”

## Git 注意事项

这些本地运行时文件已加入 `.gitignore`，正常不应再污染 `git status`：
- `data/gtd.db`
- `sync/apple-reminders-export.json`
- `sync/apple-reminders-sync-state.json`
- `sync/apple-reminders-local-map.json`
- `sync/apple-reminders-mac-runtime-state.json`
- `sync/mac-apple-mappings.json`
- `sync/mac-sync-state.json`
- `sync/mac-sync-state.json.backup`
- `sync/apple-reminders-completed-applied.json`
- `sync/apple-reminders-completed-events.json`

## 故障排查

### 1. SSL 错误
如果看到 TLS/SSL EOF 错误，先确认已拉取最新代码：
```bash
git pull
```

### 2. full-sync 重复创建
先确认本地 mapping 存在：
```bash
ls -la sync/mac-apple-mappings.json
```
必要时执行一次：
```bash
python3 scripts/sync_agent_mac.py --full-sync
```

### 3. launchd 不工作
重载：
```bash
launchctl unload ~/Library/LaunchAgents/com.wan.gtd.sync.plist
launchctl load ~/Library/LaunchAgents/com.wan.gtd.sync.plist
```
然后看日志：
```bash
tail -f ~/workspace/gtd-tasks/logs/sync.log
```
