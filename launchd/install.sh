#!/bin/bash
# GTD Mac Sync Agent launchd 安装脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GTD_ROOT="$(dirname "$SCRIPT_DIR")"
PLIST_NAME="com.wan.gtd.sync.plist"
PLIST_SRC="$SCRIPT_DIR/$PLIST_NAME"
PLIST_DST="$HOME/Library/LaunchAgents/$PLIST_NAME"

echo "Installing GTD Mac Sync Agent launchd service..."
echo "GTD_ROOT: $GTD_ROOT"

# 替换路径
sed -e "s|REPLACE_WITH_YOUR_PATH|$GTD_ROOT|g" "$PLIST_SRC" > "$PLIST_DST"

echo "Created: $PLIST_DST"

# 加载服务
launchctl unload "$PLIST_DST" 2>/dev/null || true
launchctl load "$PLIST_DST"

echo "Service loaded: com.wan.gtd.sync"
echo ""
echo "Check status: launchctl list | grep com.wan.gtd.sync"
echo "View logs: tail -f $GTD_ROOT/logs/sync.log"
echo ""
echo "To uninstall: launchctl unload $PLIST_DST && rm $PLIST_DST"
