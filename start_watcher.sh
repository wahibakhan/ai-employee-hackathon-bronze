#!/bin/bash
# ============================================================
#  Silver Tier Watcher — Startup Script
#  Panaversity Personal AI Employee Hackathon 0
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WATCHER="$SCRIPT_DIR/watcher.py"

echo ""
echo "  Panaversity AI Employee — Silver Tier Watcher"
echo "  ─────────────────────────────────────────────"

if [ ! -f "$WATCHER" ]; then
  echo "  ERROR: watcher.py not found at $WATCHER"
  exit 1
fi

echo "  Starting watcher... (Ctrl+C to stop)"
echo ""
python3 "$WATCHER"
