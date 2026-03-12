#!/bin/bash
# GTD 晚间回顾提醒 - Wife 专用
# 每晚 8:30 自动推送

GTD_DIR="${HOME}/.openclaw/workspace/gtd-tasks/users/wife"

echo "🌙 wife 的 GTD 晚间回顾时间到了～"
echo ""
echo "【当前待办清单】"
echo ""

# 读取今日待办
if [ -f "${GTD_DIR}/today.md" ]; then
    echo "📋 今日待办:"
    grep -E "^[·•]" "${GTD_DIR}/today.md" | head -10 || echo "   暂无待办事项"
fi

echo ""

# 读取 Q1 紧急重要
if [ -f "${GTD_DIR}/matrix/q1-urgent-important.md" ]; then
    Q1_COUNT=$(grep -c "^\- \[ \]" "${GTD_DIR}/matrix/q1-urgent-important.md" 2>/dev/null || echo "0")
    if [ "$Q1_COUNT" -gt 0 ]; then
        echo "🔴 Q1 紧急重要 (${Q1_COUNT}项):"
        grep -E "^[·•]|^\- \[ \]" "${GTD_DIR}/matrix/q1-urgent-important.md" | head -5
    fi
fi

# 读取 Q2 重要不紧急
if [ -f "${GTD_DIR}/matrix/q2-important-not-urgent.md" ]; then
    Q2_COUNT=$(grep -c "^\- \[ \]" "${GTD_DIR}/matrix/q2-important-not-urgent.md" 2>/dev/null || echo "0")
    if [ "$Q2_COUNT" -gt 0 ]; then
        echo "🟡 Q2 重要不紧急 (${Q2_COUNT}项):"
        grep -E "^[·•]|^\- \[ \]" "${GTD_DIR}/matrix/q2-important-not-urgent.md" | head -5
    fi
fi

echo ""
echo "请告诉我今天完成情况："
echo "1. 完成了哪些？"
echo "2. 有什么卡点？"
echo "3. 明天计划做什么？"
