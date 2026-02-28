#!/bin/bash
# Ralph Wiggum Loop — Start an autonomous multi-step task loop
#
# Usage:
#   ./scripts/ralph_loop.sh "Process all files in Needs_Action" --max-iterations 10
#   ./scripts/ralph_loop.sh "Generate weekly report" --promise "TASK_COMPLETE"

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

PROMPT="${1:?Usage: $0 \"<prompt>\" [--max-iterations N] [--promise TEXT]}"
shift

MAX_ITERATIONS=10
PROMISE="TASK_COMPLETE"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --max-iterations)
            MAX_ITERATIONS="$2"
            shift 2
            ;;
        --promise)
            PROMISE="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "=== Ralph Wiggum Loop ==="
echo "Prompt: $PROMPT"
echo "Max iterations: $MAX_ITERATIONS"
echo "Completion promise: $PROMISE"
echo "========================="

uv run python -c "
from src.ralph_wiggum import RalphWiggumLoop
loop = RalphWiggumLoop()
result = loop.start(
    prompt='$PROMPT',
    completion_promise='$PROMISE',
    max_iterations=$MAX_ITERATIONS,
)
print(f'Result: {result[\"status\"]} after {result[\"current_iteration\"]} iterations')
"
