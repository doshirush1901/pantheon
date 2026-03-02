# Common utilities
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent

STATE_FILE = PROJECT_ROOT / "openclaw" / "agents" / "ira" / "workspace" / "state.json"

__all__ = ["PROJECT_ROOT", "STATE_FILE"]
