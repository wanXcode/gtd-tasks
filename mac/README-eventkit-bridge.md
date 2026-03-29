# EventKit Bridge 最小协议说明

当前文件：`mac/reminders-bridge`

> 说明：当前是占位骨架，用于先打通 Python → bridge 调用链；后续替换为 Swift EventKit CLI 实现。

## 目标

替换原有 AppleScript 最后一跳，不重做整个同步系统。

## 当前动作协议

支持动作：
- `check-permission`
- `list-calendars`
- `get`
- `create`
- `update`
- `move`
- `complete`
- `delete`

调用方式：

```bash
./mac/reminders-bridge check-permission
./mac/reminders-bridge list-calendars
./mac/reminders-bridge get --input-json '{"reminder_id":"abc"}'
./mac/reminders-bridge create --input-json '{"title":"测试","list_name":"下一步行动@NextAction"}'
./mac/reminders-bridge update --input-json '{"reminder_id":"abc","title":"新标题","note":"备注"}'
./mac/reminders-bridge move --input-json '{"reminder_id":"abc","list_name":"项目@Project"}'
./mac/reminders-bridge complete --input-json '{"reminder_id":"abc"}'
./mac/reminders-bridge delete --input-json '{"reminder_id":"abc"}'
```

## 输出格式

成功：

```json
{
  "success": true,
  "action": "create",
  "reminder_id": "xxx"
}
```

失败：

```json
{
  "success": false,
  "action": "create",
  "error_code": "MISSING_TITLE",
  "error_message": "title is required"
}
```

## Python 对接字段

`sync_agent_mac.py` 当前传入字段：

### create
- `title`
- `list_name`
- `note`

### update
- `reminder_id`
- `title`
- `note`

### move
- `reminder_id`
- `list_name`

### complete
- `reminder_id`

### delete
- `reminder_id`

## Swift 版本建议目录

```text
mac/
  reminders-bridge                  # 可执行文件（最终产物）
  README-eventkit-bridge.md
  EventKitBridge/
    Package.swift
    Sources/
      RemindersBridge/
        main.swift
        Models.swift
        EventKitService.swift
        JsonIO.swift
```

## 当前实现状态

- `mac/reminders-bridge`：当前可运行的 Python 占位 bridge，用于先打通调用链
- `mac/EventKitBridge/`：Swift 工程骨架已建立
- `EventKitService.swift`：已补到真实 EventKit 调用方向的代码骨架（权限、列出列表、create/update/move/complete/delete），后续需要在 Mac 上编译和真机验证

## 后续替换原则

1. 保持 CLI 命令名不变
2. 保持 JSON 输入输出协议稳定
3. 让 `sync_agent_mac.py` 无需再改调用方式
4. 先在 Mac 上编译 Swift bridge 并验证 `check-permission` / `list-calendars` / `create`
5. 再逐步验证 `update` / `move` / `complete` / `delete`
