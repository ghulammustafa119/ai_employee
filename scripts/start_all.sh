#!/bin/bash
# Start all AI Employee services

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

echo "Starting AI Employee services..."

# Start main runner
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
fi

# Start WhatsApp Watcher
echo "[3/3] Starting WhatsApp Watcher..."
echo "  WhatsApp Watcher must be started manually (needs QR scan):"
echo "  uv run python -m src.watchers.whatsapp_watcher"

echo ""
echo "AI Employee is running!"
echo "Press Ctrl+C to stop all services."

# Wait and cleanup on exit
trap "echo 'Stopping...'; kill $RUNNER_PID $GMAIL_PID 2>/dev/null; exit" SIGINT SIGTERM
wait
