import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from faultlab.db import Base
from faultlab.models import Experiment, ExperimentEvent, Phase, Service
from faultlab.state import transition


def test_state_transitions_and_event_order():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        service = Service(name="gateway", target_url="http://test/checkout", control_url="http://test")
        db.add(service)
        db.flush()
        exp = Experiment(service_id=service.id, requests_per_second=1, concurrency=1,
                         baseline_seconds=1, fault_seconds=1, recovery_seconds=1,
                         timeout_seconds=1)
        db.add(exp)
        db.flush()
        with pytest.raises(ValueError):
            transition(db, exp, Phase.RECOVERY, "illegal")
        transition(db, exp, Phase.BASELINE, "baseline.started")
        transition(db, exp, Phase.FAULT_INJECTION, "fault.started")
        transition(db, exp, Phase.RECOVERY, "recovery.started")
        transition(db, exp, Phase.COMPLETED, "experiment.completed")
        with pytest.raises(ValueError):
            transition(db, exp, Phase.BASELINE, "illegal")
        assert [x.name for x in db.query(ExperimentEvent).order_by(ExperimentEvent.sequence)] == [
            "baseline.started", "fault.started", "recovery.started", "experiment.completed"]
