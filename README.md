# DHT Scoring App

A web application for scoring **Distance Handicapped Tasks (DHT)** in gliding competitions. It reads IGC flight logs directly, computes true flown distances per glider handicap, and applies the FAI 1000-point scoring formula — replacing the manual SeeYou post-processing workflow.

## Features

- **Pilot management** — maintain a pilot/glider/handicap list; import from CSV
- **Task definition** — define turnpoints manually or import a SeeYou `.cup` file; set wind conditions and wind adjustment factor
- **Barrel calculator** — automatically computes per-pilot TP barrel radii and target flown distances from the declared task and handicap list
- **Task map** — Leaflet map showing the task route with colour-coded barrel rings per handicap class
- **IGC upload** — drag-and-drop one or many `.igc` files; auto-matched to pilots by registration number extracted from the flight recorder header
- **Scoring engine** — analyses each IGC trace to detect start/TP/finish cylinder crossings, computes raw and marking distances, then applies the FAI 1000-point formula
- **Results** — sortable day results table with positions, handicapped speeds, marking distances, and day scores; CSV export

## Scoring model

The app implements the **BGA Distance Handicapped Task** rules (BGA Competition Organisers' Guide 2014 supplement) combined with the **FAI 1000-point formula**:

| Term | Formula |
|---|---|
| Handicapped Task Distance (HTD) | `DTD × (100 / H_max) × WAF` |
| Barrel radius per pilot | `0.5 + (DTD − target_FD) / (2 × N_TP)` km |
| Marking Distance | `raw_distance × (HTD / DTD)`, capped at DTD |
| Speed points | `Pv = 1000 × (Vh / Vo)` |
| Distance points | `Pd = 750 × (Dh / Do)` |
| Day score | `SP = F × FCR × max(Pv, Pd)` |

> **DTD** = Declared Task Distance · **H_max** = highest handicap in field · **WAF** = wind adjustment factor · **Vh** = pilot handicapped speed · **Vo** = winner speed · **Dh** = marking distance · **Do** = day max marking distance

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3.10+, FastAPI, SQLAlchemy, SQLite |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS v4 |
| Maps | Leaflet + react-leaflet |
| IGC parsing | Custom parser (no external dependency) |
| Geodesic math | geopy (Vincenty) |

## Project structure

```
dht-scoring-app/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app entry point
│   │   ├── models.py            # SQLAlchemy ORM models
│   │   ├── schemas.py           # Pydantic request/response schemas
│   │   ├── api/
│   │   │   ├── pilots.py        # Pilot CRUD + CSV import
│   │   │   ├── tasks.py         # Task definition + .cup import
│   │   │   └── scoring.py       # IGC upload, scoring, results
│   │   └── core/
│   │       ├── igc_parser.py    # IGC B/H-record parser
│   │       ├── geo.py           # Geodesic distance + cylinder detection
│   │       ├── dht_calculator.py # HTD, barrel radii, flight analysis
│   │       ├── scorer.py        # FAI 1000-pt formula
│   │       └── cup_parser.py    # SeeYou .cup file parser
│   └── requirements.txt
└── frontend/
    └── src/
        ├── pages/
        │   ├── PilotsPage.tsx
        │   ├── TaskPage.tsx
        │   ├── FlightsPage.tsx
        │   └── ResultsPage.tsx
        ├── components/
        │   └── TaskMap.tsx       # Leaflet task map with barrel rings
        └── services/api.ts       # Typed Axios API client
```

## Getting started

### Prerequisites

- Python 3.10+
- Node.js 18+

### Backend

```bash
cd backend
python -m venv .venv

# Windows
.\.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.  
Interactive docs: `http://localhost:8000/docs`

The SQLite database (`dht_scoring.db`) is created automatically on first run.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The app will be available at `http://localhost:5173`. All `/api` requests are proxied to the backend automatically.

## Usage workflow

1. **Pilots** — Add pilots manually or import a CSV file with columns `name,glider_type,registration,handicap`
2. **Task** — Enter the day's turnpoints (name, latitude, longitude) in order (start → TPs → finish), or import a `.cup` file. Set wind speed, direction, and wind adjustment factor. The app calculates HTD and barrel sizes for every pilot.
3. **Flights** — Upload IGC files. Each file is automatically matched to a pilot by registration number. Unmatched files can be assigned manually. Click **Run Scoring** to analyse all flights.
4. **Results** — View the day results table. Download as CSV for reporting.

### CSV pilot import format

```csv
name,glider_type,registration,handicap
Alice Smith,Discus-2c,ABC,100
Bob Jones,LS8-18,XYZ,108
Carol White,ASW-27,DEF,94
```

Handicap values follow the BGA/FAI handicap list (e.g. 100 = standard, 110 = high-performance).

## API reference

Full OpenAPI documentation is available at `http://localhost:8000/docs` when the backend is running.

Key endpoints:

| Method | Path | Description |
|---|---|---|
| `GET/POST` | `/api/pilots` | List / create pilots |
| `POST` | `/api/pilots/import` | Import CSV |
| `POST` | `/api/tasks` | Create task with turnpoints |
| `POST` | `/api/tasks/import-cup` | Import from `.cup` file |
| `GET` | `/api/tasks/{id}/barrels` | Per-pilot barrel sizes |
| `POST` | `/api/tasks/{id}/flights` | Upload IGC files |
| `POST` | `/api/tasks/{id}/score` | Run scoring engine |
| `GET` | `/api/tasks/{id}/results` | Day results |
| `GET` | `/api/tasks/{id}/results/csv` | Download results as CSV |

## Limitations and known issues

- **Wind adjustment factor** is entered manually by the scorer. An automated WAF calculator (from wind vector and task bearing) is not yet implemented.
- **F and FCR modifiers** (minimum task time and completion factor) are set to 1.0 in the MVP.
- The barrel radius formula uses a uniform approximation across all TPs. For tasks with very acute turn angles, a geometry-aware calculation would be more precise.
- Scoring is single-day only; multi-day cumulative totals are not yet supported.

## References

- [BGA DHT Distance Calculations (2014)](https://www.gliding.co.uk) — source document for DTD/HTD/Marking Distance formulas
- [FAI Sporting Code Section 3 Annex A](https://www.fai.org/igc-documents) — FAI 1000-point scoring formula
- [IGC file format specification](https://www.fai.org/igc-documents)
