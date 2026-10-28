"""PostToolUse hook: auto-format + lint-fix the Python file the agent just edited.

Claude Code passes the tool call as JSON on stdin. We never block the edit:
any problem is reported on stderr and the hook exits 0.
"""

import json
import subprocess
import sys

try:
    payload = json.load(sys.stdin)
    path = payload.get("tool_input", {}).get("file_path", "")
    if path.endswith(".py"):
        subprocess.run(["ruff", "format", "--quiet", path], check=False)
        subprocess.run(["ruff", "check", "--fix", "--quiet", path], check=False)
except Exception as e:  # noqa: BLE001 - a formatter hiccup must never break the agent
    print(f"format hook skipped: {e}", file=sys.stderr)
sys.exit(0)
