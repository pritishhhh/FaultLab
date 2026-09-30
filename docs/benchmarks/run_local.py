"""Start a disposable local stack, run measured scenarios, and stop it."""
import argparse
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx


def port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--window-seconds", type=int, default=10)
    parser.add_argument("--rps", type=int, default=10)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    ports = {name: port() for name in ("payment", "order", "gateway", "api")}
    processes: list[subprocess.Popen] = []
    with tempfile.TemporaryDirectory(prefix="faultlab-benchmark-") as temp_dir:
        env = os.environ.copy()
        env.update({"DATABASE_URL": f"sqlite:///{(Path(temp_dir) / 'benchmark.db').as_posix()}",
                    "INTERNAL_TOKEN": "benchmark-local-only",
                    "PAYMENT_URL": f"http://127.0.0.1:{ports['payment']}",
                    "ORDER_URL": f"http://127.0.0.1:{ports['order']}",
                    "DEMO_PAYMENT_URL": f"http://127.0.0.1:{ports['payment']}",
                    "DEMO_GATEWAY_URL": f"http://127.0.0.1:{ports['gateway']}"})
        subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"],
                       cwd=root, env=env, check=True)
        try:
            for name, module in (("payment", "demo.payment"), ("order", "demo.order"),
                                 ("gateway", "demo.gateway"), ("api", "faultlab.api")):
                processes.append(subprocess.Popen([
                    sys.executable, "-m", "uvicorn", f"{module}:app", "--host", "127.0.0.1",
                    "--port", str(ports[name]), "--log-level", "warning"],
                    cwd=root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
                until = time.monotonic() + 20
                while time.monotonic() < until:
                    if processes[-1].poll() is not None:
                        raise RuntimeError(f"{name} exited during startup")
                    try:
                        if httpx.get(f"http://127.0.0.1:{ports[name]}/ready", timeout=.5).status_code == 200:
                            break
                    except httpx.RequestError:
                        pass
                    time.sleep(.1)
                else:
                    raise RuntimeError(f"{name} did not become ready")
            processes.append(subprocess.Popen([sys.executable, "-m", "faultlab.worker"],
                             cwd=root, env=env, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL))
            base = f"http://127.0.0.1:{ports['api']}"
            service = httpx.post(base + "/api/services", json={"name": "gateway"}).json()
            subprocess.run([sys.executable, str(root / "docs" / "benchmarks" / "run.py"),
                            "--base-url", base, "--service-id", service["id"],
                            "--output", args.output, "--window-seconds", str(args.window_seconds),
                            "--rps", str(args.rps)], cwd=root, env=env, check=True)
        finally:
            for process in reversed(processes):
                process.terminate()
            for process in reversed(processes):
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()


if __name__ == "__main__":
    main()
