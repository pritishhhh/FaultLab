import asyncio
import hashlib
import os
import time
from typing import Literal

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from demo.common import log, request_id

app = FastAPI(title="FaultLab payment")
TOKEN = os.getenv("INTERNAL_TOKEN", "local-development-only")
fault: dict = {"type": "none"}


class Fault(BaseModel):
    type: Literal["none", "latency", "http_errors", "timeout", "dependency_unavailable", "cpu_pressure"]
    latency_ms: int | None = Field(default=None, ge=0, le=1000)
    error_rate: float | None = Field(default=None, ge=0, le=1)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready():
    return {"status": "ready"}


@app.put("/internal/fault")
def set_fault(value: Fault, x_faultlab_token: str | None = Header(default=None)):
    if x_faultlab_token != TOKEN:
        raise HTTPException(403, "Forbidden")
    fault.clear()
    fault.update(value.model_dump(exclude_none=True))
    return {"active": fault["type"] != "none", "fault": fault}


@app.post("/payments")
async def payments(request: Request):
    rid = request_id(request)
    active = fault.copy()
    kind = active["type"]
    log("payment", rid, "payment.started", fault=kind)
    if kind in ("latency", "timeout"):
        await asyncio.sleep(active.get("latency_ms", 1000) / 1000)
    elif kind == "cpu_pressure":
        # Bounded synthetic CPU work within the managed demo process.
        until = time.monotonic() + .05
        while time.monotonic() < until:
            hashlib.sha256(rid.encode()).digest()
    elif kind == "dependency_unavailable":
        return JSONResponse(status_code=503, content={"request_id": rid, "error": "dependency_unavailable"})
    elif kind == "http_errors":
        sample = int(hashlib.sha256(rid.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
        if sample < active.get("error_rate", 0):
            return JSONResponse(status_code=503, content={"request_id": rid, "error": "injected_error"})
    log("payment", rid, "payment.completed")
    return {"request_id": rid, "status": "paid"}
