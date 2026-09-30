import json
import logging
import uuid

from fastapi import Request

logging.basicConfig(level=logging.INFO, format="%(message)s")


def request_id(request: Request) -> str:
    return request.headers.get("X-Request-ID") or str(uuid.uuid4())


def log(service: str, rid: str, event: str, **fields) -> None:
    logging.info(json.dumps({"service": service, "request_id": rid,
                             "event": event, **fields}))
