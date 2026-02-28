#!/bin/bash
# Stop all Platinum Tier services

echo "Stopping Platinum services..."

for pidfile in /tmp/ai_employee_cloud.pid /tmp/ai_employee_local.pid; do
    if [ -f "$pidfile" ]; then
        PID=$(cat "$pidfile")
        kill "$PID" 2>/dev/null && echo "  Stopped PID $PID ($(basename $pidfile))"
        rm -f "$pidfile"
    fi
done

echo "Done."
