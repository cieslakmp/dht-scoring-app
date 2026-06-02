"""
Parse SeeYou .cup waypoint files to extract task turnpoints.

.cup format (CSV):
  name,code,country,lat,lon,elev,style,rwdir,rwlen,freq,desc
  Latitude: DDMMmmN  Longitude: DDDMMmmE  (no decimal in minutes field)

Task section starts with: "-----Related Tasks-----"
  taskname,options,tps...
"""
from __future__ import annotations
import csv
import io
from dataclasses import dataclass
from typing import Optional


@dataclass
class CupWaypoint:
    name: str
    lat: float
    lon: float


def _parse_cup_lat(raw: str) -> float:
    raw = raw.strip().strip('"')
    hemi = raw[-1]
    raw = raw[:-1]
    deg = int(raw[:2])
    minutes = float(raw[2:]) / 100.0  # DDMMmm → minutes = MMmm/100
    # Actually: DDMMmmN format where mm is hundredths of a minute
    # e.g. 5145.300N = 51 degrees 45.300 minutes
    deg = int(raw[:2])
    minutes = float(raw[2:])
    value = deg + minutes / 60.0
    if hemi == "S":
        value = -value
    return value


def _parse_cup_lon(raw: str) -> float:
    raw = raw.strip().strip('"')
    hemi = raw[-1]
    raw = raw[:-1]
    deg = int(raw[:3])
    minutes = float(raw[3:])
    value = deg + minutes / 60.0
    if hemi == "W":
        value = -value
    return value


def parse_cup_waypoints(content: str | bytes) -> list[CupWaypoint]:
    """Parse all waypoints from a .cup file."""
    if isinstance(content, bytes):
        content = content.decode("latin-1")

    waypoints: list[CupWaypoint] = []
    reader = csv.reader(io.StringIO(content))

    for row in reader:
        if not row or row[0].startswith("-----") or row[0].lower() == "name":
            continue
        if len(row) < 5:
            continue
        try:
            name = row[0].strip().strip('"')
            lat = _parse_cup_lat(row[3])
            lon = _parse_cup_lon(row[4])
            waypoints.append(CupWaypoint(name=name, lat=lat, lon=lon))
        except (ValueError, IndexError):
            continue

    return waypoints


def parse_cup_task(content: str | bytes) -> Optional[list[CupWaypoint]]:
    """
    Extract the first task from a .cup file.
    Returns ordered list of CupWaypoints (start, TPs, finish) or None.
    """
    if isinstance(content, bytes):
        content = content.decode("latin-1")

    # First, build a name→waypoint index
    waypoints = {wp.name: wp for wp in parse_cup_waypoints(content)}

    # Find task section
    lines = content.splitlines()
    in_task = False
    for line in lines:
        stripped = line.strip()
        if "-----Related Tasks-----" in stripped or stripped.lower().startswith("-----related"):
            in_task = True
            continue
        if not in_task:
            continue
        if not stripped or stripped.startswith("-----"):
            continue

        # Task line: name,"", tp1_name, tp2_name, ...
        try:
            parts = next(csv.reader([stripped]))
        except StopIteration:
            continue

        if len(parts) < 3:
            continue

        # First two fields are task name and options; rest are TP names
        tp_names = [p.strip().strip('"') for p in parts[2:] if p.strip()]
        task_wps = []
        for name in tp_names:
            if name in waypoints:
                task_wps.append(waypoints[name])
        if len(task_wps) >= 2:
            return task_wps

    return None
