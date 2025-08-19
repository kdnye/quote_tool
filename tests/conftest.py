import os
import sys

# Ensure project root is on sys.path for imports
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from config import Config

# Use a dedicated SQLite database for tests
os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")
Config.DATABASE_URL = os.environ["DATABASE_URL"]
