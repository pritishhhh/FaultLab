import asyncio
import time
import uuid
from collections.abc import Awaitable, Callable

import httpx

from faultlab.metrics import Window


async def run_traffic(url: str, rps: int, concurrency: int, duration: int,
                      timeout: float, stop: Callable[[], Awaitable[bool]],
                      snapshot: Callable[[dict], Awaitable[None]]) -> dict:
    semaphore = asyncio.Semaphore(concurrency)
    window = Window()
    total = Window()
    started = time.monotonic()
    next_snapshot = started + 1
    tasks: set[asyncio.Task] = set()

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
        async def one() -> None:
            try:
                began = time.monotonic()
                status = None
                error = None
                try:
                    response = await client.post(url, json={"item": "test"},
                                                 headers={"X-Request-ID": str(uuid.uuid4())})
                    status = response.status_code
                except httpx.TimeoutException:
                    error = "timeout"
                except httpx.RequestError:
                    error = "connection"
                latency = (time.monotonic() - began) * 1000
                window.record(latency, status, error)
                total.record(latency, status, error)
            finally:
                semaphore.release()

        index = 0
        try:
            while time.monotonic() - started < duration:
                if await stop():
                    break
                due = started + index / rps
                await asyncio.sleep(max(0, due - time.monotonic()))
                if time.monotonic() - started >= duration:
                    break
                await semaphore.acquire()
                if time.monotonic() - started >= duration or await stop():
                    semaphore.release()
                    break
                task = asyncio.create_task(one())
                tasks.add(task)
                task.add_done_callback(tasks.discard)
                index += 1
                if time.monotonic() >= next_snapshot:
                    await snapshot(window.summary(max(time.monotonic() - (next_snapshot - 1), .001)))
                    window = Window()
                    next_snapshot = time.monotonic() + 1
            if tasks:
                await asyncio.gather(*tasks)
            if window.successes + window.failures:
                await snapshot(window.summary(max(time.monotonic() - (next_snapshot - 1), .001)))
        finally:
            for task in tasks:
                task.cancel()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
    return total.summary(max(time.monotonic() - started, .001))
