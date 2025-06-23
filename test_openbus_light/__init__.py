
"""Test package configuration.

Ensures that the local ``src`` directory is on ``sys.path`` so that the tests
import the in-repository version of :mod:`openbus_light` rather than a
potentially installed package from elsewhere.
"""

from __future__ import annotations

from pathlib import Path
import sys

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))
