# Mac 端 EventKit Bridge 联调执行手册

## 目标

把 `gtd-tasks` 的 Mac 端 Reminders 写入层，从 AppleScript 切换到 EventKit bridge。

当前仓库状态：
- Python 主链路已接入 `scripts/apple_reminders_bridge.py`
- `scripts/sync_agent_mac.py` 已支持 `GTD_REMINDERS_BACKEND=eventkit`
- `mac/reminders-bridge` 为占位 bridge
- `mac/EventKitBridge/` 为 Swift 工程骨架

---

## 一、联调前确认

### 1. 环境要求
- macOS
- Xcode Command Line Tools
- Swift 5.9+
- 当前用户对「提醒事项」具备系统权限

### 2. 关键文件
- `scripts/sync_agent_mac.py`
- `scripts/apple_reminders_bridge.py`
- `mac/reminders-bridge`
- `mac/EventKitBridge/Package.swift`
- `mac/EventKitBridge/Sources/RemindersBridge/EventKitService.swift`

---

## 二、建议联调顺序

### Step 1：先保留 placeholder bridge，验证 Python 调用链
在仓库根目录执行：

```bash
cd /path/to/gtd-tasks
./mac/reminders-bridge check-permission
./mac/reminders-bridge list-calendars
./mac/reminders-bridge create --input-json '{"title":"测试任务","list_name":"下一步行动@NextAction"}'
```

预期：
- 返回 JSON
- `sync_agent_mac.py` 不再直接依赖 AppleScript 执行入口

### Step 2：编译 Swift bridge

```bash
cd mac/EventKitBridge
swift build -c release
```

预期产物：

```bash
.build/release/reminders-bridge
```

然后替换占位 bridge：

```bash
cp .build/release/reminders-bridge ../reminders-bridge
chmod +x ../reminders-bridge
```

### Step 3：真机权限验证
先执行：

```bash
../reminders-bridge check-permission
../reminders-bridge list-calendars
```

如果返回未授权：
- 打开「系统设置 → 隐私与安全性 → 提醒事项」
- 给终端 / 运行程序授权

### Step 4：动作级联调
依次测试：

#### create
```bash
../reminders-bridge create --input-json '{"title":"EventKit测试-创建","list_name":"下一步行动@NextAction","note":"hello"}'
```

#### update
```bash
../reminders-bridge update --input-json '{"reminder_id":"<id>","title":"EventKit测试-更新","note":"new note"}'
```

#### complete
```bash
../reminders-bridge complete --input-json '{"reminder_id":"<id>","completed":true}'
```

#### move
```bash
../reminders-bridge move --input-json '{"reminder_id":"<id>","list_name":"项目@Project"}'
```

#### delete
```bash
../reminders-bridge delete --input-json '{"reminder_id":"<id>"}'
```

---

## 三、接回 sync_agent_mac.py

设置环境变量：

```bash
export GTD_REMINDERS_BACKEND=eventkit
export GTD_REMINDERS_BRIDGE_PATH="/absolute/path/to/gtd-tasks/mac/reminders-bridge"
```

然后执行：

```bash
python3 scripts/sync_agent_mac.py
```

重点观察：
- 是否仍能创建 mapping
- 是否仍能 update / move / complete
- 是否有 bridge 调用报错
- 是否不再依赖 AppleScript 作为主执行路径

---

## 四、推荐测试顺序

先测最小闭环：
1. `check-permission`
2. `list-calendars`
3. `create`
4. `update`
5. `complete`
6. `move`
7. `delete`
8. `sync_agent_mac.py` 全链路

---

## 五、已知风险点

### 1. 权限问题
EventKit 调用是否能触发授权 / 读取提醒事项，必须真机验证。

### 2. list 标题匹配
当前按 `title == list_name` 查找 calendar，若实际 Apple Reminders 列表命名不一致，会 move/create 失败。

### 3. identifier 稳定性
`calendarItemIdentifier` 需要在真机确认是否与当前 mapping 兼容。

### 4. 完成状态语义
`complete` 当前通过 `isCompleted` 和 `completionDate` 处理，需要真机确认行为是否符合现有同步预期。

---

## 六、建议上线前验收

至少完成：
- bridge 真机编译通过
- `check-permission` 正常
- `list-calendars` 正常
- create / update / complete / move 各通过一次
- `sync_agent_mac.py` 在 `eventkit` backend 下成功跑完一轮
- 失败时有明确 JSON 错误输出

---

## 七、推荐切换方式

不要一上来彻底删 AppleScript，建议：
- 默认测试环境：`GTD_REMINDERS_BACKEND=eventkit`
- 保留回退：`GTD_REMINDERS_BACKEND=applescript`

等 EventKit 真机联调稳定后，再考虑逐步下线 AppleScript。
