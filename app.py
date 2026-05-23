"""Top-level app shim so you can run `uvicorn app:app` from the repo root.

This inserts `src/` on `sys.path` so the package `expense_triage_agent` imports correctly
without requiring the user to set `PYTHONPATH` in their shell.
"""
import os
import sys

ROOT = os.path.dirname(__file__)
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from expense_triage_agent.main import app  # noqa: E402,F401

__all__ = ["app"]
