"""
Minimal IGC file parser.

Extracts:
- B-records  → GPS fixes (time, lat, lon, alt_baro, alt_gps, valid)
- H-records  → pilot name, glider type, glider registration
"""
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Optional


@dataclass
class Fix:
    time: datetime
    lat: float   # decimal degrees, positive = North
    lon: float   # decimal degrees, positive = East
    alt_baro: int
    alt_gps: int
    valid: bool  # A = valid, V = invalid


@dataclass
class IGCFile:
    fixes: list[Fix]
    pilot_name: Optional[str]
    glider_type: Optional[str]
    registration: Optional[str]
    flight_date: Optional[date]


def _parse_lat(raw: str) -> float:
    # DDMMmmmN  where mmm = decimal minutes × 1000
    deg = int(raw[0:2])
    minutes = int(raw[2:4]) + int(raw[4:7]) / 1000.0
    value = deg + minutes / 60.0
    if raw[7] == "S":
        value = -value
    return value


def _parse_lon(raw: str) -> float:
    # DDDMMmmmE
    deg = int(raw[0:3])
    minutes = int(raw[3:5]) + int(raw[5:8]) / 1000.0
    value = deg + minutes / 60.0
    if raw[8] == "W":
        value = -value
    return value


def parse(content: str | bytes) -> IGCFile:
    if isinstance(content, bytes):
        content = content.decode("latin-1")

    fixes: list[Fix] = []
    pilot_name: Optional[str] = None
    glider_type: Optional[str] = None
    registration: Optional[str] = None
    flight_date: Optional[date] = None

    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue

        record_type = line[0]

        if record_type == "H":
            # H records: HFDTE, HFPLT, HFGTY, HFGID, HFCID etc.
            upper = line.upper()
            if upper.startswith("HFDTE") or upper.startswith("HDDTE"):
                # HFDTE DDMMYY  or  HFDTEDATE:DDMMYY,NN
                raw = line[5:].strip().lstrip(":").split(",")[0].strip()
                if len(raw) >= 6:
                    try:
                        dd, mm, yy = int(raw[0:2]), int(raw[2:4]), int(raw[4:6])
                        year = 2000 + yy if yy < 70 else 1900 + yy
                        flight_date = date(year, mm, dd)
                    except ValueError:
                        pass
            elif "PLT" in upper or "PILOTINCHARGE" in upper:
                parts = line.split(":", 1)
                if len(parts) == 2:
                    pilot_name = parts[1].strip() or None
            elif "GTY" in upper or "GLIDERTYPE" in upper:
                parts = line.split(":", 1)
                if len(parts) == 2:
                    glider_type = parts[1].strip() or None
            elif "GID" in upper or "GLIDERID" in upper:
                parts = line.split(":", 1)
                if len(parts) == 2:
                    registration = parts[1].strip() or None
            elif "CID" in upper or "COMPETITIONID" in upper:
                # Use competition ID as registration fallback
                parts = line.split(":", 1)
                if len(parts) == 2 and not registration:
                    registration = parts[1].strip() or None

        elif record_type == "B" and len(line) >= 35:
            try:
                hh = int(line[1:3])
                mm_t = int(line[3:5])
                ss = int(line[5:7])
                lat = _parse_lat(line[7:15])
                lon = _parse_lon(line[15:24])
                valid = line[24] == "A"
                alt_baro = int(line[25:30])
                alt_gps = int(line[30:35])

                if flight_date:
                    t = datetime(
                        flight_date.year, flight_date.month, flight_date.day,
                        hh, mm_t, ss, tzinfo=timezone.utc
                    )
                else:
                    # No date yet; use epoch date as placeholder
                    t = datetime(1970, 1, 1, hh, mm_t, ss, tzinfo=timezone.utc)

                fixes.append(Fix(time=t, lat=lat, lon=lon,
                                 alt_baro=alt_baro, alt_gps=alt_gps, valid=valid))
            except (ValueError, IndexError):
                continue

    # Backfill date on fixes when date was found after some B records (rare)
    if flight_date:
        for fix in fixes:
            if fix.time.year == 1970:
                fix.time = fix.time.replace(
                    year=flight_date.year,
                    month=flight_date.month,
                    day=flight_date.day,
                )

    return IGCFile(
        fixes=fixes,
        pilot_name=pilot_name,
        glider_type=glider_type,
        registration=registration,
        flight_date=flight_date,
    )
