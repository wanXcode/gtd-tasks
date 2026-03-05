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
├── inbox.md          # 收集箱（新事项入口）
├── today.md          # 今日待办（每日生成）
├── matrix/           # 四象限分类
│   ├── q1-urgent-important.md      # 紧急重要（立即做）
│   ├── q2-important-not-urgent.md  # 重要不紧急（计划做）
│   ├── q3-urgent-not-important.md  # 紧急不重要（委托做）
│   └── q4-not-urgent-not-important.md # 不紧急不重要（少做）
├── projects/         # 按项目分类
├── archive/          # 已完成归档
├── weekly/           # 周回顾记录
└── deploy.sh         # 一键部署脚本
```

## 🔄 使用流程

1. **收集** → 随时告诉 AI 助理，记入 inbox.md
2. **处理** → 每天梳理，分配到四象限
3. **组织** → 生成今日待办，按优先级排序
4. **回顾** → 每晚8:30自动提醒检查完成情况
5. **执行** → 专注做事，标记完成

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
