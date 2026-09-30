import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_ready(url: str, processes: list[subprocess.Popen], timeout: float = 15) -> None:
    until = time.monotonic() + timeout
    while time.monotonic() < until:
        for process in processes:
            if process.poll() is not None:
                raise AssertionError(f"Service exited with status {process.returncode}")
        try:
            if httpx.get(url, timeout=.5).status_code == 200:
                return
        except httpx.RequestError:
            pass
        time.sleep(.1)
    raise AssertionError(f"Service did not become ready: {url}")


@pytest.mark.integration
def test_real_local_lifecycle(tmp_path: Path):
    root = Path(__file__).resolve().parents[2]
    ports = {name: free_port() for name in ("payment", "order", "gateway", "api")}
    env = os.environ.copy()
    env.update({"DATABASE_URL": f"sqlite:///{(tmp_path / 'integration.db').as_posix()}",
                "INTERNAL_TOKEN": "integration-test-token",
                "PAYMENT_URL": f"http://127.0.0.1:{ports['payment']}",
                "ORDER_URL": f"http://127.0.0.1:{ports['order']}",
                "DEMO_PAYMENT_URL": f"http://127.0.0.1:{ports['payment']}",
                "DEMO_GATEWAY_URL": f"http://127.0.0.1:{ports['gateway']}"})
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"],
                   cwd=root, env=env, check=True, capture_output=True)
    processes: list[subprocess.Popen] = []
    try:
        for name, module in (("payment", "demo.payment"), ("order", "demo.order"),
                             ("gateway", "demo.gateway"), ("api", "faultlab.api")):
            process = subprocess.Popen([sys.executable, "-m", "uvicorn", f"{module}:app",
                                        "--host", "127.0.0.1", "--port", str(ports[name]),
                                        "--log-level", "warning"], cwd=root, env=env,
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            processes.append(process)
            wait_ready(f"http://127.0.0.1:{ports[name]}/ready", processes)
        worker = subprocess.Popen([sys.executable, "-m", "faultlab.worker"],
                                  cwd=root, env=env, stdout=subprocess.DEVNULL,
                                  stderr=subprocess.DEVNULL)
        processes.append(worker)
        base = f"http://127.0.0.1:{ports['api']}"
        request_id = "integration-request-id"
        response = httpx.post(f"http://127.0.0.1:{ports['gateway']}/checkout",
                              json={"item": "test"}, headers={"X-Request-ID": request_id})
        assert response.status_code == 200
        assert response.json()["request_id"] == request_id
        assert response.json()["result"]["payment"]["request_id"] == request_id
        service = httpx.post(base + "/api/services", json={"name": "gateway"}).json()
        created = httpx.post(base + "/api/experiments", json={
            "service_id": service["id"], "requests_per_second": 2, "concurrency": 2,
            "baseline_seconds": 3, "fault_seconds": 3, "recovery_seconds": 3,
            "timeout_seconds": 5,
            "fault": {"type": "latency", "latency_ms": 500}})
        assert created.status_code == 201, created.text
        exp_id = created.json()["id"]
        assert httpx.post(base + f"/api/experiments/{exp_id}/start").status_code == 200
        until = time.monotonic() + 30
        while time.monotonic() < until:
            current = httpx.get(base + f"/api/experiments/{exp_id}").json()
            if current["phase"] in ("COMPLETED", "FAILED", "CANCELLED"):
                break
            time.sleep(.3)
        assert current["phase"] == "COMPLETED", current
        report = httpx.get(base + f"/api/experiments/{exp_id}/report").json()
        assert report["phases"]["FAULT_INJECTION"]["p95_ms"] > report["phases"]["BASELINE"]["p95_ms"], report
        events = httpx.get(base + f"/api/experiments/{exp_id}/events").json()
        names = [event["name"] for event in events]
        assert names == ["experiment.created", "experiment.started", "baseline.started",
                         "baseline.completed", "fault.started", "fault.completed",
                         "recovery.started", "recovery.completed", "experiment.completed"]
    finally:
        for process in reversed(processes):
            process.terminate()
        for process in reversed(processes):
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
