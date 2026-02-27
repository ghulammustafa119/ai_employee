#!/bin/bash
# Stop all AI Employee services

echo "Stopping AI Employee services..."
pkill -f "src.runner" 2>/dev/null && echo "Runner stopped" || echo "Runner not running"
pkill -f "src.watchers.gmail_watcher" 2>/dev/null && echo "Gmail Watcher stopped" || echo "Gmail Watcher not running"
pkill -f "src.watchers.whatsapp_watcher" 2>/dev/null && echo "WhatsApp Watcher stopped" || echo "WhatsApp Watcher not running"
echo "All services stopped."
