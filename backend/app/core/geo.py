"""
Geodesic utilities for task analysis.
"""
import math
from typing import Optional
from dataclasses import dataclass

from geopy.distance import geodesic


@dataclass
class Point:
    lat: float
    lon: float


def distance_km(a: Point, b: Point) -> float:
    """Geodesic distance in km between two points."""
    return geodesic((a.lat, a.lon), (b.lat, b.lon)).km


def distance_km_fix(fix_lat: float, fix_lon: float, tp_lat: float, tp_lon: float) -> float:
    return geodesic((fix_lat, fix_lon), (tp_lat, tp_lon)).km


def _interpolate(lat1, lon1, lat2, lon2, frac: float):
    """Linear interpolation between two geographic points."""
    return lat1 + frac * (lat2 - lat1), lon1 + frac * (lon2 - lon1)


def first_cylinder_entry(fixes, tp_lat: float, tp_lon: float, radius_km: float):
    """
    Return the interpolated (lat, lon, time) of the first moment the track
    enters a cylinder of `radius_km` centred on (tp_lat, tp_lon).

    Returns None if the cylinder is never entered.
    Each fix must have .lat, .lon, .time attributes.
    """
    prev = None
    for fix in fixes:
        d = distance_km_fix(fix.lat, fix.lon, tp_lat, tp_lon)
        if d <= radius_km:
            if prev is None:
                return fix
            # interpolate back to barrel edge
            d_prev = distance_km_fix(prev.lat, prev.lon, tp_lat, tp_lon)
            if d_prev <= radius_km:
                return fix  # already inside
            frac = (d_prev - radius_km) / (d_prev - d) if (d_prev - d) > 0 else 0.0
            frac = max(0.0, min(1.0, frac))
            ilat, ilon = _interpolate(prev.lat, prev.lon, fix.lat, fix.lon, frac)
            dt_sec = (fix.time - prev.time).total_seconds()
            itime = prev.time.replace(
                second=int(prev.time.second + frac * dt_sec)
            ) if dt_sec > 0 else fix.time

            class _InterpFix:
                lat = ilat
                lon = ilon
                time = itime

            return _InterpFix()
        prev = fix
    return None


def crosses_line(fixes, line_lat: float, line_lon: float,
                 bearing_deg: float, half_width_km: float = 1.0):
    """
    Detect crossing of a finish line perpendicular to `bearing_deg`.
    Returns the fix where the crossing is first detected, or None.
    This is a simplified version: treat the finish as a cylinder of half_width_km.
    For a proper line crossing, use the cylinder finish geometry.
    """
    return first_cylinder_entry(fixes, line_lat, line_lon, half_width_km)
