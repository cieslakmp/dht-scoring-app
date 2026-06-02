from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel


# ── Pilot ──────────────────────────────────────────────────────────────────

class PilotBase(BaseModel):
    name: str
    glider_type: str
    registration: str
    handicap: float


class PilotCreate(PilotBase):
    pass


class PilotUpdate(BaseModel):
    name: Optional[str] = None
    glider_type: Optional[str] = None
    registration: Optional[str] = None
    handicap: Optional[float] = None


class PilotOut(PilotBase):
    id: int

    model_config = {"from_attributes": True}


# ── Turnpoint ──────────────────────────────────────────────────────────────

class TurnpointBase(BaseModel):
    name: str
    lat: float
    lon: float


class TurnpointCreate(TurnpointBase):
    pass


class TurnpointOut(TurnpointBase):
    id: int

    model_config = {"from_attributes": True}


# ── Task ───────────────────────────────────────────────────────────────────

class TaskTurnpointIn(BaseModel):
    name: str
    lat: float
    lon: float
    order: int  # 0=start, 1..N=TPs, N+1=finish


class TaskCreate(BaseModel):
    date: date
    wind_speed: float = 0.0
    wind_direction: float = 0.0
    wind_adjustment_factor: float = 1.0
    notes: Optional[str] = None
    turnpoints: list[TaskTurnpointIn]


class TaskUpdate(BaseModel):
    wind_speed: Optional[float] = None
    wind_direction: Optional[float] = None
    wind_adjustment_factor: Optional[float] = None
    notes: Optional[str] = None


class TaskTurnpointOut(BaseModel):
    order: int
    turnpoint: TurnpointOut
    leg_distance: Optional[float]

    model_config = {"from_attributes": True}


class TaskOut(BaseModel):
    id: int
    date: date
    declared_task_distance: Optional[float]
    wind_speed: float
    wind_direction: float
    wind_adjustment_factor: float
    handicapped_task_distance: Optional[float]
    notes: Optional[str]
    turnpoints: list[TaskTurnpointOut]

    model_config = {"from_attributes": True}


# ── Barrel ─────────────────────────────────────────────────────────────────

class BarrelOut(BaseModel):
    pilot: PilotOut
    barrel_radius_km: float
    target_flown_distance: float

    model_config = {"from_attributes": True}


# ── Flight ─────────────────────────────────────────────────────────────────

class FlightAssign(BaseModel):
    pilot_id: int


class FlightOut(BaseModel):
    id: int
    task_id: int
    pilot_id: Optional[int]
    igc_filename: str
    igc_registration: Optional[str]
    igc_glider_type: Optional[str]
    start_time: Optional[datetime]
    finish_time: Optional[datetime]
    task_time_seconds: Optional[int]
    raw_distance: Optional[float]
    marking_distance: Optional[float]
    finisher: Optional[bool]
    handicapped_speed: Optional[float]
    day_score: Optional[float]
    pilot: Optional[PilotOut]

    model_config = {"from_attributes": True}


# ── Result row ─────────────────────────────────────────────────────────────

class ResultRow(BaseModel):
    position: int
    pilot_name: str
    glider_type: str
    registration: str
    handicap: float
    marking_distance: Optional[float]
    handicapped_speed: Optional[float]
    finisher: bool
    day_score: float
