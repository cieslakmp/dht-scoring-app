import csv
import io
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Pilot
from ..schemas import PilotCreate, PilotUpdate, PilotOut

router = APIRouter(prefix="/api/pilots", tags=["pilots"])


@router.get("", response_model=list[PilotOut])
def list_pilots(db: Session = Depends(get_db)):
    return db.query(Pilot).order_by(Pilot.name).all()


@router.post("", response_model=PilotOut, status_code=201)
def create_pilot(payload: PilotCreate, db: Session = Depends(get_db)):
    pilot = Pilot(**payload.model_dump())
    db.add(pilot)
    db.commit()
    db.refresh(pilot)
    return pilot


@router.put("/{pilot_id}", response_model=PilotOut)
def update_pilot(pilot_id: int, payload: PilotUpdate, db: Session = Depends(get_db)):
    pilot = db.get(Pilot, pilot_id)
    if not pilot:
        raise HTTPException(status_code=404, detail="Pilot not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(pilot, field, value)
    db.commit()
    db.refresh(pilot)
    return pilot


@router.delete("/{pilot_id}", status_code=204)
def delete_pilot(pilot_id: int, db: Session = Depends(get_db)):
    pilot = db.get(Pilot, pilot_id)
    if not pilot:
        raise HTTPException(status_code=404, detail="Pilot not found")
    db.delete(pilot)
    db.commit()


@router.post("/import", response_model=list[PilotOut], status_code=201)
async def import_pilots_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Import pilots from CSV.
    Expected columns (in any order, case-insensitive headers):
      name, glider_type, registration, handicap
    """
    content = await file.read()
    text = content.decode("utf-8-sig")  # handle BOM
    reader = csv.DictReader(io.StringIO(text))

    # Normalise header names
    if reader.fieldnames is None:
        raise HTTPException(status_code=400, detail="Empty or invalid CSV file")

    headers = {h.strip().lower(): h for h in reader.fieldnames}
    required = {"name", "glider_type", "registration", "handicap"}
    missing = required - set(headers.keys())
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"CSV missing columns: {', '.join(missing)}. "
                   f"Found: {', '.join(headers.keys())}"
        )

    created = []
    for row in reader:
        normed = {k.strip().lower(): v.strip() for k, v in row.items()}
        try:
            handicap = float(normed["handicap"])
        except ValueError:
            continue  # skip bad rows

        # Upsert by registration
        existing = db.query(Pilot).filter(
            Pilot.registration == normed["registration"]
        ).first()
        if existing:
            existing.name = normed["name"]
            existing.glider_type = normed["glider_type"]
            existing.handicap = handicap
            db.commit()
            db.refresh(existing)
            created.append(existing)
        else:
            pilot = Pilot(
                name=normed["name"],
                glider_type=normed["glider_type"],
                registration=normed["registration"],
                handicap=handicap,
            )
            db.add(pilot)
            db.commit()
            db.refresh(pilot)
            created.append(pilot)

    return created
