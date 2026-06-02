"""
DHT-specific calculations:

- Compute Handicapped Task Distance (HTD)
- Compute per-pilot barrel radius
- Analyse a flight trace against the task to get raw and marking distances
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from .geo import distance_km, Point, first_cylinder_entry, distance_km_fix


START_BARREL_KM = 3.0   # Standard start cylinder radius
FINISH_BARREL_KM = 1.0  # Standard finish cylinder radius
REFERENCE_TP_BARREL_KM = 0.5  # Barrel used by the highest-handicap glider


@dataclass
class TaskPoint:
    name: str
    lat: float
    lon: float
    order: int  # 0=start, 1..N=TPs, N+1=finish


@dataclass
class FlightResult:
    finisher: bool
    start_time: Optional[object]   # datetime
    finish_time: Optional[object]  # datetime
    task_time_seconds: Optional[int]
    raw_distance: float            # km, derived from IGC crossings
    marking_distance: float        # raw × (HTD/DTD)
    handicapped_speed: Optional[float]  # HTD / task_time_hours


def compute_htd(declared_task_distance: float, h_max: float,
                wind_adjustment_factor: float = 1.0) -> float:
    """
    Handicapped Task Distance.

    HTD = DTD × (100 / H_max) × WAF
    """
    return declared_task_distance * (100.0 / h_max) * wind_adjustment_factor


def compute_declared_task_distance(task_points: list[TaskPoint]) -> float:
    """Sum of geodesic distances between consecutive task point centres."""
    total = 0.0
    for i in range(len(task_points) - 1):
        a = task_points[i]
        b = task_points[i + 1]
        total += distance_km(Point(a.lat, a.lon), Point(b.lat, b.lon))
    return total


def compute_barrel_radius(dtd: float, htd: float, handicap: float,
                          n_tps: int) -> float:
    """
    Barrel radius for a given handicap.

    target_flown_distance = HTD × (100 / H)
    extra_distance        = DTD - target_FD
    The extra is absorbed by enlarging the barrel at each of N_TP TPs.
    Each enlarged barrel saves ~2 × (r - r_ref) km on a straight leg.

    barrel_r = REFERENCE_TP_BARREL_KM + extra / (2 × n_tps)
    """
    if n_tps <= 0:
        return REFERENCE_TP_BARREL_KM
    target_fd = htd * (100.0 / handicap)
    extra = dtd - target_fd
    radius = REFERENCE_TP_BARREL_KM + extra / (2.0 * n_tps)
    return max(REFERENCE_TP_BARREL_KM, radius)


def analyse_flight(fixes, task_points: list[TaskPoint],
                   barrel_radius_km: float,
                   htd: float, dtd: float) -> FlightResult:
    """
    Walk through the IGC fixes and detect:
      - Start cylinder crossing
      - Each TP barrel crossing (in order)
      - Finish cylinder crossing (or last valid fix for landouts)

    Returns a FlightResult with raw_distance and marking_distance.
    """
    if not fixes or len(task_points) < 2:
        return FlightResult(
            finisher=False,
            start_time=None, finish_time=None,
            task_time_seconds=None,
            raw_distance=0.0,
            marking_distance=0.0,
            handicapped_speed=None,
        )

    start_tp = task_points[0]
    finish_tp = task_points[-1]
    intermediate_tps = task_points[1:-1]  # pure TPs (no start/finish)

    # ── 1. Find start crossing ──────────────────────────────────────────────
    start_fix = first_cylinder_entry(
        fixes, start_tp.lat, start_tp.lon, START_BARREL_KM
    )
    if start_fix is None:
        # Pilot never reached start cylinder — no valid flight
        return FlightResult(
            finisher=False,
            start_time=None, finish_time=None,
            task_time_seconds=None,
            raw_distance=0.0,
            marking_distance=0.0,
            handicapped_speed=None,
        )

    # Only consider fixes after the start exit (fixes after leaving start barrel)
    post_start_fixes = _fixes_after_exit(fixes, start_tp, START_BARREL_KM, start_fix)

    # ── 2. Walk through TPs in order ─────────────────────────────────────────
    crossings = [start_fix]
    remaining_fixes = post_start_fixes
    all_tps_reached = True

    for tp in intermediate_tps:
        entry = first_cylinder_entry(remaining_fixes, tp.lat, tp.lon, barrel_radius_km)
        if entry is None:
            all_tps_reached = False
            break
        crossings.append(entry)
        remaining_fixes = _fixes_from(remaining_fixes, entry)

    # ── 3. Look for finish ────────────────────────────────────────────────────
    finish_fix = None
    if all_tps_reached:
        finish_fix = first_cylinder_entry(
            remaining_fixes, finish_tp.lat, finish_tp.lon, FINISH_BARREL_KM
        )

    finisher = finish_fix is not None and all_tps_reached

    if finisher:
        crossings.append(finish_fix)
        last_fix = finish_fix
    else:
        # Use the furthest fix reached for landout distance
        last_fix = _furthest_along_task(remaining_fixes, task_points, crossings)
        if last_fix:
            crossings.append(last_fix)

    # ── 4. Sum distances between crossing points ──────────────────────────────
    raw_distance = 0.0
    for i in range(len(crossings) - 1):
        a = crossings[i]
        b = crossings[i + 1]
        raw_distance += distance_km_fix(a.lat, a.lon, b.lat, b.lon)

    # ── 5. Marking Distance ───────────────────────────────────────────────────
    factor = htd / dtd if dtd > 0 else 1.0
    marking_distance = min(raw_distance * factor, dtd)

    # ── 6. Task time and speed ────────────────────────────────────────────────
    task_time_seconds = None
    handicapped_speed = None
    start_time = getattr(start_fix, "time", None)
    finish_time = getattr(finish_fix, "time", None) if finisher else None

    if finisher and start_time and finish_time:
        task_time_seconds = int((finish_time - start_time).total_seconds())
        if task_time_seconds > 0:
            handicapped_speed = htd / (task_time_seconds / 3600.0)

    return FlightResult(
        finisher=finisher,
        start_time=start_time,
        finish_time=finish_time,
        task_time_seconds=task_time_seconds,
        raw_distance=raw_distance,
        marking_distance=marking_distance,
        handicapped_speed=handicapped_speed,
    )


# ── Helpers ────────────────────────────────────────────────────────────────

def _fixes_after_exit(fixes, tp: TaskPoint, radius_km: float, entry_fix):
    """Return fixes that come after the pilot has exited the start barrel."""
    entry_time = entry_fix.time
    outside = False
    result = []
    for fix in fixes:
        if fix.time < entry_time:
            continue
        d = distance_km_fix(fix.lat, fix.lon, tp.lat, tp.lon)
        if not outside and d > radius_km:
            outside = True
        if outside:
            result.append(fix)
    return result


def _fixes_from(fixes, from_fix):
    """Return fixes at or after from_fix.time."""
    t = from_fix.time
    return [f for f in fixes if f.time >= t]


def _furthest_along_task(remaining_fixes, task_points: list[TaskPoint], crossings):
    """
    For a landout, return the last valid fix — used as the landout point.
    """
    valid = [f for f in remaining_fixes if f.valid]
    return valid[-1] if valid else (remaining_fixes[-1] if remaining_fixes else None)
