"""Pytest conftest: ensure src is on path for superbowlengine imports."""

import sys
from pathlib import Path

src = Path(__file__).resolve().parent.parent / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))
