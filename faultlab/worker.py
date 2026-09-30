import asyncio
import logging
import os
import socket
from datetime import UTC, datetime

from sqlalchemy import select

from faultlab.db import Session
from faultlab.engine import control, execute
from faultlab.models import Experiment, Phase
from faultlab.state import transition

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
OWNER = f"{socket.gethostname()}:{os.getpid()}"


async def run() -> None:
    while True:
        try:
            cleanup_urls = []
            with Session() as db:
                stale = list(db.scalars(select(Experiment).where(
                    Experiment.phase.in_([Phase.BASELINE.value, Phase.FAULT_INJECTION.value,
                                          Phase.RECOVERY.value]),
                    Experiment.lease_until < datetime.now(UTC))))
                for exp in stale:
                    exp.error = "Worker lease expired; fault cleanup requires inspection"
                    if exp.fault_active:
                        cleanup_urls.append((exp.id, exp.service.control_url))
                    transition(db, exp, Phase.FAILED, "experiment.failed")
                if stale:
                    db.commit()
                queued = db.scalar(select(Experiment).where(
                    Experiment.phase == Phase.CREATED.value, Experiment.owner == "queued",
                    Experiment.cancel_requested.is_(False)).order_by(Experiment.created_at)
                    .with_for_update(skip_locked=True).limit(1))
                experiment_id = queued.id if queued else None
                if queued:
                    queued.owner = OWNER
                    db.commit()
            for stale_id, url in cleanup_urls:
                try:
                    await control(url, {"type": "none"})
                    with Session() as db:
                        stale_exp = db.get(Experiment, stale_id)
                        assert stale_exp is not None
                        stale_exp.fault_active = False
                        stale_exp.error = "Worker lease expired; managed fault cleaned up"
                        db.commit()
                except Exception:
                    logging.exception("orphan fault cleanup failed for %s", stale_id)
            if experiment_id:
                await execute(experiment_id, OWNER)
            else:
                await asyncio.sleep(1)
        except Exception:
            logging.exception("worker cycle failed")
            await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(run())
