#!/usr/bin/env bash
# ==============================================================================
# Plasma Column Simulation - Resume Antigravity (agy) Session Utility
# ==============================================================================
# Automatically discovers and resumes the most recent Antigravity CLI (agy)
# conversation session specifically associated with this repository workspace
# (/home/cspark/Work/projects/plasma-column).
#
# Usage:
#   bash scripts/resume_agy_session.sh [OPTIONS] [EXTRA_AGY_FLAGS...]
#   ./scripts/resume_agy_session.sh [OPTIONS]
#
# Options:
#   --list, -l          List available recent sessions for this repository.
#   --dry_run, -n       Show the conversation ID and command that would execute.
#   --session-id ID     Explicitly resume a specified conversation ID.
#   --help, -h          Display this help message.
#
# Examples:
#   bash scripts/resume_agy_session.sh
#   bash scripts/resume_agy_session.sh --list
#   bash scripts/resume_agy_session.sh --dry_run
#   bash scripts/resume_agy_session.sh --session-id 34dda9ff-36c0-44a5-a665-41183f6cea32
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Verify agy CLI is installed
AGY_BIN="$(command -v agy || true)"
if [ -z "$AGY_BIN" ]; then
  if [ -x "$HOME/.gemini/antigravity-cli/bin/agy" ]; then
    AGY_BIN="$HOME/.gemini/antigravity-cli/bin/agy"
  else
    echo "Error: 'agy' CLI executable not found in PATH or ~/.gemini/antigravity-cli/bin." >&2
    exit 1
  fi
fi

PYTHON_EXEC="$(command -v python3 || command -v python)"
if [ -z "$PYTHON_EXEC" ]; then
  echo "Error: Python 3 executable not found." >&2
  exit 1
fi

MODE="resume"
EXPLICIT_ID=""
EXTRA_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --list|-l)
      MODE="list"
      shift
      ;;
    --dry_run|-n)
      MODE="dry_run"
      shift
      ;;
    --session-id|--conversation)
      EXPLICIT_ID="$2"
      shift 2
      ;;
    --help|-h)
      echo "Usage: bash scripts/resume_agy_session.sh [OPTIONS] [EXTRA_AGY_FLAGS...]"
      echo ""
      echo "Resumes the most recent Antigravity (agy) session for this repository."
      echo ""
      echo "Options:"
      echo "  --list, -l          List all recorded sessions for this workspace."
      echo "  --dry_run, -n       Preview target conversation and resume command."
      echo "  --session-id ID     Resume a specific conversation ID."
      echo "  --help, -h          Display this help message."
      exit 0
      ;;
    *)
      EXTRA_ARGS+=("$1")
      shift
      ;;
  esac
done

cd "$PROJECT_ROOT"

# Helper python script to query sessions
query_db() {
  "$PYTHON_EXEC" - "$PROJECT_ROOT" "$MODE" "$EXPLICIT_ID" << 'PYEOF'
import os
import sys
import sqlite3

db_path = os.path.expanduser("~/.gemini/antigravity-cli/conversation_summaries.db")
repo_path = sys.argv[1]
action = sys.argv[2]
explicit_id = sys.argv[3] if len(sys.argv) > 3 else ""

if not os.path.isfile(db_path):
    print(f"Error: Database not found at {db_path}", file=sys.stderr)
    sys.exit(1)

try:
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    # Search for conversations containing this project path
    query = """
        SELECT conversation_id, title, last_modified_time, step_count
        FROM conversation_summaries
        WHERE workspace_uris LIKE ?
        ORDER BY last_modified_time DESC
    """
    pattern = f"%{os.path.basename(repo_path)}%"
    rows = cur.execute(query, (pattern,)).fetchall()
except Exception as e:
    print(f"Error querying conversation database: {e}", file=sys.stderr)
    sys.exit(1)

if action == "list":
    print("=" * 80)
    print(f" Antigravity Sessions for Workspace: {repo_path}")
    print("=" * 80)
    if not rows:
        print("  No previous sessions recorded for this repository.")
    else:
        hdr_id = "Conversation ID"
        hdr_step = "Steps"
        hdr_act = "Last Active"
        print(f"  {hdr_id:<38} | {hdr_step:<6} | {hdr_act:<20} | Title")
        print("  " + "-" * 76)
        for cid, title, modified, steps in rows:
            mod_str = modified.split(".")[0] if "." in modified else modified[:19]
            t_short = (title[:25] + "..") if len(title) > 27 else title
            print(f"  {cid:<38} | {steps:<6} | {mod_str:<20} | {t_short}")
    sys.exit(0)

target_id = explicit_id.strip()
if not target_id:
    if rows:
        target_id = rows[0][0]
    else:
        print("Warning: No existing conversation found for this workspace in database.", file=sys.stderr)
        sys.exit(2)

print(target_id)
PYEOF
}

if [ "$MODE" = "list" ]; then
  query_db
  exit 0
fi

set +e
TARGET_CID=$(query_db 2>&1)
QUERY_STATUS=$?
set -e

if [ "$QUERY_STATUS" -eq 2 ] || [ -z "$TARGET_CID" ]; then
  echo "No specific session found in history database. Falling back to 'agy --continue'."
  CMD=("$AGY_BIN" "--continue" "${EXTRA_ARGS[@]}")
else
  if [ "$QUERY_STATUS" -ne 0 ]; then
    echo "$TARGET_CID" >&2
    exit 1
  fi
  CMD=("$AGY_BIN" "--conversation" "$TARGET_CID" "${EXTRA_ARGS[@]}")
fi

echo "======================================================================"
echo " Antigravity (agy) Session Resumption"
echo "======================================================================"
echo "  Repository Workspace : $PROJECT_ROOT"
if [ -n "${TARGET_CID:-}" ] && [ "$QUERY_STATUS" -eq 0 ]; then
  echo "  Target Session ID    : $TARGET_CID"
fi
echo "  Command              : ${CMD[*]}"
echo "======================================================================"

if [ "$MODE" = "dry_run" ]; then
  echo ""
  echo "[DRY RUN] Would execute:"
  echo "  exec ${CMD[*]}"
  exit 0
fi

echo "Launching agy session..."
exec "${CMD[@]}"
