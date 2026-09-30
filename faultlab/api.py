import asyncio
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from faultlab.config import settings
from faultlab.db import get_db
from faultlab.models import (
    Experiment,
    ExperimentEvent,
    ExperimentReport,
    FaultConfiguration,
    MetricSnapshot,
    Phase,
    Service,
)
from faultlab.schemas import ExperimentCreate, ServiceCreate
from faultlab.state import add_event


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield


app = FastAPI(title="FaultLab API", lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def validation_error(_request, exc):  # type: ignore[no-untyped-def]
    return JSONResponse(status_code=422, content={"error": {"code": "validation_error",
            "message": "Invalid request", "details": [
                {"location": list(item["loc"]), "message": item["msg"], "type": item["type"]}
                for item in exc.errors()]}})


@app.exception_handler(HTTPException)
async def http_error(_request, exc):  # type: ignore[no-untyped-def]
    return JSONResponse(status_code=exc.status_code, content={"error": {
        "code": "request_error", "message": exc.detail}})


@app.exception_handler(SQLAlchemyError)
async def database_error(_request, _exc):  # type: ignore[no-untyped-def]
    return JSONResponse(status_code=503, content={"error": {
        "code": "database_unavailable", "message": "Database is unavailable"}})


def service_body(service: Service) -> dict:
    return {"id": service.id, "name": service.name, "kind": service.kind,
            "target_url": service.target_url, "created_at": service.created_at}


def experiment_body(exp: Experiment) -> dict:
    return {"id": exp.id, "service_id": exp.service_id, "phase": exp.phase,
            "fault": {"type": exp.fault.fault_type, **exp.fault.parameters},
            "requests_per_second": exp.requests_per_second, "concurrency": exp.concurrency,
            "baseline_seconds": exp.baseline_seconds, "fault_seconds": exp.fault_seconds,
            "recovery_seconds": exp.recovery_seconds, "timeout_seconds": exp.timeout_seconds,
            "cancel_requested": exp.cancel_requested, "fault_active": exp.fault_active,
            "error": exp.error, "created_at": exp.created_at, "updated_at": exp.updated_at}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ready"}


@app.get("/api/services")
def services(db: Session = Depends(get_db)):
    return [service_body(x) for x in db.scalars(select(Service).order_by(Service.name))]


@app.post("/api/services", status_code=201)
def create_service(body: ServiceCreate, db: Session = Depends(get_db)):
    if db.scalar(select(Service).where(Service.name == body.name)):
        raise HTTPException(409, "Service already registered")
    # Only this fixed demo service can be registered. URLs never come from API input.
    service = Service(name="gateway", target_url=settings.demo_gateway_url.rstrip("/") + "/checkout",
                      control_url=settings.demo_payment_url)
    db.add(service)
    db.commit()
    return service_body(service)


@app.get("/api/experiments")
def experiments(db: Session = Depends(get_db)):
    return [experiment_body(x) for x in db.scalars(
        select(Experiment).order_by(Experiment.created_at.desc()).limit(100))]


@app.post("/api/experiments", status_code=201)
def create_experiment(body: ExperimentCreate, db: Session = Depends(get_db)):
    if db.get(Service, body.service_id) is None:
        raise HTTPException(404, "Unknown registered service")
    experiment = Experiment(service_id=body.service_id,
                            requests_per_second=body.requests_per_second,
                            concurrency=body.concurrency,
                            baseline_seconds=body.baseline_seconds,
                            fault_seconds=body.fault_seconds,
                            recovery_seconds=body.recovery_seconds,
                            timeout_seconds=body.timeout_seconds)
    db.add(experiment)
    db.flush()
    parameters = body.fault.model_dump(exclude={"type"}, exclude_none=True)
    db.add(FaultConfiguration(experiment_id=experiment.id, fault_type=body.fault.type,
                              parameters=parameters))
    add_event(db, experiment, "experiment.created")
    db.commit()
    db.refresh(experiment)
    return experiment_body(experiment)


def get_experiment(db: Session, experiment_id: str) -> Experiment:
    exp = db.get(Experiment, experiment_id)
    if exp is None:
        raise HTTPException(404, "Experiment not found")
    return exp


@app.get("/api/experiments/{experiment_id}")
def experiment(experiment_id: str, db: Session = Depends(get_db)):
    return experiment_body(get_experiment(db, experiment_id))


@app.post("/api/experiments/{experiment_id}/start")
def start(experiment_id: str, db: Session = Depends(get_db)):
    exp = get_experiment(db, experiment_id)
    if exp.phase != Phase.CREATED.value or exp.owner:
        raise HTTPException(409, "Experiment cannot be started")
    conflict = db.scalar(select(Experiment.id).where(Experiment.service_id == exp.service_id,
        Experiment.id != exp.id, Experiment.phase.in_([
            Phase.BASELINE.value, Phase.FAULT_INJECTION.value, Phase.RECOVERY.value]) |
        ((Experiment.phase == Phase.CREATED.value) & (Experiment.owner == "queued"))))
    if conflict:
        raise HTTPException(409, "Service already has an active experiment")
    exp.owner = "queued"
    add_event(db, exp, "experiment.started")
    db.commit()
    return experiment_body(exp)


@app.post("/api/experiments/{experiment_id}/cancel")
def cancel(experiment_id: str, db: Session = Depends(get_db)):
    exp = get_experiment(db, experiment_id)
    if exp.phase in (Phase.COMPLETED.value, Phase.FAILED.value, Phase.CANCELLED.value):
        raise HTTPException(409, "Experiment is terminal")
    exp.cancel_requested = True
    if exp.phase == Phase.CREATED.value:
        from faultlab.state import transition
        transition(db, exp, Phase.CANCELLED, "experiment.cancelled")
    db.commit()
    return experiment_body(exp)


@app.get("/api/experiments/{experiment_id}/metrics")
def metrics(experiment_id: str, db: Session = Depends(get_db)):
    get_experiment(db, experiment_id)
    return [{"id": x.id, "phase": x.phase, "captured_at": x.captured_at, **x.metrics}
            for x in db.scalars(select(MetricSnapshot).where(
                MetricSnapshot.experiment_id == experiment_id).order_by(MetricSnapshot.captured_at))]


@app.get("/api/experiments/{experiment_id}/events")
def events(experiment_id: str, db: Session = Depends(get_db)):
    get_experiment(db, experiment_id)
    return [{"sequence": x.sequence, "name": x.name, "data": x.data,
             "created_at": x.created_at} for x in db.scalars(select(ExperimentEvent).where(
                 ExperimentEvent.experiment_id == experiment_id).order_by(ExperimentEvent.sequence))]


@app.get("/api/experiments/{experiment_id}/report")
def report(experiment_id: str, db: Session = Depends(get_db)):
    get_experiment(db, experiment_id)
    row = db.get(ExperimentReport, experiment_id)
    if row is None:
        raise HTTPException(409, "Report is available after completion")
    return row.body


@app.websocket("/ws/experiments/{experiment_id}")
async def live(websocket: WebSocket, experiment_id: str):
    from faultlab.db import Session as SessionFactory
    await websocket.accept()
    last_event = 0
    last_metric = None
    try:
        while True:
            with SessionFactory() as db:
                exp = db.get(Experiment, experiment_id)
                if exp is None:
                    await websocket.send_json({"type": "error", "message": "Experiment not found"})
                    return
                evs = list(db.scalars(select(ExperimentEvent).where(
                    ExperimentEvent.experiment_id == experiment_id,
                    ExperimentEvent.sequence > last_event).order_by(ExperimentEvent.sequence)))
                metric_rows = list(db.scalars(select(MetricSnapshot).where(
                    MetricSnapshot.experiment_id == experiment_id).order_by(
                    MetricSnapshot.captured_at.desc()).limit(1)))
                payload = experiment_body(exp)
            for event in evs:
                await websocket.send_json({"type": "event", "sequence": event.sequence,
                                           "name": event.name, "data": event.data})
                last_event = event.sequence
            if metric_rows and metric_rows[0].id != last_metric:
                row = metric_rows[0]
                await websocket.send_json({"type": "metric", "id": row.id,
                                           "phase": row.phase, **row.metrics})
                last_metric = row.id
            await websocket.send_json({"type": "state", "experiment": payload})
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        return
