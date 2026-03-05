#!/bin/bash
# GTD 任务管理系统 - 一键部署脚本
# 用法: curl -sSL https://raw.githubusercontent.com/wanXcode/gtd-tasks/main/deploy.sh | bash

set -e

REPO_URL="https://github.com/wanXcode/gtd-tasks.git"
WORKSPACE_DIR="${HOME}/.openclaw/workspace"
GTD_DIR="${WORKSPACE_DIR}/gtd-tasks"

echo "🚀 开始部署 GTD 任务管理系统..."

# 检查 openclaw 是否安装
if ! command -v openclaw &> /dev/null; then
    echo "❌ 错误: 未找到 openclaw 命令"
    echo "请先安装 OpenClaw: https://docs.openclaw.ai"
    exit 1
fi

# 创建工作目录
mkdir -p "${WORKSPACE_DIR}"

# 克隆或更新仓库
if [ -d "${GTD_DIR}" ]; then
    echo "📦 发现已有 gtd-tasks 目录，正在更新..."
    cd "${GTD_DIR}"
    git pull origin main
else
    echo "📦 克隆仓库..."
    cd "${WORKSPACE_DIR}"
    git clone "${REPO_URL}"
fi

cd "${GTD_DIR}"

# 设置 Git 用户信息（如果未设置）
if [ -z "$(git config user.email)" ]; then
    echo "⚙️  设置 Git 用户邮箱..."
    git config user.email "gtd@openclaw.local"
fi
if [ -z "$(git config user.name)" ]; then
    echo "⚙️  设置 Git 用户名..."
    git config user.name "GTD Assistant"
fi

# 检查是否已有定时任务
EXISTING_JOB=$(openclaw cron list --json 2>/dev/null | grep -o '"name":"gtd-daily-checkin"' || true)

if [ -n "$EXISTING_JOB" ]; then
    echo "⏰ 发现已有定时任务，跳过创建"
else
    echo "⏰ 创建每日提醒定时任务（晚8:30）..."
    openclaw cron add \
        --name "gtd-daily-checkin" \
        --cron "30 20 * * *" \
        --tz "Asia/Shanghai" \
        --message "你是GTD任务管理助手。现在是晚上8:30，请：

1. 先读取 ${GTD_DIR}/today.md 和 matrix/q1-urgent-important.md、matrix/q2-important-not-urgent.md
2. 整理当前待办清单（只显示未完成的）
3. 发送给用户的格式：

哥哥～晚上8点半了 🌙

【当前待办清单】
（列出今日待办 + Q1 + Q2 的未完成项）

请告诉我今天完成情况：
1. 完成了哪些？
2. 有什么卡点？
3. 明天计划做什么？" \
        --session isolated \
        2>/dev/null || echo "⚠️  定时任务创建失败，可能需要手动配置"
fi

echo ""
echo "✅ 部署完成！"
echo ""
echo "📁 工作目录: ${GTD_DIR}"
echo "📋 使用方法:"
echo "   - 查看今日待办: cat ${GTD_DIR}/today.md"
echo "   - 查看Q1紧急重要: cat ${GTD_DIR}/matrix/q1-urgent-important.md"
echo "   - 查看Q2重要不紧急: cat ${GTD_DIR}/matrix/q2-important-not-urgent.md"
echo ""
echo "💡 提示:"
echo "   - 每晚8:30会自动提醒回顾当日完成情况"
echo "   - 直接发消息给我可以添加新任务"
echo "   - 修改文件后记得 git push 同步到 GitHub"
echo ""
