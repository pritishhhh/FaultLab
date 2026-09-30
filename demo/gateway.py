import os

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from demo.common import log, request_id

app = FastAPI(title="FaultLab gateway")
ORDER_URL = os.getenv("ORDER_URL", "http://localhost:8002")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready():
    return {"status": "ready"}


@app.post("/checkout")
async def checkout(request: Request):
    rid = request_id(request)
    log("gateway", rid, "checkout.started")
    try:
        async with httpx.AsyncClient(timeout=1.2) as client:
            response = await client.post(ORDER_URL + "/orders", json={"item": "test"},
                                         headers={"X-Request-ID": rid})
        log("gateway", rid, "checkout.completed", status=response.status_code)
        if response.status_code >= 400:
            return JSONResponse(status_code=response.status_code,
                                content={"request_id": rid, "error": "order_failed"})
        return {"request_id": rid, "upstream_status": response.status_code,
                "result": response.json()}
    except httpx.TimeoutException:
        log("gateway", rid, "checkout.timeout")
        raise HTTPException(504, "Order timeout") from None
    except httpx.RequestError:
        log("gateway", rid, "checkout.unavailable")
        raise HTTPException(503, "Order unavailable") from None
