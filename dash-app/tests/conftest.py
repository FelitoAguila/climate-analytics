"""Shared test configuration.

The app validates settings at import time, so tests provide a harmless dummy URL.
Settings-specific tests override or remove it explicitly.
"""

from __future__ import annotations

import os

os.environ["READONLY_DATABASE_URL"] = (
    "postgresql://test:test@localhost:5432/climate_test"
)
os.environ["DASH_DEBUG"] = "false"
