#!/bin/bash
# AIGTD 手动待办查询统一入口
# 用途：给“待办清单 / 发我待办清单 / 当前待办 / 今天/明天/未来有哪些”这类手动查询复用
# 默认输出结构化 JSON，便于 agent 二次整理成人话；如需纯文本可传 --text。

set -euo pipefail

MODE="${1:-morning}"
FORMAT="${2:---json}"

case "$MODE" in
  morning|evening) ;;
  *)
    echo "Usage: $0 [morning|evening] [--json|--text|--pretty]" >&2
    exit 2
    ;;
esac

case "$FORMAT" in
  --json)
    exec python3 /root/.openclaw/workspace/gtd-tasks/scripts/gtd_reminder_digest.py --mode "$MODE" --json
    ;;
  --pretty)
    exec python3 /root/.openclaw/workspace/gtd-tasks/scripts/gtd_reminder_digest.py --mode "$MODE" --json --pretty
    ;;
  --text)
    exec python3 /root/.openclaw/workspace/gtd-tasks/scripts/gtd_reminder_digest.py --mode "$MODE"
    ;;
  *)
    echo "Usage: $0 [morning|evening] [--json|--text|--pretty]" >&2
    exit 2
    ;;
esac
