#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PLIST_TEMPLATE="$SCRIPT_DIR/com.xiaohua.gtd-apple-reminders-sync.plist"
TARGET_DIR="$HOME/Library/LaunchAgents"
TARGET_PLIST="$TARGET_DIR/com.xiaohua.gtd-apple-reminders-sync.plist"
USERNAME="$(id -un)"
ABS_REPO_ROOT="$REPO_ROOT"

mkdir -p "$TARGET_DIR" "$REPO_ROOT/logs"
chmod +x "$SCRIPT_DIR/run_apple_reminders_sync.sh"

sed \
  -e "s#/ABSOLUTE/PATH/TO/gtd-tasks#$ABS_REPO_ROOT#g" \
  "$PLIST_TEMPLATE" > "$TARGET_PLIST"

launchctl bootout "gui/$(id -u)" "$TARGET_PLIST" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$TARGET_PLIST"
launchctl enable "gui/$(id -u)/com.xiaohua.gtd-apple-reminders-sync"
launchctl kickstart -k "gui/$(id -u)/com.xiaohua.gtd-apple-reminders-sync"

echo "Installed launchd agent for user: $USERNAME"
echo "Plist: $TARGET_PLIST"
echo "Repo : $ABS_REPO_ROOT"
echo "Check: launchctl print gui/$(id -u)/com.xiaohua.gtd-apple-reminders-sync"
