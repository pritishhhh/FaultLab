import os

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from demo.common import log, request_id

app = FastAPI(title="FaultLab order")
PAYMENT_URL = os.getenv("PAYMENT_URL", "http://localhost:8003")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready():
    return {"status": "ready"}


@app.post("/orders")
async def orders(request: Request):
    rid = request_id(request)
    log("order", rid, "order.started")
    try:
        async with httpx.AsyncClient(timeout=.8) as client:
            response = await client.post(PAYMENT_URL + "/payments", json={"amount": 1},
                                         headers={"X-Request-ID": rid})
        log("order", rid, "order.completed", status=response.status_code)
        if response.status_code >= 400:
            return JSONResponse(status_code=response.status_code,
                                content={"request_id": rid, "error": "payment_failed"})
        return {"request_id": rid, "status": "accepted", "payment": response.json()}
    except httpx.TimeoutException:
        log("order", rid, "order.timeout")
        raise HTTPException(504, "Payment timeout") from None
    except httpx.RequestError:
        log("order", rid, "order.unavailable")
        raise HTTPException(503, "Payment unavailable") from None
