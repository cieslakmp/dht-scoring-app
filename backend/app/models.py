from sqlalchemy import Boolean, Column, Date, Float, ForeignKey, Integer, String, DateTime
from sqlalchemy.orm import relationship
from .database import Base


class Pilot(Base):
    __tablename__ = "pilots"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    glider_type = Column(String, nullable=False)
    registration = Column(String, nullable=False, index=True)
    handicap = Column(Float, nullable=False)

    flights = relationship("Flight", back_populates="pilot")
    barrels = relationship("PilotBarrel", back_populates="pilot")


class Turnpoint(Base):
    __tablename__ = "turnpoints"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)

    task_entries = relationship("TaskTurnpoint", back_populates="turnpoint")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False)
    declared_task_distance = Column(Float, nullable=True)  # km, computed from TPs
    wind_speed = Column(Float, nullable=False, default=0.0)  # km/h
    wind_direction = Column(Float, nullable=False, default=0.0)  # degrees True
    wind_adjustment_factor = Column(Float, nullable=False, default=1.0)
    handicapped_task_distance = Column(Float, nullable=True)  # computed
    notes = Column(String, nullable=True)

    turnpoints = relationship("TaskTurnpoint", back_populates="task", order_by="TaskTurnpoint.order")
    flights = relationship("Flight", back_populates="task")
    barrels = relationship("PilotBarrel", back_populates="task")


class TaskTurnpoint(Base):
    __tablename__ = "task_turnpoints"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    turnpoint_id = Column(Integer, ForeignKey("turnpoints.id"), nullable=False)
    order = Column(Integer, nullable=False)  # 0=start, 1..N=TPs, N+1=finish
    leg_distance = Column(Float, nullable=True)  # km to next TP

    task = relationship("Task", back_populates="turnpoints")
    turnpoint = relationship("Turnpoint", back_populates="task_entries")


class PilotBarrel(Base):
    __tablename__ = "pilot_barrels"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    pilot_id = Column(Integer, ForeignKey("pilots.id"), nullable=False)
    barrel_radius_km = Column(Float, nullable=False)
    target_flown_distance = Column(Float, nullable=False)

    task = relationship("Task", back_populates="barrels")
    pilot = relationship("Pilot", back_populates="barrels")


class Flight(Base):
    __tablename__ = "flights"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    pilot_id = Column(Integer, ForeignKey("pilots.id"), nullable=True)
    igc_filename = Column(String, nullable=False)
    igc_registration = Column(String, nullable=True)  # extracted from IGC H-record
    igc_glider_type = Column(String, nullable=True)
    start_time = Column(DateTime, nullable=True)
    finish_time = Column(DateTime, nullable=True)
    task_time_seconds = Column(Integer, nullable=True)
    raw_distance = Column(Float, nullable=True)    # km from IGC trace
    marking_distance = Column(Float, nullable=True)  # raw × (HTD/DTD)
    finisher = Column(Boolean, nullable=True)
    handicapped_speed = Column(Float, nullable=True)  # km/h
    day_score = Column(Float, nullable=True)

    task = relationship("Task", back_populates="flights")
    pilot = relationship("Pilot", back_populates="flights")
