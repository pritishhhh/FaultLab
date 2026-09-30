import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from faultlab.db import Base


def now() -> datetime:
    return datetime.now(UTC)


def uid() -> str:
    return str(uuid.uuid4())


class Phase(str, enum.Enum):
    CREATED = "CREATED"
    BASELINE = "BASELINE"
    FAULT_INJECTION = "FAULT_INJECTION"
    RECOVERY = "RECOVERY"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class Service(Base):
    __tablename__ = "services"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    kind: Mapped[str] = mapped_column(String(20), default="demo")
    target_url: Mapped[str] = mapped_column(String(300))
    control_url: Mapped[str] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Experiment(Base):
    __tablename__ = "experiments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    service_id: Mapped[str] = mapped_column(ForeignKey("services.id"))
    phase: Mapped[str] = mapped_column(String(24), default=Phase.CREATED.value)
    requests_per_second: Mapped[int] = mapped_column(Integer)
    concurrency: Mapped[int] = mapped_column(Integer)
    baseline_seconds: Mapped[int] = mapped_column(Integer)
    fault_seconds: Mapped[int] = mapped_column(Integer)
    recovery_seconds: Mapped[int] = mapped_column(Integer)
    timeout_seconds: Mapped[float] = mapped_column(Float)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    fault_active: Mapped[bool] = mapped_column(Boolean, default=False)
    owner: Mapped[str | None] = mapped_column(String(80), nullable=True)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(String(400), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    service: Mapped[Service] = relationship()
    fault: Mapped["FaultConfiguration"] = relationship(back_populates="experiment", uselist=False)


class FaultConfiguration(Base):
    __tablename__ = "fault_configurations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.id", ondelete="CASCADE"), unique=True)
    fault_type: Mapped[str] = mapped_column(String(30))
    parameters: Mapped[dict] = mapped_column(JSON)
    experiment: Mapped[Experiment] = relationship(back_populates="fault")


class MetricSnapshot(Base):
    __tablename__ = "metric_snapshots"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.id", ondelete="CASCADE"))
    phase: Mapped[str] = mapped_column(String(24))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    metrics: Mapped[dict] = mapped_column(JSON)


class ExperimentEvent(Base):
    __tablename__ = "experiment_events"
    __table_args__ = (UniqueConstraint("experiment_id", "sequence"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.id", ondelete="CASCADE"))
    sequence: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(80))
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ExperimentReport(Base):
    __tablename__ = "experiment_reports"
    experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.id", ondelete="CASCADE"), primary_key=True)
    body: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
