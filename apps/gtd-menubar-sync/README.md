# GTDMenubarSync

原生 macOS menubar app（SwiftUI MenuBarExtra），用于替代 `launchd + Python` 成为 GTD → Apple Reminders 同步的唯一 EventKit 权限主体。

## 当前阶段

MVP 骨架：

- 菜单栏入口
- 权限状态检查
- 基础同步状态显示
- 手动同步入口
- 本地服务层结构搭建

## 运行

```bash
cd apps/gtd-menubar-sync
swift run
```

> 说明：当前为第一版工程骨架，后续会继续补齐 EventKit 写入、服务端增量同步、状态持久化等能力。
