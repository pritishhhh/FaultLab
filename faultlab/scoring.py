from faultlab.models import Phase


def score(baseline: dict, fault: dict, recovery: dict) -> dict:
    baseline_p95 = max(float(baseline.get("p95_ms", 0)), 1.0)
    fault_p95 = float(fault.get("p95_ms", 0))
    recovery_p95 = float(recovery.get("p95_ms", 0))
    baseline_errors = float(baseline.get("error_rate", 0))
    fault_errors = float(fault.get("error_rate", 0))
    recovery_errors = float(recovery.get("error_rate", 0))
    recovered = (recovery.get("requests", 0) > 0
                 and recovery_p95 <= max(1.5 * baseline_p95, baseline_p95 + 30)
                 and recovery_errors <= max(baseline_errors + .05, .05))
    availability = max(0.0, 1 - fault_errors)
    latency = min(1.0, baseline_p95 / max(fault_p95, baseline_p95))
    error = max(0.0, 1 - max(0.0, fault_errors - baseline_errors))
    recovery_component = 1.0 if recovered else 0.0
    total = round(100 * (.35 * availability + .20 * latency + .20 * error
                         + .25 * recovery_component))
    classifications = []
    if fault_p95 > 1.5 * baseline_p95:
        classifications.append("LATENCY_DEGRADATION")
    if fault_errors > baseline_errors + .05:
        classifications.append("ERROR_AMPLIFICATION")
    if float(fault.get("timeout_rate", 0)) > float(baseline.get("timeout_rate", 0)) + .05:
        classifications.append("TIMEOUT_INCREASE")
    if fault.get("rps", 0) < .7 * baseline.get("rps", 0):
        classifications.append("THROUGHPUT_DEGRADATION")
    if not recovered:
        classifications.append("RECOVERY_FAILURE")
    return {"score": min(100, max(0, total)), "recovered": recovered,
            "latency_amplification": round(fault_p95 / baseline_p95, 3),
            "error_amplification": (round(fault_errors / baseline_errors, 3)
                                    if baseline_errors > 0 else None),
            "classifications": classifications,
            "phases": {Phase.BASELINE.value: baseline,
                       Phase.FAULT_INJECTION.value: fault,
                       Phase.RECOVERY.value: recovery}}
