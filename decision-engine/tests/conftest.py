"""Pytest configuration for KhetSathi Decision Engine."""
import sys
from pathlib import Path

# Add decision-engine directory to sys.path
decision_engine_dir = Path(__file__).resolve().parent.parent
if str(decision_engine_dir) not in sys.path:
    sys.path.insert(0, str(decision_engine_dir))
