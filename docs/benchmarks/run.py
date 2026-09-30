import argparse
import json
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def call(base: str, path: str, data: dict | None = None):
    body = json.dumps(data).encode() if data is not None else None
    req = Request(base + path, data=body, method="POST" if body else "GET",
                  headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=10) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--service-id", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    scenarios = [
        ("latency_100", {"type": "latency", "latency_ms": 100}),
        ("latency_300", {"type": "latency", "latency_ms": 300}),
        ("latency_500", {"type": "latency", "latency_ms": 500}),
        ("errors_5pct", {"type": "http_errors", "error_rate": .05}),
        ("errors_10pct", {"type": "http_errors", "error_rate": .10}),
        ("dependency_outage", {"type": "dependency_unavailable"}),
        ("cpu_pressure", {"type": "cpu_pressure"}),
    ]
    results = {"measured_at_epoch": time.time(), "scenarios": {}}
    for name, fault in scenarios:
        exp = call(args.base_url, "/api/experiments", {
            "service_id": args.service_id, "requests_per_second": 10, "concurrency": 5,
            "baseline_seconds": 10, "fault_seconds": 10, "recovery_seconds": 10,
            "timeout_seconds": 1, "fault": fault})
        call(args.base_url, f"/api/experiments/{exp['id']}/start", {})
        while True:
            state = call(args.base_url, f"/api/experiments/{exp['id']}")
            if state["phase"] in ("COMPLETED", "FAILED", "CANCELLED"):
                break
            time.sleep(2)
        results["scenarios"][name] = {"experiment_id": exp["id"], "phase": state["phase"],
                                      "report": call(args.base_url, f"/api/experiments/{exp['id']}/report")
                                      if state["phase"] == "COMPLETED" else None}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, indent=2))
    print(output)


if __name__ == "__main__":
    main()
