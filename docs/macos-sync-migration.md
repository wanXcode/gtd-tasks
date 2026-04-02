# macOS GTD → Reminders 同步迁移说明

## 结论

Mac 本地同步已从旧的 `launchd + Python sync_agent_mac.py` 链路，迁移到新的原生前台 app：

- `~/Applications/GTDMenubarSync.app`

当前这条新链路已经验证：

- Reminders 权限已授权
- 服务端在线
- 同步状态 healthy
- 任务可正常同步到 Apple Reminders

## 当前主同步程序

### 稳定运行路径

```text
~/Applications/GTDMenubarSync.app
```

### 当前角色

它现在是：

- 唯一的 EventKit / Reminders 权限主体
- 唯一的本地 GTD → Reminders 主同步链路
- 登录后自动启动的常驻 menubar app

## 旧链路

### 已停用

旧 active LaunchAgent 已停掉并删除：

```text
~/Library/LaunchAgents/com.wan.gtd.sync.plist
```

### 已备份

备份位置：

```text
archive/legacy/launchd-backups/20260403-001543/
```

包含：

- `com.wan.gtd.sync.user.plist`
- `com.wan.gtd.sync.repo.plist`

## 日常使用

### 启动

平时无需打开 Xcode。

直接运行：

```text
~/Applications/GTDMenubarSync.app
```

### 开机启动

已经为当前用户添加登录项，正常情况下登录后会自动启动。

如果以后要手动检查：

- 系统设置 → 通用 → 登录项
- 看是否存在 `GTDMenubarSync`

## 状态文件

app 的本地运行状态保存在：

```text
~/Library/Application Support/GTDMenubarSync/
```

主要文件：

- `status.json`：当前权限 / 服务端 / 健康状态
- `state.json`：client_id / last_change_id / last_sync_at
- `mappings.json`：task_id → reminder_id 映射
- `stats.json`：游标、mapping 数量、最近运行时间

## 快速排障

### 1. 看 app 是否在运行

```bash
ps aux | grep GTDMenubarSync.app/Contents/MacOS/GTDMenubarSync
```

### 2. 看当前健康状态

```bash
cat ~/Library/Application\ Support/GTDMenubarSync/status.json
cat ~/Library/Application\ Support/GTDMenubarSync/state.json
cat ~/Library/Application\ Support/GTDMenubarSync/stats.json
```

### 3. 看系统侧 Reminders 权限

```bash
/Users/wan/workspace/gtd-tasks/mac/reminders-bridge check-permission
/Users/wan/workspace/gtd-tasks/mac/reminders-bridge list-calendars
```

## 已知要点

### 1. 开发阶段不要随便 reset Reminders 权限

除非明确要重测首启授权，否则不要执行：

```bash
tccutil reset Reminders
```

否则可能把当前已打通的授权链路重置掉。

### 2. 开发调试不要依赖 launchd 旧链路

旧链路已经退场，不应再恢复为主写入通路。

### 3. 原生 app 权限请求依赖：

- 前台 app 主体
- 正常窗口上下文
- `Info.plist` 的 Reminders usage description
- 开发阶段关闭 App Sandbox

## 后续可增强项

- 菜单内增加“开机启动”开关
- 菜单内增加“打开状态目录”入口
- 增加 completed 反向回写可视化
- 增加更完整的同步日志界面
