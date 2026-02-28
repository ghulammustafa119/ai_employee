#!/bin/bash
# Start all Platinum Tier services (Cloud + Local agents + Watchdog)

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

echo "=== AI Employee (Platinum Tier) ==="

# Initialize vault sync if not exists
if [ ! -d "vault_sync.git" ]; then
    echo "Initializing vault sync..."
    bash scripts/init_vault_sync.sh
fi

# Start Cloud Agent
echo "[1/3] Starting Cloud Agent..."
AGENT_ROLE=cloud VAULT_PATH=vault_cloud uv run python -m src.platinum.cloud_runner &
CLOUD_PID=$!
echo $CLOUD_PID > /tmp/ai_employee_cloud.pid
echo "  Cloud Agent PID: $CLOUD_PID"

# Start Local Agent
echo "[2/3] Starting Local Agent..."
AGENT_ROLE=local VAULT_PATH=vault_local uv run python -m src.platinum.local_runner &
LOCAL_PID=$!
echo $LOCAL_PID > /tmp/ai_employee_local.pid
echo "  Local Agent PID: $LOCAL_PID"

# Start Watchdog
echo "[3/3] Starting Watchdog..."
VAULT_CLOUD_PATH=vault_cloud VAULT_LOCAL_PATH=vault_local uv run python -m src.platinum.watchdog &
WATCHDOG_PID=$!
echo "  Watchdog PID: $WATCHDOG_PID"

echo ""
echo "=== Platinum Services Running ==="
echo "Cloud Agent:  PID $CLOUD_PID (vault_cloud/)"
echo "Local Agent:  PID $LOCAL_PID (vault_local/)"
echo "Watchdog:     PID $WATCHDOG_PID"
echo ""
echo "=== How It Works ==="
echo "1. Drop tasks in vault_cloud/Needs_Action/<domain>/"
echo "2. Cloud drafts → vault_cloud/Pending_Approval/<domain>/"
echo "3. Sync happens automatically via Git"
echo "4. Approve: mv vault_local/Pending_Approval/<domain>/APPROVE_*.md vault_local/Approved/"
echo "5. Local executes send → vault_local/Done/"
echo ""
echo "=== Demo ==="
echo "Run: uv run python -m src.platinum.demo"
echo ""
echo "Press Ctrl+C to stop all services."

trap "echo 'Stopping...'; kill $CLOUD_PID $LOCAL_PID $WATCHDOG_PID 2>/dev/null; rm -f /tmp/ai_employee_cloud.pid /tmp/ai_employee_local.pid; exit" SIGINT SIGTERM
wait
