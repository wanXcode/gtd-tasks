# EventKit-only Cutover (2026-03-29)

## 结论

从 2026-03-29 起，`scripts/sync_agent_mac.py` 的主执行链路正式收口为 **EventKit-only**：

- 不再通过 AppleScript / `osascript` 执行 Reminders create/update/move/complete/delete
- 统一走 `mac/reminders-bridge`（Swift + EventKit）
- `scripts/apple_reminders_bridge.py` 默认 backend 固定为 `eventkit`

## 当前主链路

- Mac sync orchestrator: `scripts/sync_agent_mac.py`
- Bridge wrapper: `scripts/apple_reminders_bridge.py`
- Native bridge binary: `mac/reminders-bridge`
- Swift source: `mac/EventKitBridge/`

## 已完成事项

- EventKit bridge 真机验证通过
- 历史 orphan mappings 已清理
- 服务端已过滤 deleted task / archived task 对应的 Apple mappings 下发
- `tags` 会同步到 Reminders note，格式为：`Tags: #TAG1 #TAG2`

## Legacy 说明

以下内容已从主路径移出，并归档到 `archive/legacy/`，**不再属于当前主执行链路**：

- `archive/legacy/sync_apple_reminders_mac.applescript`
- `archive/legacy/scripts/apple_reminders_sync_lib.py`
- `archive/legacy/mac/cleanup_gtd_id_markers.applescript`
- 以及 `docs/history/` 下的历史 AppleScript 方案文档

归档原因：

- 保留历史回溯与实现上下文
- 避免主路径继续暴露 legacy AppleScript 文件
- 当前主链路已经不再依赖这些文件

## 后续建议

后续若确认 archive 中这些 legacy 文件不再需要保留：

1. 直接删除 `archive/legacy/` 下对应 AppleScript/旧同步文件
2. 继续清理历史文档中的旧路径说明（如有需要）
3. 再做一次最终物理删除
