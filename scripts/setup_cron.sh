#!/bin/bash
# Setup cron jobs for AI Employee scheduling

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
UV_PATH="$HOME/.local/bin/uv"

echo "Setting up cron jobs for AI Employee..."

# Create cron entries
CRON_JOBS="
# AI Employee — LinkedIn Post (daily at 9 AM)
0 9 * * * cd $PROJECT_DIR && $UV_PATH run python -m src.linkedin_poster >> $PROJECT_DIR/vault/Logs/cron.log 2>&1

# AI Employee — Dashboard Update (every 5 minutes)
*/5 * * * * cd $PROJECT_DIR && $UV_PATH run python -c 'from src.dashboard import update_dashboard; update_dashboard()' >> $PROJECT_DIR/vault/Logs/cron.log 2>&1
"

# Add to existing crontab (preserve old entries)
(crontab -l 2>/dev/null | grep -v "AI Employee"; echo "$CRON_JOBS") | crontab -

echo "Cron jobs installed:"
echo "  - LinkedIn Post: daily at 9:00 AM"
echo "  - Dashboard Update: every 5 minutes"
echo ""
echo "View cron jobs: crontab -l"
echo "Remove cron jobs: crontab -e (delete AI Employee lines)"
