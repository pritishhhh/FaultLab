import asyncio
import logging
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy.orm import Session

from faultlab.config import settings
from faultlab.db import Session as SessionFactory
from faultlab.models import Experiment, ExperimentReport, MetricSnapshot, Phase
from faultlab.scoring import score
from faultlab.state import add_event, transition
from faultlab.traffic import run_traffic

log = logging.getLogger(__name__)


def update_lease(db: Session, experiment: Experiment, owner: str) -> None:
    experiment.owner = owner
    experiment.lease_until = datetime.now(UTC) + timedelta(seconds=15)
    db.commit()


def cancelled(experiment_id: str) -> bool:
    with SessionFactory() as db:
        experiment = db.get(Experiment, experiment_id)
        return experiment is None or experiment.cancel_requested


def record_snapshot(experiment_id: str, phase: Phase, metrics: dict, owner: str) -> None:
    with SessionFactory() as db:
        exp = db.get(Experiment, experiment_id)
        if exp is None or exp.phase != phase.value:
            return
        db.add(MetricSnapshot(experiment_id=experiment_id, phase=phase.value, metrics=metrics))
        update_lease(db, exp, owner)


async def control(url: str, payload: dict) -> None:
    async with httpx.AsyncClient(timeout=3) as client:
        response = await client.put(url.rstrip("/") + "/internal/fault",
                                    json=payload, headers={"X-FaultLab-Token": settings.internal_token})
        response.raise_for_status()


async def execute(experiment_id: str, owner: str) -> None:
    fault_enabled = False
    phase_results: dict[str, dict] = {}
    with SessionFactory() as db:
        exp = db.get(Experiment, experiment_id)
        if exp is None or exp.phase != Phase.CREATED.value:
            return
        service = exp.service
        fault_type = exp.fault.fault_type
        parameters = exp.fault.parameters
        config = (exp.requests_per_second, exp.concurrency, exp.baseline_seconds,
                  exp.fault_seconds, exp.recovery_seconds, exp.timeout_seconds)
        target_url, control_url = service.target_url, service.control_url
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            ready = await client.get(target_url.rsplit("/", 1)[0] + "/ready")
            ready.raise_for_status()
        for phase, duration in ((Phase.BASELINE, config[2]),
                                (Phase.FAULT_INJECTION, config[3]),
                                (Phase.RECOVERY, config[4])):
            if cancelled(experiment_id):
                raise asyncio.CancelledError()
            if phase == Phase.FAULT_INJECTION:
                fault_enabled = True
                await control(control_url, {"type": fault_type, **parameters})
            if phase == Phase.RECOVERY:
                await control(control_url, {"type": "none"})
                fault_enabled = False
            with SessionFactory() as db:
                exp = db.get(Experiment, experiment_id)
                assert exp is not None
                transition(db, exp, phase, {Phase.BASELINE: "baseline.started",
                                            Phase.FAULT_INJECTION: "fault.started",
                                            Phase.RECOVERY: "recovery.started"}[phase])
                exp.fault_active = fault_enabled
                update_lease(db, exp, owner)
            async def snapshot(metrics: dict, current_phase: Phase = phase) -> None:
                record_snapshot(experiment_id, current_phase, metrics, owner)
            result = await run_traffic(target_url, config[0], config[1], duration,
                                       config[5], lambda: asyncio.sleep(0, result=cancelled(experiment_id)),
                                       snapshot)
            phase_results[phase.value] = result
            with SessionFactory() as db:
                exp = db.get(Experiment, experiment_id)
                assert exp is not None
                add_event(db, exp, {Phase.BASELINE: "baseline.completed",
                                    Phase.FAULT_INJECTION: "fault.completed",
                                    Phase.RECOVERY: "recovery.completed"}[phase], result)
                db.commit()
            if phase == Phase.BASELINE and (result["requests"] == 0 or result["success_rate"] < .9):
                raise RuntimeError("Baseline unhealthy: fewer than 90% of requests succeeded")
            if cancelled(experiment_id):
                raise asyncio.CancelledError()
        with SessionFactory() as db:
            exp = db.get(Experiment, experiment_id)
            assert exp is not None
            db.add(ExperimentReport(experiment_id=experiment_id,
                                    body=score(phase_results[Phase.BASELINE.value],
                                               phase_results[Phase.FAULT_INJECTION.value],
                                               phase_results[Phase.RECOVERY.value])))
            transition(db, exp, Phase.COMPLETED, "experiment.completed")
            exp.owner = None
            db.commit()
    except (Exception, asyncio.CancelledError) as exc:
        log.exception("experiment %s stopped", experiment_id)
        cleanup_error = None
        if fault_enabled:
            for attempt in range(3):
                try:
                    await control(control_url, {"type": "none"})
                    cleanup_error = None
                    break
                except Exception as cleanup_exc:
                    cleanup_error = str(cleanup_exc)
                    await asyncio.sleep(.5 * (attempt + 1))
            else:
                log.error("fault cleanup failed for %s: %s", experiment_id, cleanup_error)
        with SessionFactory() as db:
            exp = db.get(Experiment, experiment_id)
            if exp and exp.phase not in (Phase.COMPLETED.value, Phase.FAILED.value, Phase.CANCELLED.value):
                exp.fault_active = bool(cleanup_error)
                exp.error = (f"{type(exc).__name__}: {exc}" +
                             (f"; CLEANUP REQUIRED: {cleanup_error}" if cleanup_error else ""))[:400]
                transition(db, exp, Phase.CANCELLED if isinstance(exc, asyncio.CancelledError)
                           or exp.cancel_requested else Phase.FAILED,
                           "experiment.cancelled" if isinstance(exc, asyncio.CancelledError)
                           or exp.cancel_requested else "experiment.failed")
                exp.owner = None
                db.commit()
