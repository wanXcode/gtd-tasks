# GTD Menubar Sync 技术方案

## 设计原则

1. **原生 Swift menubar app 是唯一 EventKit 权限主体**
2. **同步编排与 EventKit 写入在同一个前台宿主内完成**
3. **保持 MVP 简洁，优先打通稳定主链路**
4. **复用现有服务端协议与映射规则，不复用后台权限模型**
5. **日志、状态、错误必须对用户可见**

## 技术选型

- UI：`SwiftUI + MenuBarExtra`
- 平台：`macOS 14+`
- 权限 / 数据：`EventKit`
- 日志：`OSLog`
- 本地状态：JSON（MVP），后续可迁 SQLite
- 网络：`URLSession`
- 并发：Swift Concurrency

## 推荐目录结构

```text
apps/
  gtd-menubar-sync/
    Package.swift
    README.md
    Sources/
      GTDMenubarSync/
        App/
          GTDMenubarSyncApp.swift
          AppState.swift
        UI/
          MenuBarRootView.swift
          StatusSectionView.swift
        Models/
          TaskModels.swift
          SyncModels.swift
        Services/
          PermissionManager.swift
          RemindersStore.swift
          ServerAPI.swift
          LocalStore.swift
          SyncEngine.swift
          SyncMapper.swift
          AppLogger.swift
```

## 模块划分

### 1. App
负责：
- 应用入口
- 菜单栏挂载
- 初始化 AppState / SyncEngine
- 管理生命周期

### 2. AppState
负责：
- 当前权限状态
- 同步状态
- 服务端状态
- 上次成功同步时间
- 最近错误摘要
- 将状态暴露给 UI

### 3. PermissionManager
负责：
- 检查 Reminders 授权状态
- 请求授权
- 给出可显示的权限状态枚举

### 4. RemindersStore
负责：
- EventKit reminder CRUD
- 列出 reminders 日历
- Reminder 与本地模型的映射
- EventKit 错误标准化

### 5. ServerAPI
负责：
- `/api/changes`
- `/api/tasks`
- `/api/apple/mappings`
- `/api/sync/clients/{client}/ack`
- 后续 completed 回写接口

### 6. LocalStore
负责：
- 持久化 client_id
- 持久化 last_change_id
- 持久化 task_id → reminder_id mapping
- 保存最近同步状态与错误快照

### 7. SyncMapper
负责：
- 将服务端 task / change 转成 reminder 操作意图
- 复用现有 bucket/category → list 规则
- 复用 title / tag / note / due_date 映射规则

### 8. SyncEngine
负责：
- 定时同步
- 手动同步
- 防重入
- 串行执行
- 协调 PermissionManager / ServerAPI / RemindersStore / LocalStore
- 成功后 ack，失败则保留 cursor

## 数据流

### 启动流程
1. App 启动
2. AppState 初始化
3. PermissionManager 读取权限状态
4. LocalStore 载入 cursor / mappings / last status
5. SyncEngine 准备定时器

### 一轮同步流程
1. 检查是否已在同步，若是则跳过
2. 检查权限，未授权则更新 UI 并返回
3. 读取本地 last_change_id
4. 调用 `/api/changes`
5. 遍历变更并映射成本地 reminder 操作
6. 调用 RemindersStore 执行 create/update/move/complete/delete
7. 成功时更新 mapping 和连续成功的 ack 边界
8. 对连续成功的 change 执行 ack
9. 更新本地 sync status 与 UI

## 持久化设计（MVP）

建议放在：

`~/Library/Application Support/GTDMenubarSync/`

文件：

- `state.json`
  - client_id
  - last_change_id
  - last_sync_at
  - last_success_at
- `mappings.json`
  - task_id -> reminder_id
- `status.json`
  - 当前状态
  - 最近错误
  - 服务端状态

### 为什么先用 JSON
- 实现快
- 便于调试
- 可直接对照现有 Python 时代的状态概念

## API 集成点

MVP 直接沿用当前服务端接口：

- `GET /api/changes?since_change_id=...&limit=...`
- `GET /api/tasks?status=open&limit=1000`
- `GET /api/apple/mappings`
- `POST /api/apple/mappings`
- `POST /api/sync/clients/{client_id}/ack`

## 权限策略

### 核心原则
只允许这个 menubar app 触碰 EventKit。

### 执行规则
- 启动时执行权限检查
- 菜单中保留“请求权限”按钮
- 权限异常时不做 EventKit 写入
- UI 显示清晰错误，而不是静默 defer

## 同步调度策略

### MVP
- 默认 60 秒轮询一次
- 支持手动立即同步
- 单实例串行同步，禁止重入

### 防重入
SyncEngine 维护内部 `isSyncing` 状态；同步期间忽略新的自动触发，只允许 UI 看到“同步中”。

## 错误处理

### 分层处理
- 权限错误：立即停止本轮并更新状态
- 网络错误：本轮失败，不改 cursor
- 单条 reminder 错误：记录错误并停止 ack 到该点之后
- 持久化错误：写日志并更新 UI

### Ack 规则
只 ack **连续成功** 的 change，保持与现有修复后的原则一致。

## 日志与观测

### 记录内容
- 启动与退出
- 权限状态变化
- 每轮同步开始/结束
- changes 数量
- success / failure 数量
- ack 边界
- 最近错误详情

### 用户可见状态
- Sync health
- Permission status
- Server health
- Last success time
- Recent error summary

## 与现有 Python 逻辑的关系

### 可概念复用
- 同步模型：change 拉取、连续成功 ack
- 数据模型：task、mapping、last_change_id
- 映射规则：bucket/category/tag/note/due_date

### 不再延续的部分
- launchd 作为 EventKit 主体
- Python 后台 worker 直接写 Reminders
- 依赖后台上下文权限是否稳定

## 迁移计划

### Step 1
搭建 menubar app 骨架，打通：
- 启动
- 菜单栏显示
- 权限检查
- reminders 日历读取

### Step 2
打通本地 EventKit 写入：
- create/update/complete/delete

### Step 3
打通服务端 API：
- changes 拉取
- ack
- mapping 保存

### Step 4
用新 app 做主同步通路，停用旧 launchd EventKit 写入

## 风险与缓解

### 风险 1：重复创建 reminders
缓解：先迁移 mapping，再开 create；所有 create 前先查 mapping。

### 风险 2：旧同步器与新 app 双写
缓解：切换期必须停掉旧 EventKit 写入。

### 风险 3：MVP 范围失控
缓解：第一版只做菜单栏、权限、同步、状态；不做复杂 UI。

### 风险 4：completed 回写复杂度偏高
缓解：列为第二阶段，不阻塞 MVP 主链路。
