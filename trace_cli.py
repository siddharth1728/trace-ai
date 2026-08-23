"""Direct entry point for running TRACE CLI without module shadowing."""

import importlib
import sys
from pathlib import Path

# Ensure src/ is at the head of sys.path
src_dir = str(Path(__file__).resolve().parent / "src")
if sys.path[0] != src_dir:
    sys.path.insert(0, src_dir)

if "trace" in sys.modules and not hasattr(sys.modules["trace"], "__path__"):
    del sys.modules["trace"]

from trace.cli.main import app

if __name__ == "__main__":
    app()
