#!/bin/bash
# GTD 提醒入口（兼容旧脚本名）
# 默认走 evening 模式；真正内容由 API-first 提醒脚本生成。

set -euo pipefail

MODE="${1:-evening}"
python3 /root/.openclaw/workspace/gtd-tasks/scripts/gtd_reminder_digest.py --mode "$MODE"
