# Apple Reminders Mac 自动执行（launchd）

这套方案是给 **Mac 本机定时执行 Apple Reminders 单向同步** 用的，核心思路现在明确改成：

- Linux 端只负责更新 Git 仓库、生成导出文件
- Mac 端在本地仓库里 **主动 `git pull`** 获取最新 export
- 然后在 Mac 本机调用 AppleScript 写入 Apple Reminders
- **不再使用 Linux 主动 SSH / rsync / scp 推送到 Mac**

这样更安全，也更容易回退：Mac 只是消费自己本地仓库里的内容，不需要把 Linux 到 Mac 的远程写入链路长期打开。

## 设计目标

- 低风险：仍然只做 `GTD -> Apple Reminders`
- 好回退：停掉 launchd，或关闭 git pull，就回到手动执行
- 依赖少：只用 macOS 自带的 `launchd + osascript + python3`，外加常规 `git`
- 与现有手动方式兼容：底层仍然调用 `sync_apple_reminders_mac.applescript`
- 保守保护：Mac 本地工作区不干净时，**跳过 pull，但继续消费当前本地 export**
- 运行产物和业务文件分开对待：`logs/` 忽略，`sync/apple-reminders-export.json` 在 pull 前按可重建产物处理

## 安全架构（推荐）

### 新架构：Mac 主动拉取

1. Linux 端更新任务，生成同步产物 `sync/apple-reminders-export.json` 和状态文件
2. Linux 端可选地自动 `git add/commit/push`，但**只允许**提交 Apple Reminders 同步相关文件
3. Mac 本地定时任务运行 `mac/run_apple_reminders_sync.sh`
4. 包装脚本先尝试在 **Mac 本地仓库** 执行 `git fetch + git pull --ff-only`
5. pull 成功后，继续用最新 export 执行 AppleScript
6. 如果 pull 跳过/失败，仍继续使用 Mac 当前本地已有 export

### 明确不再推荐的旧架构

下面这类方式现在都不建议再作为主方案：

- Linux 主动 `ssh` 到 Mac 执行同步
- Linux 主动 `scp` / `rsync` 覆盖 Mac 本地仓库内容
- 任何 Linux -> Mac 的自动远程写入链路

原因很简单：远程推送更容易把 Mac 本地环境搞乱，排障也更麻烦。现在优先保留“Mac 自己拉、自己执行”的边界。

## 文件说明

- `run_apple_reminders_sync.sh`：Mac 侧包装脚本，统一处理 `git pull`、路径、日志、锁、错误码
- `com.xiaohua.gtd-apple-reminders-sync.plist`：launchd 模板
- `install_launchd_sync.sh`：一键安装/刷新 launchd agent
- `../sync_apple_reminders_mac.applescript`：真正写入 Apple Reminders 的脚本

## 推荐目录

建议把整个仓库放在 Mac 本地固定目录，例如：

```bash
~/workspace/gtd-tasks
```

后文都以这个路径举例。

## 先准备好 Git 仓库

Mac 本地仓库需要满足：

1. 已经 clone 了 `gtd-tasks`
2. 当前分支能正常 `git pull`
3. `origin` 指向你平时同步的远端

先自检一下：

```bash
cd ~/workspace/gtd-tasks
git remote -v
git branch --show-current
git pull --ff-only
```

如果这里都不通，先把 Git 链路调通，再上 launchd。

## 先手动跑通一次

第一次先不要上 launchd，先确认手动链路没问题：

```bash
cd ~/workspace/gtd-tasks
chmod +x mac/run_apple_reminders_sync.sh
./mac/run_apple_reminders_sync.sh
```

如果你暂时不想让它自动 pull，可以这样跑：

```bash
cd ~/workspace/gtd-tasks
GTD_APPLE_REMINDERS_ENABLE_GIT_PULL=0 ./mac/run_apple_reminders_sync.sh
```

如果是第一次运行，macOS 可能会弹出权限请求：

- Terminal 控制“提醒事项”
- 或 `osascript` / 终端自动化相关授权

需要点允许。

## 包装脚本的 `git pull` 策略

`run_apple_reminders_sync.sh` 现在会先尝试 Git 更新，但实现是 **保守模式**。

### 会执行 pull 的前提

同时满足以下条件时才会 pull：

- `GTD_APPLE_REMINDERS_ENABLE_GIT_PULL` 没有被关闭（默认开启）
- 当前目录是一个 git worktree
- 当前分支不是 detached HEAD，或者你显式指定了分支
- **工作区没有已跟踪文件的未提交修改**
- `git fetch` 成功
- `git pull --ff-only` 成功

### 遇到这些情况会跳过/降级，但继续同步

- `logs/` 不会再让仓库变脏，因为已加入 `.gitignore`
- `sync/apple-reminders-export.json` 如果只是本地运行造成修改，脚本会在 pull 前优先尝试 restore
- 还有其他 tracked 文件脏：跳过 pull，继续用当前本地 export
- `git fetch` 失败：记日志，继续用当前本地 export
- `git pull --ff-only` 失败：记日志，继续用当前本地 export
- 不是 git 仓库：记日志，继续走本地文件
- detached HEAD 且未指定分支：记日志，继续走本地文件

### 为什么用 `--ff-only`

因为这是最保守的策略：

- 不自动制造 merge commit
- 不偷偷改写历史
- 拉不下来就算了，只记日志，不硬搞

这很适合 launchd 这种无人值守执行。

## 可选环境变量

### 1) 是否启用自动 `git pull`

默认开启：

```bash
GTD_APPLE_REMINDERS_ENABLE_GIT_PULL=1
```

关闭后，包装脚本就退回到“只消费本地 export”的旧模式：

```bash
GTD_APPLE_REMINDERS_ENABLE_GIT_PULL=0
```

### 2) 指定 remote

默认是 `origin`：

```bash
GTD_APPLE_REMINDERS_GIT_REMOTE=origin
```

### 3) 指定 branch

默认自动取当前分支；如果你想固定分支，可以设置：

```bash
GTD_APPLE_REMINDERS_GIT_BRANCH=main
```

### 4) pull 前是否自动恢复本地 export

默认开启：

```bash
GTD_APPLE_REMINDERS_GIT_RESTORE_EXPORT_BEFORE_PULL=1
```

关闭后，如果 `sync/apple-reminders-export.json` 被本地改脏，就会和其他 tracked 文件一样导致跳过 pull：

```bash
GTD_APPLE_REMINDERS_GIT_RESTORE_EXPORT_BEFORE_PULL=0
```

### 5) 其他现有变量

- `GTD_APPLE_REMINDERS_EXPORT_PATH`
- `GTD_APPLE_REMINDERS_APPLESCRIPT_PATH`
- `GTD_APPLE_REMINDERS_LOG_DIR`
- `PYTHON_BIN`
- `OSASCRIPT_BIN`
- `GIT_BIN`

## 安装 launchd

### 方式 A：用安装脚本（推荐）

```bash
cd ~/workspace/gtd-tasks
chmod +x mac/install_launchd_sync.sh mac/run_apple_reminders_sync.sh
./mac/install_launchd_sync.sh
```

它会做这些事：

- 把 plist 模板渲染到 `~/Library/LaunchAgents/`
- 自动填入仓库绝对路径
- 给包装脚本加执行权限
- 重载 launchd agent

### 方式 B：手动安装

#### 1) 复制模板到 LaunchAgents

```bash
mkdir -p ~/Library/LaunchAgents
cp ~/workspace/gtd-tasks/mac/com.xiaohua.gtd-apple-reminders-sync.plist ~/Library/LaunchAgents/
```

#### 2) 把模板里的绝对路径改成你的真实路径

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

#### 3) 赋可执行权限

```bash
chmod +x ~/workspace/gtd-tasks/mac/run_apple_reminders_sync.sh
```

#### 4) 加载服务

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

## launchd 默认执行策略

模板里默认：

- `RunAtLoad = true`：登录后立刻跑一次
- `StartInterval = 300`：每 5 分钟跑一次
- 默认启用 `GTD_APPLE_REMINDERS_ENABLE_GIT_PULL=1`

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

查看 Git 状态：

```bash
cd ~/workspace/gtd-tasks
git status --short
git remote -v
git branch --show-current
```

### 常见日志含义

- `git: pull disabled ...`：你关闭了自动 pull
- `git: skip pull because tracked working tree is dirty`：Mac 本地有未提交改动，脚本为了安全没有拉取
- `git: fetch failed ...`：远端不可达或认证有问题
- `git: pull failed ... continue with current local export`：拉取没成功，但脚本继续消费了当前本地 export
- `start: export=... tasks=...`：准备执行 AppleScript
- `done: exit_code=0`：本次同步完成

## 回退 / 停用

这套方案回退很简单。

### 方案 1：临时关闭 git pull，保留本地自动同步

```bash
export GTD_APPLE_REMINDERS_ENABLE_GIT_PULL=0
```

如果是 launchd，直接把 plist 里的环境变量改掉后 reload 即可。

### 方案 2：停掉 launchd

```bash
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.xiaohua.gtd-apple-reminders-sync.plist
```

### 方案 3：永久停用

```bash
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.xiaohua.gtd-apple-reminders-sync.plist
rm -f ~/Library/LaunchAgents/com.xiaohua.gtd-apple-reminders-sync.plist
```

停掉后，仍然可以继续手动执行：

```bash
cd ~/workspace/gtd-tasks
./mac/run_apple_reminders_sync.sh
```

## 手动执行方式（保持兼容）

这次改动后，原有手动方式仍然可用。

### 直接执行包装脚本

```bash
cd ~/workspace/gtd-tasks
./mac/run_apple_reminders_sync.sh
```

### 指定 export 文件

```bash
./mac/run_apple_reminders_sync.sh /absolute/path/to/apple-reminders-export.json
```

### 关闭 git pull 后执行

```bash
GTD_APPLE_REMINDERS_ENABLE_GIT_PULL=0 ./mac/run_apple_reminders_sync.sh
```

## 错误码

包装脚本会尽量给稳定错误码：

- `10`：导出 JSON 不存在
- `11`：AppleScript 不存在
- `12`：`osascript` 不可执行
- `13`：`python3` 不可执行
- `20`：已有同步进程在运行，本次跳过
- 其他：直接透传 `osascript` 的退出码

说明：Git 相关失败当前不会单独终止任务，而是会记日志后继续消费本地 export。这是刻意的保守策略。

## Mac 上的使用注意事项

1. **尽量不要在 Mac 本地仓库里长期手改已跟踪文件**  
   否则包装脚本会判定工作区脏，自动跳过 pull。

2. **如果你确实要在 Mac 上做临时调试**  
   调完后要么提交，要么还原，要么 stash；不然自动 pull 会一直跳过。

3. **远端认证要稳定**  
   比如 GitHub SSH key / HTTPS token 要在 Mac 上配置好，不然 `git fetch` 会失败。

4. **这是单向同步，不做回写**  
   Apple Reminders 的改动不会自动回到 Linux，也不会回写仓库。

5. **launchd 仍然要在用户图形会话里跑**  
   因为 Reminders / AppleScript 这套东西本来就依赖登录态和桌面会话。

## 已知限制

- 当前仍然是 **单向同步**，不做回写
- 不删除 Apple Reminders 里已经存在但 GTD 已移除的项目
- 当前主要靠 `[GTD_ID]` 查重，别手动删掉机器标记
- `git pull` 只走保守模式：工作区脏、fetch 失败、fast-forward 失败都会直接跳过
- 如果 Mac 长期离线，自动同步只会消费本地最后一次拉下来的 export
- 如果远端出现需要人工处理的 Git 冲突/分叉，脚本不会自动修复，只会记日志

小花的看法：这个方案比“Linux 主动往 Mac 推东西”干净很多。Mac 这边只负责“自己拉、自己执行、拉不动也别乱动”，边界清楚，坏了也好收拾。