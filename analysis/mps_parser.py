"""Pure parser for .mps instrument files (latin-1, [BlockName] sections) — no Django/ORM dependency."""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

# Maps .mps file stat key -> model field name
STATS_KEY_MAP: dict[str, str] = {
    "Mean": "mean",
    "Mode": "mode",
    "Median": "median",
    "SD": "std",
    "Skew": "skew",
    "Kurtosis": "kurtosis",
    "FWMean": "fwmean",
    "FWMedian": "fwmedian",
    "FWSD": "fwsd",
    "FWSkew": "fwskew",
    "FWKurt": "fwkurt",
}


def _parse_stats_line(line: str, stats: dict) -> None:
    """Parse one key=value line from a [SizeStats] block into the stats dict."""
    try:
        key, value = line.split("=")
        attr = STATS_KEY_MAP.get(key.strip())
        if attr:
            stats[attr] = float(value.strip())
    except ValueError:
        pass


def parse_block_line(line: str, block: str | None, state: dict) -> None:
    """Update mutable parse state for one data line based on the current block."""
    if block == "#Bindiam":
        with contextlib.suppress(ValueError):
            state["classes"].append(float(line))
    elif block == "#Binheight":
        with contextlib.suppress(ValueError):
            state["measured_data"].append(float(line))
    elif block in {"Size0", "Size1", "Size2"}:
        try:
            key, value = line.split("=")
            if key.strip() == "Obs":
                state["concentration"].append(float(value.strip()))
        except ValueError:
            pass
    elif block == "SizeStats":
        _parse_stats_line(line, state["stats"])


def parse_mps_lines(lines: Sequence[str]) -> dict:
    """Parse .mps file lines into a structured data dict."""
    state: dict = {
        "classes": [],
        "measured_data": [],
        "concentration": [],
        "stats": dict.fromkeys(STATS_KEY_MAP.values(), None),
    }
    current_block: str | None = None

    for raw_line in lines:
        line = raw_line.strip()
        if line.startswith("[") and line.endswith("]"):
            current_block = line[1:-1]
        else:
            parse_block_line(line, current_block, state)

    return {
        "classes": state["classes"],
        "measured_data": state["measured_data"],
        "concentration": state["concentration"],
        **state["stats"],
    }


def read_mps_file(file_path: str | Path) -> dict:
    """Read and parse a .mps instrument file into a structured data dict."""
    with Path(file_path).open(encoding="latin-1", errors="ignore") as file:
        return parse_mps_lines(file.readlines())
