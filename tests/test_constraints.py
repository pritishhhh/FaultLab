import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from faultlab.db import Base
from faultlab.models import Experiment, FaultConfiguration, Service


@pytest.fixture
def db():
    engine = create_engine("sqlite://")

    @event.listens_for(engine, "connect")
    def foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def test_service_unique_constraint(db: Session):
    db.add(Service(name="gateway", target_url="http://test", control_url="http://test"))
    db.commit()
    db.add(Service(name="gateway", target_url="http://test", control_url="http://test"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_experiment_service_foreign_key(db: Session):
    db.add(Experiment(service_id="does-not-exist", requests_per_second=1, concurrency=1,
                      baseline_seconds=1, fault_seconds=1, recovery_seconds=1,
                      timeout_seconds=1))
    with pytest.raises(IntegrityError):
        db.commit()


def test_fault_configuration_unique_per_experiment(db: Session):
    service = Service(name="gateway", target_url="http://test", control_url="http://test")
    db.add(service)
    db.flush()
    exp = Experiment(service_id=service.id, requests_per_second=1, concurrency=1,
                     baseline_seconds=1, fault_seconds=1, recovery_seconds=1,
                     timeout_seconds=1)
    db.add(exp)
    db.flush()
    db.add(FaultConfiguration(experiment_id=exp.id, fault_type="latency", parameters={"latency_ms": 100}))
    db.commit()
    db.add(FaultConfiguration(experiment_id=exp.id, fault_type="latency", parameters={"latency_ms": 200}))
    with pytest.raises(IntegrityError):
        db.commit()
