"""
Ralph Wiggum Loop — Autonomous multi-step task completion.

The Ralph Wiggum pattern keeps Claude Code iterating on a task until it's done.
It uses a Stop hook that intercepts Claude's exit and re-injects the prompt
if the task isn't complete yet.

Two completion strategies:
1. Promise-based: Claude outputs <promise>TASK_COMPLETE</promise>
2. File-movement: Task file moves to /Done folder

Usage:
    loop = RalphWiggumLoop()
    loop.start(
        prompt="Process all files in /Needs_Action",
        completion_promise="TASK_COMPLETE",
        max_iterations=10,
    )
"""

import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path

from src.config import VAULT_PATH, DONE, LOGS
from src.brain import log_action

logger = logging.getLogger(__name__)

STATE_DIR = VAULT_PATH / "In_Progress"


class RalphWiggumLoop:
    """Manages autonomous task loops using the Ralph Wiggum pattern."""

    def __init__(self):
        STATE_DIR.mkdir(parents=True, exist_ok=True)

    def start(
        self,
        prompt: str,
        completion_promise: str = "TASK_COMPLETE",
        max_iterations: int = 10,
        task_id: str = "",
    ) -> dict:
        """
        Start a Ralph Wiggum loop.

        Args:
            prompt: The task prompt for Claude Code.
            completion_promise: String that signals task completion.
            max_iterations: Maximum number of iterations before force-stop.
            task_id: Optional task identifier (auto-generated if empty).

        Returns:
            dict with status, iterations, and output.
        """
        if not task_id:
            task_id = f"ralph_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        state = {
            "task_id": task_id,
            "prompt": prompt,
            "completion_promise": completion_promise,
            "max_iterations": max_iterations,
            "current_iteration": 0,
            "status": "running",
            "started_at": datetime.now().isoformat(),
            "outputs": [],
        }

        state_file = STATE_DIR / f"{task_id}.json"
        self._save_state(state_file, state)

        logger.info(f"Ralph Wiggum loop started: {task_id} (max {max_iterations} iterations)")
        log_action(task_id, "ralph_loop_started", "running", f"max_iterations={max_iterations}")

        for iteration in range(1, max_iterations + 1):
            state["current_iteration"] = iteration
            logger.info(f"[{task_id}] Iteration {iteration}/{max_iterations}")

            try:
                output = self._execute_iteration(prompt, task_id, iteration)
                state["outputs"].append({
                    "iteration": iteration,
                    "timestamp": datetime.now().isoformat(),
                    "output_preview": output[:500] if output else "",
                })
            except Exception as e:
                logger.error(f"[{task_id}] Iteration {iteration} failed: {e}")
                state["outputs"].append({
                    "iteration": iteration,
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e),
                })
                self._save_state(state_file, state)
                continue

            # Check completion: promise-based
            if completion_promise and completion_promise in (output or ""):
                state["status"] = "completed"
                state["completed_at"] = datetime.now().isoformat()
                self._save_state(state_file, state)
                self._move_to_done(state_file, task_id)
                logger.info(f"[{task_id}] Completed via promise at iteration {iteration}")
                log_action(task_id, "ralph_loop_completed", "success", f"iterations={iteration}")
                return state

            # Check completion: file-movement (task file in Done/)
            if self._check_file_in_done(task_id):
                state["status"] = "completed"
                state["completed_at"] = datetime.now().isoformat()
                self._save_state(state_file, state)
                logger.info(f"[{task_id}] Completed via file movement at iteration {iteration}")
                log_action(task_id, "ralph_loop_completed", "success", f"iterations={iteration}")
                return state

            self._save_state(state_file, state)

        # Max iterations reached
        state["status"] = "max_iterations_reached"
        state["completed_at"] = datetime.now().isoformat()
        self._save_state(state_file, state)
        logger.warning(f"[{task_id}] Max iterations ({max_iterations}) reached")
        log_action(task_id, "ralph_loop_max_iterations", "warning", f"iterations={max_iterations}")
        return state

    def _execute_iteration(self, prompt: str, task_id: str, iteration: int) -> str:
        """Execute a single iteration by running Claude Code as a subprocess."""
        full_prompt = (
            f"[Ralph Wiggum Loop - Task: {task_id}, Iteration: {iteration}]\n\n"
            f"{prompt}\n\n"
            f"When the task is fully complete, output: <promise>TASK_COMPLETE</promise>"
        )

        try:
            result = subprocess.run(
                ["claude", "--print", full_prompt],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=str(VAULT_PATH),
            )
            return result.stdout
        except subprocess.TimeoutExpired:
            logger.warning(f"[{task_id}] Iteration {iteration} timed out")
            return ""
        except FileNotFoundError:
            logger.warning(f"[{task_id}] Claude CLI not found, using mock output")
            return f"[MOCK] Iteration {iteration} completed for: {prompt}"

    def _check_file_in_done(self, task_id: str) -> bool:
        """Check if the task file has been moved to Done/."""
        for f in DONE.iterdir():
            if task_id in f.name:
                return True
        return False

    def _move_to_done(self, state_file: Path, task_id: str) -> None:
        """Move the state file to Done/ folder."""
        import shutil
        dest = DONE / state_file.name
        shutil.move(str(state_file), str(dest))

    @staticmethod
    def _save_state(state_file: Path, state: dict) -> None:
        """Save loop state to JSON file."""
        state_file.write_text(json.dumps(state, indent=2))

    @staticmethod
    def get_active_loops() -> list[dict]:
        """Get all currently active Ralph Wiggum loops."""
        loops = []
        if not STATE_DIR.exists():
            return loops
        for f in STATE_DIR.glob("ralph_*.json"):
            try:
                data = json.loads(f.read_text())
                if data.get("status") == "running":
                    loops.append(data)
            except (json.JSONDecodeError, Exception):
                continue
        return loops


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    loop = RalphWiggumLoop()
    result = loop.start(
        prompt="Process all files in Needs_Action and move completed ones to Done",
        completion_promise="TASK_COMPLETE",
        max_iterations=3,
    )
    print(f"Loop result: {result['status']} after {result['current_iteration']} iterations")
