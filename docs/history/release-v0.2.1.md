# GTD Tasks v0.2.1

## 这版做了什么

v0.2.1 重点不是新增一堆功能，而是把 GTD 从“靠 markdown 手工维护”收口到“结构化主库 + 自动渲染视图”的稳定形态。

这一版之后：
- `data/tasks.json` 成为主账号 GTD 的唯一事实源
- `today.md / inbox.md / matrix/*` 变成展示层，而不是手工维护的数据源
- wife 账号的数据层也完成初始化
- 时间口径统一为 `Asia/Shanghai`

## 核心更新

### 1. 结构化主库落地
- 新增 `data/tasks.json`
- 新增 `data/README.md`
- GTD 开始从 markdown-first 过渡到 data-first

### 2. 主账号脚本补齐
新增：
- `scripts/task_cli.py`
- `scripts/render_views.py`
- `scripts/migrate_legacy.py`

能力包括：
- 列表查看
- 新增任务
- 更新任务
- 标记完成
- 自动渲染 `today / inbox / matrix`
- 检查迁移状态

### 3. wife 数据层初始化
新增：
- `users/wife/data/tasks.json`
- `users/wife/data/README.md`
- `users/wife/scripts/task_cli.py`
- `users/wife/scripts/render_views.py`

说明：
- 当前 wife 主库已初始化
- 结构已 ready
- 后续可以继续往里面写真实任务

### 4. 文档和口径收口
- 更新根目录 `README.md`
- 更新 `users/wife/README.md`
- 新增 `CHANGELOG.md`
- 明确 markdown 视图不再是事实源
- 明确业务时间统一按北京时间解释

### 5. 清理旧问题
- 去掉 `today.md` 里的业务硬编码提醒文本
- 修正渲染视图与当前任务状态不一致的问题
- 修复一个 Q4 渲染文本异常

## 当前版本判断

v0.2.1 可以理解为：
- 数据层已落地
- 渲染层已跑通
- 文档已基本跟上
- 发版已完成

但它还不是最终形态，后面更适合在 `v0.2.2 / v0.3.0` 继续补：
- 更完整的迁移工具
- 更通用的模板能力
- 更顺滑的多账号/多端同步

## Tag
- `v0.2.1`

## Commit
- release commit: `1ec4354`
- changelog commit: `1d51401`
