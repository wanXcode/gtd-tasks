# Apple Reminders Mac 自动执行（launchd）

这套方案是给 **Mac 本机定时执行 Apple Reminders 单向同步** 用的，目标是：

- 低风险：仍然只做 `GTD -> Apple Reminders`
- 好回退：停掉 launchd 就回到手动执行
- 依赖少：只用 macOS 自带的 `launchd + osascript + python3`
- 与现有手动方式兼容：底层仍然调用 `sync_apple_reminders_mac.applescript`

## 文件说明

- `run_apple_reminders_sync.sh`：Mac 侧包装脚本，统一处理路径、日志、锁、错误码
- `com.xiaohua.gtd-apple-reminders-sync.plist`：launchd 模板
- `../sync_apple_reminders_mac.applescript`：真正写入 Apple Reminders 的脚本

## 推荐目录

建议把整个仓库放在 Mac 本地固定目录，例如：

```bash
~/workspace/gtd-tasks
```

后文都以这个路径举例。

## 先手动跑通一次

第一次先不要上 launchd，先确认手动链路没问题：

```bash
cd ~/workspace/gtd-tasks
chmod +x mac/run_apple_reminders_sync.sh
osascript sync_apple_reminders_mac.applescript ~/workspace/gtd-tasks/sync/apple-reminders-export.json
./mac/run_apple_reminders_sync.sh
```

如果是第一次运行，macOS 可能会弹出权限请求：

- Terminal 控制“提醒事项”
- 或 `osascript` / 终端自动化相关授权

需要点允许。

## 安装 launchd

### 1) 复制模板到 LaunchAgents

```bash
mkdir -p ~/Library/LaunchAgents
cp ~/workspace/gtd-tasks/mac/com.xiaohua.gtd-apple-reminders-sync.plist ~/Library/LaunchAgents/
```

### 2) 把模板里的绝对路径改成你的真实路径

打开：

```bash
~/Library/LaunchAgents/com.xiaohua.gtd-apple-reminders-sync.plist
```

至少替换这几处：

- `/ABSOLUTE/PATH/TO/gtd-tasks/mac/run_apple_reminders_sync.sh`
- `/ABSOLUTE/PATH/TO/gtd-tasks/sync/apple-reminders-export.json`
- `/ABSOLUTE/PATH/TO/gtd-tasks`
- `/ABSOLUTE/PATH/TO/gtd-tasks/logs/apple-reminders-launchd.out.log`
- `/ABSOLUTE/PATH/TO/gtd-tasks/logs/apple-reminders-launchd.err.log`

如果仓库路径就是 `~/workspace/gtd-tasks`，建议统一替换成：

```text
/Users/<你的用户名>/workspace/gtd-tasks
```

### 3) 赋可执行权限

```bash
chmod +x ~/workspace/gtd-tasks/mac/run_apple_reminders_sync.sh
```

### 4) 加载服务

首次加载：

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.xiaohua.gtd-apple-reminders-sync.plist
launchctl enable gui/$(id -u)/com.xiaohua.gtd-apple-reminders-sync
launchctl kickstart -k gui/$(id -u)/com.xiaohua.gtd-apple-reminders-sync
```

如果之前已经加载过，更新配置后可以直接：

```bash
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.xiaohua.gtd-apple-reminders-sync.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.xiaohua.gtd-apple-reminders-sync.plist
launchctl kickstart -k gui/$(id -u)/com.xiaohua.gtd-apple-reminders-sync
```

## 默认执行策略

模板里默认：

- `RunAtLoad = true`：登录后立刻跑一次
- `StartInterval = 300`：每 5 分钟跑一次

如果你想更保守，可以改成：

- 600：每 10 分钟
- 900：每 15 分钟

我更建议先从 **10 分钟** 开始，联调稳定后再调快。

## 日志与排查

主要看这几个文件：

```bash
~/workspace/gtd-tasks/logs/apple-reminders-sync-mac.log
~/workspace/gtd-tasks/logs/apple-reminders-launchd.out.log
~/workspace/gtd-tasks/logs/apple-reminders-launchd.err.log
```

查看最近日志：

```bash
tail -n 100 ~/workspace/gtd-tasks/logs/apple-reminders-sync-mac.log
```

查看 launchd 状态：

```bash
launchctl print gui/$(id -u)/com.xiaohua.gtd-apple-reminders-sync
```

## 回退 / 停用

这套方案回退很简单：

### 临时停掉

```bash
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.xiaohua.gtd-apple-reminders-sync.plist
```

### 永久停用

```bash
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.xiaohua.gtd-apple-reminders-sync.plist
rm -f ~/Library/LaunchAgents/com.xiaohua.gtd-apple-reminders-sync.plist
```

停掉后，仍然可以继续手动执行：

```bash
cd ~/workspace/gtd-tasks
./mac/run_apple_reminders_sync.sh
```

## 典型使用链路

### 方案 A：Git 同步

1. Linux 端更新仓库并生成 `sync/apple-reminders-export.json`
2. Mac 端 `git pull`
3. launchd 自动跑包装脚本
4. 包装脚本调用 AppleScript 写入 Reminders

### 方案 B：SSH/rsync 同步导出文件

1. Linux 端生成最新 JSON
2. 通过 `scp/rsync` 传到 Mac 仓库里的 `sync/` 目录
3. launchd 定时检测并执行

## 错误码

包装脚本会尽量给稳定错误码：

- `10`：导出 JSON 不存在
- `11`：AppleScript 不存在
- `12`：`osascript` 不可执行
- `13`：`python3` 不可执行
- `20`：已有同步进程在运行，本次跳过
- 其他：直接透传 `osascript` 的退出码

## 已知限制

- 当前仍然是 **单向同步**，不做回写
- 不删除 Apple Reminders 里已经存在但 GTD 已移除的项目
- 当前主要靠 `[GTD_ID]` 查重，别手动删掉机器标记
- 如果任务命中的目标列表变了，AppleScript 现在会尝试迁移，但仍建议先小规模联调
- `launchd` 只能在用户登录后的图形会话里稳定控制 Reminders，不适合拿 system daemon 跑
