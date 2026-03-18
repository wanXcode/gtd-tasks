# Apple Reminders Mac 同步桥 - MVP 使用说明

## 目标

把 Linux 端导出的 `sync/apple-reminders-export.json` 写入 macOS 的 Apple Reminders。

当前是 MVP：
- 支持创建 Reminder List（不存在则自动创建）
- 支持按 `[GTD_ID]` 查重
- 支持创建新提醒事项
- 支持更新同一列表内已有提醒事项的标题和备注

当前不做：
- 从旧列表迁移到新列表
- 删除已不存在的任务
- 完成状态回写 GTD
- 双向同步

---

## 文件

- Linux 导出文件：`sync/apple-reminders-export.json`
- Mac 桥接脚本：`sync_apple_reminders_mac.applescript`

---

## 在 Mac 上执行

```bash
osascript sync_apple_reminders_mac.applescript /absolute/path/to/apple-reminders-export.json
```

例如：

```bash
osascript ~/workspace/gtd-tasks/sync_apple_reminders_mac.applescript ~/workspace/gtd-tasks/sync/apple-reminders-export.json
```

---

## 推荐链路

### 方案 A：Git 同步
1. Linux 端生成导出文件
2. push 到仓库
3. Mac 端 pull 最新仓库
4. 在 Mac 上执行 AppleScript

### 方案 B：SSH / rsync
1. Linux 端生成导出文件
2. 用 scp/rsync 把 JSON 传到 Mac
3. 在 Mac 上执行 AppleScript

---

## 注意事项

1. 第一次运行脚本时，macOS 可能会要求授权“终端/osascript 控制提醒事项”，需要允许。
2. 当前脚本通过 note 中的 `[GTD_ID] xxx` 查重，所以不要手动删掉这行机器标记。
3. 当前脚本只在目标列表内查找已有 Reminder；如果后续分类规则变化导致任务应移动到别的列表，MVP 版本不会自动迁移旧任务，需要后续增强。

---

## 下一步增强建议

1. 支持跨列表查找并迁移 Reminder
2. 支持完成状态同步（GTD done → Reminders completed 或移除）
3. 支持从 Reminders 勾选完成回写 GTD
4. 支持定时自动执行
