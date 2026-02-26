from __future__ import annotations

import re
from typing import Optional


def parse_length_to_cm(value: str | float | int | None) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip().lower().replace(",", ".")
    match = re.search(r"(\d+(?:\.\d+)?)\s*(mm|cm|m)?", text)
    if not match:
        return None

    number = float(match.group(1))
    unit = match.group(2) or "cm"

    if unit == "mm":
        return number / 10.0
    if unit == "m":
        return number * 100.0
    return number
