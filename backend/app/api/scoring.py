import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Flight, Pilot, PilotBarrel, Task
from ..schemas import FlightAssign, FlightOut, ResultRow
from ..core import igc_parser
from ..core.dht_calculator import analyse_flight, TaskPoint
from ..core.scorer import score_day, ScoringInput

UPLOAD_DIR = Path(__file__).resolve().parents[3] / "igc_uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

router = APIRouter(prefix="/api/tasks/{task_id}", tags=["scoring"])


def _get_task_or_404(task_id: int, db: Session) -> Task:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


def _task_points(task: Task) -> list[TaskPoint]:
    return [
        TaskPoint(name=ttp.turnpoint.name, lat=ttp.turnpoint.lat,
                  lon=ttp.turnpoint.lon, order=ttp.order)
        for ttp in sorted(task.turnpoints, key=lambda x: x.order)
    ]


@router.post("/flights", response_model=list[FlightOut], status_code=201)
async def upload_flights(
    task_id: int,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    task = _get_task_or_404(task_id, db)
    created = []

    for upload in files:
        content = await upload.read()
        igc = igc_parser.parse(content)

        # Save file
        fname = f"{uuid.uuid4().hex}_{upload.filename}"
        fpath = UPLOAD_DIR / fname
        fpath.write_bytes(content)

        # Try auto-match by registration
        pilot = None
        if igc.registration:
            pilot = db.query(Pilot).filter(
                Pilot.registration.ilike(igc.registration.strip())
            ).first()

        flight = Flight(
            task_id=task_id,
            pilot_id=pilot.id if pilot else None,
            igc_filename=fname,
            igc_registration=igc.registration,
            igc_glider_type=igc.glider_type,
        )
        db.add(flight)
        db.commit()
        db.refresh(flight)
        created.append(flight)

    return created


@router.get("/flights", response_model=list[FlightOut])
def list_flights(task_id: int, db: Session = Depends(get_db)):
    _get_task_or_404(task_id, db)
    return (
        db.query(Flight)
        .filter(Flight.task_id == task_id)
        .all()
    )


@router.put("/flights/{flight_id}/assign", response_model=FlightOut)
def assign_pilot(
    task_id: int, flight_id: int,
    payload: FlightAssign,
    db: Session = Depends(get_db),
):
    flight = db.get(Flight, flight_id)
    if not flight or flight.task_id != task_id:
        raise HTTPException(status_code=404, detail="Flight not found")
    pilot = db.get(Pilot, payload.pilot_id)
    if not pilot:
        raise HTTPException(status_code=404, detail="Pilot not found")
    flight.pilot_id = pilot.id
    db.commit()
    db.refresh(flight)
    return flight


@router.post("/score", response_model=list[FlightOut])
def run_scoring(task_id: int, db: Session = Depends(get_db)):
    """
    Analyse all assigned IGC flights for this task and compute day scores.
    """
    task = _get_task_or_404(task_id, db)

    if task.declared_task_distance is None or task.handicapped_task_distance is None:
        raise HTTPException(
            status_code=400,
            detail="Task has no declared distance. Add turnpoints first."
        )

    pts = _task_points(task)
    dtd = task.declared_task_distance
    htd = task.handicapped_task_distance

    flights = (
        db.query(Flight)
        .filter(Flight.task_id == task_id, Flight.pilot_id != None)
        .all()
    )

    if not flights:
        raise HTTPException(status_code=400, detail="No assigned flights to score")

    # Barrel map: pilot_id → radius_km
    barrel_map: dict[int, float] = {
        b.pilot_id: b.barrel_radius_km
        for b in db.query(PilotBarrel).filter(PilotBarrel.task_id == task_id).all()
    }

    scoring_inputs = []
    for flight in flights:
        pilot_id = flight.pilot_id
        barrel_km = barrel_map.get(pilot_id, 0.5)  # default 0.5 km

        # Load and parse IGC
        fpath = UPLOAD_DIR / flight.igc_filename
        if not fpath.exists():
            continue
        igc = igc_parser.parse(fpath.read_bytes())

        result = analyse_flight(igc.fixes, pts, barrel_km, htd, dtd)

        flight.finisher = result.finisher
        flight.start_time = result.start_time
        flight.finish_time = result.finish_time
        flight.task_time_seconds = result.task_time_seconds
        flight.raw_distance = round(result.raw_distance, 3)
        flight.marking_distance = round(result.marking_distance, 3)
        flight.handicapped_speed = (
            round(result.handicapped_speed, 2)
            if result.handicapped_speed else None
        )

        scoring_inputs.append(ScoringInput(
            flight_id=flight.id,
            finisher=result.finisher,
            marking_distance=result.marking_distance,
            handicapped_speed=result.handicapped_speed,
        ))

    db.commit()

    # Score
    scored = score_day(scoring_inputs)
    score_map = {s.flight_id: s.day_score for s in scored}
    for flight in flights:
        if flight.id in score_map:
            flight.day_score = score_map[flight.id]
    db.commit()

    for f in flights:
        db.refresh(f)
    return flights


@router.get("/results", response_model=list[ResultRow])
def get_results(task_id: int, db: Session = Depends(get_db)):
    _get_task_or_404(task_id, db)
    flights = (
        db.query(Flight)
        .filter(Flight.task_id == task_id, Flight.pilot_id != None)
        .all()
    )

    rows = []
    for f in flights:
        if f.day_score is None or f.pilot is None:
            continue
        rows.append(ResultRow(
            position=0,  # assigned below after sort
            pilot_name=f.pilot.name,
            glider_type=f.pilot.glider_type,
            registration=f.pilot.registration,
            handicap=f.pilot.handicap,
            marking_distance=f.marking_distance,
            handicapped_speed=f.handicapped_speed,
            finisher=bool(f.finisher),
            day_score=f.day_score,
        ))

    rows.sort(key=lambda r: r.day_score, reverse=True)
    for i, row in enumerate(rows, start=1):
        row.position = i

    return rows


@router.get("/results/csv")
def get_results_csv(task_id: int, db: Session = Depends(get_db)):
    task = _get_task_or_404(task_id, db)
    rows = get_results(task_id=task_id, db=db)

    import io
    import csv

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "Position", "Pilot", "Glider", "Registration",
        "Handicap", "Marking Dist (km)", "Speed (km/h)", "Finisher", "Day Score"
    ])
    for r in rows:
        writer.writerow([
            r.position, r.pilot_name, r.glider_type, r.registration,
            r.handicap,
            f"{r.marking_distance:.1f}" if r.marking_distance else "",
            f"{r.handicapped_speed:.1f}" if r.handicapped_speed else "",
            "Yes" if r.finisher else "No",
            r.day_score,
        ])

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=results_task_{task_id}.csv"
        },
    )
