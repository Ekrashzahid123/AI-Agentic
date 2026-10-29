"""
main.py (Root Proxy) - Enterprise Support AI Agent

This root entrypoint allows running `uvicorn main:app --reload` directly from the
repository root directory (C:\\Users\\Microsoft\\Desktop\\AI Agentic) as well as
from inside the junior-ai-agent/ folder.
"""

import importlib.util
from pathlib import Path
import sys

AGENT_DIR = Path(__file__).resolve().parent / "junior-ai-agent"
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

# Dynamically load the FastAPI app from junior-ai-agent/main.py without circular import
spec = importlib.util.spec_from_file_location("junior_main", AGENT_DIR / "main.py")
if spec is None or spec.loader is None:
    raise ImportError(f"Could not load module from {AGENT_DIR / 'main.py'}")

junior_main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(junior_main)

app = junior_main.app
