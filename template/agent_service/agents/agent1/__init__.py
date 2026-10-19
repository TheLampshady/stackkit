import sys
from os import path

# agent1/__init__.py -> agent1/ -> agents/ -> agent_service/
root_path = path.dirname(path.dirname(path.dirname(path.abspath(__file__))))
if root_path not in sys.path:
    sys.path.insert(0, root_path)

import app_settings  # noqa: F401

from .agent import root_agent

__all__ = ["root_agent"]
