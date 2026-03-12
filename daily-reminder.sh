#!/bin/bash
# GTD 每日提醒脚本 - 生成带清单的提醒消息

echo "哥哥～晚上8点半了 🌙

先给你看当前的任务清单：

=== 今日待办 ==="
cat /root/.openclaw/workspace/gtd-tasks/today.md 2>/dev/null | grep -E '^[·•]' | head -20

echo "
=== Q1 紧急重要 ==="
cat /root/.openclaw/workspace/gtd-tasks/matrix/q1-urgent-important.md 2>/dev/null | grep -E '^\- \[.\]' | head -10

echo "
=== Q2 重要不紧急 ==="
cat /root/.openclaw/workspace/gtd-tasks/matrix/q2-important-not-urgent.md 2>/dev/null | grep -E '^\- \[.\]' | head -5

echo "
请告诉我：
1. 今天完成了哪些？
2. 有什么卡点？
3. 明天计划做什么？"
