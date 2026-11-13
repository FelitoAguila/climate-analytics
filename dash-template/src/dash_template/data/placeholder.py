"""Neutral placeholder data so the template runs out of the box.

Replace this module (or the functions it exposes) with your real data source.
"""

from __future__ import annotations

from functools import lru_cache

import pandas as pd

_CATEGORIES = ["Alpha", "Beta", "Gamma", "Delta"]
_STATUSES = ["Active", "Pending", "Archived"]
_NAMES = [
    "Aurora",
    "Basalt",
    "Cinder",
    "Delta",
    "Ember",
    "Fjord",
    "Granite",
    "Harbor",
    "Iris",
    "Juniper",
    "Kestrel",
    "Lumen",
    "Meadow",
    "Nimbus",
    "Onyx",
    "Prairie",
    "Quartz",
    "Ridge",
    "Summit",
    "Tundra",
    "Umbra",
    "Vertex",
    "Willow",
    "Zephyr",
]


@lru_cache(maxsize=1)
def records() -> pd.DataFrame:
    rows = []
    for index, name in enumerate(_NAMES, start=1):
        rows.append(
            {
                "id": f"record-{index:03d}",
                "name": name,
                "category": _CATEGORIES[index % len(_CATEGORIES)],
                "status": _STATUSES[index % len(_STATUSES)],
                "score": round(0.1 + (index * 3.7) % 9.9, 2),
                "updated": f"2026-{(index % 12) + 1:02d}-{(index % 27) + 1:02d}",
            }
        )
    return pd.DataFrame(rows)


def get_record(record_id: str) -> dict | None:
    frame = records()
    match = frame[frame["id"] == record_id]
    if match.empty:
        return None
    return match.iloc[0].to_dict()


def categories() -> list[str]:
    return list(_CATEGORIES)


def statuses() -> list[str]:
    return list(_STATUSES)
