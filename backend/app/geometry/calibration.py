"""Floor-plan scale calibration and pixel -> metre conversion.

Physical dimensions are never inferred from pixels alone: a scale only exists once the
designer gives two points on the plan and the real distance between them.
"""
from __future__ import annotations
import math
from typing import Sequence

Point = tuple[float, float]
MIN_REFERENCE_PX = 20.0


class CalibrationError(ValueError):
    pass


def scale_from_reference(p1: Point, p2: Point, real_m: float) -> float:
    """Metres per pixel from two clicked points and the known real distance."""
    if real_m <= 0:
        raise CalibrationError("The real distance must be greater than zero.")
    d = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
    if d < MIN_REFERENCE_PX:
        raise CalibrationError(f"The two reference points are only {d:.0f} px apart. Pick two points farther apart for an accurate scale.")
    return real_m / d


def px_to_m(points: Sequence[Point], scale: float) -> list[Point]:
    return [(x * scale, y * scale) for x, y in points]


def snap_coordinates(points: Sequence[Point], tol: float) -> list[Point]:
    """Align near-equal x (and y) values so almost-straight walls become exactly straight.
    Values within `tol` of the first value in a cluster are replaced by the cluster mean."""
    if tol <= 0 or not points:
        return [tuple(p) for p in points]
    out = [list(p) for p in points]
    for axis in (0, 1):
        idx = sorted(range(len(points)), key=lambda i: points[i][axis])
        group = [idx[0]]

        def flush():
            mean = sum(points[i][axis] for i in group) / len(group)
            for i in group:
                out[i][axis] = mean

        for i in idx[1:]:
            if points[i][axis] - points[group[0]][axis] <= tol:
                group.append(i)
            else:
                flush(); group = [i]
        flush()
    return [(p[0], p[1]) for p in out]


def round_to_grid(points: Sequence[Point], step: float) -> list[Point]:
    if step <= 0:
        return [tuple(p) for p in points]
    r = lambda v: round(round(v / step) * step, 6)
    return [(r(x), r(y)) for x, y in points]
