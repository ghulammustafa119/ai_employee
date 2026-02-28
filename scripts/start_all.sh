#!/bin/bash
# Start all AI Employee services (Gold Tier)

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

echo "=== AI Employee (Gold Tier) ==="
echo "Starting all services..."
echo ""

# Start main runner (includes task processing, social media, CEO briefing)
echo "[1/3] Starting Runner..."
uv run python -m src.runner &
RUNNER_PID=$!
echo "  Runner PID: $RUNNER_PID"

# Start Gmail Watcher (only if credentials exist)
if [ -f "credentials.json" ]; then
    echo "[2/3] Starting Gmail Watcher..."
    uv run python -m src.watchers.gmail_watcher &
    GMAIL_PID=$!
    echo "  Gmail Watcher PID: $GMAIL_PID"
else
    echo "[2/3] Gmail Watcher skipped (no credentials.json)"
    GMAIL_PID=""
fi

# Start WhatsApp Watcher
echo "[3/3] Starting WhatsApp Watcher..."
echo "  WhatsApp Watcher must be started manually (needs QR scan):"
echo "  uv run python -m src.watchers.whatsapp_watcher"

echo ""
echo "=== Services Running ==="
echo "Runner:          PID $RUNNER_PID"
[ -n "$GMAIL_PID" ] && echo "Gmail Watcher:   PID $GMAIL_PID"
echo ""
echo "=== MCP Servers (start separately) ==="
echo "Email:  cd mcp_servers/email_server && npm start"
echo "Odoo:   cd mcp_servers/odoo_server && npm install && npm start"
echo ""
echo "=== Scheduled Tasks ==="
echo "CEO Briefing: Runs automatically on $BRIEFING_DAY (default: Monday)"
echo "To set up cron: ./scripts/setup_cron.sh"
echo ""
echo "=== Ralph Wiggum Loop ==="
echo "To start: ./scripts/ralph_loop.sh \"<prompt>\" --max-iterations 10"
echo ""
echo "Press Ctrl+C to stop all services."

# Wait and cleanup on exit
trap "echo 'Stopping...'; kill $RUNNER_PID $GMAIL_PID 2>/dev/null; exit" SIGINT SIGTERM
wait
