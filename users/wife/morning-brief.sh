#!/bin/bash
# GTD 早间推送 - Wife 专用
# 工作日上午 10:00 自动推送

GTD_DIR="${HOME}/.openclaw/workspace/gtd-tasks/users/wife"

echo "☀️ wife 的早安！今日待办清单来啦～"
echo ""
echo "【今日重点】"
echo ""

# 读取今日待办
if [ -f "${GTD_DIR}/today.md" ]; then
    grep -A 100 "## 今日重点" "${GTD_DIR}/today.md" | grep -E "^[·•]|^\- \[|^[^#\-]" | head -15 || echo "暂无待办事项"
fi

echo ""
echo "💪 加油！有进展随时告诉我～"
