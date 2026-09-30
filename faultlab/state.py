from sqlalchemy import func, select
from sqlalchemy.orm import Session

from faultlab.models import Experiment, ExperimentEvent, Phase

ALLOWED = {
    Phase.CREATED: {Phase.BASELINE, Phase.CANCELLED, Phase.FAILED},
    Phase.BASELINE: {Phase.FAULT_INJECTION, Phase.CANCELLED, Phase.FAILED},
    Phase.FAULT_INJECTION: {Phase.RECOVERY, Phase.CANCELLED, Phase.FAILED},
    Phase.RECOVERY: {Phase.COMPLETED, Phase.CANCELLED, Phase.FAILED},
    Phase.COMPLETED: set(), Phase.CANCELLED: set(), Phase.FAILED: set(),
}


def add_event(db: Session, experiment: Experiment, name: str, data: dict | None = None) -> None:
    last = db.scalar(select(func.max(ExperimentEvent.sequence)).where(
        ExperimentEvent.experiment_id == experiment.id)) or 0
    db.add(ExperimentEvent(experiment_id=experiment.id, sequence=last + 1,
                           name=name, data=data or {}))


def transition(db: Session, experiment: Experiment, target: Phase, event: str) -> None:
    current = Phase(experiment.phase)
    if target not in ALLOWED[current]:
        raise ValueError(f"Illegal transition {current.value} -> {target.value}")
    experiment.phase = target.value
    add_event(db, experiment, event)
    db.flush()
