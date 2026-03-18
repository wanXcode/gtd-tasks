#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEFAULT_EXPORT_PATH="$REPO_ROOT/sync/apple-reminders-export.json"
DEFAULT_APPLESCRIPT_PATH="$REPO_ROOT/sync_apple_reminders_mac.applescript"
DEFAULT_LOG_DIR="$REPO_ROOT/logs"
DEFAULT_STDOUT_LOG="$DEFAULT_LOG_DIR/apple-reminders-launchd.out.log"
DEFAULT_STDERR_LOG="$DEFAULT_LOG_DIR/apple-reminders-launchd.err.log"
DEFAULT_RUNTIME_STATE_PATH="$REPO_ROOT/sync/apple-reminders-mac-runtime-state.json"

EXPORT_PATH="${1:-${GTD_APPLE_REMINDERS_EXPORT_PATH:-$DEFAULT_EXPORT_PATH}}"
APPLESCRIPT_PATH="${GTD_APPLE_REMINDERS_APPLESCRIPT_PATH:-$DEFAULT_APPLESCRIPT_PATH}"
LOG_DIR="${GTD_APPLE_REMINDERS_LOG_DIR:-$DEFAULT_LOG_DIR}"
RUN_LOG="$LOG_DIR/apple-reminders-sync-mac.log"
LOCK_DIR="$LOG_DIR/.apple-reminders-sync.lock"
RUNTIME_STATE_PATH="${GTD_APPLE_REMINDERS_MAC_RUNTIME_STATE_PATH:-$DEFAULT_RUNTIME_STATE_PATH}"
PYTHON_BIN="${PYTHON_BIN:-/usr/bin/python3}"
OSASCRIPT_BIN="${OSASCRIPT_BIN:-/usr/bin/osascript}"
GIT_BIN="${GIT_BIN:-$(command -v git || true)}"
ENABLE_GIT_PULL="${GTD_APPLE_REMINDERS_ENABLE_GIT_PULL:-1}"
GIT_REMOTE="${GTD_APPLE_REMINDERS_GIT_REMOTE:-origin}"
GIT_BRANCH="${GTD_APPLE_REMINDERS_GIT_BRANCH:-}"
GIT_RESTORE_EXPORT_BEFORE_PULL="${GTD_APPLE_REMINDERS_GIT_RESTORE_EXPORT_BEFORE_PULL:-1}"
SECOND_PULL_WAIT_SECONDS="${GTD_APPLE_REMINDERS_SECOND_PULL_WAIT_SECONDS:-2}"

mkdir -p "$LOG_DIR"

log() {
  printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S%z')" "$*" | tee -a "$RUN_LOG"
}

cleanup() {
  rmdir "$LOCK_DIR" >/dev/null 2>&1 || true
}
trap cleanup EXIT

run_git() {
  "$GIT_BIN" -C "$REPO_ROOT" "$@"
}

normalize_bool() {
  local raw lowered
  raw="${1:-}"
  lowered="$(printf '%s' "$raw" | tr '[:upper:]' '[:lower:]')"
  case "$lowered" in
    1|true|yes|on) echo "1" ;;
    0|false|no|off) echo "0" ;;
    *) echo "$raw" ;;
  esac
}

is_git_repo() {
  [[ -n "$GIT_BIN" ]] || return 1
  run_git rev-parse --is-inside-work-tree >/dev/null 2>&1
}

current_branch() {
  run_git rev-parse --abbrev-ref HEAD 2>/dev/null || true
}

read_export_generated_at() {
  local path="$1"
  [[ -f "$path" ]] || return 0
  "$PYTHON_BIN" - <<'PY' "$path"
import json, sys
path = sys.argv[1]
try:
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(data.get('generated_at', '') or '')
except Exception:
    print('')
PY
}

read_last_consumed_generated_at() {
  local path="$RUNTIME_STATE_PATH"
  [[ -f "$path" ]] || return 0
  "$PYTHON_BIN" - <<'PY' "$path"
import json, sys
path = sys.argv[1]
try:
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(data.get('last_consumed_generated_at', '') or '')
except Exception:
    print('')
PY
}

write_runtime_state() {
  local generated_at="$1"
  local task_count="$2"
  local export_path="$3"
  "$PYTHON_BIN" - <<'PY' "$RUNTIME_STATE_PATH" "$generated_at" "$task_count" "$export_path"
import json, os, sys
from datetime import datetime, timezone
path, generated_at, task_count, export_path = sys.argv[1:5]
os.makedirs(os.path.dirname(path), exist_ok=True)
state = {
    'last_consumed_generated_at': generated_at,
    'last_consumed_task_count': int(task_count or '0'),
    'last_consumed_export_path': export_path,
    'updated_at': datetime.now(timezone.utc).astimezone().isoformat(),
}
with open(path, 'w', encoding='utf-8') as f:
    json.dump(state, f, ensure_ascii=False, indent=2)
    f.write('\n')
PY
}

restore_export_if_needed() {
  local enabled tracked modified_output
  enabled="$(normalize_bool "$GIT_RESTORE_EXPORT_BEFORE_PULL")"
  if [[ "$enabled" != "1" ]]; then
    return 0
  fi

  tracked="$(run_git ls-files --error-unmatch -- sync/apple-reminders-export.json 2>/dev/null || true)"
  if [[ -z "$tracked" ]]; then
    return 0
  fi

  modified_output="$(run_git status --porcelain -- sync/apple-reminders-export.json 2>/dev/null || true)"
  if [[ -z "$modified_output" ]]; then
    return 0
  fi

  log "git: restoring tracked runtime export before pull: sync/apple-reminders-export.json"
  if ! run_git restore --worktree --source=HEAD -- sync/apple-reminders-export.json >/dev/null 2>&1; then
    log "git: restore export failed; keep current working tree"
  fi
}

maybe_git_pull() {
  local enabled dirty_output branch_before branch_after status fetch_output pull_output export_before export_after
  enabled="$(normalize_bool "$ENABLE_GIT_PULL")"

  if [[ "$enabled" != "1" ]]; then
    log "git: pull disabled by GTD_APPLE_REMINDERS_ENABLE_GIT_PULL=$ENABLE_GIT_PULL"
    return 0
  fi

  if ! is_git_repo; then
    log "git: skip pull because repo is not a git worktree or git is unavailable"
    return 0
  fi

  branch_before="${GIT_BRANCH:-$(current_branch)}"
  if [[ -z "$branch_before" || "$branch_before" == "HEAD" ]]; then
    log "git: skip pull because current branch is detached and GTD_APPLE_REMINDERS_GIT_BRANCH is unset"
    return 0
  fi

  export_before="$(read_export_generated_at "$EXPORT_PATH")"
  restore_export_if_needed

  dirty_output="$(run_git status --porcelain --untracked-files=no 2>/dev/null || true)"
  if [[ -n "$dirty_output" ]]; then
    log "git: skip pull because tracked working tree is dirty"
    while IFS= read -r line; do
      [[ -n "$line" ]] && log "git-status: $line"
    done <<< "$dirty_output"
    return 0
  fi

  set +e
  fetch_output="$(run_git fetch --quiet "$GIT_REMOTE" 2>&1)"
  status=$?
  set -e
  if [[ -n "$fetch_output" ]]; then
    while IFS= read -r line; do
      [[ -n "$line" ]] && log "git-fetch: $line"
    done <<< "$fetch_output"
  fi
  if [[ $status -ne 0 ]]; then
    log "git: fetch failed remote=$GIT_REMOTE exit_code=$status; continue with local export"
    return 0
  fi

  set +e
  pull_output="$(run_git pull --ff-only "$GIT_REMOTE" "$branch_before" 2>&1)"
  status=$?
  set -e
  if [[ -n "$pull_output" ]]; then
    while IFS= read -r line; do
      [[ -n "$line" ]] && log "git-pull: $line"
    done <<< "$pull_output"
  fi
  if [[ $status -ne 0 ]]; then
    log "git: pull failed remote=$GIT_REMOTE branch=$branch_before exit_code=$status; continue with current local export"
    return 0
  fi

  branch_after="$(current_branch)"
  export_after="$(read_export_generated_at "$EXPORT_PATH")"
  log "git: pull ok remote=$GIT_REMOTE branch=${branch_after:-$branch_before} export_before=${export_before:-none} export_after=${export_after:-none}"
  return 0
}

if ! mkdir "$LOCK_DIR" >/dev/null 2>&1; then
  log "skip: another sync process is running"
  exit 20
fi

PREVIOUS_GENERATED_AT="$(read_last_consumed_generated_at)"
maybe_git_pull

if [[ ! -f "$EXPORT_PATH" ]]; then
  log "error: export json not found: $EXPORT_PATH"
  exit 10
fi

CURRENT_GENERATED_AT="$(read_export_generated_at "$EXPORT_PATH")"
if [[ -n "$PREVIOUS_GENERATED_AT" && -n "$CURRENT_GENERATED_AT" && "$CURRENT_GENERATED_AT" == "$PREVIOUS_GENERATED_AT" ]]; then
  if [[ "$(normalize_bool "$ENABLE_GIT_PULL")" == "1" ]] && is_git_repo; then
    log "git: export generated_at unchanged after pull ($CURRENT_GENERATED_AT); wait ${SECOND_PULL_WAIT_SECONDS}s and retry once"
    sleep "$SECOND_PULL_WAIT_SECONDS"
    maybe_git_pull
    CURRENT_GENERATED_AT="$(read_export_generated_at "$EXPORT_PATH")"
  fi
fi

if [[ -n "$PREVIOUS_GENERATED_AT" && -n "$CURRENT_GENERATED_AT" && "$CURRENT_GENERATED_AT" == "$PREVIOUS_GENERATED_AT" ]]; then
  log "export: generated_at unchanged since last consume ($CURRENT_GENERATED_AT); continue idempotent replay"
else
  log "export: generated_at ready previous=${PREVIOUS_GENERATED_AT:-none} current=${CURRENT_GENERATED_AT:-none}"
fi

if [[ ! -f "$APPLESCRIPT_PATH" ]]; then
  log "error: AppleScript not found: $APPLESCRIPT_PATH"
  exit 11
fi

if [[ ! -x "$OSASCRIPT_BIN" ]]; then
  log "error: osascript not executable: $OSASCRIPT_BIN"
  exit 12
fi

if [[ ! -x "$PYTHON_BIN" ]]; then
  log "error: python3 not executable: $PYTHON_BIN"
  exit 13
fi

TASK_COUNT="$($PYTHON_BIN - <<'PY' "$EXPORT_PATH"
import json, sys
path = sys.argv[1]
with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)
print(len(data.get('tasks', [])))
PY
)"

log "start: export=$EXPORT_PATH tasks=$TASK_COUNT"
set +e
OUTPUT="$($OSASCRIPT_BIN "$APPLESCRIPT_PATH" "$EXPORT_PATH" 2>&1)"
STATUS=$?
set -e

if [[ -n "$OUTPUT" ]]; then
  while IFS= read -r line; do
    [[ -n "$line" ]] && log "osascript: $line"
  done <<< "$OUTPUT"
fi

if [[ $STATUS -ne 0 ]]; then
  log "failed: exit_code=$STATUS"
  exit $STATUS
fi

write_runtime_state "$CURRENT_GENERATED_AT" "$TASK_COUNT" "$EXPORT_PATH"
log "done: exit_code=0 generated_at=${CURRENT_GENERATED_AT:-none}"
exit 0
