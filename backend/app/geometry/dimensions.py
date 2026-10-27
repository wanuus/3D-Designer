"""Parse dimension strings found on floor plans (OCR output) into metres.

Explicit units always win. A bare number uses `default_unit`, which the designer
configures, because plans differ (3000 = mm on most plans, 3.0 = m on others).
"""
from __future__ import annotations
import re

_UNIT = {"mm": 0.001, "cm": 0.01, "m": 1.0, "meter": 1.0, "meters": 1.0, "metre": 1.0, "metres": 1.0}
_NUM = r"(\d+(?:[.,]\d+)?)"
_VAL = re.compile(rf"{_NUM}\s*(mm|cm|metres?|meters?|m)?\b", re.I)
_PAIR = re.compile(rf"{_NUM}\s*(mm|cm|m)?\s*[x×*]\s*{_NUM}\s*(mm|cm|m)?", re.I)
_FEET = re.compile(r"(\d+)\s*'\s*(?:(\d+(?:\.\d+)?)\s*\")?")


def _to_m(num: str, unit: str | None, default_unit: str) -> float:
    v = float(num.replace(",", "."))
    return v * _UNIT[(unit or default_unit).lower()]


def parse_dimension(text: str, default_unit: str = "m") -> float | None:
    """Parse a single length. Returns metres, or None if no length is found."""
    t = text.strip()
    f = _FEET.search(t)
    if f:
        return (int(f.group(1)) * 12 + float(f.group(2) or 0)) * 0.0254
    m = _VAL.search(t)
    return _to_m(m.group(1), m.group(2), default_unit) if m else None


def parse_pair(text: str, default_unit: str = "m") -> tuple[float, float] | None:
    """Parse 'W x L' strings such as '3.0 x 4.0 m' or '3000x4000'."""
    m = _PAIR.search(text)
    if not m:
        return None
    u1, u2 = m.group(2), m.group(4)
    unit1, unit2 = u1 or u2, u2 or u1  # '3 x 4 m' applies m to both
    return (_to_m(m.group(1), unit1, default_unit), _to_m(m.group(3), unit2, default_unit))
