import math
from dataclasses import dataclass, field


def percentile(values: list[float], percent: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = (len(ordered) - 1) * percent
    low, high = math.floor(index), math.ceil(index)
    return round(ordered[low] + (ordered[high] - ordered[low]) * (index - low), 3)


@dataclass
class Window:
    latencies_ms: list[float] = field(default_factory=list)
    statuses: dict[str, int] = field(default_factory=dict)
    successes: int = 0
    failures: int = 0
    timeouts: int = 0
    connection_errors: int = 0

    def record(self, latency_ms: float, status: int | None = None,
               error: str | None = None) -> None:
        self.latencies_ms.append(latency_ms)
        if status is not None:
            key = str(status)
            self.statuses[key] = self.statuses.get(key, 0) + 1
        if status is not None and 200 <= status < 400:
            self.successes += 1
        else:
            self.failures += 1
        self.timeouts += int(error == "timeout")
        self.connection_errors += int(error == "connection")

    def summary(self, elapsed: float) -> dict:
        count = self.successes + self.failures
        return {
            "requests": count, "successes": self.successes, "failures": self.failures,
            "timeouts": self.timeouts, "connection_errors": self.connection_errors,
            "statuses": self.statuses, "rps": round(count / max(elapsed, 0.001), 3),
            "success_rate": round(self.successes / count, 4) if count else 0.0,
            "error_rate": round(self.failures / count, 4) if count else 0.0,
            "timeout_rate": round(self.timeouts / count, 4) if count else 0.0,
            "p50_ms": percentile(self.latencies_ms, .5),
            "p95_ms": percentile(self.latencies_ms, .95),
            "p99_ms": percentile(self.latencies_ms, .99),
        }
