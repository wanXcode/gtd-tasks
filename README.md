# GTD Tasks - 工作事项管理

基于 GTD + 四象限法则的待办管理系统，专为 OpenClaw AI 助手设计。

## 🚀 快速部署

### 一键安装

```bash
curl -sSL https://raw.githubusercontent.com/wanXcode/gtd-tasks/main/deploy.sh | bash
```

### 手动部署

```bash
# 1. 克隆仓库
cd ~/.openclaw/workspace
git clone https://github.com/wanXcode/gtd-tasks.git

# 2. 进入目录
cd gtd-tasks

# 3. 设置 Git（如果未设置）
git config user.email "your@email.com"
git config user.name "Your Name"

# 4. 创建定时任务（可选）
openclaw cron add --name "gtd-daily-checkin" \
  --cron "30 20 * * *" \
  --tz "Asia/Shanghai" \
  --message "你是GTD任务管理助手..." \
  --session isolated
```

## 📁 目录结构

```
├── data/
│   ├── tasks.json    # v0.2.1 主库（唯一事实源）
│   └── README.md     # 数据层说明
├── scripts/
│   ├── render_views.py   # 生成 today/inbox/matrix 视图
│   ├── task_cli.py       # 任务增删改查
│   └── migrate_legacy.py # 迁移占位脚本
├── inbox.md          # 收集箱/总览（由主库生成）
├── today.md          # 今日待办（由主库生成）
├── matrix/           # 四象限视图（由主库生成）
│   ├── q1-urgent-important.md
│   ├── q2-important-not-urgent.md
│   ├── q3-urgent-not-important.md
│   └── q4-not-urgent-not-important.md
├── archive/          # 已完成归档
└── deploy.sh         # 一键部署脚本
```

## 🔄 使用流程

1. **收集/更新** → 随时告诉 AI 助理，或通过 `task_cli.py` 更新主库
2. **主库存储** → 所有任务统一写入 `data/tasks.json`
3. **渲染视图** → 通过 `render_views.py` 生成 `today.md / inbox.md / matrix/*`
4. **提醒** → 每晚 8:30 定时脚本读取 `today.md`
5. **执行/完成** → 标记完成后自动从待办视图移除，进入已处理

## 📋 四象限说明

| 象限 | 特征 | 策略 |
|------|------|------|
| Q1 🔴 | 紧急重要 | 立即亲自处理 |
| Q2 🟡 | 重要不紧急 | 计划时间，重点投入 |
| Q3 🟠 | 紧急不重要 | 尽量委托他人 |
| Q4 ⚪ | 不紧急不重要 | 减少或不做 |

## 💬 常用指令

对 AI 助理说：
- "帮我记个事：xxx" → 添加到收集箱
- "生成今日待办" → 从四象限挑选优先级
- "xxx完成了" → 标记完成并归档
- "查看本周总结" → 生成周报

## 🔧 配置说明

### 定时任务
默认每晚8:30提醒回顾当日完成情况。如需修改时间：

```bash
# 删除旧任务
openclaw cron rm gtd-daily-checkin

# 创建新任务（例如改为晚上9点）
openclaw cron add --name "gtd-daily-checkin" \
  --cron "0 21 * * *" \
  --tz "Asia/Shanghai" \
  --message "..." \
  --session isolated
```

### GitHub 同步
修改文件后记得推送：

```bash
git add .
git commit -m "更新任务状态"
git push
```

## 📄 License

MIT

---
*由 AI 助理小花维护*
