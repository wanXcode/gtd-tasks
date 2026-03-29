# EventKit Operations Quickstart

## 当前主链路

Mac Reminders 同步主链路现在是 **EventKit-only**：

- Orchestrator: `scripts/sync_agent_mac.py`
- Bridge wrapper: `scripts/apple_reminders_bridge.py`
- Native bridge binary: `mac/reminders-bridge`
- Swift source: `mac/EventKitBridge/`

不要再按旧 AppleScript 主路径排障；旧文件已归档到 `archive/legacy/`。

## 日常使用

手动跑一次同步：

```bash
python3 scripts/sync_agent_mac.py
```

如果只想做语法检查：

```bash
python3 -m py_compile scripts/sync_agent_mac.py scripts/apple_reminders_bridge.py
```

## 更新 EventKit bridge

当 `mac/EventKitBridge/` 有变更时，在 Mac 上重新编译：

```bash
cd mac/EventKitBridge
swift build -c release
cp .build/release/RemindersBridge ../reminders-bridge
cd ../..
```

然后做一次权限/桥接验证：

```bash
printf '{"permission":"authorized"}' | ./mac/reminders-bridge check-permission
printf '{}' | ./mac/reminders-bridge list-calendars
```

## 常用排障文件

优先看这几个：

- `logs/mac-sync-agent.log`
- `sync/mac-apple-mappings.json`
- `sync/mac-sync-state.json`

## 常用排障命令

诊断 mappings：

```bash
python3 scripts/diagnose_eventkit_mappings.py
```

手动同步一次：

```bash
python3 scripts/sync_agent_mac.py
```

检查主链路脚本语法：

```bash
python3 -m py_compile scripts/sync_agent_mac.py scripts/apple_reminders_bridge.py scripts/task_cli.py scripts/nlp_capture.py
```

## 遇到问题时先判断

### 1. 桥接问题
表现：
- bridge binary 不存在
- EventKit 权限异常
- `reminders-bridge` 动作失败

先检查：
- `mac/reminders-bridge` 是否存在
- 是否重新 `swift build -c release`
- Reminders 权限是否已授权

### 2. mappings 问题
表现：
- 本地有重复 reminder
- sync 日志里出现 not found
- 历史 mapping 没清干净

先检查：
- `python3 scripts/diagnose_eventkit_mappings.py`
- `sync/mac-apple-mappings.json`

### 3. 服务端问题
表现：
- `502 Bad Gateway`
- `/api/apple/mappings` 或 `/api/changes` 请求失败

先检查：
- x2 上 `python3 /root/gtd-tasks/run_8083.py` 是否存活
- nginx upstream 是否正常

## 原则

- 主链路只认 **EventKit-only**
- legacy AppleScript 文件只做历史归档，不再作为当前排障依据
