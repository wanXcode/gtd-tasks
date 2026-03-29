#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BRIDGE_PATH="${GTD_REMINDERS_BRIDGE_PATH:-$ROOT_DIR/mac/reminders-bridge}"

if [[ ! -x "$BRIDGE_PATH" ]]; then
  echo "bridge not executable: $BRIDGE_PATH" >&2
  exit 1
fi

echo "[1/3] check-permission"
"$BRIDGE_PATH" check-permission

echo "[2/3] list-calendars"
"$BRIDGE_PATH" list-calendars

echo "[3/3] create (smoke)"
"$BRIDGE_PATH" create --input-json '{"title":"Bridge Smoke Test","list_name":"下一步行动@NextAction","note":"smoke"}'

echo "OK: bridge smoke checks finished"
