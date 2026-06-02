"""
FAI 1000-point scoring for DHT tasks.

Pv = 1000 × (Vh / Vo)        — speed points (finishers)
Pd =  750 × (Dh / Do)        — distance points (all pilots)
SP = F × FCR × max(Pv, Pd)

MVP: F = 1.0, FCR = 1.0
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class ScoringInput:
    flight_id: int
    finisher: bool
    marking_distance: float   # km
    handicapped_speed: Optional[float]  # km/h, None for landouts


@dataclass
class ScoringOutput:
    flight_id: int
    day_score: float
    speed_points: Optional[float]
    distance_points: float


def score_day(flights: list[ScoringInput],
              f_factor: float = 1.0,
              fcr: float = 1.0) -> list[ScoringOutput]:
    """
    Compute day scores for all pilots.

    f_factor : maximum available points modifier (1.0 = full 1000 pts available)
    fcr      : completion factor (1.0 = no penalty for low finish rate)
    """
    if not flights:
        return []

    # Day distance = max marking distance
    do = max(fl.marking_distance for fl in flights) if flights else 0.0

    # Winner speed = max handicapped_speed among finishers
    finisher_speeds = [
        fl.handicapped_speed for fl in flights
        if fl.finisher and fl.handicapped_speed is not None
    ]
    vo = max(finisher_speeds) if finisher_speeds else None

    results = []
    for fl in flights:
        # Distance points
        pd = (750.0 * fl.marking_distance / do) if do > 0 else 0.0

        # Speed points (finishers only)
        pv = None
        if fl.finisher and fl.handicapped_speed is not None and vo:
            pv = 1000.0 * (fl.handicapped_speed / vo)

        raw = max(pv if pv is not None else 0.0, pd)
        day_score = f_factor * fcr * raw

        results.append(ScoringOutput(
            flight_id=fl.flight_id,
            day_score=round(day_score, 1),
            speed_points=round(pv, 1) if pv is not None else None,
            distance_points=round(pd, 1),
        ))

    return results
