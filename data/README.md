# GTD v0.2.1 数据层说明

从 v0.2.1 开始，`data/tasks.json` 是主账号 GTD 的结构化主库；`users/wife/data/tasks.json` 是 wife 的结构化主库。

## 规则

- `data/tasks.json` / `users/wife/data/tasks.json` 是各自账户的唯一事实源
- `today.md` / `inbox.md` / `matrix/*` 都由渲染脚本生成，不再手改
- 已完成/已取消任务不再显示在待办视图里
- 时间口径统一使用 `Asia/Shanghai`
- Markdown 视图是展示层，JSON 主库才是数据层

## 当前脚本

- 渲染主账号视图：`python3 scripts/render_views.py`
- 列出主账号任务：`python3 scripts/task_cli.py list`
- 新增主账号任务：`python3 scripts/task_cli.py add "任务标题" --bucket today`
- 完成主账号任务：`python3 scripts/task_cli.py done tsk_20260317_001`
- 更新主账号任务：`python3 scripts/task_cli.py update tsk_xxx --bucket future --note "备注"`
- 查看迁移状态：`python3 scripts/migrate_legacy.py`

## 迁移口径

- 主账号旧任务已收敛到 `data/tasks.json`
- wife 目录已完成数据层初始化，后续任务直接写入 `users/wife/data/tasks.json`
- 旧 markdown 文件保留为展示/历史痕迹，不再作为事实源反向写回
- 当前迁移脚本为安全说明版，不做破坏性自动覆盖

## 后续演进

- v0.2.1：完成结构化主库、渲染层、wife 目录并仓、迁移口径收口
- v0.3.0：增加 iOS 单向同步字段
- v0.4.0：增加双向同步与冲突处理
