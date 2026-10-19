import sys
from os import path

# Add the agents directory to sys.path
agents_dir = path.dirname(path.abspath(__file__))
if agents_dir not in sys.path:
    sys.path.insert(0, agents_dir)
