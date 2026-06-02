from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Pilot, Task, TaskTurnpoint, Turnpoint, PilotBarrel
from ..schemas import TaskCreate, TaskUpdate, TaskOut, BarrelOut
from ..core.dht_calculator import (
    compute_declared_task_distance,
    compute_htd,
    compute_barrel_radius,
    TaskPoint,
)
from ..core.cup_parser import parse_cup_task

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def _build_task_points(task: Task) -> list[TaskPoint]:
    return [
        TaskPoint(
            name=ttp.turnpoint.name,
            lat=ttp.turnpoint.lat,
            lon=ttp.turnpoint.lon,
            order=ttp.order,
        )
        for ttp in sorted(task.turnpoints, key=lambda x: x.order)
    ]


def _recompute_task(task: Task, db: Session):
    """Recompute DTD, HTD, leg distances and PilotBarrel records."""
    pts = _build_task_points(task)
    if len(pts) < 2:
        return

    from ..core.geo import distance_km, Point as GeoPoint

    # Leg distances
    for i, ttp in enumerate(sorted(task.turnpoints, key=lambda x: x.order)):
        if i < len(pts) - 1:
            ttp.leg_distance = distance_km(
                GeoPoint(pts[i].lat, pts[i].lon),
                GeoPoint(pts[i + 1].lat, pts[i + 1].lon),
            )
        else:
            ttp.leg_distance = None

    dtd = compute_declared_task_distance(pts)
    task.declared_task_distance = dtd

    # HTD
    pilots = db.query(Pilot).all()
    if pilots:
        h_max = max(p.handicap for p in pilots)
        htd = compute_htd(dtd, h_max, task.wind_adjustment_factor)
        task.handicapped_task_distance = htd

        # Barrel records
        db.query(PilotBarrel).filter(PilotBarrel.task_id == task.id).delete()
        n_tps = len(pts) - 2  # exclude start and finish
        for pilot in pilots:
            radius = compute_barrel_radius(dtd, htd, pilot.handicap, n_tps)
            target_fd = htd * (100.0 / pilot.handicap)
            db.add(PilotBarrel(
                task_id=task.id,
                pilot_id=pilot.id,
                barrel_radius_km=radius,
                target_flown_distance=target_fd,
            ))

    db.commit()


@router.get("", response_model=list[TaskOut])
def list_tasks(db: Session = Depends(get_db)):
    return db.query(Task).order_by(Task.date.desc()).all()


@router.post("", response_model=TaskOut, status_code=201)
def create_task(payload: TaskCreate, db: Session = Depends(get_db)):
    task = Task(
        date=payload.date,
        wind_speed=payload.wind_speed,
        wind_direction=payload.wind_direction,
        wind_adjustment_factor=payload.wind_adjustment_factor,
        notes=payload.notes,
    )
    db.add(task)
    db.flush()  # get task.id

    for tp_in in sorted(payload.turnpoints, key=lambda x: x.order):
        # Upsert turnpoint by name+lat+lon
        tp = db.query(Turnpoint).filter(
            Turnpoint.name == tp_in.name
        ).first()
        if not tp:
            tp = Turnpoint(name=tp_in.name, lat=tp_in.lat, lon=tp_in.lon)
            db.add(tp)
            db.flush()

        db.add(TaskTurnpoint(
            task_id=task.id,
            turnpoint_id=tp.id,
            order=tp_in.order,
        ))

    db.commit()
    db.refresh(task)
    _recompute_task(task, db)
    db.refresh(task)
    return task


@router.post("/import-cup", response_model=TaskOut, status_code=201)
async def create_task_from_cup(
    file: UploadFile = File(...),
    wind_speed: float = 0.0,
    wind_direction: float = 0.0,
    wind_adjustment_factor: float = 1.0,
    db: Session = Depends(get_db),
):
    content = await file.read()
    cup_wps = parse_cup_task(content)
    if not cup_wps:
        raise HTTPException(status_code=400, detail="No task found in .cup file")

    from datetime import date as date_type
    task = Task(
        date=date_type.today(),
        wind_speed=wind_speed,
        wind_direction=wind_direction,
        wind_adjustment_factor=wind_adjustment_factor,
    )
    db.add(task)
    db.flush()

    for order, wp in enumerate(cup_wps):
        tp = db.query(Turnpoint).filter(Turnpoint.name == wp.name).first()
        if not tp:
            tp = Turnpoint(name=wp.name, lat=wp.lat, lon=wp.lon)
            db.add(tp)
            db.flush()
        db.add(TaskTurnpoint(task_id=task.id, turnpoint_id=tp.id, order=order))

    db.commit()
    db.refresh(task)
    _recompute_task(task, db)
    db.refresh(task)
    return task


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.put("/{task_id}", response_model=TaskOut)
def update_task(task_id: int, payload: TaskUpdate, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(task, field, value)
    db.commit()
    _recompute_task(task, db)
    db.refresh(task)
    return task


@router.get("/{task_id}/barrels", response_model=list[BarrelOut])
def get_barrels(task_id: int, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    barrels = task.barrels
    return [
        BarrelOut(
            pilot=b.pilot,
            barrel_radius_km=b.barrel_radius_km,
            target_flown_distance=b.target_flown_distance,
        )
        for b in sorted(barrels, key=lambda x: x.pilot.handicap, reverse=True)
    ]
