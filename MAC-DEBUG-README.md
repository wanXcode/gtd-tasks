# Mac 端调试指南

> 服务端主库方案 v2.0 Phase 2 - Mac Sync Agent 调试

---

## 当前状态

✅ **服务端已就绪**
- API 运行正常
- 28 个任务已导入数据库
- 支持 changes 增量接口
- 支持 Apple completed 回写

⏳ **Mac Agent 已创建**
- 脚本路径：`scripts/sync_agent_mac.py`
- 功能：从服务端拉 changes → 同步到 Apple → 回写 completed

---

## 快速开始

### 1. 启动服务端（在服务器上）

```bash
cd ~/gtd-tasks
python3 -m server.app
# 或后台运行
nohup python3 -m server.app > logs/server.log 2>&1 &
```

服务端默认监听 `http://127.0.0.1:8000`

### 2. Mac 端配置

在 Mac 上设置环境变量：

```bash
# 默认使用线上服务端，如需本地测试可修改
export GTD_API_BASE_URL="https://gtd.5666.net"

# 客户端标识（可选，默认 mac-primary）
export GTD_SYNC_CLIENT_ID="mac-primary"
```

### 3. 初始化同步状态

```bash
cd ~/gtd-tasks
python3 scripts/sync_agent_mac.py --init
```

这会创建 `sync/mac-sync-state.json`：
```json
{
  "client_id": "mac-primary",
  "last_change_id": 0,
  "last_sync_at": null
}
```

### 4. 测试同步（Dry Run）

```bash
python3 scripts/sync_agent_mac.py --dry-run
```

这会：
- 连接服务端
- 获取 changes
- 打印日志，但不操作 Apple Reminders

### 5. 正式同步

```bash
python3 scripts/sync_agent_mac.py
```

---

## 调试检查清单

### 检查 1：服务端可达

Mac 上执行：
```bash
curl http://your-server:8000/health
# 应返回 {"ok": true}
```

### 检查 2：Changes 接口正常

```bash
curl "http://your-server:8000/api/changes?since_change_id=0&limit=10"
# 应返回变更列表（首次可能为空）
```

### 检查 3：本地状态文件

```bash
cat ~/gtd-tasks/sync/mac-sync-state.json
# 确认 last_change_id 在更新
```

### 检查 4：日志输出

```bash
tail -f ~/gtd-tasks/logs/mac-sync-agent.log
```

---

## launchd 定时任务配置

创建 `~/Library/LaunchAgents/com.gtd.sync-agent.plist`：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.gtd.sync-agent</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/YOUR_USERNAME/gtd-tasks/scripts/sync_agent_mac.py</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>GTD_API_BASE_URL</key>
        <string>http://your-server:8000</string>
    </dict>
    <key>StartInterval</key>
    <integer>60</integer>
    <key>StandardOutPath</key>
    <string>/Users/YOUR_USERNAME/gtd-tasks/logs/sync-agent.out</string>
    <key>StandardErrorPath</key>
    <string>/Users/YOUR_USERNAME/gtd-tasks/logs/sync-agent.err</string>
</dict>
</plist>
```

加载并启动：
```bash
launchctl load ~/Library/LaunchAgents/com.gtd.sync-agent.plist
launchctl start com.gtd.sync-agent
```

---

## 已知限制

当前 Mac Agent 是 **MVP 版本**，以下功能待完善：

1. **AppleScript 集成简化**
   - 当前使用内嵌 AppleScript 字符串
   - 建议复用现有的 `sync_apple_reminders_mac.applescript`

2. **Apple Mapping 缓存**
   - 需要本地缓存 task_id ↔ apple_reminder_id 映射
   - 建议读写 `sync/apple_reminders_local_map.json`

3. **任务更新同步**
   - 当前只实现了 create 的基础框架
   - update/move/done 需要补充 AppleScript 调用

4. **Completed 回写**
   - 需要完善 AppleScript 获取已完成任务
   - 需要解析返回结果并构造回写请求

---

## 下一步建议

### 方案 A：先验证基础链路（推荐）

1. 启动服务端
2. Mac 上运行 `--dry-run` 确认能连上服务端
3. 在服务端新建一个任务：`python3 scripts/task_cli.py --backend api add "测试任务" --bucket today`
4. Mac 上运行正式同步，观察是否能获取到 changes
5. 确认 `last_change_id` 更新

### 方案 B：直接完善 AppleScript 集成

如果需要完整的 Apple Reminders 同步，需要：
1. 复用/改造现有的 `sync_apple_reminders_mac.applescript`
2. 在 Mac Agent 中调用外部 AppleScript 文件
3. 实现完整的 create/update/move/done 操作

---

## 文件位置总结

| 文件 | 位置 | 说明 |
|------|------|------|
| 服务端 | `server/app.py` | 已就绪 |
| Mac Agent | `scripts/sync_agent_mac.py` | 待调试 |
| 同步状态 | `sync/mac-sync-state.json` | Mac 本地生成 |
| 日志 | `logs/mac-sync-agent.log` | Mac 本地生成 |
| AppleScript | `sync_apple_reminders_mac.applescript` | 复用现有 |

---

## 联系

调试遇到问题随时告诉我 🌸
