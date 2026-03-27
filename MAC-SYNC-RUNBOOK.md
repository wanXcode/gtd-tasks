# GTD Mac Sync 运行手册

## 当前状态

已完成并验证：
- 服务端任务 → Apple Reminders 同步
- Apple Reminders 勾选完成 → 服务端自动回写
- launchd 每分钟自动同步
- full-sync 防重复创建（基于 task_id -> apple_reminder_id mapping）
- 本地 mapping 持久化
- 启动时合并服务端 mappings 到本地，减少重复创建风险

当前主链路已经明确为：
- **主链路**：`launchd/com.wan.gtd.sync.plist` → `scripts/sync_agent_mac.py` → `/api/changes` → Apple Reminders
- **旧兼容链路（待停用）**：`mac/com.xiaohua.gtd-apple-reminders-sync.plist` → `mac/run_apple_reminders_sync.sh` → Git pull / export 文件

结论：日常运行、排查、验收都应优先围绕 `sync_agent_mac.py` 展开；旧 `run_apple_reminders_sync.sh` 不再作为主同步入口。

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

### 3. 故障恢复：重置 cursor 并重做一次恢复型同步
```bash
python3 scripts/sync_agent_mac.py --reset-cursor --full-sync
```

适用场景：
- 怀疑 `last_change_id` 错位
- 线上已有任务，但 Mac 没拉下来
- 迁移/重装后需要补同步
- 本地状态文件损坏后重建

### 4. 初始化状态文件
```bash
python3 scripts/sync_agent_mac.py --init
```

### 5. 查看日志
```bash
tail -f ~/workspace/gtd-tasks/logs/mac-sync-agent.log
```

### 6. 重载 launchd
```bash
launchctl unload ~/Library/LaunchAgents/com.wan.gtd.sync.plist
launchctl load ~/Library/LaunchAgents/com.wan.gtd.sync.plist
```

### 7. 查看 launchd 状态
```bash
launchctl list | grep com.wan.gtd.sync
launchctl print gui/$(id -u)/com.wan.gtd.sync
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
如果错误是偶发性的，后续重试成功且日志出现 `Got N changes` / `Sync completed`，通常可按瞬时网络波动处理。

### 2. 线上已有任务，但 Mac 没拉下来
优先检查：
```bash
cat sync/mac-sync-state.json
```
如果怀疑 `last_change_id` 错位，直接执行恢复命令：
```bash
python3 scripts/sync_agent_mac.py --reset-cursor --full-sync
```

### 3. full-sync 重复创建
先确认本地 mapping 存在：
```bash
ls -la sync/mac-apple-mappings.json
```
必要时先拉服务端 mapping，再跑：
```bash
python3 scripts/sync_agent_mac.py --full-sync
```

### 4. launchd 不工作
重载：
```bash
launchctl unload ~/Library/LaunchAgents/com.wan.gtd.sync.plist
launchctl load ~/Library/LaunchAgents/com.wan.gtd.sync.plist
```
然后看日志：
```bash
tail -f ~/workspace/gtd-tasks/logs/mac-sync-agent.log
```

### 5. 旧链路误启动/干扰
当前应只保留：
- `com.wan.gtd.sync`

如果看到以下旧链路重新出现，应停用并归档：
- `com.xiaohua.gtd-apple-reminders-sync`
- `com.iosgtd.syncbridge`

检查：
```bash
launchctl list | grep gtd
```
理想状态是只剩：
```text
com.wan.gtd.sync
```
