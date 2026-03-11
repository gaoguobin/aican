"""python -m aican entry point — auto-installs dependencies then starts MCP server."""
import subprocess
import sys

REQUIRED_PACKAGES = ["mcp", "cantools"]


def _ensure_deps():
    missing = []
    for pkg in REQUIRED_PACKAGES:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"[aican] Installing missing dependencies: {missing}", file=sys.stderr)
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet"] + missing
        )


_ensure_deps()

from aican.server import main  # noqa: E402

main()
