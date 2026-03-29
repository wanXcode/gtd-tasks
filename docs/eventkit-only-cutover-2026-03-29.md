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

以下内容仍保留在仓库中，但**不再属于当前主执行链路**：

- `sync_apple_reminders_mac.applescript`
- `scripts/apple_reminders_sync_lib.py`
- `mac/cleanup_gtd_id_markers.applescript`
- 以及 `docs/history/` 下的历史 AppleScript 方案文档

保留原因：

- 旧自动 push / 历史回溯仍可能参考
- 历史文档需要保留上下文
- 避免在同一轮 cutover 中误删仍被其他脚本引用的 legacy 文件

## 后续建议

后续若确认没有任何调用方再依赖 `scripts/apple_reminders_sync_lib.py`：

1. 将 legacy AppleScript 文件移动到 `archive/legacy/`
2. 清理 `nlp_capture.py` / `task_cli.py` 对旧自动 push 的依赖
3. 再做一次最终物理删除
