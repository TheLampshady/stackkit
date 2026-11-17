"""
Test fixtures for job_service tests.

Jobs run against mocks, so tests need no network or emulator.
"""

import sys
from os import path

# Put job_service/ first on sys.path so imports resolve to its own copies
_job_service_dir = path.dirname(path.dirname(path.abspath(__file__)))
if _job_service_dir not in sys.path:
    sys.path.insert(0, _job_service_dir)
