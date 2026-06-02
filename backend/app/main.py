from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import engine, Base
from .api import pilots, tasks, scoring

Base.metadata.create_all(bind=engine)

app = FastAPI(title="DHT Scoring", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pilots.router)
app.include_router(tasks.router)
app.include_router(scoring.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
